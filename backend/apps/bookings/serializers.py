import json

from django.conf import settings
from rest_framework import serializers

from apps.vehicles.models import Vehicle

from .models import (
    Booking, BookingDocument, BookingExtra, BookingFlight, BookingNote, BookingStatusHistory, ExtraService,
    LocationType, PaymentMethodChoice,
)


class ExtrasField(serializers.DictField):
    child = serializers.IntegerField(min_value=0, max_value=20)


class TripSerializer(serializers.Serializer):
    vehicle = serializers.SlugRelatedField(slug_field="slug", queryset=Vehicle.objects.filter(is_active=True))
    pickup_date = serializers.DateField()
    pickup_time = serializers.TimeField()
    return_date = serializers.DateField()
    return_time = serializers.TimeField()
    pickup_type = serializers.ChoiceField(choices=LocationType.choices)
    return_type = serializers.ChoiceField(choices=LocationType.choices)
    extras = ExtrasField(required=False, default=dict)


class QuoteSerializer(TripSerializer):
    pass


class CustomerInputSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=120, min_length=2)
    email = serializers.EmailField(max_length=254)
    phone = serializers.RegexField(r"^\+?[0-9 ()\-]{7,25}$", max_length=40,
                                   error_messages={"invalid": "Enter a valid phone number including country code."})
    nationality = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")
    additional_info = serializers.CharField(max_length=2000, required=False, allow_blank=True, default="")


class FlightInputSerializer(serializers.Serializer):
    airline_name = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")
    flight_number = serializers.RegexField(r"^[A-Za-z0-9 \-]{0,20}$", max_length=20, required=False,
                                           allow_blank=True, default="")
    arrival_date = serializers.DateField(required=False, allow_null=True, default=None)
    arrival_time = serializers.TimeField(required=False, allow_null=True, default=None)
    arrival_airport = serializers.CharField(max_length=160, required=False, allow_blank=True, default="")
    notes = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")


class BookingCreateSerializer(TripSerializer):
    customer = CustomerInputSerializer()
    pickup_area = serializers.CharField(max_length=160, required=False, allow_blank=True, default="")
    pickup_address = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    pickup_instructions = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")
    return_area = serializers.CharField(max_length=160, required=False, allow_blank=True, default="")
    return_address = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    return_instructions = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")
    flight = FlightInputSerializer(required=False, default=dict)
    payment_method = serializers.ChoiceField(choices=PaymentMethodChoice.choices)
    accept_terms = serializers.BooleanField()

    def validate_accept_terms(self, value):
        if not value:
            raise serializers.ValidationError("You must accept the rental terms and privacy policy.")
        return value

    @classmethod
    def from_request(cls, request):
        """Accept JSON bodies, or multipart with a JSON ``payload`` field plus files."""
        if hasattr(request.data, "getlist") and "payload" in request.data:
            try:
                data = json.loads(request.data["payload"])
            except (TypeError, ValueError):
                raise serializers.ValidationError({"payload": "Invalid booking data."})
        else:
            data = request.data
        return cls(data=data)


class ExtraServicePublicSerializer(serializers.ModelSerializer):
    pricing_type_display = serializers.CharField(source="get_pricing_type_display", read_only=True)

    class Meta:
        model = ExtraService
        fields = ["code", "name", "description", "price", "pricing_type", "pricing_type_display", "max_quantity",
                  "requires_documents"]


class ExtraServiceAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtraService
        fields = ["id", "code", "name", "description", "price", "pricing_type", "max_quantity", "requires_documents",
                  "is_active", "is_system", "display_order"]
        read_only_fields = ["id", "is_system"]

    def validate(self, attrs):
        inst = self.instance
        if inst and inst.is_system and "code" in attrs and attrs["code"] != inst.code:
            raise serializers.ValidationError({"code": "System service codes cannot be changed."})
        if attrs.get("price") is not None and attrs["price"] < 0:
            raise serializers.ValidationError({"price": "Price cannot be negative."})
        return attrs


class BookingExtraSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingExtra
        fields = ["code", "service_name", "pricing_type", "quantity", "unit_price", "total_price"]


class FlightSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingFlight
        fields = ["airline_name", "flight_number", "arrival_date", "arrival_time", "arrival_airport", "notes"]


def _vehicle_brief(v, request):
    img = v.primary_image
    url = None
    if img:
        url = img.image.url
        if request and url.startswith("/"):
            url = request.build_absolute_uri(url)
    return {"id": str(v.pk), "slug": v.slug, "name": v.name, "brand": v.brand, "model": v.model, "image": url,
            "transmission": v.get_transmission_display(), "passenger_capacity": v.passenger_capacity}


class _BookingCommon(serializers.ModelSerializer):
    vehicle = serializers.SerializerMethodField()
    booking_status_display = serializers.CharField(source="get_booking_status_display", read_only=True)
    payment_status_display = serializers.CharField(source="get_payment_status_display", read_only=True)
    payment_method_display = serializers.CharField(source="get_payment_method_display", read_only=True)
    pickup_type_display = serializers.CharField(source="get_pickup_type_display", read_only=True)
    return_type_display = serializers.CharField(source="get_return_type_display", read_only=True)
    balance_due = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    extras = BookingExtraSerializer(many=True, read_only=True)

    def get_vehicle(self, obj):
        return _vehicle_brief(obj.vehicle, self.context.get("request"))


