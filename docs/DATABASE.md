# Database schema

The database is PostgreSQL. Major records use UUID primary keys. Money is stored as `NUMERIC(10–12, 2)` and calculated with Python's `Decimal`.

## Overview

```
AdminUser ─┬─< AuditLog
           └─< (verified_by / changed_by / author on many tables)

Customer ─< Booking >─ Vehicle ─< VehicleImage
                │              └< VehicleFeature
                ├─< BookingExtra >─ ExtraService
                ├─1 BookingFlight
                ├─< BookingDocument            (private storage)
                ├─< BookingStatusHistory
                ├─< BookingNote                (internal only)
                ├─< BookingAccessToken         (SHA-256 hashes only)
                ├─< Invoice ─< InvoiceItem     (revisions: original_invoice, supersedes)
                ├─< Payment ─< Refund
                │          └─1 Receipt
                └─< NotificationLog

SiteSettings (singleton) · Sequence (document counters) · ContactMessage · Testimonial
```

## Tables

### accounts.AdminUser
`id` (UUID), `email` (unique), `full_name`, `role` (ADMIN | MANAGER | STAFF), `dashboard_access`, `is_active`, `is_staff` (Django admin access), `is_superuser`, `password` (hashed), `last_login`, `date_joined`.

### customers.Customer
`id`, `full_name`, `email` (unique, case-insensitive), `phone`, `nationality`, `created_at`, `updated_at`. Guests have no passwords.

### vehicles.Vehicle
`id`, `slug` (unique), `name`, `brand`, `model`, `year`, `category`, `description`, `price_per_day` (CHECK > 0), `transmission`, `fuel_type`, `passenger_capacity` (CHECK ≥ 1), `luggage_capacity`, `doors`, `availability_status` (AVAILABLE | MAINTENANCE | UNAVAILABLE), `is_featured`, `is_active`, `display_order`, timestamps. Index on (`is_active`, `availability_status`).

### vehicles.VehicleImage / VehicleFeature
- **VehicleImage:** `vehicle` FK, `image` (public storage, random name), `alt_text`, `display_order`.
- **VehicleFeature:** `vehicle` FK, `feature_name`. Each feature name is unique per vehicle.

### bookings.ExtraService
`code` (unique), `name`, `description`, `price` (CHECK ≥ 0), `pricing_type` (PER_BOOKING | PER_UNIT | PER_DAY | PER_UNIT_PER_DAY), `max_quantity`, `requires_documents`, `is_system`, `is_active`, `display_order`. Seeded rows: `outside_zone_delivery`, `baby_seat`, `driving_permit`.

### bookings.Booking
| Group | Columns |
|---|---|
| Identity | `id`, `booking_reference` (unique, random e.g. `RCH-7K3Q9PX`), `customer` FK, `vehicle` FK (PROTECT) |
| Time | `pickup_date`, `pickup_time`, `return_date`, `return_time`, `pickup_at`, `return_at`, `blocked_until` (return + turnaround), `rental_days` |
| Locations | `pickup_type`/`return_type` (AIRPORT \| TOWN \| OUTSIDE_ZONE), `*_area`, `*_address`, `*_instructions` |
| Money snapshot | `daily_rate`, `rental_total`, `pickup_fee`, `return_fee`, `extras_total`, `tax_amount`, `grand_total`, `amount_paid`, `currency`, `pricing_breakdown` (JSON) |
| Status | `booking_status` (PENDING_CONFIRMATION, CONFIRMED, REJECTED, CANCELLED, COMPLETED, EXPIRED), `payment_status` (UNPAID, PENDING_VERIFICATION, PARTIALLY_PAID, PAID, PARTIALLY_REFUNDED, REFUNDED), `payment_method` (MANUAL \| ONLINE), `status_reason` |
| Hold | `blocks_inventory`, `hold_expires_at` |
| Other | `customer_notes`, `confirmed_at`, `cancelled_at`, `completed_at`, timestamps |

Constraints:
- `CHECK return_at > pickup_at`
- `CHECK blocked_until ≥ return_at`
- `CHECK rental_days ≥ 1`
- `CHECK grand_total ≥ 0`
- **`EXCLUDE USING gist (vehicle_id WITH =, tstzrange(pickup_at, blocked_until) WITH &&) WHERE blocks_inventory`**: no two active reservations of the same vehicle can overlap.

Indexes: (`vehicle`, `blocks_inventory`, `pickup_at`), (`booking_status`, `hold_expires_at`), plus `pickup_date`, `booking_status`, `payment_status` and `created_at`.

> **Change from the spec:** `secure_access_token_hash` became a separate `BookingAccessToken` table. A booking can then have several independent, expiring, revocable tokens (one for the confirmation page, one per email).

