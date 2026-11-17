"""Payment workflows. The ONLY code paths that can make money count:

* ``apply_gateway_status`` — after a server-to-server status check.
* ``verify_manual_payment`` — explicit, audited staff review.
* ``record_offline_payment`` — staff record money received in person (audited).
"""
import logging
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone

from apps.bookings.models import Booking, BookingStatus, PaymentStatus
from apps.bookings.services import set_payment_status
from apps.core.exceptions import BusinessRuleError
from apps.core.files import validate_upload
from apps.core.models import SiteSettings
from apps.core.pdf import logo_path, site_dict
from apps.core.utils import audit, money, next_sequence_value, random_reference

from .gateways import GatewayError, get_gateway
from .models import Channel, Method, Payment, Receipt, Refund, Status, VerificationSource
from .pdf import render_receipt_pdf

logger = logging.getLogger(__name__)
PAYABLE_BOOKING_STATUSES = (BookingStatus.PENDING_CONFIRMATION, BookingStatus.CONFIRMED, BookingStatus.COMPLETED)


def _new_reference() -> str:
    for _ in range(10):
        ref = random_reference("RCP", 8)
        if not Payment.objects.filter(payment_reference=ref).exists():
            return ref
    raise RuntimeError("Could not allocate a payment reference")


def recalculate_booking_payment_status(booking: Booking, *, actor=None, notes="") -> Booking:
    """Derive amount_paid / payment_status from verified payments and refunds."""
    agg = booking.payments.filter(payment_status=Status.VERIFIED).aggregate(
        paid=Sum("amount"), refunded=Sum("refunded_amount"))
    paid, refunded = money(agg["paid"] or 0), money(agg["refunded"] or 0)
    net = paid - refunded
    if refunded > 0 and net <= 0:
        status = PaymentStatus.REFUNDED
    elif refunded > 0:
        status = PaymentStatus.PARTIALLY_REFUNDED
    elif net >= booking.grand_total and net > 0:
        status = PaymentStatus.PAID
    elif net > 0:
        status = PaymentStatus.PARTIALLY_PAID
    elif booking.payments.filter(payment_status=Status.PENDING_VERIFICATION).exists():
        status = PaymentStatus.PENDING_VERIFICATION
    else:
        status = PaymentStatus.UNPAID
    booking.amount_paid = net
    set_payment_status(booking, status, actor=actor, notes=notes)
    booking.save(update_fields=["amount_paid", "payment_status", "updated_at"])
    return booking


def _check_amount(booking: Booking, amount: Decimal, *, allow_over=False) -> Decimal:
    amount = money(amount)
    if amount <= 0:
        raise ValidationError({"amount": "Amount must be greater than zero."})
    if not allow_over and amount > booking.balance_due:
        raise ValidationError({"amount": f"Amount exceeds the outstanding balance of ${booking.balance_due}."})
    return amount


def _issue_receipt(payment: Payment) -> Receipt:
    if hasattr(payment, "receipt"):
        return payment.receipt
    b = payment.booking
    year = timezone.localdate().year
    number = f"RCR-{year}-{next_sequence_value(f'RCR-{year}'):06d}"
    site = SiteSettings.load()
    snap = {
        "receipt_number": number, "issue_date": f"{timezone.localdate():%d %B %Y}",
        "booking_reference": b.booking_reference, "payment_reference": payment.payment_reference,
        "site": site_dict(site), "customer": {"full_name": b.customer.full_name, "email": b.customer.email},
        "vehicle": b.vehicle.name, "amount": str(payment.amount), "currency": payment.currency,
        "method": payment.get_payment_method_display(),
        "channel": payment.get_channel_display() if payment.channel else (payment.gateway or "").title(),
        "transaction_reference": payment.transaction_reference,
        "booking_total": str(b.grand_total), "total_paid": str(b.amount_paid), "balance": str(b.balance_due),
        "footer": site.invoice_footer,
    }
    receipt = Receipt.objects.create(receipt_number=number, payment=payment, booking=b,
                                     issue_date=timezone.localdate(), amount=payment.amount,
                                     currency=payment.currency, snapshot=snap)
    try:
        pdf = render_receipt_pdf(snap, logo_path(site))
        receipt.pdf_file.save(f"{number}.pdf", ContentFile(pdf), save=True)
    except Exception:
        logger.exception("Receipt PDF rendering failed for %s", number)
    return receipt


