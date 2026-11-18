import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.core.files import RandomUploadPath, private_storage
from apps.core.models import TimeStampedModel, UUIDModel



class LocationType(models.TextChoices):
    AIRPORT = "AIRPORT", "Zanzibar Airport"
    TOWN = "TOWN", "Zanzibar Town"
    OUTSIDE_ZONE = "OUTSIDE_ZONE", "Outside Free Zone"


class BookingStatus(models.TextChoices):
    PENDING_CONFIRMATION = "PENDING_CONFIRMATION", "Pending confirmation"
    CONFIRMED = "CONFIRMED", "Confirmed"
    REJECTED = "REJECTED", "Rejected"
    CANCELLED = "CANCELLED", "Cancelled"
    COMPLETED = "COMPLETED", "Completed"
    EXPIRED = "EXPIRED", "Expired"


class PaymentStatus(models.TextChoices):
    UNPAID = "UNPAID", "Unpaid"
    PENDING_VERIFICATION = "PENDING_VERIFICATION", "Payment pending verification"
    PARTIALLY_PAID = "PARTIALLY_PAID", "Partially paid"
    PAID = "PAID", "Paid"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED", "Partially refunded"
    REFUNDED = "REFUNDED", "Refunded"


class PaymentMethodChoice(models.TextChoices):
    MANUAL = "MANUAL", "Manual payment"
    ONLINE = "ONLINE", "Online payment"


class PricingType(models.TextChoices):
    PER_BOOKING = "PER_BOOKING", "Per booking"
    PER_UNIT = "PER_UNIT", "Per unit, per booking"
    PER_DAY = "PER_DAY", "Per day"
    PER_UNIT_PER_DAY = "PER_UNIT_PER_DAY", "Per unit, per day"


class ExtraService(UUIDModel, TimeStampedModel):
    """Priced options. All fees live here so prices are never hard-coded.

    System rows (``is_system``) are created by migration and drive core rules:
      * outside_zone_delivery — charged per leg (pickup / return) outside the free zone
      * baby_seat              — per seat, per booking
      * driving_permit         — permit arrangement, requires documents
    """

    OUTSIDE_ZONE = "outside_zone_delivery"
    BABY_SEAT = "baby_seat"
    DRIVING_PERMIT = "driving_permit"

    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    pricing_type = models.CharField(max_length=20, choices=PricingType.choices, default=PricingType.PER_BOOKING)
    max_quantity = models.PositiveSmallIntegerField(default=1)
    # Optional volume price, e.g. baby seats: $60 each, or $50 each when taking 2 or more.
    bulk_min_quantity = models.PositiveSmallIntegerField(null=True, blank=True)
    bulk_unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    requires_documents = models.BooleanField(default=False)
    is_system = models.BooleanField(default=False, editable=False)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]
        constraints = [models.CheckConstraint(condition=Q(price__gte=0), name="extra_price_non_negative")]

    def __str__(self):
        return f"{self.name} (${self.price})"


class Booking(UUIDModel, TimeStampedModel):
    booking_reference = models.CharField(max_length=20, unique=True)
    customer = models.ForeignKey("customers.Customer", on_delete=models.PROTECT, related_name="bookings")
    vehicle = models.ForeignKey("vehicles.Vehicle", on_delete=models.PROTECT, related_name="bookings")

    pickup_date = models.DateField(db_index=True)
    pickup_time = models.TimeField()
    return_date = models.DateField()
    return_time = models.TimeField()
    pickup_at = models.DateTimeField()
    return_at = models.DateTimeField()
    # return_at + turnaround buffer; the exclusion constraint uses this.
    blocked_until = models.DateTimeField()
    rental_days = models.PositiveSmallIntegerField()

    pickup_type = models.CharField(max_length=15, choices=LocationType.choices)
    pickup_area = models.CharField(max_length=160, blank=True)
    pickup_address = models.CharField(max_length=255, blank=True)
    pickup_instructions = models.TextField(max_length=1000, blank=True)
    return_type = models.CharField(max_length=15, choices=LocationType.choices)
    return_area = models.CharField(max_length=160, blank=True)
    return_address = models.CharField(max_length=255, blank=True)
    return_instructions = models.TextField(max_length=1000, blank=True)

    # Price snapshot — never recalculated from the live vehicle price.
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2)
    rental_total = models.DecimalField(max_digits=12, decimal_places=2)
    pickup_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    return_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    extras_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    grand_total = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=3, default="USD")
    pricing_breakdown = models.JSONField(default=dict)

    booking_status = models.CharField(max_length=22, choices=BookingStatus.choices,
                                      default=BookingStatus.PENDING_CONFIRMATION, db_index=True)
    payment_status = models.CharField(max_length=22, choices=PaymentStatus.choices,
                                      default=PaymentStatus.UNPAID, db_index=True)
    payment_method = models.CharField(max_length=10, choices=PaymentMethodChoice.choices)

    # Inventory hold: True while the booking reserves the vehicle.
    blocks_inventory = models.BooleanField(default=True)
    hold_expires_at = models.DateTimeField(null=True, blank=True, db_index=True)

    customer_notes = models.TextField(max_length=2000, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=Q(return_at__gt=models.F("pickup_at")), name="booking_return_after_pickup"),
            models.CheckConstraint(condition=Q(blocked_until__gte=models.F("return_at")), name="booking_block_after_return"),
            models.CheckConstraint(condition=Q(rental_days__gte=1), name="booking_min_one_day"),
            models.CheckConstraint(condition=Q(grand_total__gte=0), name="booking_total_non_negative"),
            # The PostgreSQL EXCLUSION constraint "booking_no_vehicle_overlap" is
            # added by migration 0003 (PostgreSQL only, so SQLite works for dev).
        ]
        indexes = [
            models.Index(fields=["vehicle", "blocks_inventory", "pickup_at"]),
            models.Index(fields=["booking_status", "hold_expires_at"]),
        ]

    def __str__(self):
        return self.booking_reference

    @property
    def balance_due(self) -> Decimal:
        return max(self.grand_total - self.amount_paid, Decimal("0.00"))

    @property
    def is_open(self) -> bool:
        return self.booking_status in (BookingStatus.PENDING_CONFIRMATION, BookingStatus.CONFIRMED)

    def location_label(self, leg: str) -> str:
        t = getattr(self, f"{leg}_type")
        area = getattr(self, f"{leg}_area")
        label = LocationType(t).label
        return f"{label} — {area}" if area else label

    def location_address(self, leg: str) -> str:
        if getattr(self, f"{leg}_type") == LocationType.AIRPORT:
            return settings.DEFAULT_ARRIVAL_AIRPORT
        return getattr(self, f"{leg}_address")


