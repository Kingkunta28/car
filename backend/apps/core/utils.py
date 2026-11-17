import hashlib
import secrets
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction

CENT = Decimal("0.01")
# Unambiguous alphabet for references read over the phone (no 0/O, 1/I/L).
REF_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def money(value) -> Decimal:
    """Normalise any numeric value to a 2-dp Decimal (never via float)."""
    if isinstance(value, float):
        value = repr(value)
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def random_reference(prefix: str, length: int = 7) -> str:
    return f"{prefix}-" + "".join(secrets.choice(REF_ALPHABET) for _ in range(length))


def sha256_hex(value: str | bytes) -> str:
    if isinstance(value, str):
        value = value.encode()
    return hashlib.sha256(value).hexdigest()


def next_sequence_value(key: str) -> int:
    """Return the next value for ``key``. Must be called inside a transaction."""
    from .models import Sequence

    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError("next_sequence_value() must run inside transaction.atomic()")
    Sequence.objects.bulk_create([Sequence(key=key, last_value=0)], ignore_conflicts=True)
    seq = Sequence.objects.select_for_update().get(key=key)
    seq.last_value += 1
    seq.save(update_fields=["last_value"])
    return seq.last_value


def client_ip(request) -> str | None:
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def audit(action: str, *, actor=None, target=None, summary: str = "", request=None, **metadata):
    from .models import AuditLog

    if actor is not None and not getattr(actor, "is_authenticated", False):
        actor = None
    return AuditLog.objects.create(
        actor=actor,
        action=action,
        target_type=target._meta.label_lower if target is not None else "",
        target_id=str(target.pk) if target is not None else "",
        summary=summary[:255],
        metadata=metadata,
        ip_address=client_ip(request),
    )
