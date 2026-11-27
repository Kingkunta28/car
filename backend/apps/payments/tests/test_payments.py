from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import Role
from apps.bookings.models import Booking, PaymentStatus
from apps.core.models import AuditLog
from apps.core.tests import factories as f
from apps.payments.gateways.base import GatewayStatus
from apps.payments.models import Payment, Receipt, Status


class PaymentTestBase(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.v = f.vehicle()  # 3 days × $55 = $165
        with self.captureOnCommitCallbacks(execute=True):
            res = self.client.post("/api/v1/bookings/", f.booking_payload(self.v), format="json")
        self.res = res
        self.booking = Booking.objects.get(booking_reference=res.data["booking_reference"])
        self.headers = {"HTTP_X_BOOKING_REFERENCE": res.data["booking_reference"],
                        "HTTP_X_BOOKING_TOKEN": res.data["access_token"]}
        self.manager = f.staff(Role.MANAGER)

    def submit_manual(self, amount="100.00", **extra):
        data = {"amount": amount, "channel": "BANK_TRANSFER", "transaction_reference": "TRX-12345", **extra}
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post("/api/v1/payments/manual/", data, format="multipart", **self.headers)

    def record_offline(self, amount="100.00", notes="Cash received at vehicle pickup", channel="CASH"):
        self.client.force_authenticate(self.manager)
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post("/api/v1/admin/payments/record/", {
                "booking": str(self.booking.pk), "amount": amount, "channel": channel, "notes": notes,
            }, format="json")


class ManualPaymentTests(PaymentTestBase):
    def test_submission_does_not_mark_paid(self):
        res = self.submit_manual("165.00")
        self.assertEqual(res.status_code, 400, res.data)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.payment_status, PaymentStatus.UNPAID)
        self.assertEqual(self.booking.amount_paid, Decimal("0.00"))
        self.assertFalse(Payment.objects.exists())
        self.assertFalse(Receipt.objects.exists())

    def test_requires_valid_token(self):
        res = self.client.post("/api/v1/payments/manual/", {"amount": "10", "channel": "CASH",
                                                            "transaction_reference": "x"},
                               HTTP_X_BOOKING_REFERENCE=self.booking.booking_reference)
        self.assertEqual(res.status_code, 404)

    def test_cannot_exceed_balance(self):
        self.assertEqual(self.submit_manual("500.00").status_code, 400)

    def test_requires_reference_or_proof(self):
        self.assertEqual(self.submit_manual("50.00", transaction_reference="").status_code, 400)
        res = self.submit_manual("50.00", transaction_reference="", proof=f.png_upload("slip.png"))
        self.assertEqual(res.status_code, 400)

    def test_verification_is_audited_and_issues_receipt(self):
        res = self.record_offline("165.00", notes="Cash received at airport handover")
        self.assertEqual(res.status_code, 201, res.data)
        p = Payment.objects.get()
        p.refresh_from_db()
        self.assertEqual(p.payment_status, Status.VERIFIED)
        self.assertEqual(p.verified_by, self.manager)
        self.assertIsNotNone(p.verified_at)
        self.assertEqual(p.verification_source, "STAFF_RECORDED")
        self.assertTrue(AuditLog.objects.filter(action="payment.verified", target_id=str(p.pk)).exists())
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.payment_status, PaymentStatus.PAID)
        r = Receipt.objects.get(payment=p)
        self.assertTrue(r.receipt_number.startswith("RCR-"))
        self.assertTrue(r.pdf_file)

    def test_staff_role_cannot_verify(self):
        self.record_offline("100.00")
        p = Payment.objects.get()
        self.client.force_authenticate(f.staff(Role.STAFF))
        res = self.client.post(f"/api/v1/admin/payments/{p.pk}/verify/", {"confirm": True}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_reject(self):
        p = Payment.objects.create(booking=self.booking, payment_reference="RCP-PENDING", payment_method="MANUAL",
                                   channel="BANK_TRANSFER", amount=Decimal("100.00"), currency="USD",
                                   payment_status=Status.PENDING_VERIFICATION)
        self.client.force_authenticate(self.manager)
        with self.captureOnCommitCallbacks(execute=True):
            res = self.client.post(f"/api/v1/admin/payments/{p.pk}/reject/", {"reason": "No funds received"},
                                   format="json")
        self.assertEqual(res.status_code, 200)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.payment_status, PaymentStatus.UNPAID)

    def test_partial_payments_and_offline_record(self):
        first = self.record_offline("65.00")
        self.assertEqual(first.status_code, 201, first.data)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.payment_status, PaymentStatus.PARTIALLY_PAID)
        self.assertEqual(self.booking.balance_due, Decimal("100.00"))
        # Offline record requires a description of how money was received.
        self.assertEqual(self.client.post("/api/v1/admin/payments/record/", {
            "booking": str(self.booking.pk), "amount": "100.00", "channel": "CASH", "notes": ""},
            format="json").status_code, 400)
        res = self.record_offline("100.00", notes="Cash received at airport handover")
        self.assertEqual(res.status_code, 201, res.data)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.payment_status, PaymentStatus.PAID)
        self.assertEqual(Receipt.objects.count(), 2)

    def test_refund_tracking(self):
        self.client.force_authenticate(self.manager)
        res = self.client.post("/api/v1/admin/payments/record/", {
            "booking": str(self.booking.pk), "amount": "165.00", "channel": "CASH", "notes": "Paid in cash"},
            format="json")
        pid = res.data["id"]
        res = self.client.post(f"/api/v1/admin/payments/{pid}/refund/", {"amount": "40.00", "reason": "Returned early"},
                               format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.payment_status, PaymentStatus.PARTIALLY_REFUNDED)
        self.assertEqual(self.booking.amount_paid, Decimal("125.00"))
        self.assertEqual(self.client.post(f"/api/v1/admin/payments/{pid}/refund/",
                                          {"amount": "500.00", "reason": "x"}, format="json").status_code, 400)

    def test_cannot_mark_verified_without_audit_fields(self):
        from django.db import IntegrityError, transaction
        with self.assertRaises(IntegrityError), transaction.atomic():
            Payment.objects.create(booking=self.booking, payment_reference="RCP-RAW", payment_method="MANUAL",
                                   amount=Decimal("10"), payment_status=Status.VERIFIED)


