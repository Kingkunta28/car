"""WhatsApp click-to-chat links (https://wa.me). No documents, ever."""
import re
from urllib.parse import quote

from apps.core.models import SiteSettings


def _digits(number: str) -> str:
    return re.sub(r"\D", "", number or "")


def booking_summary_text(b) -> str:
    extras = ", ".join(f"{e.service_name} x{e.quantity}" for e in b.extras.all()) or "None"
    lines = [
        f"*Rafiki Car Hire booking {b.booking_reference}*",
        f"Name: {b.customer.full_name}",
        f"Vehicle: {b.vehicle_name}",
        f"Pickup: {b.pickup_date:%d %b %Y} {b.pickup_time:%H:%M} — {b.location_label('pickup')}",
        f"Return: {b.return_date:%d %b %Y} {b.return_time:%H:%M} — {b.location_label('return')}",
        f"Additional services: {extras}",
        f"Grand total: ${b.grand_total:,.2f} USD",
        f"Payment: {b.get_payment_method_display()} ({b.get_payment_status_display()})",
    ]
    return "\n".join(lines)


def guest_to_owner_url(b) -> str | None:
    """Link the guest taps on the confirmation page to message the business."""
    number = _digits(SiteSettings.load().whatsapp_number)
    if not number:
        return None
    return f"https://wa.me/{number}?text={quote(booking_summary_text(b))}"


def guest_chat_url(b) -> str | None:
    """Link staff use to contact the guest directly."""
    number = _digits(b.customer.phone)
    if len(number) < 8:
        return None
    text = f"Hello {b.customer.full_name.split()[0]}, this is Rafiki Car Hire about your booking {b.booking_reference}."
    return f"https://wa.me/{number}?text={quote(text)}"


def owner_message_url(b) -> str | None:
    return guest_to_owner_url(b)
