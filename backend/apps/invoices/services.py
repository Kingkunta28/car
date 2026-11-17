import logging
from decimal import Decimal

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from apps.bookings.models import BookingFlight
from apps.core.models import SiteSettings
from apps.core.pdf import logo_path, site_dict
from apps.core.utils import audit, next_sequence_value, sha256_hex

from .models import Invoice, InvoiceItem, InvoiceStatus
from .pdf import render_invoice_pdf

logger = logging.getLogger(__name__)


def _fmt_dt(d, t):
    return f"{d:%a %d %b %Y} at {t:%H:%M}"


def build_snapshot(booking, *, invoice_number, issue_date, revision_number, supersedes_number="", reason="") -> dict:
    site = SiteSettings.load()
    bd = booking.pricing_breakdown
    items = []
    for i, line in enumerate(bd.get("lines", [])):
        if line["kind"] in ("pickup", "return") and Decimal(line["total"]) == 0:
            desc = f'{line["description"]} (free)'
        else:
            desc = line["description"]
        items.append({"description": desc, "quantity": line["quantity"], "unit_price": line["unit_price"],
                      "total_price": line["total"], "sort_order": i})
    flight = BookingFlight.objects.filter(booking=booking).first()
    v = booking.vehicle
    return {
        "invoice_number": invoice_number,
        "booking_reference": booking.booking_reference,
        "issue_date": f"{issue_date:%d %B %Y}",
        "revision_number": revision_number,
        "supersedes_number": supersedes_number,
        "revision_reason": reason,
        "currency": booking.currency,
        "site": site_dict(site),
        "customer": {"full_name": booking.customer.full_name, "email": booking.customer.email,
                     "phone": booking.customer.phone, "nationality": booking.customer.nationality},
        "trip": {
            "vehicle": f"{v.name} ({v.brand} {v.model}{', ' + str(v.year) if v.year else ''})",
            "rental_days": booking.rental_days,
            "pickup_datetime": _fmt_dt(booking.pickup_date, booking.pickup_time),
            "return_datetime": _fmt_dt(booking.return_date, booking.return_time),
            "pickup_location": booking.location_label("pickup"),
            "return_location": booking.location_label("return"),
            "pickup_address": booking.location_address("pickup"),
            "return_address": booking.location_address("return"),
        },
        "flight": {
            "summary": f"{flight.airline_name} {flight.flight_number}".strip(),
            "arrival": f"{flight.arrival_date or ''} {flight.arrival_time.strftime('%H:%M') if flight.arrival_time else ''}".strip(),
        } if flight and (flight.airline_name or flight.flight_number) else None,
        "items": items,
        "subtotal": bd.get("subtotal"),
        "tax_rate": bd.get("tax_rate"),
        "tax_label": bd.get("tax_label"),
        "tax_amount": str(booking.tax_amount),
        "total_amount": str(booking.grand_total),
        "payment_method": booking.get_payment_method_display(),
        "payment_method_code": booking.payment_method,
        "payment_status": booking.get_payment_status_display(),
        "booking_status": booking.get_booking_status_display(),
        "payment_instructions": site.payment_instructions,
        "terms": site.invoice_terms,
        "footer": site.invoice_footer,
    }


def render_and_store_pdf(invoice: Invoice) -> bool:
    try:
        pdf = render_invoice_pdf(invoice.snapshot, logo_path(SiteSettings.load()))
    except Exception:  # never lose the invoice because rendering failed
        logger.exception("Invoice PDF rendering failed for %s", invoice.invoice_number)
        return False
    if invoice.pdf_file:
        invoice.pdf_file.delete(save=False)
    invoice.pdf_file.save(f"{invoice.invoice_number}.pdf", ContentFile(pdf), save=False)
    invoice.pdf_sha256 = sha256_hex(pdf)
    invoice.save(update_fields=["pdf_file", "pdf_sha256"])
    return True


def ensure_pdf(invoice: Invoice) -> bool:
    """Make sure the stored PDF exists (re-render from snapshot if missing)."""
    if invoice.pdf_file:
        try:
            if invoice.pdf_file.storage.exists(invoice.pdf_file.name):
                return True
        except Exception:
            pass
    return render_and_store_pdf(invoice)


@transaction.atomic
def issue_invoice(booking, *, actor=None, reason: str = "") -> Invoice:
    """Issue the first invoice for a booking, or a revision superseding the current one.

    Issued invoices are never edited: a revision preserves the original and
    links to it. Numbering is sequential per year and concurrency-safe.
    """
    current = (Invoice.objects.select_for_update().filter(booking=booking, invoice_status=InvoiceStatus.ISSUED)
               .first())
    today = timezone.localdate()
    if current is None:
        seq = next_sequence_value(f"RCI-{today.year}")
        number, revision, root = f"RCI-{today.year}-{seq:06d}", 0, None
    else:
        root = current.original_invoice or current
        revision = (Invoice.objects.filter(booking=booking).order_by("-revision_number")
                    .values_list("revision_number", flat=True).first() or 0) + 1
        number = f"{root.invoice_number}-R{revision}"
        current.invoice_status = InvoiceStatus.SUPERSEDED
        current.save(update_fields=["invoice_status"])

    snap = build_snapshot(booking, invoice_number=number, issue_date=today, revision_number=revision,
                          supersedes_number=current.invoice_number if current else "", reason=reason)
    invoice = Invoice.objects.create(
        invoice_number=number, booking=booking, issue_date=today, revision_number=revision,
        original_invoice=root, supersedes=current, revision_reason=reason[:255],
        subtotal=Decimal(snap["subtotal"]), tax_amount=booking.tax_amount, total_amount=booking.grand_total,
        currency=booking.currency, snapshot=snap,
        issued_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    InvoiceItem.objects.bulk_create([
        InvoiceItem(invoice=invoice, description=i["description"][:255], quantity=i["quantity"],
                    unit_price=Decimal(i["unit_price"]), total_price=Decimal(i["total_price"]),
                    sort_order=i["sort_order"])
        for i in snap["items"]
    ])
    render_and_store_pdf(invoice)
    audit("invoice.revised" if current else "invoice.issued", actor=actor, target=invoice,
          summary=f"{number} for {booking.booking_reference}", total=str(invoice.total_amount))
    return invoice


def current_invoice(booking) -> Invoice | None:
    return booking.invoices.filter(invoice_status=InvoiceStatus.ISSUED).first()
