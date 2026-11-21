# Rafiki Car Hire 2.0

*Drive Zanzibar with Confidence.*

This is the car rental and booking management platform for Rafiki Car Hire in Zanzibar, Tanzania. It has four parts:

- a public website for guests;
- a booking system where Django calculates every price on the server;
- PDF invoices and receipts;
- a staff dashboard for managing bookings, payments, invoices and the fleet.

| Layer | Technology |
|---|---|
| Backend / API | Python 3.13+, Django 6.1, Django REST Framework |
| Database | PostgreSQL 16+ (required: it enforces the overlap rules) |
| Background jobs | Celery and Redis (emails, retries, hold expiry, document purge, payment reconciliation) |
| Frontend | React 19, Vite 7, Tailwind CSS 4, TanStack Query |
| PDFs | ReportLab (server-side) |
| Payments | Manual payments verified by staff, plus Pesapal API 3.0 (pluggable gateway layer) |
| Storage | Local disk in development; S3-compatible public and **private** buckets in production |

---

## 1. Project structure

```
car/
├── backend/
│   ├── config/                 settings/{base,dev,prod,test}.py, urls.py, celery.py
│   ├── apps/
│   │   ├── core/               SiteSettings, AuditLog, Sequence (numbering), contact, testimonials,
│   │   │                       file validation, PDF toolkit, error envelope, throttles
│   │   ├── accounts/           AdminUser (custom user, roles), auth API, permissions
│   │   ├── customers/          Customer (guests; no passwords)
│   │   ├── vehicles/           Vehicle, VehicleImage, VehicleFeature, public + admin APIs
│   │   ├── bookings/           Booking, extras, flight, documents, history, notes, access tokens,
│   │   │                       pricing engine, availability, retention policy, WhatsApp links
│   │   ├── invoices/           Invoice, InvoiceItem, numbering, PDF, revisions
│   │   ├── payments/           Payment, Refund, Receipt, gateways/ (base, pesapal, registry)
│   │   ├── notifications/      NotificationLog, email queue + retries
│   │   └── reports/            dashboard metrics, reports, CSV/PDF export
│   ├── templates/emails/       branded HTML email templates
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/         Layout, VehicleCard, ui/ primitives
│   │   ├── lib/                api client, guest session, formatting, SEO, hooks
│   │   └── pages/public|admin/
│   ├── vercel.json / netlify.toml
│   └── .env.example
├── docs/DATABASE.md            schema documentation
├── docs/API.md                 endpoint reference
└── render.yaml                 Render blueprint (API, worker, Postgres, Redis)
```

---

## 2. Local installation

### Prerequisites
- Python 3.13 or later, and Node.js 20 or later
- PostgreSQL 16 or later, running locally
- Redis (optional locally: set `CELERY_TASK_ALWAYS_EAGER=True` to run tasks inline)

### Backend
```bash
cd backend
python -m venv ../venv && ../venv/Scripts/activate      # macOS/Linux: source ../venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                                     # then edit (see §3)
# Local dev defaults to SQLite (DATABASE_URL=sqlite:///db.sqlite3) — no database server needed.
# To develop on PostgreSQL instead: createdb -U postgres rafiki, and set DATABASE_URL=postgres://...
python manage.py migrate                                 # also seeds the core fees and site settings
python manage.py createsuperuser                         # your first ADMIN user
python manage.py runserver
```

### Frontend
```bash
cd frontend
npm install
npm run dev            # http://localhost:5173; /api is proxied to :8000
```

- **Staff dashboard:** http://localhost:5173/admin
- **Django admin (secondary back-office):** http://localhost:8000/django-admin/

### Background jobs
```bash
celery -A config worker -B --loglevel=info      # with Redis
# Without Redis/beat, run these on a schedule (cron / Task Scheduler):
python manage.py process_notifications          # send queued emails, retry failed ones
python manage.py release_holds                  # expire lapsed reservation holds
python manage.py purge_documents                # delete identity documents past retention
python manage.py check_setup                    # list what the owner still has to configure
```

---

## 3. Environment configuration

All secrets are read from environment variables. `backend/.env.example` documents every variable. The important ones:

| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | Long random string. Different in each environment. |
| `DATABASE_URL` | `postgres://user:pass@host:5432/rafiki` |
| `REDIS_URL` | Celery broker, cache and rate-limit store |
| `FRONTEND_URL`, `BACKEND_URL` | Used in email links, payment callbacks and the webhook URL |
| `EMAIL_*`, `DEFAULT_FROM_EMAIL` | SMTP relay (Brevo, Resend, Postmark and others) |
| `OWNER_NOTIFICATION_EMAIL` | Fallback address for owner alerts. Can also be set in the dashboard. |
| `PESAPAL_*` | Gateway credentials (§7) |
| `USE_S3`, `AWS_*` | Public and private buckets. **Required in production.** |
| `BOOKING_HOLD_HOURS` | How long a pending booking blocks the car (default 24) |
| `BOOKING_TURNAROUND_HOURS` | Cleaning buffer between rentals (default 2) |
| `DOCUMENT_RETENTION_DAYS` | Days after the rental ends before passports and licences are erased (default 30) |

