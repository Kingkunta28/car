"""Booking-time vehicle snapshots and the server-authoritative static rates.

The React catalogue owns vehicle presentation and attributes. The backend keeps
only the approved daily rates needed to validate money before saving a booking.
"""
from decimal import Decimal
from types import SimpleNamespace


STATIC_VEHICLE_RATES = {
    "toyota-land-cruiser-prado-2020": Decimal("150.00"),
    "toyota-land-cruiser-prado-classic": Decimal("85.00"),
    "toyota-harrier-2015": Decimal("45.00"),
    "toyota-rav4-2018": Decimal("35.00"),
    "toyota-vanguard-2018": Decimal("40.00"),
    "toyota-rav4-2016-3-door": Decimal("30.00"),
    "suzuki-escudo-2019": Decimal("26.00"),
    "suzuki-escudo-grand-vitara": Decimal("50.00"),
    "nissan-juke-2018": Decimal("25.00"),
    "toyota-ist-2018": Decimal("20.00"),
    "toyota-hilux": Decimal("90.00"),
    "toyota-alphard": Decimal("45.00"),
}


def model_vehicle_snapshot(vehicle, *, agreed_rate=None) -> dict:
    """Convert a legacy Vehicle row to the same immutable shape as the frontend."""
    primary = vehicle.primary_image
    image_url = primary.image.url if primary else ""
    return {
        "id": vehicle.slug,
        "slug": vehicle.slug,
        "name": vehicle.name,
        "brand": vehicle.brand,
        "model": vehicle.model,
        "year": vehicle.year,
        "category": vehicle.category,
        "category_display": vehicle.get_category_display(),
        "description": vehicle.description,
        "price_per_day": str(agreed_rate if agreed_rate is not None else vehicle.price_per_day),
        "transmission": vehicle.transmission,
        "transmission_display": vehicle.get_transmission_display(),
        "fuel_type": vehicle.fuel_type,
        "fuel_type_display": vehicle.get_fuel_type_display(),
        "passenger_capacity": vehicle.passenger_capacity,
        "luggage_capacity": vehicle.luggage_capacity,
        "doors": vehicle.doors,
        "features": list(vehicle.features.values_list("feature_name", flat=True)),
        "availability_status": vehicle.availability_status,
        "availability_display": vehicle.get_availability_status_display(),
        "main_image": image_url,
        "gallery_images": [image.image.url for image in vehicle.images.exclude(pk=primary.pk)] if primary else [],
    }


def quote_vehicle(snapshot: dict):
    """Minimal priceable vehicle value; no Vehicle model instance is needed."""
    return SimpleNamespace(
        slug=snapshot["slug"], name=snapshot["name"],
        price_per_day=Decimal(str(snapshot["price_per_day"])), is_bookable=True,
    )


def booking_vehicle_snapshot(booking) -> dict:
    """Return the saved snapshot, falling back to its legacy relation if needed."""
    if booking.vehicle_snapshot:
        return booking.vehicle_snapshot
    if booking.vehicle_id:
        return model_vehicle_snapshot(booking.vehicle, agreed_rate=booking.daily_rate)
    return {"id": booking.vehicle_slug, "slug": booking.vehicle_slug, "name": "Vehicle",
            "brand": "", "model": "", "year": None, "transmission_display": "", "image": ""}


def booking_vehicle_object(booking):
    """Object-style adapter for existing email templates."""
    return SimpleNamespace(**booking_vehicle_snapshot(booking))
