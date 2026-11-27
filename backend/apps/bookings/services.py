"""Booking workflows: creation, status transitions and administrative changes."""
import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.exceptions import BusinessRuleError, ConflictError
from apps.core.files import file_sha256, validate_upload
from apps.core.utils import audit, random_reference
from apps.customers.models import Customer
from apps.vehicles.models import Vehicle
import pypdfium2 as pdfium

from . import availability
from .models import (
    Booking, BookingDocument, BookingExtra, BookingFlight, BookingStatus, BookingStatusHistory, DocumentType,
    ExtraService, LocationType,
)
from .pricing import Quote, build_quote
from .tokens import issue_access_token
from .vehicle_data import model_vehicle_snapshot, quote_vehicle

logger = logging.getLogger(__name__)
MAX_IDENTITY_PDF_PAGES = 12


def validate_identity_upload(upload):
    """Validate identity files and bound the cost of rendering uploaded PDFs."""
    kind = validate_upload(upload)
    if kind != "pdf":
        return kind
    upload.seek(0)
    try:
        source = pdfium.PdfDocument(upload.read())
        page_count = len(source)
        source.close()
    except Exception as exc:
        raise ValidationError("The uploaded PDF could not be opened. Upload an unlocked, valid PDF.") from exc
    finally:
        upload.seek(0)
    if page_count < 1 or page_count > MAX_IDENTITY_PDF_PAGES:
        raise ValidationError(f"Identity PDFs must contain between 1 and {MAX_IDENTITY_PDF_PAGES} pages.")
    return kind

OVERLAP_MESSAGE = "Sorry — this vehicle is already reserved for some or all of the selected dates."


def combine(d: date, t: time) -> datetime:
    return timezone.make_aware(datetime.combine(d, t), timezone.get_default_timezone())


def validate_rental_window(pickup_at: datetime, return_at: datetime, *, enforce_lead=True):
    now = timezone.now()
    errors = {}
    if enforce_lead and pickup_at < now + timedelta(hours=settings.BOOKING_MIN_LEAD_HOURS):
        errors["pickup_date"] = f"Pickup must be at least {settings.BOOKING_MIN_LEAD_HOURS} hours from now."
    if pickup_at > now + timedelta(days=settings.BOOKING_MAX_ADVANCE_DAYS):
        errors["pickup_date"] = "Pickup date is too far in the future."
    if return_at <= pickup_at:
        errors["return_date"] = "Return must be after pickup."
    elif return_at - pickup_at > timedelta(days=settings.BOOKING_MAX_RENTAL_DAYS):
        errors["return_date"] = f"Rentals longer than {settings.BOOKING_MAX_RENTAL_DAYS} days need a custom quote."
    if errors:
        raise ValidationError(errors)


def validate_locations(data: dict):
    """Conditional address rules for each leg."""
    errors = {}
    for leg in ("pickup", "return"):
        loc = data.get(f"{leg}_type")
        if loc in (LocationType.TOWN, LocationType.OUTSIDE_ZONE) and not (data.get(f"{leg}_address") or "").strip():
            errors[f"{leg}_address"] = "Please enter the exact address, hotel or property name."
        if loc == LocationType.OUTSIDE_ZONE and not (data.get(f"{leg}_area") or "").strip():
            errors[f"{leg}_area"] = "Please enter the area or destination."
        if loc == LocationType.AIRPORT:
            data[f"{leg}_area"] = ""
            data[f"{leg}_address"] = ""
        elif loc == LocationType.TOWN:
            data[f"{leg}_area"] = ""
    if errors:
        raise ValidationError(errors)


def _record_status(booking, field, previous, new, actor=None, notes=""):
    BookingStatusHistory.objects.create(
        booking=booking, status_field=field, previous_status=previous or "", new_status=new,
        changed_by=actor if getattr(actor, "is_authenticated", False) else None, notes=notes,
    )


