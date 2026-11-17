from rest_framework import serializers

from .models import Invoice, InvoiceItem


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = ["description", "quantity", "unit_price", "total_price"]


class InvoiceListSerializer(serializers.ModelSerializer):
    booking_reference = serializers.CharField(source="booking.booking_reference", read_only=True)
    booking_id = serializers.UUIDField(source="booking.pk", read_only=True)
    customer_name = serializers.CharField(source="booking.customer.full_name", read_only=True)
    invoice_status_display = serializers.CharField(source="get_invoice_status_display", read_only=True)
    payment_status = serializers.CharField(source="booking.payment_status", read_only=True)
    payment_status_display = serializers.CharField(source="booking.get_payment_status_display", read_only=True)
    has_pdf = serializers.SerializerMethodField()
    delivery = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = ["id", "invoice_number", "booking_id", "booking_reference", "customer_name", "issue_date",
                  "revision_number", "revision_reason", "subtotal", "tax_amount", "total_amount", "currency",
                  "invoice_status", "invoice_status_display", "payment_status", "payment_status_display", "has_pdf",
                  "delivery", "created_at"]

    def get_has_pdf(self, obj):
        return bool(obj.pdf_file)

    def get_delivery(self, obj):
        logs = list(obj.notifications.order_by("-created_at").values("recipient", "delivery_status", "attempts",
                                                                     "sent_at", "notification_type")[:6])
        return logs


class InvoiceDetailSerializer(InvoiceListSerializer):
    items = InvoiceItemSerializer(many=True, read_only=True)
    supersedes_number = serializers.CharField(source="supersedes.invoice_number", read_only=True, default=None)

    class Meta(InvoiceListSerializer.Meta):
        fields = InvoiceListSerializer.Meta.fields + ["items", "supersedes_number", "snapshot"]