def _mark_verified(payment: Payment, *, source: str, actor=None, notes: str = "") -> Payment:
    from apps.notifications import services as notify

    payment.payment_status = Status.VERIFIED
    payment.verified_at = timezone.now()
    payment.verification_source = source
    payment.verified_by = actor if getattr(actor, "is_authenticated", False) else None
    if notes:
        payment.review_notes = notes
    payment.save()
    booking = Booking.objects.select_for_update().get(pk=payment.booking_id)
    recalculate_booking_payment_status(booking, actor=actor, notes=f"Payment {payment.payment_reference} verified")
    payment.booking = booking
    receipt = _issue_receipt(payment)
    audit("payment.verified", actor=actor, target=payment, summary=f"{payment.payment_reference} ${payment.amount}",
          source=source, booking=booking.booking_reference)
    notify.payment_received(payment, receipt)
    return payment


# --------------------------------------------------------------------------
# Manual payments
# --------------------------------------------------------------------------
@transaction.atomic
def submit_manual_payment(booking: Booking, *, amount, channel, transaction_reference="", note="", proof=None,
                          request=None) -> Payment:
    from apps.notifications import services as notify

    booking = Booking.objects.select_for_update().get(pk=booking.pk)
    if booking.booking_status not in PAYABLE_BOOKING_STATUSES:
        raise BusinessRuleError("Payments cannot be submitted for this booking.")
    if channel not in Channel.values or channel == Channel.CARD:
        raise ValidationError({"channel": "Choose a valid payment channel."})
    amount = _check_amount(booking, amount)
    if proof:
        validate_upload(proof)
    if not transaction_reference and not proof:
        raise ValidationError({"transaction_reference": "Provide a transaction reference or upload proof of payment."})
    payment = Payment.objects.create(
        booking=booking, payment_reference=_new_reference(), payment_method=Method.MANUAL, channel=channel,
        amount=amount, currency=booking.currency, payment_status=Status.PENDING_VERIFICATION,
        transaction_reference=transaction_reference[:120], payer_note=note, proof_file=proof or "",
    )
    recalculate_booking_payment_status(booking, notes="Manual payment submitted")
    audit("payment.manual_submitted", target=payment, request=request,
          summary=f"{payment.payment_reference} ${amount} for {booking.booking_reference}")
    notify.manual_payment_submitted(payment)
    return payment


@transaction.atomic
def verify_manual_payment(payment: Payment, *, actor, notes="", amount=None) -> Payment:
    payment = Payment.objects.select_for_update().get(pk=payment.pk)
    if payment.payment_status != Status.PENDING_VERIFICATION:
        raise BusinessRuleError("Only payments awaiting verification can be verified.")
    if amount is not None:  # staff confirm the amount actually received
        amount = money(amount)
        if amount <= 0:
            raise ValidationError({"amount": "Amount must be greater than zero."})
        if amount != payment.amount:
            notes = f"{notes} (amount adjusted from ${payment.amount} to ${amount})".strip()
            payment.amount = amount
    return _mark_verified(payment, source=VerificationSource.STAFF_REVIEW, actor=actor, notes=notes)


@transaction.atomic
def reject_manual_payment(payment: Payment, *, actor, reason: str) -> Payment:
    from apps.notifications import services as notify

    if not reason.strip():
        raise ValidationError({"reason": "A reason is required."})
    payment = Payment.objects.select_for_update().get(pk=payment.pk)
    if payment.payment_status != Status.PENDING_VERIFICATION:
        raise BusinessRuleError("Only payments awaiting verification can be rejected.")
    payment.payment_status = Status.REJECTED
    payment.review_notes = reason
    payment.verified_by = actor
    payment.save()
    booking = Booking.objects.select_for_update().get(pk=payment.booking_id)
    recalculate_booking_payment_status(booking, actor=actor, notes=f"Payment {payment.payment_reference} rejected")
    audit("payment.rejected", actor=actor, target=payment, summary=reason[:255])
    notify.manual_payment_rejected(payment)
    return payment


