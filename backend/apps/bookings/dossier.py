"""Generation and private storage for staff-only booking dossiers."""
import hashlib
import json
import logging

from django.core.files.base import ContentFile
from django.db import transaction

from apps.core.models import SiteSettings
from apps.core.utils import audit

from .dossier_pdf import render_booking_dossier
from .models import BookingDossier

logger = logging.getLogger(__name__)


def _source_digest(booking):
    docs = list(booking.documents.order_by("document_type", "uploaded_at").values(
        "id", "document_type", "file_kind", "file_size", "sha256", "verification_status", "secure_file",
        "uploaded_at", "purged_at",
    ))
    flight = getattr(booking, "flight", None)
    payload = {
        "booking": {field: str(getattr(booking, field)) for field in (
            "updated_at", "booking_reference", "booking_status", "payment_status", "payment_method",
            "amount_paid", "grand_total", "tax_amount", "currency", "pickup_date", "pickup_time",
            "return_date", "return_time", "rental_days", "pickup_type", "pickup_area", "pickup_address",
            "pickup_instructions", "return_type", "return_area", "return_address", "return_instructions",
            "daily_rate", "pricing_breakdown", "customer_notes",
        )},
        "customer": {field: str(getattr(booking.customer, field)) for field in
                     ("full_name", "email", "phone", "nationality")},
        "vehicle": {field: str(getattr(booking.vehicle, field)) for field in ("name", "brand", "model", "year")},
        "flight": ({field: str(getattr(flight, field)) for field in
                    ("airline_name", "flight_number", "arrival_date", "arrival_time", "arrival_airport", "notes")}
                   if flight else None),
        "documents": [{k: (v.isoformat() if hasattr(v, "isoformat") else str(v) if v is not None else None)
                       for k, v in doc.items()} for doc in docs],
        "site_updated_at": SiteSettings.load().updated_at.isoformat(),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


@transaction.atomic
def ensure_dossier(booking, *, actor=None, request=None) -> BookingDossier:
    """Create or refresh the private dossier when its source data has changed."""
    dossier, _ = BookingDossier.objects.select_for_update().get_or_create(booking=booking)
    digest = _source_digest(booking)
    if dossier.pdf_file and dossier.source_digest == digest:
        try:
            if dossier.pdf_file.storage.exists(dossier.pdf_file.name):
                return dossier
        except Exception:
            logger.exception("Could not check stored dossier %s", booking.booking_reference)

    try:
        data = render_booking_dossier(booking)
    except Exception:
        logger.exception("Booking dossier rendering failed for %s", booking.booking_reference)
        raise

    old_name = dossier.pdf_file.name if dossier.pdf_file else ""
    dossier.pdf_file.save(f"{booking.booking_reference}-dossier.pdf", ContentFile(data), save=False)
    dossier.source_digest = digest
    dossier.save(update_fields=["pdf_file", "source_digest", "updated_at"])
    if old_name and old_name != dossier.pdf_file.name:
        try:
            dossier.pdf_file.storage.delete(old_name)
        except Exception:
            logger.exception("Could not remove replaced dossier file for %s", booking.booking_reference)
    audit("dossier.generated", actor=actor, target=booking, request=request,
          summary=f"Private booking dossier generated for {booking.booking_reference}", document_count=booking.documents.count())
    return dossier
