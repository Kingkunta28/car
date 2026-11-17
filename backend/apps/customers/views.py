from django.db.models import Count, Max, Q, Sum
from rest_framework import serializers, viewsets
from rest_framework.response import Response

from apps.bookings.serializers import AdminBookingListSerializer
from apps.invoices.serializers import InvoiceListSerializer
from apps.invoices.models import Invoice
from apps.payments.models import Payment
from apps.payments.serializers import PaymentSerializer

from .models import Customer


class CustomerSerializer(serializers.ModelSerializer):
    booking_count = serializers.IntegerField(read_only=True)
    total_spent = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    last_booking_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Customer
        fields = ["id", "full_name", "email", "phone", "nationality", "booking_count", "total_spent",
                  "last_booking_at", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class AdminCustomerViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    http_method_names = ["get", "patch", "head", "options"]
    ordering_fields = ["full_name", "created_at", "last_booking_at", "total_spent"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = Customer.objects.annotate(
            booking_count=Count("bookings", distinct=True),
            total_spent=Sum("bookings__amount_paid"),
            last_booking_at=Max("bookings__created_at"),
        )
        q = self.request.query_params.get("q", "").strip()
        if q:
            qs = qs.filter(Q(full_name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q)
                           | Q(bookings__booking_reference__icontains=q)).distinct()
        return qs

    def retrieve(self, request, *args, **kwargs):
        c = self.get_object()
        data = self.get_serializer(c).data
        bookings = c.bookings.select_related("vehicle", "customer").prefetch_related("extras", "vehicle__images")
        data["bookings"] = AdminBookingListSerializer(bookings, many=True, context={"request": request}).data
        data["invoices"] = InvoiceListSerializer(
            Invoice.objects.filter(booking__customer=c).select_related("booking", "booking__customer"), many=True).data
        data["payments"] = PaymentSerializer(
            Payment.objects.filter(booking__customer=c).select_related("booking", "booking__customer"), many=True).data
        return Response(data)