GUEST_FIELDS = [
    "booking_reference", "vehicle", "pickup_date", "pickup_time", "return_date", "return_time", "rental_days",
    "pickup_type", "pickup_type_display", "pickup_area", "pickup_address", "pickup_instructions",
    "return_type", "return_type_display", "return_area", "return_address", "return_instructions",
    "daily_rate", "rental_total", "pickup_fee", "return_fee", "extras_total", "tax_amount", "grand_total",
    "amount_paid", "balance_due", "currency", "extras", "booking_status", "booking_status_display",
    "payment_status", "payment_status_display", "payment_method", "payment_method_display", "created_at",
    "hold_expires_at",
]


class GuestBookingSerializer(_BookingCommon):
    """What a guest holding a valid token may see about THEIR booking."""

    customer = serializers.SerializerMethodField()
    flight = serializers.SerializerMethodField()
    invoices = serializers.SerializerMethodField()
    receipts = serializers.SerializerMethodField()
    payments = serializers.SerializerMethodField()
    documents = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = GUEST_FIELDS + ["customer", "flight", "invoices", "receipts", "payments", "documents"]
        read_only_fields = fields

    def get_customer(self, obj):
        c = obj.customer
        return {"full_name": c.full_name, "email": c.email, "phone": c.phone, "nationality": c.nationality}

    def get_flight(self, obj):
        f = BookingFlight.objects.filter(booking=obj).first()
        return FlightSerializer(f).data if f else None

    def get_invoices(self, obj):
        return [{"invoice_number": i.invoice_number, "issue_date": i.issue_date, "total_amount": str(i.total_amount),
                 "invoice_status": i.invoice_status, "revision_number": i.revision_number}
                for i in obj.invoices.order_by("-revision_number")]

    def get_receipts(self, obj):
        return [{"receipt_number": r.receipt_number, "issue_date": r.issue_date, "amount": str(r.amount)}
                for r in obj.receipts.all()]

    def get_payments(self, obj):
        return [{"payment_reference": p.payment_reference, "amount": str(p.amount),
                 "payment_method": p.get_payment_method_display(), "status": p.payment_status,
                 "status_display": p.get_payment_status_display(), "created_at": p.created_at}
                for p in obj.payments.exclude(payment_status="CANCELLED")]

    def get_documents(self, obj):
        # Metadata only — files are never downloadable by guests.
        return [{"document_type": d.get_document_type_display(), "status": d.get_verification_status_display()}
                for d in obj.documents.all()]


class AdminBookingListSerializer(_BookingCommon):
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    customer_email = serializers.CharField(source="customer.email", read_only=True)
    customer_phone = serializers.CharField(source="customer.phone", read_only=True)

    class Meta:
        model = Booking
        fields = ["id", "booking_reference", "customer_name", "customer_email", "customer_phone", "vehicle",
                  "pickup_date", "pickup_time", "return_date", "return_time", "rental_days", "pickup_type",
                  "pickup_type_display", "return_type", "return_type_display", "grand_total", "amount_paid",
                  "balance_due", "booking_status", "booking_status_display", "payment_status",
                  "payment_status_display", "payment_method", "payment_method_display", "hold_expires_at",
                  "created_at", "extras"]


class DocumentSerializer(serializers.ModelSerializer):
    document_type_display = serializers.CharField(source="get_document_type_display", read_only=True)
    verification_status_display = serializers.CharField(source="get_verification_status_display", read_only=True)
    verified_by = serializers.CharField(source="verified_by.full_name", read_only=True, default=None)
    has_file = serializers.SerializerMethodField()

    class Meta:
        model = BookingDocument
        fields = ["id", "document_type", "document_type_display", "original_filename", "file_kind", "file_size",
                  "uploaded_at", "verification_status", "verification_status_display", "verified_by",
                  "verified_at", "purged_at", "has_file"]

    def get_has_file(self, obj):
        return bool(obj.secure_file)


class HistorySerializer(serializers.ModelSerializer):
    changed_by = serializers.CharField(source="changed_by.full_name", read_only=True, default=None)

    class Meta:
        model = BookingStatusHistory
        fields = ["id", "status_field", "previous_status", "new_status", "changed_by", "notes", "created_at"]


class NoteSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="author.full_name", read_only=True, default=None)

    class Meta:
        model = BookingNote
        fields = ["id", "body", "author", "created_at"]
        read_only_fields = ["id", "author", "created_at"]