Never commit `.env`. It is listed in `.gitignore`.

---

## 4. How the core rules are implemented

### Pricing (`apps/bookings/pricing.py`)
- Every fee is a row in **ExtraService**, which staff can edit under Settings → Prices & services. The migration seeds the business price list:

  | Service | Price | How it's charged |
  |---|---:|---|
  | `outside_zone_delivery` | $25 | Per leg (pickup and return charged separately) |
  | `baby_seat` | $60 | Per seat, per booking (not per day) |
  | `driving_permit` | $25 | Once per booking |

  Zanzibar Airport and Zanzibar Town are always free.
- The rental charge is `daily_rate × rental_days`. Each started 24-hour period counts as one day.
- All arithmetic uses `Decimal`. Totals sent by the browser are ignored (a test covers this).
- A full `pricing_breakdown` is saved on every booking. Later price changes never alter existing bookings. When staff modify a booking, the originally agreed daily rate is kept unless the car itself changes.

### Availability (`apps/bookings/availability.py`)
- A submitted booking creates a **hold** (`blocks_inventory=True`, `hold_expires_at`).
- Double booking is prevented at two levels:
  1. **In the application:** the vehicle row is locked with `SELECT … FOR UPDATE` and conflicts are checked.
  2. **In the database:** a PostgreSQL `EXCLUSION` constraint (`btree_gist`, added by migration `bookings.0003`) forbids two blocking bookings for the same vehicle whose time ranges overlap, including the turnaround buffer. SQLite (local development only) relies on check 1. Production settings refuse to start unless the database is PostgreSQL.
- Rejected, cancelled, expired and completed bookings release the car. Lapsed holds expire automatically (Celery beat, plus a check on every new booking). Bookings with any verified payment are never expired automatically.

### Invoices (`apps/invoices`)
- An invoice is issued in the same transaction as the booking: status `PENDING_CONFIRMATION`, payment status `UNPAID`.
- Numbers look like `RCI-2026-000001`. A row-locked `Sequence` table issues them, so concurrent requests can't get duplicates (a threaded test covers this).
- Issued invoices are never edited. A financial change creates a revision (`RCI-2026-000001-R1`): the original is marked `SUPERSEDED` and kept, and the new one records `supersedes` and a reason.
- The PDF is rendered from an immutable `snapshot` and kept in private storage. If the file is ever lost, it is re-rendered on download.
- **Receipts** (`RCR-2026-000001`) are separate documents, issued only for verified payments.

### Payments (`apps/payments`)
- A booking can have many payments, which allows deposits and part-payments. Only `VERIFIED` payments count towards `amount_paid`.
- A payment can become `VERIFIED` in only three ways:
  1. the gateway's server-to-server status API confirms it;
  2. a staff member verifies it explicitly and ticks a confirmation box;
  3. a staff member records money received in person, with a description.

  A database `CHECK` constraint rejects any verified payment that has no verification timestamp and source.
- Webhooks are treated as hints only. The server always re-queries Pesapal before changing anything, so a forged notification can't mark a booking as paid. The amount, currency and merchant reference must all match.
- Refunds are tracked per payment (recorded manually, or requested through the gateway API).

### Guest access and security
- Guests have no accounts. After booking they receive a random 256-bit token, and only its SHA-256 hash is stored. Tokens expire and can be revoked, and each email gets its own token.
- The token travels in the URL **fragment** (`/booking/manage#ref=…&token=…`), which browsers never send to servers. API calls send it in the `X-Booking-Token` header. A booking reference on its own never grants access.
- Passports, licences, payment proofs, invoices and receipts are stored in **private** storage. No URL points to them. They are streamed only through permission-checked views, and every document view is written to the audit log. Uploads are checked for size, extension **and magic bytes** (file signature), and saved under random names.
- Identity documents are securely erased (overwritten, then deleted) once the retention period has passed.
- Staff sign in with session cookies and CSRF protection. Passwords must be at least 12 characters and pass Django's validators. Logins are rate-limited.
- Roles:
  - **ADMIN:** everything.
  - **MANAGER:** operations plus finance, documents and reports.
  - **STAFF:** booking operations. Cannot see revenue figures or identity documents, and cannot verify payments.
- Per-endpoint rate limits apply to booking creation, quotes, guest access, payments, the contact form and login.

---

## 5. Testing

```bash
cd backend
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test apps
```

