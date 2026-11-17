"""Seed the core priced services from the business price list.

Prices are data, editable from the dashboard — never hard-coded in views.
"""
from decimal import Decimal

from django.db import migrations

SERVICES = [
    {"code": "outside_zone_delivery", "name": "Outside Free Zone delivery",
     "description": "Charged separately for pickup and for return outside Zanzibar Airport / Zanzibar Town.",
     "price": Decimal("25.00"), "pricing_type": "PER_BOOKING", "max_quantity": 1, "display_order": 0},
    {"code": "baby_seat", "name": "Baby seat",
     "description": "Per seat, for the whole booking (not per day).",
     "price": Decimal("60.00"), "pricing_type": "PER_UNIT", "max_quantity": 4, "display_order": 1},
    {"code": "driving_permit", "name": "Driving permit arrangement",
     "description": "We arrange your Zanzibar driving permit. Requires passport and driving licence copies. "
                    "Approval is decided by the issuing authority.",
     "price": Decimal("25.00"), "pricing_type": "PER_BOOKING", "max_quantity": 1, "requires_documents": True,
     "display_order": 2},
]


def seed(apps, schema_editor):
    ExtraService = apps.get_model("bookings", "ExtraService")
    for svc in SERVICES:
        ExtraService.objects.update_or_create(code=svc["code"], defaults={**svc, "is_system": True, "is_active": True})
    SiteSettings = apps.get_model("core", "SiteSettings")
    SiteSettings.objects.get_or_create(pk=1)


def unseed(apps, schema_editor):
    apps.get_model("bookings", "ExtraService").objects.filter(code__in=[s["code"] for s in SERVICES]).delete()


class Migration(migrations.Migration):
    dependencies = [("bookings", "0001_initial"), ("core", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]
