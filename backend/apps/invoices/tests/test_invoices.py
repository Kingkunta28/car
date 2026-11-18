from unittest import skipUnless
import threading
from datetime import timedelta
from decimal import Decimal

from django.core import mail
from django.core.cache import cache
from django.db import connection, transaction
from django.test import TestCase, TransactionTestCase
import pypdfium2 as pdfium
from rest_framework.test import APIClient

from apps.accounts.models import Role
from apps.bookings.models import Booking
from apps.bookings.services import modify_booking
from apps.core.models import Sequence
from apps.core.tests import factories as f
from apps.core.utils import next_sequence_value
from apps.invoices.models import Invoice, InvoiceStatus
from apps.invoices.pdf import render_invoice_pdf
from apps.notifications.models import DeliveryStatus, NotificationLog
from apps.notifications.services import deliver, due_for_retry


class InvoiceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.v = f.vehicle()
        self.manager = f.staff(Role.MANAGER)

    def book(self, **kw):
        with self.captureOnCommitCallbacks(execute=True):
            res = self.client.post("/api/v1/bookings/", f.booking_payload(self.v, **kw), format="json")
        self.assertEqual(res.status_code, 201, res.data)
        return res, Booking.objects.get(booking_reference=res.data["booking_reference"])

    def test_sequential_unique_numbers(self):
        _, b1 = self.book(start_days=10)
        _, b2 = self.book(start_days=20)
        n1, n2 = b1.invoices.get().invoice_number, b2.invoices.get().invoice_number
        self.assertNotEqual(n1, n2)
        self.assertEqual(int(n2.rsplit("-", 1)[1]), int(n1.rsplit("-", 1)[1]) + 1)

    def test_invoice_snapshot_contents(self):
        _, b = self.book(pickup_type="OUTSIDE_ZONE", extras={"baby_seat": 2, "driving_permit": 0})
        inv = b.invoices.get()
        snap = inv.snapshot
        self.assertEqual(snap["booking_reference"], b.booking_reference)
        self.assertEqual(snap["customer"]["email"], "amina@example.com")
        self.assertEqual(snap["payment_status"], "Unpaid")
        self.assertEqual(snap["booking_status"], "Pending confirmation")
        descriptions = [i["description"] for i in snap["items"]]
        self.assertTrue(any("Outside Free Zone" in d for d in descriptions))
        self.assertEqual(inv.items.count(), len(snap["items"]))
        self.assertEqual(sum(i.total_price for i in inv.items.all()), inv.total_amount)

    def test_guest_booking_confirmation_pdf_requires_booking_token(self):
        res, booking = self.book()
        headers = {"HTTP_X_BOOKING_REFERENCE": booking.booking_reference,
                   "HTTP_X_BOOKING_TOKEN": res.data["access_token"]}
        response = self.client.get("/api/v1/bookings/confirmation/download/", **headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(response["Cache-Control"], "private, no-store, max-age=0")
        self.assertTrue(b"%PDF" in response.content[:10])

        denied = self.client.get("/api/v1/bookings/confirmation/download/")
        self.assertEqual(denied.status_code, 404)

    def test_customer_invoice_has_four_pages_and_no_identity_document_fields(self):
        _, booking = self.book()
        invoice = booking.invoices.get()
        self.assertNotIn("documents", invoice.snapshot)
        pdf = pdfium.PdfDocument(render_invoice_pdf(invoice.snapshot))
        self.assertEqual(len(pdf), 4)
        pdf.close()

    def test_revision_preserves_original(self):
        _, b = self.book(days=3)
        original = b.invoices.get()
        original_pdf_hash = original.pdf_sha256
        with self.captureOnCommitCallbacks(execute=True):
            b, revised = modify_booking(b, {"extras": {"baby_seat": 1}}, actor=self.manager, reason="Guest added a seat")
        original.refresh_from_db()
        self.assertEqual(original.invoice_status, InvoiceStatus.SUPERSEDED)
        self.assertEqual(original.pdf_sha256, original_pdf_hash)
        self.assertEqual(original.total_amount, Decimal("165.00"))
        self.assertEqual(revised.invoice_number, f"{original.invoice_number}-R1")
        self.assertEqual(revised.supersedes, original)
        self.assertEqual(revised.total_amount, Decimal("225.00"))
        self.assertEqual(Invoice.objects.filter(booking=b, invoice_status=InvoiceStatus.ISSUED).count(), 1)
        self.assertTrue(any("Revised" in m.subject for m in mail.outbox))

    def test_modify_keeps_agreed_daily_rate(self):
        _, b = self.book(days=2)
        self.v.price_per_day = Decimal("90.00")
        self.v.save()
        new_return = b.return_date + timedelta(days=1)
        b, inv = modify_booking(b, {"return_date": new_return}, actor=self.manager, reason="Extended by one day")
        self.assertEqual(b.rental_total, Decimal("165.00"))  # 3 × original 55

    def test_admin_download_and_resend(self):
        _, b = self.book()
        inv = b.invoices.get()
        self.client.force_authenticate(self.manager)
        res = self.client.get(f"/api/v1/admin/invoices/{inv.pk}/download/")
        self.assertEqual(res.status_code, 200)
        mail.outbox.clear()
        with self.captureOnCommitCallbacks(execute=True):
            res = self.client.post(f"/api/v1/admin/invoices/{inv.pk}/resend/", {}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(mail.outbox[0].to, ["amina@example.com"])

    def test_missing_pdf_regenerated_on_download(self):
        res, b = self.book()
        inv = b.invoices.get()
        inv.pdf_file.delete(save=True)
        headers = {"HTTP_X_BOOKING_REFERENCE": res.data["booking_reference"],
                   "HTTP_X_BOOKING_TOKEN": res.data["access_token"]}
        self.assertEqual(self.client.get("/api/v1/invoices/download/", **headers).status_code, 200)

    def test_admin_endpoints_require_staff(self):
        _, b = self.book()
        inv = b.invoices.get()
        self.assertIn(self.client.get("/api/v1/admin/invoices/").status_code, (401, 403))
        self.assertIn(self.client.get(f"/api/v1/admin/invoices/{inv.pk}/download/").status_code, (401, 403))


class EmailRetryTests(TestCase):
    def test_failure_is_recorded_and_retried_without_losing_booking(self):
        v = f.vehicle()
        with self.settings(EMAIL_BACKEND="apps.notifications.tests.failing_backend.FailingBackend"):
            with self.captureOnCommitCallbacks(execute=True):
                res = APIClient().post("/api/v1/bookings/", f.booking_payload(v), format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Booking.objects.count(), 1)
        self.assertEqual(Invoice.objects.count(), 1)
        logs = NotificationLog.objects.all()
        self.assertEqual(logs.count(), 2)
        for log in logs:
            self.assertEqual(log.delivery_status, DeliveryStatus.FAILED)
            self.assertEqual(log.attempts, 1)
            self.assertIn("SMTP down", log.error_message)
            self.assertIsNotNone(log.next_retry_at)
        # Backoff elapses, mail server recovers → retry succeeds.
        NotificationLog.objects.update(next_retry_at=None)
        NotificationLog.objects.update(next_retry_at=logs[0].created_at)
        for log_id in due_for_retry().values_list("pk", flat=True):
            self.assertTrue(deliver(log_id))
        self.assertEqual(NotificationLog.objects.filter(delivery_status=DeliveryStatus.SENT).count(), 2)
        self.assertEqual(len(mail.outbox), 2)

    def test_gives_up_after_max_attempts(self):
        v = f.vehicle()
        with self.settings(EMAIL_BACKEND="apps.notifications.tests.failing_backend.FailingBackend",
                           NOTIFICATION_MAX_ATTEMPTS=2):
            with self.captureOnCommitCallbacks(execute=True):
                APIClient().post("/api/v1/bookings/", f.booking_payload(v), format="json")
            log = NotificationLog.objects.first()
            deliver(log.pk)
        log.refresh_from_db()
        self.assertEqual(log.delivery_status, DeliveryStatus.ABANDONED)


@skipUnless(connection.vendor == "postgresql", "PostgreSQL-only behaviour")
class SequenceConcurrencyTests(TransactionTestCase):
    """Real concurrent transactions must never receive the same number."""

    def test_parallel_allocation_is_unique(self):
        results, errors = [], []

        def worker():
            try:
                for _ in range(10):
                    with transaction.atomic():
                        results.append(next_sequence_value("TEST-SEQ"))
            except Exception as exc:  # pragma: no cover
                errors.append(exc)
            finally:
                connection.close()

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertFalse(errors)
        self.assertEqual(len(results), 50)
        self.assertEqual(len(set(results)), 50)
        self.assertEqual(Sequence.objects.get(key="TEST-SEQ").last_value, 50)
