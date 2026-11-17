import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .gateways import GatewayError
from .models import Method, Payment, Status
from .services import sync_online_payment

logger = logging.getLogger(__name__)


@shared_task
def reconcile_pending_online_payments():
    """Safety net for missed webhooks: re-check recent unconfirmed online payments."""
    since = timezone.now() - timedelta(days=3)
    qs = Payment.objects.filter(payment_method=Method.ONLINE, payment_status=Status.INITIATED,
                                gateway_order_id__isnull=False, created_at__gte=since)
    checked = 0
    for payment in qs[:200]:
        try:
            sync_online_payment(payment)
            checked += 1
        except GatewayError as exc:
            logger.warning("Reconcile failed for %s: %s", payment.payment_reference, exc)
    # Abandon checkouts that never completed.
    Payment.objects.filter(payment_method=Method.ONLINE, payment_status=Status.INITIATED,
                           created_at__lt=since).update(payment_status=Status.CANCELLED)
    return checked