### bookings.BookingExtra
`booking` FK, `extra_service` FK (nullable), `code`, `service_name`, `pricing_type`, `quantity` (CHECK ≥ 1), `unit_price`, `total_price`. Each code is unique per booking.

### bookings.BookingFlight
One-to-one with `booking`: `airline_name`, `flight_number`, `arrival_date`, `arrival_time`, `arrival_airport`, `notes`.

### bookings.BookingDocument
`booking` FK, `document_type` (PASSPORT | DRIVING_LICENCE), `secure_file` (**private storage**, random name), `original_filename`, `file_kind`, `file_size`, `sha256`, `uploaded_at`, `verification_status` (PENDING | VERIFIED | REJECTED | PURGED), `verified_by`, `verified_at`, `purged_at`.

### bookings.BookingStatusHistory / BookingNote / BookingAccessToken
- **BookingStatusHistory:** `booking`, `status_field` (booking_status \| payment_status), `previous_status`, `new_status`, `changed_by`, `notes`, `created_at`.
- **BookingNote:** `booking`, `author`, `body`, `created_at`. Visible to staff only.
- **BookingAccessToken:** `booking`, `token_hash` (unique SHA-256), `purpose`, `expires_at`, `revoked_at`, `last_used_at`.

### invoices.Invoice / InvoiceItem
- **Invoice:** `invoice_number` (unique, e.g. `RCI-2026-000001` or `…-R1`), `booking` FK (PROTECT), `issue_date`, `revision_number`, `original_invoice` FK, `supersedes` (one-to-one), `revision_reason`, `subtotal`, `tax_amount`, `total_amount`, `currency`, `invoice_status` (ISSUED | SUPERSEDED | VOID), `snapshot` (JSON of everything printed), `pdf_file` (private), `pdf_sha256`, `issued_by`, `created_at`.
  - Partial unique index: at most one `ISSUED` invoice per booking.
  - Unique (`booking`, `revision_number`).
- **InvoiceItem:** `invoice` FK, `description`, `quantity`, `unit_price`, `total_price`, `sort_order`.

### payments.Payment / Refund / Receipt
- **Payment:** `booking` FK, `payment_reference` (unique), `payment_method`, `channel`, `gateway`, `amount` (CHECK > 0), `currency`, `payment_status` (INITIATED, PENDING_VERIFICATION, VERIFIED, FAILED, REJECTED, CANCELLED, REVERSED), `transaction_reference`, `gateway_order_id`, `gateway_response_reference`, `gateway_payload` (sanitised JSON), `checkout_url`, `proof_file` (private), `payer_note`, `refunded_amount`, `recorded_by`, `verified_by`, `verified_at`, `verification_source` (GATEWAY_API | STAFF_REVIEW | STAFF_RECORDED), `review_notes`, timestamps.
  - Constraints:
    - unique (`gateway`, `gateway_order_id`);
    - unique (`gateway`, `transaction_reference`) for online payments;
    - `0 ≤ refunded_amount ≤ amount`;
    - **a VERIFIED payment must have `verified_at` and `verification_source`**.
  - No card data is ever stored.
- **Refund:** `payment` FK, `amount`, `reason`, `status` (REQUESTED | COMPLETED | FAILED), `gateway_reference`, `recorded_by`, `created_at`, `processed_at`.
- **Receipt:** `receipt_number` (unique, e.g. `RCR-2026-000001`), `payment` (one-to-one), `booking`, `issue_date`, `amount`, `currency`, `snapshot`, `pdf_file` (private).

### notifications.NotificationLog
`booking`, `invoice`, `payment`, `recipient`, `notification_type` (13 types), `subject`, `context` (non-sensitive JSON only: never tokens or document URLs), `delivery_status` (QUEUED | SENT | FAILED | ABANDONED), `attempts`, `error_message`, `last_attempt_at`, `next_retry_at`, `sent_at`, timestamps.

### core
- **SiteSettings** (singleton): business name, tagline, email, phone, WhatsApp, address, logo, hero image, owner email, invoice footer and terms, payment instructions, currency, tax rate and label, email configuration note. **It contains no credentials.**
- **Sequence:** `key` (e.g. `RCI-2026`), `last_value`. Incremented under `SELECT … FOR UPDATE`.
- **AuditLog:** actor, action, target type and id, summary, metadata, IP address, time. Append-only (read-only in the Django admin).
- **ContactMessage**, **Testimonial** (`is_published` must be set before a review appears on the site).

## Migrations
```bash
python manage.py migrate
```
- `bookings.0001` enables the `btree_gist` extension before it creates the exclusion constraint. The database user needs permission to `CREATE EXTENSION` on the first run; managed Postgres services allow this.
- `bookings.0002` seeds the core fees and the site settings row.