def _apply_quote(booking: Booking, quote: Quote):
    booking.rental_days = quote.rental_days
    booking.daily_rate = quote.daily_rate
    booking.rental_total = quote.rental_total
    booking.pickup_fee = quote.pickup_fee
    booking.return_fee = quote.return_fee
    booking.extras_total = quote.extras_total
    booking.tax_amount = quote.tax_amount
    booking.grand_total = quote.grand_total
    booking.currency = quote.currency
    booking.pricing_breakdown = quote.as_dict()


def _write_extras(booking: Booking, quote: Quote):
    booking.extras.all().delete()
    BookingExtra.objects.bulk_create([
        BookingExtra(
            booking=booking, extra_service_id=line.extra_service_id, code=line.code, service_name=line.description,
            pricing_type=line.pricing_type, quantity=line.quantity, unit_price=line.unit_price, total_price=line.total,
        )
        for line in quote.extra_lines()
    ])


def _is_overlap_error(exc: IntegrityError) -> bool:
    return "booking_no_vehicle_overlap" in str(exc)


@dataclass
class BookingResult:
    booking: Booking
    access_token: str
    invoice: object


def create_booking(data: dict, *, documents: dict | None = None, request=None) -> BookingResult:
    """Create a booking from validated serializer data.

    Runs in one transaction: customer upsert, server-side pricing, extras,
    flight, private documents, invoice,
    and queued notifications (sent after commit).
    """
    from apps.invoices.services import current_invoice, issue_invoice
    from apps.notifications import services as notify

    documents = documents or {}
    pickup_at = combine(data["pickup_date"], data["pickup_time"])
    return_at = combine(data["return_date"], data["return_time"])
    validate_rental_window(pickup_at, return_at)
    validate_locations(data)

    extras = dict(data.get("extras") or {})
    if extras.get(ExtraService.DRIVING_PERMIT):
        extras[ExtraService.DRIVING_PERMIT] = 1
        missing = [t for t in (DocumentType.PASSPORT, DocumentType.DRIVING_LICENCE) if not documents.get(t)]
        if missing:
            raise ValidationError({"documents": "The driving permit service requires a copy of your passport "
                                                "and your driving licence."})
    for f in documents.values():
        validate_identity_upload(f)

    submission_key = data.get("submission_key")
    if submission_key:
        existing = Booking.objects.filter(submission_key=submission_key).first()
        if existing:
            invoice = current_invoice(existing) or issue_invoice(existing)
            token = issue_access_token(existing, purpose="confirmation")
            return BookingResult(booking=existing, access_token=token, invoice=invoice)

    try:
        with transaction.atomic():
            vehicle_model = data.get("vehicle_model")
            if vehicle_model is not None:
                availability.release_expired_holds()
                vehicle = Vehicle.objects.select_for_update().get(pk=vehicle_model.pk)
                if not vehicle.is_bookable:
                    raise BusinessRuleError("This vehicle is not currently available for booking.")
                vehicle_snapshot = model_vehicle_snapshot(vehicle)
            else:
                vehicle = None
                vehicle_snapshot = data["vehicle_snapshot"]
            vehicle_slug = data["vehicle_slug"]
            # The public frontend catalogue is not inventory-managed in Django.
            # Preserve the legacy database vehicle guard for staff-managed cars.
            if vehicle_model is not None and availability.conflicting_bookings(vehicle_slug, pickup_at, return_at).exists():
                raise ConflictError(OVERLAP_MESSAGE)

            quote = build_quote(vehicle=quote_vehicle(vehicle_snapshot), pickup_at=pickup_at, return_at=return_at,
                                pickup_type=data["pickup_type"], return_type=data["return_type"], extras=extras)
            # total_amount from the browser is a display estimate only. Always
            # persist the server-calculated quote, without requiring a separate
            # availability or charge-confirmation round trip.

            c = data["customer"]
            customer, created = Customer.objects.get_or_create(
                email__iexact=c["email"].strip(),
                defaults={"email": c["email"], "full_name": c["full_name"], "phone": c["phone"],
                          "nationality": c.get("nationality", "")},
            )
            if not created:
                customer.full_name, customer.phone = c["full_name"], c["phone"]
                customer.nationality = c.get("nationality") or customer.nationality
                customer.save()

            booking = Booking(
                submission_key=submission_key, booking_reference=_unique_reference(), customer=customer, vehicle=vehicle,
                vehicle_slug=vehicle_slug, vehicle_snapshot=vehicle_snapshot,
                pickup_date=data["pickup_date"], pickup_time=data["pickup_time"],
                return_date=data["return_date"], return_time=data["return_time"],
                pickup_at=pickup_at, return_at=return_at, blocked_until=return_at + availability.turnaround(),
                pickup_type=data["pickup_type"], pickup_area=data.get("pickup_area", ""),
                pickup_address=data.get("pickup_address", ""), pickup_instructions=data.get("pickup_instructions", ""),
                return_type=data["return_type"], return_area=data.get("return_area", ""),
                return_address=data.get("return_address", ""), return_instructions=data.get("return_instructions", ""),
                payment_method=data["payment_method"], language=data.get("language", "en"),
                customer_notes=c.get("additional_info", ""),
                # Static catalogue vehicles remain selectable but wait for
                # staff confirmation without reserving a Django fleet record.
                # Legacy database vehicles use the same confirmation workflow
                # and retain their existing inventory checks.
                booking_status=BookingStatus.PENDING_CONFIRMATION,
                hold_expires_at=(timezone.now() + timedelta(hours=settings.BOOKING_HOLD_HOURS)
                                 if vehicle_model is not None else None),
                # Static frontend catalogue bookings do not reserve a Django fleet
                # record or block another visitor from booking the same catalogue car.
                blocks_inventory=vehicle_model is not None,
            )
            _apply_quote(booking, quote)
            booking.save()
            _write_extras(booking, quote)

            flight = data.get("flight") or {}
            if any(v for v in flight.values()):
                BookingFlight.objects.create(booking=booking, **{
                    **flight, "arrival_airport": flight.get("arrival_airport") or settings.DEFAULT_ARRIVAL_AIRPORT,
                })

            for doc_type, f in documents.items():
                kind = validate_identity_upload(f)
                BookingDocument.objects.create(
                    booking=booking, document_type=doc_type, secure_file=f, original_filename=(f.name or "")[:255],
                    file_kind=kind, file_size=f.size, sha256=file_sha256(f),
                )

            _record_status(booking, BookingStatusHistory.Field.BOOKING, "", booking.booking_status,
                           notes="Booking submitted by guest; awaiting staff confirmation.")
            token = issue_access_token(booking, purpose="confirmation")
            invoice = issue_invoice(booking)
            notify.booking_submitted(booking, invoice)
            audit("booking.created", target=booking, summary=f"Booking {booking.booking_reference} submitted",
                  request=request, grand_total=str(booking.grand_total))
    except IntegrityError as exc:
        if _is_overlap_error(exc):
            raise ConflictError(OVERLAP_MESSAGE) from exc
        # A concurrent retry can race the preflight lookup. The database
        # uniqueness constraint ensures only one booking is committed.
        if submission_key:
            existing = Booking.objects.filter(submission_key=submission_key).first()
            if existing:
                invoice = current_invoice(existing) or issue_invoice(existing)
                token = issue_access_token(existing, purpose="confirmation")
                return BookingResult(booking=existing, access_token=token, invoice=invoice)
        raise
    if documents:
        # The booking is already committed. A dossier-rendering failure must
        # never roll back a valid reservation request or its invoice.
        try:
            from .dossier import ensure_dossier

            ensure_dossier(booking)
        except Exception:
            logger.exception("Private booking dossier generation failed for %s", booking.booking_reference)
    return BookingResult(booking=booking, access_token=token, invoice=invoice)