class BookingExtra(UUIDModel):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="extras")
    extra_service = models.ForeignKey(ExtraService, null=True, blank=True, on_delete=models.SET_NULL)
    code = models.SlugField(max_length=50)
    service_name = models.CharField(max_length=100)
    pricing_type = models.CharField(max_length=20, choices=PricingType.choices)
    quantity = models.PositiveSmallIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["service_name"]
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gte=1), name="booking_extra_qty_positive"),
            models.UniqueConstraint(fields=["booking", "code"], name="booking_extra_unique_code"),
        ]

    def __str__(self):
        return f"{self.service_name} × {self.quantity}"


class BookingFlight(UUIDModel):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="flight")
    airline_name = models.CharField(max_length=80, blank=True)
    flight_number = models.CharField(max_length=20, blank=True)
    arrival_date = models.DateField(null=True, blank=True)
    arrival_time = models.TimeField(null=True, blank=True)
    arrival_airport = models.CharField(max_length=160, blank=True)
    notes = models.TextField(max_length=1000, blank=True)

    def __str__(self):
        return f"{self.airline_name} {self.flight_number}".strip() or "Flight"


class DocumentType(models.TextChoices):
    PASSPORT = "PASSPORT", "Passport"
    DRIVING_LICENCE = "DRIVING_LICENCE", "Driving licence"


class DocumentStatus(models.TextChoices):
    PENDING = "PENDING", "Pending review"
    VERIFIED = "VERIFIED", "Verified"
    REJECTED = "REJECTED", "Rejected"
    PURGED = "PURGED", "Deleted (retention policy)"


class BookingDocument(UUIDModel):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    # Stored in PRIVATE storage under a random name; never publicly addressable.
    secure_file = models.FileField(storage=private_storage, upload_to=RandomUploadPath("documents"),
                                   max_length=255, blank=True)
    original_filename = models.CharField(max_length=255, blank=True)
    file_kind = models.CharField(max_length=10, blank=True)
    file_size = models.PositiveIntegerField(default=0)
    sha256 = models.CharField(max_length=64, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verification_status = models.CharField(max_length=10, choices=DocumentStatus.choices,
                                           default=DocumentStatus.PENDING)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name="+")
    verified_at = models.DateTimeField(null=True, blank=True)
    purged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["document_type", "uploaded_at"]

    def __str__(self):
        return f"{self.get_document_type_display()} — {self.booking}"


class BookingDossier(UUIDModel, TimeStampedModel):
    """Private staff-only PDF containing a booking and uploaded identity files."""

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="dossier")
    pdf_file = models.FileField(storage=private_storage, upload_to=RandomUploadPath("dossiers"), blank=True,
                                max_length=255)
    source_digest = models.CharField(max_length=64, blank=True)

    def __str__(self):
        return f"Dossier for {self.booking.booking_reference}"


class BookingStatusHistory(models.Model):
    class Field(models.TextChoices):
        BOOKING = "booking_status", "Booking status"
        PAYMENT = "payment_status", "Payment status"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="status_history")
    status_field = models.CharField(max_length=20, choices=Field.choices, default=Field.BOOKING)
    previous_status = models.CharField(max_length=22, blank=True)
    new_status = models.CharField(max_length=22)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name="+")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name_plural = "booking status history"


class BookingNote(UUIDModel):
    """Internal staff notes — never shown to guests."""

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    body = models.TextField(max_length=4000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class BookingAccessToken(UUIDModel):
    """Expiring guest access credential. Only the SHA-256 hash is stored.

    A booking may have several live tokens (the confirmation page, each
    email); each can be revoked independently.
    """

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="access_tokens")
    token_hash = models.CharField(max_length=64, unique=True)
    purpose = models.CharField(max_length=64, default="guest")
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["booking", "expires_at"])]