@transaction.atomic
def record_offline_payment(booking: Booking, *, actor, amount, channel, transaction_reference="", notes="") -> Payment:
    """Staff record money received directly (e.g. cash at handover). Verified on creation, fully audited."""
    booking = Booking.objects.select_for_update().get(pk=booking.pk)
    if channel not in Channel.values:
        raise ValidationError({"channel": "Choose a valid payment channel."})
    if not notes.strip():
        raise ValidationError({"notes": "Describe how and when the payment was received."})
    amount = _check_amount(booking, amount)
    payment = Payment.objects.create(
        booking=booking, payment_reference=_new_reference(), payment_method=Method.MANUAL, channel=channel,
        amount=amount, currency=booking.currency, payment_status=Status.PENDING_VERIFICATION,
        transaction_reference=transaction_reference[:120], recorded_by=actor,
    )
    return _mark_verified(payment, source=VerificationSource.STAFF_RECORDED, actor=actor, notes=notes)


# --------------------------------------------------------------------------
# Online payments
# --------------------------------------------------------------------------
def initiate_online_payment(booking: Booking, *, gateway_code: str, amount=None, request=None) -> Payment:
    gateway = get_gateway(gateway_code)
    if gateway is None or not gateway.is_configured():
        raise BusinessRuleError("Online payment is not available at the moment. Please choose manual payment "
                                "or contact us.")
    with transaction.atomic():
        booking = Booking.objects.select_for_update().get(pk=booking.pk)
        if booking.booking_status not in (BookingStatus.PENDING_CONFIRMATION, BookingStatus.CONFIRMED):
            raise BusinessRuleError("This booking can no longer be paid online.")
        if booking.currency not in gateway.supported_currencies:
            raise BusinessRuleError("This currency is not supported by the payment gateway.")
        amount = _check_amount(booking, amount if amount is not None else booking.balance_due)
        payment = Payment.objects.create(
            booking=booking, payment_reference=_new_reference(), payment_method=Method.ONLINE, channel=Channel.CARD,
            gateway=gateway.code, amount=amount, currency=booking.currency, payment_status=Status.INITIATED,
        )
    base = f"{settings.FRONTEND_URL}/payment/return?ref={booking.booking_reference}"
    try:
        session = gateway.create_checkout(payment=payment, booking=booking, callback_url=base,
                                          cancellation_url=f"{base}&cancelled=1")
    except GatewayError as exc:
        payment.payment_status = Status.FAILED
        payment.review_notes = str(exc)[:500]
        payment.save(update_fields=["payment_status", "review_notes", "updated_at"])
        logger.warning("Checkout creation failed for %s: %s", payment.payment_reference, exc)
        raise BusinessRuleError("We could not start the online payment. Please try again shortly.") from exc
    payment.gateway_order_id = session.gateway_order_id
    payment.checkout_url = session.redirect_url
    payment.gateway_payload = {"checkout": session.raw}
    payment.save(update_fields=["gateway_order_id", "checkout_url", "gateway_payload", "updated_at"])
    audit("payment.online_initiated", target=payment, request=request,
          summary=f"{payment.payment_reference} ${amount} via {gateway.code}")
    return payment


def sync_online_payment(payment: Payment) -> Payment:
    """Fetch the authoritative status from the gateway and apply it."""
    gateway = get_gateway(payment.gateway)
    if gateway is None or not payment.gateway_order_id:
        return payment
    status = gateway.fetch_status(payment.gateway_order_id)
    return apply_gateway_status(payment, status)