**Result: 78 tests, all passing on PostgreSQL 18.** They cover:
- pricing for every fee rule;
- booking creation and validation;
- conflicting bookings, the turnaround buffer and the database-level overlap constraint;
- hold expiry;
- guest token security: no token, wrong token, expired token, another booking's token;
- the driving permit's document requirement, disguised or oversized uploads, document access by role, and retention purging;
- invoice contents, numbering under concurrency, revisions, regeneration of a missing PDF, and admin resend;
- email failure: the failure is recorded, retried with backoff, and eventually abandoned;
- manual payment submission, verification, rejection, audit trail and receipts;
- partial payments, offline payments and refunds;
- Pesapal: checkout, webhook verification, forged webhooks, amount and reference mismatches, failed payments, duplicate notifications;
- admin permissions and roles, the CSRF-protected login, and booking status transitions.

A live run against the real server also exercised the whole flow: booking options, then a booking with an outside-zone pickup and 2 baby seats ($365.00; the fake `grand_total` of $1.00 sent by the client was ignored), invoice PDF download with the token (200), the same request without the token (404), and a double booking (409).

Frontend: `npm run build` completes without errors.

---

## 6. Deployment

The free Render setup is **frontend on Vercel** and one free Render web service running the Django API plus best-effort Celery tasks. Neon provides PostgreSQL, and an existing Render Key Value instance supplies Redis (`render.yaml` does not create another one). Free services can sleep or restart, so this setup is for demos and testing rather than reliable background processing.

1. **Object storage.** Create two buckets (Cloudflare R2, S3, Backblaze B2 or similar):
   - `rafiki-public` for vehicle photos and the logo, with public read access;
   - `rafiki-private` for documents, invoices and receipts. **Block all public access** on this one.
2. **Render.** Choose New → Blueprint and select this repository and its production branch. The Blueprint uses the existing Neon database and Render Key Value instance; it creates neither datastore. During first setup, provide `DATABASE_URL` (Neon's direct URL), `DATABASE_URL_POOLED` (Neon's pooled URL), and `REDIS_URL` (the existing Key Value connection URL). Both database URLs must have TLS enabled. Also provide the AWS-compatible storage credentials/endpoint and SMTP, owner email, and Pesapal settings when prompted. If the Blueprint already exists, Render ignores newly added `sync: false` entries during later syncs, so add those values manually under the service's Environment settings. On free Render, migrations run at service startup; the API and Celery processes share one web service.
3. **Frontend.** Import the `frontend/` folder into Vercel, set the root directory to `frontend`, build command to `npm run build`, output directory to `dist`, and set `VITE_SITE_URL=https://www.rafikicarhire.com`. Leave `VITE_API_BASE` empty: the existing rewrite sends `/api` to `https://api.rafikicarhire.com`, preserving same-origin session and CSRF behavior. Do not put database or backend secrets in any `VITE_*` variable.
4. **DNS and HTTPS.** Add `api.rafikicarhire.com` to the Render web service and point its DNS record to Render. Point the `www` and apex site domains to Vercel. Both providers issue TLS certificates automatically. Django enforces HTTPS, HSTS and secure cookies in production.
5. **Admin and Pesapal setup.** Free Render does not provide shell access. Create the Django admin user from a trusted local environment using the Neon `DATABASE_URL`, or temporarily upgrade the service to run the management command. After the API domain is live, run `python manage.py register_pesapal_ipn`, set the resulting value as `PESAPAL_IPN_ID`, and redeploy the API.
6. **Backups.** Configure Neon backups/restore for the production branch and turn on versioning for the private object-storage bucket. The old Render database, if one was created by an earlier Blueprint, is no longer used and is left untouched by this configuration.
7. **Monitoring.** Set `SENTRY_DSN`. The health check is at `/api/v1/health/`.

---

## 7. What the owner still needs to configure

Run `python manage.py check_setup` at any time to see what's still missing.

| Item | Where |
|---|---|
| PostgreSQL password for local development | `backend/.env` → `DATABASE_URL` |
| First admin account | `python manage.py createsuperuser` |
| Business email, phone, **WhatsApp number**, address | Dashboard → Settings → Business |
| Owner notification email | Dashboard → Settings → Business |
| **Manual payment instructions** (bank and mobile-money details) | Dashboard → Settings → Business |
| Logo and homepage hero photo | Dashboard → Settings → Business |
| Vehicles, real prices and **real photos** | Dashboard → Vehicles |
| Genuine guest reviews (optional) | Dashboard → Settings → Reviews |
| SMTP account (Brevo or Resend: verify your sending domain, then set SPF and DKIM records) | environment `EMAIL_*` |
| Pesapal merchant account: sandbox keys first, then live keys after Pesapal approves the merchant account | environment `PESAPAL_*` |
| Private and public storage buckets | environment `AWS_*` |
| Domain name: update `robots.txt`, `vercel.json`/`netlify.toml` and `VITE_SITE_URL` | frontend |
| Open Graph share image (`frontend/public/og-image.jpg`, 1200×630) | frontend |
| **Legal review** of the Terms and Privacy pages (deposit, age, insurance and cancellation policy) | `src/pages/public/InfoPages.jsx` |
