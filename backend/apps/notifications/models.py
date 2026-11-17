from django.db import models

from apps.core.models import TimeStampedModel, UUIDModel


class NotificationType(models.TextChoices):
    BOOKING_SUBMITTED_GUEST = "BOOKING_SUBMITTED_GUEST", "Booking received + invoice (guest)"
    BOOKING_SUBMITTED_OWNER = "BOOKING_SUBMITTED_OWNER", "New booking + invoice (owner)"
    INVOICE_GUEST = "INVOICE_GUEST", "Invoice delivery (guest)"
    INVOICE_OWNER = "INVOICE_OWNER", "Invoice notification (owner)"
    BOOKING_CONFIRMED = "BOOKING_CONFIRMED", "Booking confirmed (guest)"
    BOOKING_REJECTED = "BOOKING_REJECTED", "Booking rejected (guest)"
    BOOKING_CANCELLED = "BOOKING_CANCELLED", "Booking cancelled (guest)"
    PAYMENT_RECEIVED_GUEST = "PAYMENT_RECEIVED_GUEST", "Payment received (guest)"
    PAYMENT_RECEIVED_OWNER = "PAYMENT_RECEIVED_OWNER", "Payment received (owner)"
    MANUAL_PAYMENT_SUBMITTED_OWNER = "MANUAL_PAYMENT_SUBMITTED_OWNER", "Manual payment to verify (owner)"
    MANUAL_PAYMENT_REJECTED = "MANUAL_PAYMENT_REJECTED", "Manual payment not verified (guest)"
    PAYMENT_FAILED = "PAYMENT_FAILED", "Online payment failed (guest)"
    CONTACT_MESSAGE_OWNER = "CONTACT_MESSAGE_OWNER", "Contact form message (owner)"


class DeliveryStatus(models.TextChoices):
    QUEUED = "QUEUED", "Queued"
    SENT = "SENT", "Sent"
    FAILED = "FAILED", "Failed — will retry"
    ABANDONED = "ABANDONED", "Failed — retries exhausted"


class NotificationLog(UUIDModel, TimeStampedModel):
    booking = models.ForeignKey("bookings.Booking", null=True, blank=True, on_delete=models.CASCADE,
                                related_name="notifications")
    invoice = models.ForeignKey("invoices.Invoice", null=True, blank=True, on_delete=models.SET_NULL,
                                related_name="notifications")
    payment = models.ForeignKey("payments.Payment", null=True, blank=True, on_delete=models.SET_NULL,
                                related_name="notifications")
    recipient = models.EmailField()
    notification_type = models.CharField(max_length=40, choices=NotificationType.choices, db_index=True)
    subject = models.CharField(max_length=200, blank=True)
    # Non-sensitive render inputs only (never tokens, never document URLs).
    context = models.JSONField(default=dict, blank=True)
    delivery_status = models.CharField(max_length=10, choices=DeliveryStatus.choices, default=DeliveryStatus.QUEUED,
                                       db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    error_message = models.TextField(blank=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_notification_type_display()} → {self.recipient} ({self.delivery_status})"
