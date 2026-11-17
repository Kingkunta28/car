from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.bookings.models import ExtraService
from apps.bookings.pricing import build_quote, rental_days_between
from apps.core.models import SiteSettings
from apps.core.tests import factories as f


class PricingEngineTests(TestCase):
    def setUp(self):
        self.v = f.vehicle(price_per_day=Decimal("50.00"))
        self.start = timezone.now() + timedelta(days=5)

    def q(self, days=3, pickup="AIRPORT", ret="AIRPORT", extras=None, hours=0):
        return build_quote(vehicle=self.v, pickup_at=self.start, return_at=self.start + timedelta(days=days, hours=hours),
                           pickup_type=pickup, return_type=ret, extras=extras)

    def test_rental_total_per_day(self):
        q = self.q(days=3)
        self.assertEqual(q.rental_days, 3)
        self.assertEqual(q.rental_total, Decimal("150.00"))
        self.assertEqual(q.grand_total, Decimal("150.00"))

    def test_partial_day_rounds_up(self):
        self.assertEqual(self.q(days=2, hours=1).rental_days, 3)
        self.assertEqual(rental_days_between(self.start, self.start + timedelta(hours=5)), 1)

    def test_airport_and_town_are_free(self):
        for loc in ("AIRPORT", "TOWN"):
            q = self.q(pickup=loc, ret=loc)
            self.assertEqual(q.pickup_fee, Decimal("0.00"))
            self.assertEqual(q.return_fee, Decimal("0.00"))

    def test_outside_zone_charged_per_leg_independently(self):
        self.assertEqual(self.q(pickup="OUTSIDE_ZONE").pickup_fee, Decimal("25.00"))
        self.assertEqual(self.q(pickup="OUTSIDE_ZONE").return_fee, Decimal("0.00"))
        q = self.q(pickup="OUTSIDE_ZONE", ret="OUTSIDE_ZONE")
        self.assertEqual(q.pickup_fee + q.return_fee, Decimal("50.00"))
        self.assertEqual(q.grand_total, Decimal("200.00"))

    def test_baby_seat_is_per_seat_per_booking_not_per_day(self):
        q = self.q(days=7, extras={"baby_seat": 1})
        self.assertEqual(q.extras_total, Decimal("60.00"))  # 1 × $60, regardless of 7 days

    def test_baby_seat_bulk_price_from_two(self):
        # Website: "$60.00 per seat" and "$50.00 each when you take 2 or more"
        self.assertEqual(self.q(extras={"baby_seat": 1}).extras_total, Decimal("60.00"))
        self.assertEqual(self.q(extras={"baby_seat": 2}).extras_total, Decimal("100.00"))
        self.assertEqual(self.q(days=7, extras={"baby_seat": 3}).extras_total, Decimal("150.00"))
        line = [l for l in self.q(extras={"baby_seat": 2}).lines if l.code == "baby_seat"][0]
        self.assertEqual(line.unit_price, Decimal("50.00"))

    def test_bulk_price_editable(self):
        ExtraService.objects.filter(code="baby_seat").update(bulk_min_quantity=None, bulk_unit_price=None)
        self.assertEqual(self.q(extras={"baby_seat": 2}).extras_total, Decimal("120.00"))

    def test_baby_seat_zero_quantity_ignored(self):
        self.assertEqual(self.q(extras={"baby_seat": 0}).extras_total, Decimal("0.00"))

    def test_baby_seat_max_quantity_enforced(self):
        with self.assertRaises(ValidationError):
            self.q(extras={"baby_seat": 99})

    def test_driving_permit_flat_fee(self):
        self.assertEqual(self.q(extras={"driving_permit": 1}).extras_total, Decimal("25.00"))

    def test_full_combination(self):
        q = self.q(days=4, pickup="OUTSIDE_ZONE", ret="TOWN", extras={"baby_seat": 2, "driving_permit": 1})
        # 4×50 + 25 + 0 + 2×50 (bulk) + 25
        self.assertEqual(q.grand_total, Decimal("350.00"))

    def test_prices_come_from_database(self):
        ExtraService.objects.filter(code="baby_seat").update(price=Decimal("65.00"))
        self.assertEqual(self.q(extras={"baby_seat": 1}).extras_total, Decimal("65.00"))

    def test_unknown_or_location_extra_rejected(self):
        for code in ("free_upgrade", ExtraService.OUTSIDE_ZONE):
            with self.assertRaises(ValidationError):
                self.q(extras={code: 1})

    def test_tax_applied_when_configured(self):
        s = SiteSettings.load()
        s.tax_rate = Decimal("18.00")
        s.save()
        q = self.q(days=1)
        self.assertEqual(q.tax_amount, Decimal("9.00"))
        self.assertEqual(q.grand_total, Decimal("59.00"))

    def test_daily_rate_override_keeps_agreed_price(self):
        self.v.price_per_day = Decimal("80.00")
        self.v.save()
        q = build_quote(vehicle=self.v, pickup_at=self.start, return_at=self.start + timedelta(days=2),
                        pickup_type="AIRPORT", return_type="AIRPORT", daily_rate=Decimal("50.00"))
        self.assertEqual(q.rental_total, Decimal("100.00"))
