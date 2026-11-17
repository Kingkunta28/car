from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.core.files import RandomUploadPath, private_storage
from apps.core.models import UUIDModel


class InvoiceStatus(models.TextChoices):
    ISSUED = "ISSUED", "Issued"
    SUPERSEDED = "SUPERSEDED", "Superseded by revision"
    VOID = "VOID", "Void"


class Invoice(UUIDModel):
    """An issued invoice. Immutable once issued: changes create a revision.

    ``snapshot`` holds every value printed on the PDF, so the document can be
    re-rendered byte-for-byte in content even if the booking later changes.
    """

    invoice_number = models.CharField(max_length=30, unique=True)
    booking = models.ForeignKey("bookings.Booking", on_delete=models.PROTECT, related_name="invoices")
    issue_date = models.DateField()
    revision_number = models.PositiveSmallIntegerField(default=0)
    original_invoice = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT,
                                         related_name="revisions")
    supersedes = models.OneToOneField("self", null=True, blank=True, on_delete=models.PROTECT,
                                      related_name="superseded_by")
    revision_reason = models.CharField(max_length=255, blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    invoice_status = models.CharField(max_length=12, choices=InvoiceStatus.choices, default=InvoiceStatus.ISSUED,
                                      db_index=True)
    snapshot = models.JSONField(default=dict)
    pdf_file = models.FileField(storage=private_storage, upload_to=RandomUploadPath("invoices"), blank=True,
                                max_length=255)
    pdf_sha256 = models.CharField(max_length=64, blank=True)
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                  related_name="+")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # At most one current (ISSUED) invoice per booking.
            models.UniqueConstraint(fields=["booking"], condition=Q(invoice_status="ISSUED"),
                                    name="invoice_one_current_per_booking"),
            models.UniqueConstraint(fields=["booking", "revision_number"], name="invoice_unique_revision"),
            models.CheckConstraint(condition=Q(total_amount__gte=0), name="invoice_total_non_negative"),
        ]

    def __str__(self):
        return self.invoice_number

    @property
    def filename(self):
        return f"Rafiki-Car-Hire-Invoice-{self.invoice_number}.pdf"


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.description