class AdminBookingDetailSerializer(AdminBookingListSerializer):
    customer = serializers.SerializerMethodField()
    flight = serializers.SerializerMethodField()
    documents = DocumentSerializer(many=True, read_only=True)
    status_history = HistorySerializer(many=True, read_only=True)
    notes = NoteSerializer(many=True, read_only=True)
    invoices = serializers.SerializerMethodField()
    payments = serializers.SerializerMethodField()
    receipts = serializers.SerializerMethodField()
    notifications = serializers.SerializerMethodField()
    whatsapp = serializers.SerializerMethodField()
    allowed_transitions = serializers.SerializerMethodField()

    class Meta(AdminBookingListSerializer.Meta):
        fields = AdminBookingListSerializer.Meta.fields + [
            "customer", "pickup_area", "pickup_address", "pickup_instructions", "return_area", "return_address",
            "return_instructions", "daily_rate", "rental_total", "pickup_fee", "return_fee", "extras_total",
            "tax_amount", "currency", "pricing_breakdown", "customer_notes", "blocks_inventory", "status_reason",
            "confirmed_at", "cancelled_at", "completed_at", "flight", "documents", "status_history", "notes",
            "invoices", "payments", "receipts", "notifications", "whatsapp", "allowed_transitions", "updated_at",
        ]

    def get_customer(self, obj):
        c = obj.customer
        return {"id": str(c.pk), "full_name": c.full_name, "email": c.email, "phone": c.phone,
                "nationality": c.nationality}

    def get_flight(self, obj):
        f = BookingFlight.objects.filter(booking=obj).first()
        return FlightSerializer(f).data if f else None

    def get_invoices(self, obj):
        from apps.invoices.serializers import InvoiceListSerializer
        return InvoiceListSerializer(obj.invoices.order_by("-revision_number"), many=True).data

    def get_payments(self, obj):
        from apps.payments.serializers import PaymentSerializer
        return PaymentSerializer(obj.payments.all(), many=True).data

    def get_receipts(self, obj):
        return [{"id": str(r.pk), "receipt_number": r.receipt_number, "amount": str(r.amount),
                 "issue_date": r.issue_date} for r in obj.receipts.all()]

    def get_notifications(self, obj):
        from apps.notifications.serializers import NotificationSerializer
        return NotificationSerializer(obj.notifications.all()[:50], many=True).data

    def get_whatsapp(self, obj):
        from .whatsapp import guest_chat_url, owner_message_url
        return {"to_guest": guest_chat_url(obj), "owner_summary": owner_message_url(obj)}

    def get_allowed_transitions(self, obj):
        from .services import ALLOWED_TRANSITIONS
        return sorted(ALLOWED_TRANSITIONS.get(obj.booking_status, set()))


class StatusActionSerializer(serializers.Serializer):
    notes = serializers.CharField(max_length=2000, required=False, allow_blank=True, default="")
    notify_guest = serializers.BooleanField(required=False, default=True)


class ModifyBookingSerializer(serializers.Serializer):
    vehicle = serializers.PrimaryKeyRelatedField(queryset=Vehicle.objects.all(), required=False)
    pickup_date = serializers.DateField(required=False)
    pickup_time = serializers.TimeField(required=False)
    return_date = serializers.DateField(required=False)
    return_time = serializers.TimeField(required=False)
    pickup_type = serializers.ChoiceField(choices=LocationType.choices, required=False)
    return_type = serializers.ChoiceField(choices=LocationType.choices, required=False)
    pickup_area = serializers.CharField(max_length=160, required=False, allow_blank=True)
    pickup_address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    pickup_instructions = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    return_area = serializers.CharField(max_length=160, required=False, allow_blank=True)
    return_address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    return_instructions = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    extras = ExtrasField(required=False)
    reason = serializers.CharField(max_length=255)


def booking_options() -> dict:
    """Public configuration the booking form needs (prices come from the DB)."""
    from apps.core.models import SiteSettings
    from apps.payments.gateways import available_gateways

    services = {s.code: s for s in ExtraService.objects.filter(is_active=True)}
    zone = services.get(ExtraService.OUTSIDE_ZONE)
    zone_fee = str(zone.price) if zone else "0.00"
    site = SiteSettings.load()
    return {
        "currency": settings.CURRENCY,
        "locations": [
            {"code": LocationType.AIRPORT, "label": LocationType.AIRPORT.label, "fee": "0.00"},
            {"code": LocationType.TOWN, "label": LocationType.TOWN.label, "fee": "0.00"},
            {"code": LocationType.OUTSIDE_ZONE, "label": LocationType.OUTSIDE_ZONE.label, "fee": zone_fee},
        ],
        "extras": ExtraServicePublicSerializer(
            [s for c, s in services.items() if c != ExtraService.OUTSIDE_ZONE], many=True).data,
        "default_arrival_airport": settings.DEFAULT_ARRIVAL_AIRPORT,
        "hold_hours": settings.BOOKING_HOLD_HOURS,
        "min_lead_hours": settings.BOOKING_MIN_LEAD_HOURS,
        "max_rental_days": settings.BOOKING_MAX_RENTAL_DAYS,
        "max_upload_mb": settings.MAX_UPLOAD_SIZE_MB,
        "payment_methods": {
            "manual": {"available": True, "instructions": site.payment_instructions},
            "online": {"available": bool(available_gateways()),
                       "gateways": [{"code": g.code, "name": g.display_name} for g in available_gateways()]},
        },
    }
