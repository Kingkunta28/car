# API reference (`/api/v1/`)

All responses are JSON unless noted.

Errors always use this shape:

```json
{"error": {"code": "validation_error", "message": "Pickup date: Pickup must be at least 3 hours from now.", "details": {"pickup_date": ["…"]}}}
```

Common status codes: `400` validation or business rule, `401`/`403` authentication or permission, `404` not found (also returned for invalid guest credentials, so bookings can't be enumerated), `409` vehicle already reserved, `429` rate limited.

Lists are paginated: `?page=`, `?page_size=` (maximum 100) → `{count, next, previous, results}`.

## Guest authentication
Guest endpoints need **both** of these headers:
```
X-Booking-Reference: RCH-7K3Q9PX
X-Booking-Token: <token from the booking response or email link>
```
A reference alone is never enough.

## Public

| Method | Path | Description |
|---|---|---|
| GET | `/health/` | Liveness and database check |
| GET | `/site/` | Public business info (name, contacts, WhatsApp, logo, hero image) |
| GET | `/testimonials/` | Published reviews |
| POST | `/contact/` | `{name, email, phone?, subject?, message}`. Rate-limited, honeypot field `website` |
| GET | `/vehicles/` | Active fleet. Filters: `category`, `transmission`, `fuel_type`, `min_price`, `max_price`, `min_passengers`, `featured=true`, `search`, `ordering`. Availability filters apply only to database-managed legacy vehicles; the static customer catalogue is always selectable. |
| GET | `/vehicles/{slug}/` | Vehicle details, images and features |
| GET | `/vehicles/{slug}/availability/` | Legacy database-managed vehicle availability; the customer booking form does not call this endpoint. |
| GET | `/booking-options/` | Locations with fees, extras with prices, default airport, hold hours, upload limit, available payment methods and manual payment instructions |
| POST | `/bookings/quote/` | `{vehicle, pickup_date, pickup_time, return_date, return_time, pickup_type, return_type, extras}` → server-calculated price breakdown |
| POST | `/bookings/` | Create a booking (below) |
| GET | `/bookings/track/` | *Guest headers.* Booking, invoices, receipts, payments and payment options |
| GET | `/invoices/download/?invoice=<number\|latest>` | *Guest headers.* PDF |
| GET | `/receipts/download/?receipt=<number>` | *Guest headers.* PDF |
| POST | `/payments/manual/` | Guest payment submissions are disabled. Payment is recorded by authorized staff after local collection. |
| POST | `/payments/online/initiate/` | Online gateways are disabled; this endpoint cannot start customer checkout. |
| POST | `/payments/online/verify/` | Legacy gateway callback; no new customer payments can be initiated. |
| GET/POST | `/webhooks/payments/{provider}/` | Legacy gateway callback; no new customer payments can be initiated. |
| GET | `/sitemap.xml` (site root) | Sitemap including every active vehicle |

### Create booking: `POST /bookings/`
Send either a JSON body, or multipart with a `payload` field (a JSON string) plus the files `passport` and `driving_licence` (PDF, JPG or PNG, up to 8 MB each). The files are required when `extras.driving_permit` is 1.

```json
{
  "customer": {"full_name": "Amina Guest", "email": "amina@example.com", "phone": "+44 7700 900123",
               "nationality": "British", "additional_info": ""},
  "vehicle": "toyota-rav4-automatic",
  "pickup_date": "2026-12-20", "pickup_time": "10:00", "return_date": "2026-12-24", "return_time": "10:00",
  "pickup_type": "OUTSIDE_ZONE", "pickup_area": "Nungwi", "pickup_address": "Hotel name / street", "pickup_instructions": "",
  "return_type": "AIRPORT", "return_area": "", "return_address": "", "return_instructions": "",
  "flight": {"airline_name": "Kenya Airways", "flight_number": "KQ 484", "arrival_date": "2026-12-20",
             "arrival_time": "09:15", "arrival_airport": "", "notes": ""},
  "extras": {"baby_seat": 2, "driving_permit": 0},
  "payment_method": "MANUAL",
  "accept_terms": true
}
```
Response `201`:
```json
{"booking_reference": "RCH-7K3Q9PX", "access_token": "…", "invoice_number": "RCI-2026-000001",
 "booking_status": "PENDING_CONFIRMATION", "payment_status": "UNPAID", "payment_method": "MANUAL",
 "grand_total": "365.00", "currency": "USD", "hold_expires_at": "…", "whatsapp_url": "https://wa.me/…"}
```
Price fields in the request are ignored. If the car is already reserved, the response is `409`.

## Admin (`/admin/…`): session cookie and CSRF

| Method | Path | Roles |
|---|---|---|
| GET | `/admin/auth/csrf/` | Public. Sets the CSRF cookie |
| POST | `/admin/auth/login/` | Public. `{email, password}`. Needs CSRF; rate-limited |
| POST | `/admin/auth/logout/` · GET `/admin/auth/me/` | All |
| GET | `/admin/dashboard/` | All. Revenue is hidden from STAFF |
| GET | `/admin/bookings/` | All. Filters: `q`, `booking_status`, `payment_status`, `payment_method`, `vehicle`, `customer`, `pickup_from`, `pickup_to`, `created_from`, `created_to`, `outstanding`, `ordering` |
| GET | `/admin/bookings/{id}/` | All. Full detail: documents metadata, history, notes, invoices, payments, emails, WhatsApp links, allowed transitions |
| POST | `/admin/bookings/{id}/confirm\|reject\|cancel\|complete/` | All. `{notes, notify_guest}`. Reject and cancel need notes |
| POST | `/admin/bookings/{id}/notes/` | All. `{body}` |
| POST | `/admin/bookings/{id}/modify/` | ADMIN, MANAGER. Changed fields plus `reason`. Issues a revised invoice automatically |
| GET | `/admin/bookings/{id}/documents/{doc}/download/` | ADMIN, MANAGER. Every view is audited |
| POST | `/admin/bookings/{id}/documents/{doc}/verify/` | ADMIN, MANAGER. `{status: VERIFIED\|REJECTED}` |
| GET, POST · PATCH, DELETE | `/admin/vehicles/` · `/admin/vehicles/{id}/` | Read: all. Write: ADMIN, MANAGER. Deleting a vehicle with bookings deactivates it instead |
| POST | `/admin/vehicles/{id}/images/` | ADMIN, MANAGER. Multipart `images[]` |
| PATCH, DELETE | `/admin/vehicles/{id}/images/{img}/` | ADMIN, MANAGER. `{alt_text?, display_order?, make_cover?}` |
| CRUD | `/admin/extras/` | Read: all. Write: ADMIN, MANAGER. System rows can't be deleted |
| GET, PATCH | `/admin/customers/` · `/admin/customers/{id}/` | All. Detail includes bookings, invoices and payments |
| GET | `/admin/invoices/` · `/{id}/` · `/{id}/download/` | All |
| POST | `/admin/invoices/{id}/resend/` | All. `{to_owner?}` |
| POST | `/admin/invoices/{id}/revise/` | ADMIN, MANAGER. `{reason}` |
| GET | `/admin/receipts/` · `/{id}/download/` | All |
| GET | `/admin/payments/` | All. Filters: `q`, `payment_status`, `payment_method`, `channel`, `gateway`, `booking`, `created_from`, `created_to` |
| POST | `/admin/payments/{id}/verify/` | ADMIN, MANAGER. `{confirm: true, notes?, amount?}` |
| POST | `/admin/payments/{id}/reject/` | ADMIN, MANAGER. `{reason}` |
| POST | `/admin/payments/record/` | ADMIN, MANAGER. `{booking, amount, channel, transaction_reference?, notes}` |
| POST | `/admin/payments/{id}/refund/` | ADMIN, MANAGER. `{amount, reason, via_gateway?}` |
| POST | `/admin/payments/{id}/sync/` | ADMIN, MANAGER. Re-checks with the gateway |
| GET | `/admin/payments/{id}/proof/` | ADMIN, MANAGER |
| GET | `/admin/reports/{bookings\|revenue\|vehicles\|payments\|outstanding}/` | ADMIN, MANAGER. `year` or `date_from`/`date_to`; `export=csv\|pdf` |
| GET, PATCH | `/admin/settings/` | Read: all. Write: ADMIN (multipart for logo and hero image) |
| GET · POST | `/admin/notifications/` · `/admin/notifications/{id}/resend/` | All |
| CRUD | `/admin/testimonials/`, GET/PATCH `/admin/messages/` | All |
| GET | `/admin/audit-logs/` | ADMIN |

## Rate limits (per IP; configurable via `THROTTLE_*` environment variables)
| Scope | Limit |
|---|---|
| Booking creation | 10/hour |
| Quotes | 120/min |
| Guest access | 60/hour |
| Payments | 20/hour |
| Contact form | 5/hour |
| Login | 10/hour |
| Anonymous requests overall | 600/hour |
