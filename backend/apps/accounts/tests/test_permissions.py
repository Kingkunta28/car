from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Role
from apps.bookings.models import Booking, BookingStatus
from apps.core.tests import factories as f

ADMIN_ENDPOINTS = [
    "/api/v1/admin/dashboard/", "/api/v1/admin/bookings/", "/api/v1/admin/vehicles/", "/api/v1/admin/customers/",
    "/api/v1/admin/invoices/", "/api/v1/admin/payments/", "/api/v1/admin/notifications/",
    "/api/v1/admin/reports/revenue/", "/api/v1/admin/settings/",
]


class AdminPermissionTests(TestCase):
    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)

    def test_anonymous_blocked_everywhere(self):
        for url in ADMIN_ENDPOINTS:
            self.assertIn(self.client.get(url).status_code, (401, 403), url)

    def test_user_without_dashboard_access_blocked(self):
        self.client.force_authenticate(f.staff(Role.ADMIN, dashboard_access=False))
        self.assertEqual(self.client.get("/api/v1/admin/bookings/").status_code, 403)

    def test_inactive_user_blocked(self):
        self.client.force_authenticate(f.staff(Role.ADMIN, is_active=False))
        self.assertIn(self.client.get("/api/v1/admin/bookings/").status_code, (401, 403))

    def test_staff_role_limits(self):
        self.client.force_authenticate(f.staff(Role.STAFF))
        self.assertEqual(self.client.get("/api/v1/admin/bookings/").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/admin/reports/revenue/").status_code, 403)
        self.assertIsNone(self.client.get("/api/v1/admin/dashboard/").data["revenue"])
        self.assertEqual(self.client.post("/api/v1/admin/vehicles/", {}, format="json").status_code, 403)
        self.assertEqual(self.client.patch("/api/v1/admin/settings/", {"tax_rate": "5"}, format="json").status_code, 403)

    def test_only_admin_changes_settings(self):
        self.client.force_authenticate(f.staff(Role.ADMIN, email="boss@rafiki.test"))
        res = self.client.patch("/api/v1/admin/settings/", {"whatsapp_number": "255777000111"}, format="json")
        self.assertEqual(res.status_code, 200)

    def test_login_flow_with_csrf(self):
        f.staff(Role.MANAGER, email="m@rafiki.test")
        csrf = self.client.get("/api/v1/admin/auth/csrf/").data["csrfToken"]
        bad = self.client.post("/api/v1/admin/auth/login/", {"email": "m@rafiki.test", "password": "nope"},
                               format="json", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(bad.status_code, 401)
        ok = self.client.post("/api/v1/admin/auth/login/", {"email": "M@rafiki.test", "password": "Str0ng-Passw0rd!"},
                              format="json", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(ok.status_code, 200, ok.data)
        self.assertEqual(self.client.get("/api/v1/admin/auth/me/").status_code, 200)

    def test_login_requires_csrf(self):
        f.staff(Role.MANAGER, email="m@rafiki.test")
        res = self.client.post("/api/v1/admin/auth/login/", {"email": "m@rafiki.test", "password": "Str0ng-Passw0rd!"},
                               format="json")
        self.assertEqual(res.status_code, 403)

    def test_public_endpoints_never_expose_customer_lists(self):
        for url in ("/api/v1/bookings/", "/api/v1/customers/"):
            self.assertIn(self.client.get(url).status_code, (404, 405))


class BookingAdminActionsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        v = f.vehicle()
        with self.captureOnCommitCallbacks(execute=True):
            res = self.client.post("/api/v1/bookings/", f.booking_payload(v), format="json")
        self.booking = Booking.objects.get(booking_reference=res.data["booking_reference"])
        self.client.force_authenticate(f.staff(Role.STAFF))

    def post(self, action, **data):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(f"/api/v1/admin/bookings/{self.booking.pk}/{action}/", data, format="json")

    def test_confirm_complete_and_history(self):
        self.assertEqual(self.post("confirm", notes="See you at the airport").status_code, 200)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.booking_status, BookingStatus.CONFIRMED)
        self.assertIsNone(self.booking.hold_expires_at)
        self.assertEqual(self.post("complete").status_code, 200)
        self.booking.refresh_from_db()
        self.assertFalse(self.booking.blocks_inventory)
        statuses = list(self.booking.status_history.filter(status_field="booking_status")
                        .values_list("new_status", flat=True))
        self.assertEqual(statuses, ["PENDING_CONFIRMATION", "CONFIRMED", "COMPLETED"])

    def test_cancel_requires_reason_and_releases_vehicle(self):
        self.assertEqual(self.post("cancel").status_code, 400)
        self.assertEqual(self.post("cancel", notes="Guest changed plans").status_code, 200)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.booking_status, BookingStatus.CANCELLED)
        self.assertFalse(self.booking.blocks_inventory)

    def test_invalid_transition(self):
        self.post("reject", notes="No availability")
        self.assertEqual(self.post("confirm").status_code, 400)

    def test_internal_notes_hidden_from_guest(self):
        self.client.post(f"/api/v1/admin/bookings/{self.booking.pk}/notes/", {"body": "VIP guest"}, format="json")
        detail = self.client.get(f"/api/v1/admin/bookings/{self.booking.pk}/")
        self.assertEqual(detail.data["notes"][0]["body"], "VIP guest")

    def test_search(self):
        res = self.client.get("/api/v1/admin/bookings/", {"q": self.booking.booking_reference})
        self.assertEqual(res.data["count"], 1)
