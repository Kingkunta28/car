"""Persist and retrieve the customer voucher through private storage."""
from hashlib import sha256

from django.core.files.base import ContentFile

from .pdf import render_confirmation_pdf


def ensure_voucher(booking):
    """Return the saved private voucher, creating it from the booking snapshot if needed."""
    voucher = booking.voucher_file
    if voucher:
        try:
            if voucher.storage.exists(voucher.name):
                return voucher
        except Exception:
            # A transient private-storage failure may be recoverable on retry.
            pass

    pdf = render_confirmation_pdf(booking)
    booking.voucher_file.save(
        f"{booking.booking_reference}.pdf", ContentFile(pdf), save=False,
    )
    booking.voucher_sha256 = sha256(pdf).hexdigest()
    booking.save(update_fields=["voucher_file", "voucher_sha256", "updated_at"])
    return booking.voucher_file
