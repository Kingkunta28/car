import django_filters
from django.db.models import Q
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import FINANCE_ROLES
from apps.bookings.views import guest_booking_or_404
from apps.core.exceptions import BusinessRuleError
from apps.core.files import private_file_response
from apps.core.throttles import BookingAccessThrottle
from apps.core.utils import audit
from apps.notifications import services as notify
from apps.payments.models import Receipt

from .models import Invoice, InvoiceStatus
from .serializers import InvoiceDetailSerializer, InvoiceListSerializer
from .services import ensure_pdf, issue_invoice


def _pdf_response(invoice: Invoice, inline=False):
    if not ensure_pdf(invoice):
        raise BusinessRuleError("The invoice PDF could not be generated. Please try again shortly.")
    return private_file_response(invoice.pdf_file, invoice.filename, as_attachment=not inline)


class GuestInvoiceDownloadView(APIView):
    """GET /invoices/download/?invoice=<number|latest> with X-Booking-Reference / X-Booking-Token headers."""

    permission_classes = [AllowAny]
    throttle_classes = [BookingAccessThrottle]

    def get(self, request):
        booking = guest_booking_or_404(request)
        number = request.query_params.get("invoice", "latest")
        qs = booking.invoices.all()
        invoice = (qs.filter(invoice_status=InvoiceStatus.ISSUED).first() if number == "latest"
                   else qs.filter(invoice_number=number).first())
        if invoice is None:
            raise NotFound("Invoice not found.")
        return _pdf_response(invoice)


class GuestReceiptDownloadView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [BookingAccessThrottle]

    def get(self, request):
        booking = guest_booking_or_404(request)
        receipt = booking.receipts.filter(receipt_number=request.query_params.get("receipt", "")).first()
        if receipt is None or not receipt.pdf_file:
            raise NotFound("Receipt not found.")
        return private_file_response(receipt.pdf_file, receipt.filename)


class InvoiceFilter(django_filters.FilterSet):
    issued_from = django_filters.DateFilter(field_name="issue_date", lookup_expr="gte")
    issued_to = django_filters.DateFilter(field_name="issue_date", lookup_expr="lte")

    class Meta:
        model = Invoice
        fields = ["invoice_status", "booking"]


class ReviseSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255)


class AdminInvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    filterset_class = InvoiceFilter
    ordering = ["-created_at"]
    action_roles = {"revise": FINANCE_ROLES}

    def get_queryset(self):
        qs = Invoice.objects.select_related("booking", "booking__customer", "supersedes")
        q = self.request.query_params.get("q", "").strip()
        if q:
            qs = qs.filter(Q(invoice_number__icontains=q) | Q(booking__booking_reference__icontains=q)
                           | Q(booking__customer__full_name__icontains=q))
        return qs

    def get_serializer_class(self):
        return InvoiceDetailSerializer if self.action == "retrieve" else InvoiceListSerializer

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        invoice = self.get_object()
        audit("invoice.downloaded", actor=request.user, target=invoice, request=request, summary=invoice.invoice_number)
        return _pdf_response(invoice, inline=request.query_params.get("inline") == "1")

    @action(detail=True, methods=["post"])
    def resend(self, request, pk=None):
        invoice = self.get_object()
        if invoice.invoice_status != InvoiceStatus.ISSUED:
            raise BusinessRuleError("Only the current invoice can be resent.")
        notify.invoice_issued(invoice.booking, invoice, revised=bool(invoice.revision_number),
                              to_owner=request.data.get("to_owner") in (True, "true", "1"))
        audit("invoice.resent", actor=request.user, target=invoice, request=request, summary=invoice.invoice_number)
        return Response({"queued": True, "recipient": invoice.booking.customer.email})

    @action(detail=True, methods=["post"])
    def revise(self, request, pk=None):
        """Re-issue from the booking's current details (e.g. after a correction)."""
        invoice = self.get_object()
        if invoice.invoice_status != InvoiceStatus.ISSUED:
            raise BusinessRuleError("Only the current invoice can be revised.")
        s = ReviseSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        new = issue_invoice(invoice.booking, actor=request.user, reason=s.validated_data["reason"])
        notify.invoice_issued(new.booking, new, revised=True)
        return Response(InvoiceDetailSerializer(new).data)


class AdminReceiptViewSet(viewsets.ReadOnlyModelViewSet):
    ordering = ["-created_at"]

    class _S(serializers.ModelSerializer):
        booking_reference = serializers.CharField(source="booking.booking_reference")
        payment_reference = serializers.CharField(source="payment.payment_reference")
        customer_name = serializers.CharField(source="booking.customer.full_name")

        class Meta:
            model = Receipt
            fields = ["id", "receipt_number", "booking_reference", "payment_reference", "customer_name", "issue_date",
                      "amount", "currency", "created_at"]

    serializer_class = _S

    def get_queryset(self):
        qs = Receipt.objects.select_related("booking", "booking__customer", "payment")
        q = self.request.query_params.get("q", "").strip()
        if q:
            qs = qs.filter(Q(receipt_number__icontains=q) | Q(booking__booking_reference__icontains=q))
        return qs

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        r = self.get_object()
        if not r.pdf_file:
            raise NotFound("Receipt PDF is not available.")
        return private_file_response(r.pdf_file, r.filename, as_attachment=request.query_params.get("inline") != "1")
