import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.core.utils import sha256_hex

from .models import Booking, BookingAccessToken


def issue_access_token(booking: Booking, purpose: str = "guest", days: int | None = None) -> str:
    """Create a new guest token and return the RAW value (only time it exists)."""
    raw = secrets.token_urlsafe(32)
    BookingAccessToken.objects.create(
        booking=booking, token_hash=sha256_hex(raw), purpose=purpose,
        expires_at=timezone.now() + timedelta(days=days or settings.BOOKING_ACCESS_TOKEN_DAYS),
    )
    return raw


def resolve_booking(reference: str | None, raw_token: str | None) -> Booking | None:
    """Return the booking only if reference AND a valid, unexpired token match.

    A booking reference alone never grants access.
    """
    if not reference or not raw_token or len(raw_token) > 200:
        return None
    now = timezone.now()
    token = (
        BookingAccessToken.objects.select_related("booking", "booking__vehicle", "booking__customer")
        .filter(token_hash=sha256_hex(raw_token.strip()), revoked_at__isnull=True, expires_at__gt=now,
                booking__booking_reference=reference.strip().upper())
        .first()
    )
    if token is None:
        return None
    BookingAccessToken.objects.filter(pk=token.pk).update(last_used_at=now)
    return token.booking


def revoke_tokens(booking: Booking, purpose: str | None = None) -> int:
    qs = booking.access_tokens.filter(revoked_at__isnull=True)
    if purpose:
        qs = qs.filter(purpose=purpose)
    return qs.update(revoked_at=timezone.now())


def guest_manage_url(booking: Booking, raw_token: str) -> str:
    # Credentials travel in the URL *fragment*, which browsers never send to servers or proxies.
    return f"{settings.FRONTEND_URL}/booking/manage#ref={booking.booking_reference}&token={raw_token}"
