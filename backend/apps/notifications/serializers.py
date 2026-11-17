from rest_framework import serializers

from .models import NotificationLog


class NotificationSerializer(serializers.ModelSerializer):
    notification_type_display = serializers.CharField(source="get_notification_type_display", read_only=True)
    delivery_status_display = serializers.CharField(source="get_delivery_status_display", read_only=True)
    booking_reference = serializers.CharField(source="booking.booking_reference", default=None, read_only=True)
    invoice_number = serializers.CharField(source="invoice.invoice_number", default=None, read_only=True)

    class Meta:
        model = NotificationLog
        fields = ["id", "booking_reference", "invoice_number", "recipient", "notification_type",
                  "notification_type_display", "subject", "delivery_status", "delivery_status_display", "attempts",
                  "error_message", "last_attempt_at", "next_retry_at", "sent_at", "created_at"]
