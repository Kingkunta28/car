"""Small helpers for building test data (no external factory library)."""
import json
from datetime import timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.accounts.models import AdminUser, Role
from apps.vehicles.models import Vehicle

PDF_BYTES = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def vehicle(**kw) -> Vehicle:
    defaults = dict(name="Toyota RAV4", brand="Toyota", model="RAV4", category="SUV",
                    price_per_day=Decimal("55.00"), transmission="AUTOMATIC", fuel_type="PETROL",
                    passenger_capacity=5, luggage_capacity=3)
    defaults.update(kw)
    return Vehicle.objects.create(**defaults)


def staff(role=Role.MANAGER, email=None, **kw) -> AdminUser:
    email = email or f"{role.lower()}@rafiki.test"
    return AdminUser.objects.create_user(email=email, password="Str0ng-Passw0rd!", full_name=f"{role.title()} User",
                                         role=role, **kw)


def future(days=10, hour=10):
    d = (timezone.localtime() + timedelta(days=days)).date()
    return d, f"{hour:02d}:00"


def booking_payload(vehicle_obj, *, start_days=10, days=3, pickup_type="AIRPORT", return_type="AIRPORT",
                    extras=None, payment_method="MANUAL", **overrides):
    pd, pt = future(start_days)
    rd = pd + timedelta(days=days)
    data = {
        "customer": {"full_name": "Amina Guest", "email": "amina@example.com", "phone": "+44 7700 900123",
                     "nationality": "British"},
        "vehicle": vehicle_obj.slug,
        "pickup_date": str(pd), "pickup_time": pt, "return_date": str(rd), "return_time": pt,
        "pickup_type": pickup_type, "return_type": return_type,
        "extras": extras or {},
        "payment_method": payment_method,
        "accept_terms": True,
    }
    if pickup_type in ("TOWN", "OUTSIDE_ZONE"):
        data["pickup_address"] = "Emerson Spice Hotel, Stone Town"
    if pickup_type == "OUTSIDE_ZONE":
        data["pickup_area"] = "Nungwi"
    if return_type in ("TOWN", "OUTSIDE_ZONE"):
        data["return_address"] = "Zuri Zanzibar, Kendwa"
    if return_type == "OUTSIDE_ZONE":
        data["return_area"] = "Kendwa"
    data.update(overrides)
    return data


def multipart(payload, **files):
    body = {"payload": json.dumps(payload)}
    body.update(files)
    return body


def pdf_upload(name="doc.pdf"):
    return SimpleUploadedFile(name, PDF_BYTES, content_type="application/pdf")


def png_upload(name="doc.png"):
    return SimpleUploadedFile(name, PNG_BYTES, content_type="image/png")