def _unique_reference() -> str:
    for _ in range(10):
        ref = random_reference("RCH", 7)
        if not Booking.objects.filter(booking_reference=ref).exists():
            return ref
    raise RuntimeError("Could not allocate a booking reference")


# --------------------------------------------------------------------------
# Status transitions
# --------------------------------------------------------------------------
ALLOWED_TRANSITIONS = {
    BookingStatus.PENDING_CONFIRMATION: {BookingStatus.CONFIRMED, BookingStatus.REJECTED, BookingStatus.CANCELLED},
    BookingStatus.CONFIRMED: {BookingStatus.CANCELLED, BookingStatus.COMPLETED},
    BookingStatus.EXPIRED: {BookingStatus.CONFIRMED, BookingStatus.CANCELLED},
    BookingStatus.REJECTED: set(),
    BookingStatus.CANCELLED: set(),
    BookingStatus.COMPLETED: set(),
}


def change_status(booking: Booking, new_status: str, *, actor=None, notes: str = "", request=None,
                  notify_guest: bool = True) -> Booking:
    from apps.notifications import services as notify

    try:
        with transaction.atomic():
            b = Booking.objects.select_for_update().get(pk=booking.pk)
            previous = b.booking_status
            if new_status not in ALLOWED_TRANSITIONS.get(previous, set()):
                raise BusinessRuleError(
                    f"A booking that is {BookingStatus(previous).label.lower()} cannot be changed to "
                    f"{BookingStatus(new_status).label.lower()}."
                )
            now = timezone.now()
            b.booking_status = new_status
            b.status_reason = notes[:255]
            if new_status == BookingStatus.CONFIRMED:
                if previous == BookingStatus.EXPIRED and b.vehicle_id is not None:
                    if availability.conflicting_bookings(b.vehicle_slug, b.pickup_at, b.return_at, exclude_pk=b.pk).exists():
                        raise ConflictError("The vehicle has since been reserved by another booking for these dates.")
                b.blocks_inventory, b.hold_expires_at, b.confirmed_at = (b.vehicle_id is not None), None, now
            elif new_status in (BookingStatus.REJECTED, BookingStatus.CANCELLED):
                b.blocks_inventory = False
                b.cancelled_at = now
            elif new_status == BookingStatus.COMPLETED:
                b.blocks_inventory = False
                b.completed_at = now
            b.save()
            _record_status(b, BookingStatusHistory.Field.BOOKING, previous, new_status, actor, notes)
            audit(f"booking.{new_status.lower()}", actor=actor, target=b, request=request,
                  summary=f"{b.booking_reference}: {previous} → {new_status}", notes=notes)
            if notify_guest:
                notify.booking_status_changed(b, new_status, notes)
    except IntegrityError as exc:
        if _is_overlap_error(exc):
            raise ConflictError("The vehicle has since been reserved by another booking for these dates.") from exc
        raise
    booking.refresh_from_db()
    return booking


