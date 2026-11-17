import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class Sequence(models.Model):
    """Concurrency-safe counters for human-readable document numbers.

    One row per key (e.g. "RCI-2026"). Rows are incremented under
    SELECT ... FOR UPDATE inside the caller's transaction, so two
    concurrent requests can never receive the same value.
    """

    key = models.CharField(max_length=40, primary_key=True)
    last_value = models.PositiveBigIntegerField(default=0)

    def __str__(self):
        return f"{self.key}: {self.last_value}"


class SiteSettings(models.Model):
    """Singleton holding business information managed from the dashboard.

    Contains no secrets: SMTP and payment credentials live in environment
    variables only. ``email_configuration_reference`` is a human note such as
    "Brevo SMTP — configured on Render".
    """

    business_name = models.CharField(max_length=120, default="Rafiki Car Hire")
    tagline = models.CharField(max_length=160, default="Drive Zanzibar with Confidence.")
    business_email = models.EmailField(blank=True)
    business_phone = models.CharField(max_length=40, blank=True)
    whatsapp_number = models.CharField(
        max_length=20, blank=True,
        help_text="International format digits only, e.g. 255777123456",
    )
    business_address = models.CharField(max_length=255, default="Zanzibar, Tanzania")
    logo = models.ImageField(upload_to="branding/", blank=True)
    hero_image = models.ImageField(upload_to="branding/", blank=True,
                                   help_text="Wide landscape photo for the homepage hero (min. 2000px wide).")
    owner_notification_email = models.EmailField(
        blank=True, help_text="Where new booking and payment alerts are sent. Falls back to the environment setting.",
    )
    invoice_footer = models.TextField(blank=True, default="Thank you for choosing Rafiki Car Hire.")
    invoice_terms = models.TextField(
        blank=True,
        default=(
            "This invoice confirms that a booking request has been received. It is not a confirmation of "
            "the reservation or a receipt of payment. Your reservation is confirmed only when Rafiki Car "
            "Hire confirms it in writing. A payment receipt is issued separately for each verified payment."
        ),
    )
    payment_instructions = models.TextField(
        blank=True, help_text="Shown to guests who choose manual payment (bank, mobile money, etc.).",
    )
    currency = models.CharField(max_length=3, default="USD", editable=False)
    tax_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Percentage applied to invoice subtotals. 0 disables tax.",
    )
    tax_label = models.CharField(max_length=40, default="VAT", blank=True)
    email_configuration_reference = models.CharField(max_length=200, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = verbose_name_plural = "Site settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "SiteSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def owner_email(self) -> str:
        return self.owner_notification_email or settings.OWNER_NOTIFICATION_EMAIL

    def __str__(self):
        return self.business_name


class AuditLog(models.Model):
    """Append-only record of security- and money-relevant actions."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                              related_name="audit_logs")
    action = models.CharField(max_length=80, db_index=True)
    target_type = models.CharField(max_length=60, blank=True)
    target_id = models.CharField(max_length=64, blank=True)
    summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["target_type", "target_id"])]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.action} {self.target_type}:{self.target_id}"


class ContactMessage(UUIDModel, TimeStampedModel):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    subject = models.CharField(max_length=160, blank=True)
    message = models.TextField(max_length=4000)
    is_handled = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} — {self.subject or 'Enquiry'}"


class Testimonial(UUIDModel, TimeStampedModel):
    """Genuine customer reviews entered by staff. Nothing is shown until published."""

    customer_name = models.CharField(max_length=120)
    country = models.CharField(max_length=80, blank=True)
    quote = models.TextField(max_length=1000)
    rating = models.PositiveSmallIntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(5)])
    is_published = models.BooleanField(default=False)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "-created_at"]

    def __str__(self):
        return self.customer_name