@transaction.atomic
def apply_gateway_status(payment: Payment, status) -> Payment:
    """Idempotently apply a server-verified gateway status."""
    from apps.notifications import services as notify

    payment = Payment.objects.select_for_update().get(pk=payment.pk)
    payload = dict(payment.gateway_payload or {})
    payload["last_status"] = status.raw
    payment.gateway_payload = payload
    if status.merchant_reference and status.merchant_reference != payment.payment_reference:
        logger.error("Gateway reference mismatch for %s: %s", payment.payment_reference, status.merchant_reference)
        payment.save(update_fields=["gateway_payload", "updated_at"])
        return payment

    if status.state == "completed":
        if payment.payment_status == Status.VERIFIED:
            payment.save(update_fields=["gateway_payload", "updated_at"])
            return payment
        if status.amount is None or money(status.amount) != payment.amount or status.currency != payment.currency:
            payment.review_notes = (f"Gateway reported {status.amount} {status.currency}; expected "
                                    f"{payment.amount} {payment.currency}. Requires manual review.")
            payment.save(update_fields=["gateway_payload", "review_notes", "updated_at"])
            audit("payment.amount_mismatch", target=payment, summary=payment.review_notes[:255])
            return payment
        payment.transaction_reference = status.confirmation_code[:120]
        payment.gateway_response_reference = (status.payment_method or "")[:120]
        return _mark_verified(payment, source=VerificationSource.GATEWAY_API,
                              notes=f"Confirmed by {payment.gateway}: {status.description}")
    if status.state == "failed" and payment.payment_status == Status.INITIATED:
        payment.payment_status = Status.FAILED
        payment.review_notes = status.description[:500]
        payment.save()
        notify.payment_failed(payment)
    elif status.state == "reversed" and payment.payment_status == Status.VERIFIED:
        payment.payment_status = Status.REVERSED
        payment.save()
        booking = Booking.objects.select_for_update().get(pk=payment.booking_id)
        recalculate_booking_payment_status(booking, notes=f"Payment {payment.payment_reference} reversed by gateway")
        audit("payment.reversed", target=payment, summary=f"{payment.payment_reference} reversed by gateway")
    else:
        payment.save(update_fields=["gateway_payload", "updated_at"])
    return payment


# --------------------------------------------------------------------------
# Refunds
# --------------------------------------------------------------------------
def record_refund(payment: Payment, *, actor, amount, reason: str, via_gateway: bool = False) -> Refund:
    if not reason.strip():
        raise ValidationError({"reason": "A reason is required."})
    amount = money(amount)
    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment.pk)
        if payment.payment_status != Status.VERIFIED:
            raise BusinessRuleError("Only verified payments can be refunded.")
        if amount <= 0 or amount > payment.net_amount:
            raise ValidationError({"amount": f"Refund must be between $0.01 and ${payment.net_amount}."})
        status, gw_ref = Refund.RefundStatus.COMPLETED, ""
        if via_gateway:
            gateway = get_gateway(payment.gateway)
            if not gateway or not gateway.supports_refunds:
                raise BusinessRuleError("This payment's gateway does not support refunds through the API.")
            try:
                result = gateway.refund(payment=payment, amount=amount, reason=reason, requested_by=actor.email)
            except GatewayError as exc:
                raise BusinessRuleError(str(exc)) from exc
            if not result.accepted:
                raise BusinessRuleError(result.message or "The gateway declined the refund request.")
            status, gw_ref = Refund.RefundStatus.REQUESTED, result.reference
        refund = Refund.objects.create(payment=payment, amount=amount, reason=reason, status=status,
                                       gateway_reference=gw_ref, recorded_by=actor,
                                       processed_at=timezone.now() if status == Refund.RefundStatus.COMPLETED else None)
        payment.refunded_amount = money(payment.refunded_amount + amount)
        payment.save(update_fields=["refunded_amount", "updated_at"])
        booking = Booking.objects.select_for_update().get(pk=payment.booking_id)
        recalculate_booking_payment_status(booking, actor=actor, notes=f"Refund ${amount}: {reason}")
        audit("payment.refund", actor=actor, target=payment, summary=f"Refund ${amount}: {reason}"[:255],
              via_gateway=via_gateway)
    return refund


def outstanding_bookings():
    return Booking.objects.filter(
        booking_status__in=[BookingStatus.PENDING_CONFIRMATION, BookingStatus.CONFIRMED, BookingStatus.COMPLETED],
    ).filter(amount_paid__lt=F("grand_total"))
