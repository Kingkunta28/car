"""Align service data with the public booking price rules."""
from decimal import Decimal

from django.db import migrations


def update_booking_prices(apps, schema_editor):
    ExtraService = apps.get_model("bookings", "ExtraService")
    alias = schema_editor.connection.alias
    ExtraService.objects.using(alias).filter(code="baby_seat").update(
        price=Decimal("60.00"),
        bulk_min_quantity=None,
        bulk_unit_price=None,
        description="Per seat, for the whole booking (not per day).",
    )
    ExtraService.objects.using(alias).filter(code="outside_zone_delivery").update(
        price=Decimal("25.00"),
        description="Charged once per booking when pickup or return is outside Zanzibar Airport / Zanzibar Town.",
    )


def restore_previous_booking_prices(apps, schema_editor):
    ExtraService = apps.get_model("bookings", "ExtraService")
    alias = schema_editor.connection.alias
    ExtraService.objects.using(alias).filter(code="baby_seat").update(
        price=Decimal("60.00"),
        bulk_min_quantity=2,
        bulk_unit_price=Decimal("50.00"),
        description="$60 per seat, or $50 each when you take 2 or more — per booking, not per day.",
    )
    ExtraService.objects.using(alias).filter(code="outside_zone_delivery").update(
        price=Decimal("25.00"),
        description="Charged separately for pickup and for return outside Zanzibar Airport / Zanzibar Town.",
    )


class Migration(migrations.Migration):
    dependencies = [("bookings", "0007_booking_language")]
    operations = [migrations.RunPython(update_booking_prices, restore_previous_booking_prices)]
