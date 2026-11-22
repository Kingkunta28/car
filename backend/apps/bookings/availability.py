from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Booking, BookingStatus, BookingStatusHistory


def turnaround() -> timedelta:
    return timedelta(hours=settings.BOOKING_TURNAROUND_HOURS)


def conflicting_bookings(vehicle, pickup_at: datetime, return_at: datetime, exclude_pk=None):
    """Active holds/reservations overlapping [pickup_at, return_at + turnaround).

    Both sides include the turnaround buffer: an existing booking blocks until
    its ``blocked_until``; the requested booking needs the car until its own
    return + turnaround.
    """
    slug = vehicle if isinstance(vehicle, str) else vehicle.slug
    qs = Booking.objects.filter(
        vehicle_slug=slug, blocks_inventory=True,
        pickup_at__lt=return_at + turnaround(), blocked_until__gt=pickup_at,
    )
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return qs


def is_available(vehicle, pickup_at: datetime, return_at: datetime, exclude_pk=None) -> bool:
    bookable = getattr(vehicle, "is_bookable", True)
    return bookable and not conflicting_bookings(vehicle, pickup_at, return_at, exclude_pk).exists()


def blocked_periods(vehicle, start: datetime, end: datetime) -> list[dict]:
    """Public, anonymised list of busy periods (no customer information)."""
    slug = vehicle if isinstance(vehicle, str) else vehicle.slug
    rows = Booking.objects.filter(
        vehicle_slug=slug, blocks_inventory=True, pickup_at__lt=end, blocked_until__gt=start,
    ).order_by("pickup_at").values_list("pickup_at", "blocked_until")
    return [{"start": s.isoformat(), "end": e.isoformat()} for s, e in rows]


def release_expired_holds(now=None) -> int:
    """Expire pending bookings whose hold lapsed. Paid bookings are never auto-expired."""
    now = now or timezone.now()
    count = 0
    ids = list(
        Booking.objects.filter(
            booking_status=BookingStatus.PENDING_CONFIRMATION, blocks_inventory=True,
            hold_expires_at__lt=now, amount_paid=0,
        ).values_list("pk", flat=True)[:500]
    )
    for pk in ids:
        with transaction.atomic():
            b = Booking.objects.select_for_update(skip_locked=True).filter(pk=pk).first()
            if not b or b.booking_status != BookingStatus.PENDING_CONFIRMATION or not b.blocks_inventory:
                continue
            if b.amount_paid > 0 or not b.hold_expires_at or b.hold_expires_at >= now:
                continue
            b.booking_status = BookingStatus.EXPIRED
            b.blocks_inventory = False
            b.status_reason = "Reservation hold expired before confirmation."
            b.save(update_fields=["booking_status", "blocks_inventory", "status_reason", "updated_at"])
            BookingStatusHistory.objects.create(
                booking=b, previous_status=BookingStatus.PENDING_CONFIRMATION, new_status=BookingStatus.EXPIRED,
                notes="Hold expired automatically.",
            )
            count += 1
    return count
