import logging

import django_filters
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import FINANCE_ROLES
from apps.bookings.models import Booking
from apps.bookings.views import guest_booking_or_404
from apps.core.files import private_file_response
from apps.core.throttles import PaymentThrottle
from apps.core.utils import audit

from . import services
from .gateways import GatewayError, get_gateway
from .models import Method, Payment, Status
from .serializers import (OnlineInitiateSerializer, OnlineVerifySerializer, PaymentSerializer,
                          RecordPaymentSerializer, RefundInputSerializer, RejectSerializer, VerifySerializer)

logger = logging.getLogger(__name__)


def _guest_payment(p: Payment) -> dict:
    return {"payment_reference": p.payment_reference, "amount": str(p.amount), "currency": p.currency,
            "status": p.payment_status, "status_display": p.get_payment_status_display(),
            "booking_reference": p.booking.booking_reference,
            "booking_payment_status": p.booking.get_payment_status_display(),
            "balance_due": str(p.booking.balance_due)}


class ManualPaymentView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PaymentThrottle]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        guest_booking_or_404(request)
        from apps.core.exceptions import BusinessRuleError

        raise BusinessRuleError("Payment is collected locally on arrival or at vehicle pickup.")


class OnlinePaymentInitiateView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PaymentThrottle]

    def post(self, request):
        booking = guest_booking_or_404(request)
        s = OnlineInitiateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        payment = services.initiate_online_payment(booking, gateway_code=s.validated_data["gateway"],
                                                   amount=s.validated_data.get("amount"), request=request)
        return Response({**_guest_payment(payment), "redirect_url": payment.checkout_url},
                        status=status.HTTP_201_CREATED)


class OnlinePaymentVerifyView(APIView):
    """Called by the return page. Triggers a server-side status check —
    the browser's word is never taken as proof of payment."""

    permission_classes = [AllowAny]
    throttle_classes = [PaymentThrottle]

    def post(self, request):
        s = OnlineVerifySerializer(data=request.data)
        s.is_valid(raise_exception=True)
        payment = Payment.objects.select_related("booking").filter(
            payment_method=Method.ONLINE, gateway_order_id=s.validated_data["order_tracking_id"]).first()
        if payment is None:
            raise NotFound("Payment not found.")
        try:
            payment = services.sync_online_payment(payment)
        except GatewayError as exc:
            logger.warning("Status check failed for %s: %s", payment.payment_reference, exc)
        payment.refresh_from_db()
        return Response(_guest_payment(payment))


class PaymentWebhookView(APIView):
    """IPN endpoint: /api/v1/webhooks/payments/<provider>/.

    The notification body is treated only as a hint — we always re-query the
    gateway's API before changing anything, so a forged call cannot mark a
    payment as paid.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []

    def _handle(self, request, provider):
        gateway = get_gateway(provider)
        if gateway is None:
            raise NotFound()
        order_id = gateway.parse_webhook(request)
        payment = Payment.objects.filter(gateway=provider, gateway_order_id=order_id).first() if order_id else None
        ok = True
        if payment is not None:
            try:
                services.sync_online_payment(payment)
            except GatewayError as exc:
                logger.warning("Webhook status check failed for %s: %s", order_id, exc)
                ok = False
        else:
            logger.info("Webhook for unknown order %s (%s)", order_id, provider)
        return Response(gateway.webhook_ack(request, ok), status=200 if ok else 500)

    def get(self, request, provider):
        return self._handle(request, provider)

    def post(self, request, provider):
        return self._handle(request, provider)


# --------------------------------------------------------------------------
# Admin
# --------------------------------------------------------------------------
class PaymentFilter(django_filters.FilterSet):
    created_from = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    created_to = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    class Meta:
        model = Payment
        fields = ["payment_status", "payment_method", "channel", "gateway", "booking"]


class AdminPaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer
    filterset_class = PaymentFilter
    ordering = ["-created_at"]
    action_roles = {"verify": FINANCE_ROLES, "reject": FINANCE_ROLES, "record": FINANCE_ROLES,
                    "refund": FINANCE_ROLES, "proof": FINANCE_ROLES, "sync": FINANCE_ROLES}

    def get_queryset(self):
        qs = Payment.objects.select_related("booking", "booking__customer", "verified_by", "recorded_by") \
            .prefetch_related("refunds")
        q = self.request.query_params.get("q", "").strip()
        if q:
            qs = qs.filter(Q(payment_reference__icontains=q) | Q(booking__booking_reference__icontains=q)
                           | Q(transaction_reference__icontains=q) | Q(booking__customer__full_name__icontains=q))
        return qs

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        s = VerifySerializer(data=request.data)
        s.is_valid(raise_exception=True)
        p = services.verify_manual_payment(self.get_object(), actor=request.user, notes=s.validated_data["notes"],
                                           amount=s.validated_data.get("amount"))
        return Response(PaymentSerializer(p).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        s = RejectSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        p = services.reject_manual_payment(self.get_object(), actor=request.user, reason=s.validated_data["reason"])
        return Response(PaymentSerializer(p).data)

    @action(detail=False, methods=["post"])
    def record(self, request):
        s = RecordPaymentSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        booking = get_object_or_404(Booking, pk=d["booking"])
        p = services.record_offline_payment(booking, actor=request.user, amount=d["amount"], channel=d["channel"],
                                            transaction_reference=d["transaction_reference"], notes=d["notes"])
        return Response(PaymentSerializer(p).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def refund(self, request, pk=None):
        s = RefundInputSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        services.record_refund(self.get_object(), actor=request.user, **s.validated_data)
        return Response(PaymentSerializer(self.get_queryset().get(pk=pk)).data)

    @action(detail=True, methods=["post"])
    def sync(self, request, pk=None):
        """Re-check an online payment with the gateway."""
        p = self.get_object()
        if p.payment_method != Method.ONLINE:
            return Response({"error": {"code": "business_rule", "message": "Not an online payment."}}, status=400)
        try:
            services.sync_online_payment(p)
        except GatewayError as exc:
            return Response({"error": {"code": "gateway_error", "message": str(exc)}}, status=502)
        return Response(PaymentSerializer(self.get_queryset().get(pk=pk)).data)

    @action(detail=True, methods=["get"])
    def proof(self, request, pk=None):
        p = self.get_object()
        if not p.proof_file:
            raise NotFound("No proof of payment was uploaded.")
        audit("payment.proof_viewed", actor=request.user, target=p, request=request, summary=p.payment_reference)
        ext = p.proof_file.name.rsplit(".", 1)[-1]
        return private_file_response(p.proof_file, f"{p.payment_reference}-proof.{ext}",
                                     as_attachment=request.query_params.get("inline") != "1")


__all__ = ["Status"]
