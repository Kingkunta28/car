from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.core.files import RandomUploadPath, private_storage
from apps.core.models import TimeStampedModel, UUIDModel


class Method(models.TextChoices):
    MANUAL = "MANUAL", "Manual payment"
    ONLINE = "ONLINE", "Online payment"


class Channel(models.TextChoices):
    BANK_TRANSFER = "BANK_TRANSFER", "Bank transfer"
    MOBILE_MONEY = "MOBILE_MONEY", "Mobile money"
    CASH = "CASH", "Cash"
    CARD = "CARD", "Card"
    OTHER = "OTHER", "Other"


class Status(models.TextChoices):
    INITIATED = "INITIATED", "Initiated"  # online checkout started, not yet confirmed
    PENDING_VERIFICATION = "PENDING_VERIFICATION", "Pending verification"  # manual, awaiting staff review
    VERIFIED = "VERIFIED", "Verified"
    FAILED = "FAILED", "Failed"
    REJECTED = "REJECTED", "Rejected"
    CANCELLED = "CANCELLED", "Cancelled"
    REVERSED = "REVERSED", "Reversed by gateway"


class VerificationSource(models.TextChoices):
    GATEWAY_API = "GATEWAY_API", "Confirmed by gateway API"
    STAFF_REVIEW = "STAFF_REVIEW", "Verified by staff review"
    STAFF_RECORDED = "STAFF_RECORDED", "Recorded by staff"


class Payment(UUIDModel, TimeStampedModel):
    """A single payment attempt. A booking may have many (deposits, balances).

    Only VERIFIED payments count towards ``Booking.amount_paid``. Card data
    is never seen or stored: online payments happen on the gateway's page.
    """

    booking = models.ForeignKey("bookings.Booking", on_delete=models.PROTECT, related_name="payments")
    payment_reference = models.CharField(max_length=20, unique=True)
    payment_method = models.CharField(max_length=10, choices=Method.choices)
    channel = models.CharField(max_length=15, choices=Channel.choices, blank=True)
    gateway = models.CharField(max_length=30, blank=True, db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    payment_status = models.CharField(max_length=22, choices=Status.choices, db_index=True)
    # Payer-supplied reference (manual) or gateway confirmation code (online).
    transaction_reference = models.CharField(max_length=120, blank=True)
    # Gateway's own order id (Pesapal OrderTrackingId) — unique per gateway.
    gateway_order_id = models.CharField(max_length=120, null=True, blank=True)
    gateway_response_reference = models.CharField(max_length=120, blank=True)
    gateway_payload = models.JSONField(default=dict, blank=True)
    checkout_url = models.URLField(max_length=500, blank=True)
    proof_file = models.FileField(storage=private_storage, upload_to=RandomUploadPath("payment-proofs"),
                                  blank=True, max_length=255)
    payer_note = models.TextField(max_length=1000, blank=True)
    refunded_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name="+")
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name="+")
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_source = models.CharField(max_length=15, choices=VerificationSource.choices, blank=True)
    review_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="payment_amount_positive"),
            models.CheckConstraint(condition=Q(refunded_amount__gte=0) & Q(refunded_amount__lte=models.F("amount")),
                                   name="payment_refund_within_amount"),
            models.UniqueConstraint(fields=["gateway", "gateway_order_id"], condition=Q(gateway_order_id__isnull=False),
                                    name="payment_unique_gateway_order"),
            models.UniqueConstraint(fields=["gateway", "transaction_reference"],
                                    condition=Q(payment_method="ONLINE") & ~Q(transaction_reference=""),
                                    name="payment_unique_gateway_transaction"),
            # A verified payment must say who/what verified it.
            models.CheckConstraint(
                condition=~Q(payment_status="VERIFIED") | (Q(verified_at__isnull=False) & ~Q(verification_source="")),
                name="payment_verified_is_audited",
            ),
        ]

    def __str__(self):
        return f"{self.payment_reference} ${self.amount} {self.payment_status}"

    @property
    def net_amount(self) -> Decimal:
        return self.amount - self.refunded_amount


class Refund(UUIDModel):
    class RefundStatus(models.TextChoices):
        REQUESTED = "REQUESTED", "Requested at gateway"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="refunds")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=RefundStatus.choices)
    gateway_reference = models.CharField(max_length=120, blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name="refund_amount_positive")]


class Receipt(UUIDModel):
    """Proof of a verified payment — distinct from an invoice."""

    receipt_number = models.CharField(max_length=30, unique=True)
    payment = models.OneToOneField(Payment, on_delete=models.PROTECT, related_name="receipt")
    booking = models.ForeignKey("bookings.Booking", on_delete=models.PROTECT, related_name="receipts")
    issue_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    snapshot = models.JSONField(default=dict)
    pdf_file = models.FileField(storage=private_storage, upload_to=RandomUploadPath("receipts"), blank=True,
                                max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.receipt_number

    @property
    def filename(self):
        return f"Rafiki-Car-Hire-Receipt-{self.receipt_number}.pdf"