def set_payment_status(booking: Booking, new_status: str, *, actor=None, notes=""):
    """Called by the payments app only (after verified money movement)."""
    if booking.payment_status != new_status:
        _record_status(booking, BookingStatusHistory.Field.PAYMENT, booking.payment_status, new_status, actor, notes)
        booking.payment_status = new_status


# --------------------------------------------------------------------------
# Administrative changes to financial details → revised invoice
# --------------------------------------------------------------------------
FINANCIAL_FIELDS = {
    "vehicle", "pickup_date", "pickup_time", "return_date", "return_time", "pickup_type", "return_type", "extras",
}
EDITABLE_FIELDS = FINANCIAL_FIELDS | {
    "pickup_area", "pickup_address", "pickup_instructions", "return_area", "return_address", "return_instructions",
}


def modify_booking(booking: Booking, changes: dict, *, actor, reason: str, request=None):
    """Apply staff changes. Financial changes always issue a revised invoice."""
    from apps.invoices.services import issue_invoice
    from apps.notifications import services as notify

    unknown = set(changes) - EDITABLE_FIELDS
    if unknown:
        raise ValidationError({"changes": f"Fields cannot be edited: {', '.join(sorted(unknown))}"})
    if not reason.strip():
        raise ValidationError({"reason": "Please give a reason for the change."})

    try:
        with transaction.atomic():
            b = Booking.objects.select_for_update().select_related("vehicle").get(pk=booking.pk)
            original_vehicle_slug = b.vehicle_slug
            if not b.is_open:
                raise BusinessRuleError("Only pending or confirmed bookings can be modified.")
            data = {f: getattr(b, f) for f in EDITABLE_FIELDS - {"extras"}}
            data["extras"] = {e.code: e.quantity for e in b.extras.all()}
            before = {k: str(v) for k, v in data.items()}
            if "extras" in changes:
                changes["extras"] = {k: int(v) for k, v in changes["extras"].items() if int(v or 0) > 0}
            # Keep only real changes, so an unchanged form never issues a revision.
            changes = {k: v for k, v in changes.items() if v != data.get(k)}
            if not changes:
                raise BusinessRuleError("Nothing was changed.")
            data.update(changes)
            validate_locations(data)
            vehicle_ref = data["vehicle"]
            if vehicle_ref is not None:
                if isinstance(vehicle_ref, Vehicle):
                    vehicle = Vehicle.objects.select_for_update().get(pk=vehicle_ref.pk)
                    vehicle_slug = vehicle.slug
                    vehicle_snapshot = b.vehicle_snapshot if vehicle_slug == original_vehicle_slug and b.vehicle_snapshot \
                        else model_vehicle_snapshot(vehicle, agreed_rate=b.daily_rate if vehicle_slug == original_vehicle_slug else None)
                elif vehicle_ref == original_vehicle_slug:
                    vehicle = None
                    vehicle_slug = b.vehicle_slug
                    vehicle_snapshot = b.vehicle_snapshot
                else:
                    raise BusinessRuleError("A static-catalogue booking can keep its selected car or switch to a saved vehicle.")
            else:
                vehicle = None
                vehicle_slug = b.vehicle_slug
                vehicle_snapshot = b.vehicle_snapshot
            pickup_at = combine(data["pickup_date"], data["pickup_time"])
            return_at = combine(data["return_date"], data["return_time"])
            validate_rental_window(pickup_at, return_at, enforce_lead=False)
            if b.blocks_inventory and availability.conflicting_bookings(vehicle_slug, pickup_at, return_at,
                                                                        exclude_pk=b.pk).exists():
                raise ConflictError(OVERLAP_MESSAGE)
            if ExtraService.DRIVING_PERMIT in data["extras"] and not b.documents.exclude(
                    verification_status="PURGED").exists():
                raise BusinessRuleError("Driving permit arrangement needs the guest's uploaded documents.")

            financial_change = bool(FINANCIAL_FIELDS & set(changes))
            for f in EDITABLE_FIELDS - {"extras", "vehicle"}:
                setattr(b, f, data[f])
            b.vehicle = vehicle
            b.vehicle_slug = vehicle_slug
            b.vehicle_snapshot = vehicle_snapshot
            b.pickup_at, b.return_at = pickup_at, return_at
            b.blocked_until = return_at + availability.turnaround()
            invoice = None
            if financial_change:
                # Keep the originally agreed daily rate unless the vehicle changed.
                same_vehicle = vehicle_slug == original_vehicle_slug
                quote = build_quote(vehicle=quote_vehicle(vehicle_snapshot), pickup_at=pickup_at, return_at=return_at,
                                    pickup_type=data["pickup_type"], return_type=data["return_type"],
                                    extras=data["extras"], daily_rate=b.daily_rate if same_vehicle else None)
                _apply_quote(b, quote)
                _write_extras(b, quote)
            b.save()
            from apps.payments.services import recalculate_booking_payment_status
            recalculate_booking_payment_status(b, actor=actor)
            audit("booking.modified", actor=actor, target=b, request=request, summary=reason[:255],
                  before=before, changes={k: str(v) for k, v in changes.items()})
            if financial_change:
                invoice = issue_invoice(b, actor=actor, reason=reason)
                notify.invoice_issued(b, invoice, revised=True)
    except IntegrityError as exc:
        if _is_overlap_error(exc):
            raise ConflictError(OVERLAP_MESSAGE) from exc
        raise
    booking.refresh_from_db()
    return booking, invoice
