"""Queue notifications and deliver them with retries.

Queuing writes a NotificationLog row inside the caller's transaction and
dispatches the Celery task after commit, so a failed email can never roll
back (or lose) a booking, invoice or payment.
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

from apps.core.models import SiteSettings

from .models import DeliveryStatus, NotificationLog
from .models import NotificationType as T

logger = logging.getLogger(__name__)

# type -> (subject template, template name, include guest manage link, attachment)
SPEC = {
    T.BOOKING_SUBMITTED_GUEST: ("Booking request received — {ref}", "booking_submitted_guest", True, "invoice"),
    T.BOOKING_SUBMITTED_OWNER: ("New booking {ref} — {name} — ${total}", "booking_submitted_owner", False, "invoice"),
    T.INVOICE_GUEST: ("Your invoice {invoice} — Rafiki Car Hire", "invoice_guest", True, "invoice"),
    T.INVOICE_OWNER: ("Invoice {invoice} issued for {ref}", "invoice_owner", False, "invoice"),
    T.BOOKING_CONFIRMED: ("Your booking {ref} is confirmed", "booking_confirmed", True, None),
    T.BOOKING_REJECTED: ("Update on your booking request {ref}", "booking_rejected", False, None),
    T.BOOKING_CANCELLED: ("Booking {ref} has been cancelled", "booking_cancelled", False, None),
    T.PAYMENT_RECEIVED_GUEST: ("Payment received — {ref}", "payment_received_guest", True, "receipt"),
    T.PAYMENT_RECEIVED_OWNER: ("Payment verified: ${amount} for {ref}", "payment_received_owner", False, None),
    T.MANUAL_PAYMENT_SUBMITTED_OWNER: ("Action needed: verify payment for {ref}", "manual_payment_submitted_owner",
                                       False, None),
    T.MANUAL_PAYMENT_REJECTED: ("We could not verify your payment — {ref}", "manual_payment_rejected", True, None),
    T.PAYMENT_FAILED: ("Your online payment was not completed — {ref}", "payment_failed", True, None),
    T.CONTACT_MESSAGE_OWNER: ("Website enquiry from {name}", "contact_owner", False, None),
}


def _dispatch(log_id):
    from .tasks import send_notification

    try:
        send_notification.delay(str(log_id))
    except Exception:  # broker down: the periodic sweep will deliver it
        logger.exception("Could not enqueue notification %s", log_id)


def queue(ntype, recipient, *, booking=None, invoice=None, payment=None, context=None) -> NotificationLog | None:
    if not recipient:
        logger.warning("Skipping %s: no recipient configured", ntype)
        return None
    log = NotificationLog.objects.create(notification_type=ntype, recipient=recipient, booking=booking,
                                         invoice=invoice, payment=payment, context=context or {})
    transaction.on_commit(lambda: _dispatch(log.pk))
    return log


def _owner():
    return SiteSettings.load().owner_email


# -- Business events ----------------------------------------------------------
def booking_submitted(booking, invoice):
    queue(T.BOOKING_SUBMITTED_GUEST, booking.customer.email, booking=booking, invoice=invoice)
    queue(T.BOOKING_SUBMITTED_OWNER, _owner(), booking=booking, invoice=invoice)


def invoice_issued(booking, invoice, *, revised=False, to_owner=True):
    queue(T.INVOICE_GUEST, booking.customer.email, booking=booking, invoice=invoice, context={"revised": revised})
    if to_owner:
        queue(T.INVOICE_OWNER, _owner(), booking=booking, invoice=invoice, context={"revised": revised})


def booking_status_changed(booking, status, notes=""):
    ntype = {"CONFIRMED": T.BOOKING_CONFIRMED, "REJECTED": T.BOOKING_REJECTED,
             "CANCELLED": T.BOOKING_CANCELLED}.get(status)
    if ntype:
        queue(ntype, booking.customer.email, booking=booking, context={"message": notes})


def payment_received(payment, receipt=None):
    b = payment.booking
    queue(T.PAYMENT_RECEIVED_GUEST, b.customer.email, booking=b, payment=payment)
    queue(T.PAYMENT_RECEIVED_OWNER, _owner(), booking=b, payment=payment)


def manual_payment_submitted(payment):
    queue(T.MANUAL_PAYMENT_SUBMITTED_OWNER, _owner(), booking=payment.booking, payment=payment)


def manual_payment_rejected(payment):
    queue(T.MANUAL_PAYMENT_REJECTED, payment.booking.customer.email, booking=payment.booking, payment=payment,
          context={"message": payment.review_notes})


def payment_failed(payment):
    queue(T.PAYMENT_FAILED, payment.booking.customer.email, booking=payment.booking, payment=payment)


def contact_message(msg):
    queue(T.CONTACT_MESSAGE_OWNER, _owner(), context={
        "name": msg.name, "email": msg.email, "phone": msg.phone, "subject": msg.subject, "message": msg.message,
    })


# -- Delivery -------------------------------------------------------------------
def _render(log: NotificationLog):
    from apps.bookings.tokens import guest_manage_url, issue_access_token, revoke_tokens

    subject_tpl, template, guest_link, attachment = SPEC[log.notification_type]
    site = SiteSettings.load()
    b, inv, pay = log.booking, log.invoice, log.payment
    ctx = {
        "site": site, "booking": b, "invoice": inv, "payment": pay, "ctx": log.context,
        "frontend_url": settings.FRONTEND_URL, "currency": "USD",
    }
    if b is not None:
        ctx.update(customer=b.customer, vehicle=b.vehicle, extras=list(b.extras.all()),
                   admin_url=f"{settings.FRONTEND_URL}/admin/bookings/{b.pk}")
        try:
            ctx["flight"] = b.flight
        except Exception:
            ctx["flight"] = None
        if guest_link:
            # Fresh single-purpose token per notification; earlier ones for this
            # notification (previous retry attempts) are revoked. Raw token is never stored.
            purpose = f"email:{log.pk}"
            revoke_tokens(b, purpose=purpose)
            ctx["manage_url"] = guest_manage_url(b, issue_access_token(b, purpose=purpose))
    fmt = {
        "ref": b.booking_reference if b else "", "name": (b.customer.full_name if b else log.context.get("name", "")),
        "total": f"{b.grand_total:,.2f}" if b else "", "invoice": inv.invoice_number if inv else "",
        "amount": f"{pay.amount:,.2f}" if pay else "",
    }
    subject = subject_tpl.format(**fmt)
    if log.context.get("revised") and log.notification_type in (T.INVOICE_GUEST, T.INVOICE_OWNER):
        subject = "Revised " + subject[0].lower() + subject[1:]
    ctx["subject"] = subject
    html = render_to_string(f"emails/{template}.html", ctx)
    files = []
    if attachment == "invoice" and inv is not None:
        from apps.invoices.services import ensure_pdf

        if ensure_pdf(inv):
            inv.pdf_file.open("rb")
            files.append((inv.filename, inv.pdf_file.read(), "application/pdf"))
            inv.pdf_file.close()
    elif attachment == "receipt" and pay is not None and hasattr(pay, "receipt") and pay.receipt.pdf_file:
        r = pay.receipt
        r.pdf_file.open("rb")
        files.append((r.filename, r.pdf_file.read(), "application/pdf"))
        r.pdf_file.close()
    return subject, html, files


def deliver(log_id) -> bool:
    with transaction.atomic():
        log = NotificationLog.objects.select_for_update(skip_locked=True).filter(pk=log_id).first()
        if log is None or log.delivery_status in (DeliveryStatus.SENT, DeliveryStatus.ABANDONED):
            return False
        log.attempts += 1
        log.last_attempt_at = timezone.now()
        try:
            # Savepoint: a failure while rendering/sending must not poison the
            # outer transaction, so the failure itself can still be recorded.
            with transaction.atomic():
                subject, html, files = _render(log)
            site = SiteSettings.load()
            msg = EmailMultiAlternatives(subject=subject, body=strip_tags(html), to=[log.recipient],
                                         from_email=settings.DEFAULT_FROM_EMAIL,
                                         reply_to=[site.business_email] if site.business_email else None)
            msg.attach_alternative(html, "text/html")
            for name, content, mimetype in files:
                msg.attach(name, content, mimetype)
            msg.send(fail_silently=False)
        except Exception as exc:
            log.error_message = f"{exc.__class__.__name__}: {exc}"[:2000]
            if log.attempts >= settings.NOTIFICATION_MAX_ATTEMPTS:
                log.delivery_status = DeliveryStatus.ABANDONED
                log.next_retry_at = None
            else:
                log.delivery_status = DeliveryStatus.FAILED
                log.next_retry_at = timezone.now() + timedelta(minutes=2 ** log.attempts)
            log.save()
            logger.warning("Notification %s failed (attempt %s): %s", log.pk, log.attempts, log.error_message)
            return False
        log.subject = subject[:200]
        log.delivery_status = DeliveryStatus.SENT
        log.sent_at = timezone.now()
        log.next_retry_at = None
        log.error_message = ""
        log.save()
        return True


def due_for_retry(now=None):
    now = now or timezone.now()
    from django.db.models import Q

    return NotificationLog.objects.filter(
        Q(delivery_status=DeliveryStatus.FAILED, next_retry_at__lte=now)
        | Q(delivery_status=DeliveryStatus.QUEUED, created_at__lte=now - timedelta(minutes=2))
    )


def resend(log: NotificationLog) -> NotificationLog:
    """Staff resend: a new log row so the history of the failed one is kept."""
    new = queue(log.notification_type, log.recipient, booking=log.booking, invoice=log.invoice,
                payment=log.payment, context=log.context)
    return new