class FakeResponse:
    def __init__(self, data, status=200):
        self._data, self.status_code = data, status

    def json(self):
        return self._data


def pesapal_router(status_payload):
    def _request(method, url, **kw):
        if url.endswith("/api/Auth/RequestToken"):
            return FakeResponse({"token": "tok", "status": "200"})
        if url.endswith("/api/Transactions/SubmitOrderRequest"):
            return FakeResponse({"order_tracking_id": "trk-123", "merchant_reference": kw["json"]["id"],
                                 "redirect_url": "https://pay.example/checkout/trk-123", "status": "200"})
        if url.endswith("/api/Transactions/GetTransactionStatus"):
            return FakeResponse(status_payload())
        raise AssertionError(url)
    return _request


@override_settings(PAYMENT_GATEWAYS_ENABLED=["pesapal"])
class OnlinePaymentTests(PaymentTestBase):
    def initiate(self, status_payload, amount=None):
        with mock.patch("apps.payments.gateways.pesapal.requests.request", side_effect=pesapal_router(status_payload)):
            body = {"gateway": "pesapal"} | ({"amount": amount} if amount else {})
            return self.client.post("/api/v1/payments/online/initiate/", body, format="json", **self.headers)

    def status(self, code=1, amount=165.0, currency="USD", ref=None):
        def payload():
            p = Payment.objects.get(gateway_order_id="trk-123")
            return {"status_code": code, "amount": amount, "currency": currency, "confirmation_code": "PSPL-999",
                    "payment_status_description": {1: "Completed", 2: "Failed"}.get(code, "Invalid"),
                    "merchant_reference": ref or p.payment_reference, "payment_method": "Visa", "status": "200"}
        return payload

    def call_webhook(self, status_payload):
        with mock.patch("apps.payments.gateways.pesapal.requests.request", side_effect=pesapal_router(status_payload)):
            with self.captureOnCommitCallbacks(execute=True):
                return self.client.get("/api/v1/webhooks/payments/pesapal/",
                                       {"OrderTrackingId": "trk-123", "OrderMerchantReference": "x",
                                        "OrderNotificationType": "IPNCHANGE"})

    def test_initiate_returns_redirect_and_stays_unpaid(self):
        res = self.initiate(self.status())
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["redirect_url"], "https://pay.example/checkout/trk-123")
        p = Payment.objects.get()
        self.assertEqual(p.payment_status, Status.INITIATED)
        self.assertEqual(p.amount, Decimal("165.00"))
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.payment_status, PaymentStatus.UNPAID)

    def test_webhook_verifies_with_gateway_api(self):
        self.initiate(self.status())
        res = self.call_webhook(self.status(code=1))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], 200)
        self.assertEqual(res.data["orderTrackingId"], "trk-123")
        p = Payment.objects.get()
        self.assertEqual(p.payment_status, Status.VERIFIED)
        self.assertEqual(p.verification_source, "GATEWAY_API")
        self.assertEqual(p.transaction_reference, "PSPL-999")
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.payment_status, PaymentStatus.PAID)
        # Idempotent: a duplicate notification changes nothing.
        self.call_webhook(self.status(code=1))
        self.assertEqual(Receipt.objects.count(), 1)

    def test_forged_webhook_cannot_mark_paid(self):
        """The webhook carries no trust — the gateway API says it's not paid."""
        self.initiate(self.status())
        self.call_webhook(self.status(code=0))
        self.assertEqual(Payment.objects.get().payment_status, Status.INITIATED)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.payment_status, PaymentStatus.UNPAID)

    def test_amount_mismatch_not_accepted(self):
        self.initiate(self.status())
        self.call_webhook(self.status(code=1, amount=1.0))
        p = Payment.objects.get()
        self.assertEqual(p.payment_status, Status.INITIATED)
        self.assertIn("manual review", p.review_notes)

    def test_reference_mismatch_not_accepted(self):
        self.initiate(self.status())
        self.call_webhook(self.status(code=1, ref="RCP-OTHER"))
        self.assertEqual(Payment.objects.get().payment_status, Status.INITIATED)

    def test_failed_payment(self):
        self.initiate(self.status())
        self.call_webhook(self.status(code=2))
        self.assertEqual(Payment.objects.get().payment_status, Status.FAILED)

    def test_return_page_verify_endpoint(self):
        self.initiate(self.status())
        with mock.patch("apps.payments.gateways.pesapal.requests.request", side_effect=pesapal_router(self.status())):
            with self.captureOnCommitCallbacks(execute=True):
                res = self.client.post("/api/v1/payments/online/verify/", {"order_tracking_id": "trk-123"},
                                       format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], "VERIFIED")
        self.assertNotIn("customer", res.data)

    def test_partial_online_payment(self):
        self.initiate(self.status(), amount="50.00")
        self.call_webhook(self.status(code=1, amount=50.0))
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.payment_status, PaymentStatus.PARTIALLY_PAID)

    def test_unconfigured_gateway_refuses(self):
        with self.settings(PESAPAL_CONSUMER_KEY=""):
            res = self.client.post("/api/v1/payments/online/initiate/", {"gateway": "pesapal"}, format="json",
                                   **self.headers)
        self.assertEqual(res.status_code, 400)
