import json
from uuid import UUID

from django.conf import settings
from rest_framework import serializers

from apps.vehicles.models import Vehicle

from .models import (
    Booking, BookingDocument, BookingExtra, BookingFlight, BookingNote, BookingStatusHistory, ExtraService,
    LocationType, PaymentMethodChoice,
)
from .vehicle_data import STATIC_VEHICLE_RATES, model_vehicle_snapshot


class ExtrasField(serializers.DictField):
    child = serializers.IntegerField(min_value=0, max_value=20)


class VehicleSnapshotInputSerializer(serializers.Serializer):
    id = serializers.SlugField(max_length=140)
    slug = serializers.SlugField(max_length=140)
    name = serializers.CharField(max_length=160)
    brand = serializers.CharField(max_length=80)
    model = serializers.CharField(max_length=100)
    year = serializers.IntegerField(required=False, allow_null=True)
    category = serializers.CharField(max_length=30)
    category_display = serializers.CharField(max_length=60, required=False, allow_blank=True, default="")
    description = serializers.CharField(max_length=4000, required=False, allow_blank=True, default="")
    price_per_day = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    transmission = serializers.CharField(max_length=20)
    transmission_display = serializers.CharField(max_length=40, required=False, allow_blank=True, default="")
    fuel_type = serializers.CharField(max_length=20)
    fuel_type_display = serializers.CharField(max_length=40, required=False, allow_blank=True, default="")
    passenger_capacity = serializers.IntegerField(min_value=1, max_value=30)
    luggage_capacity = serializers.IntegerField(min_value=0, max_value=30)
    doors = serializers.IntegerField(required=False, min_value=1, max_value=10, default=4)
    features = serializers.ListField(child=serializers.CharField(max_length=120), required=False, default=list)
    availability_status = serializers.CharField(max_length=20, required=False, default="AVAILABLE")
    availability_display = serializers.CharField(max_length=40, required=False, default="Available")
    main_image = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    gallery_images = serializers.ListField(child=serializers.CharField(max_length=500), required=False, default=list)


class BookingVehicleReferenceField(serializers.CharField):
    """Resolve legacy UUIDs to Vehicle rows and leave static booking slugs as strings."""
    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        try:
            UUID(value)
        except (ValueError, TypeError, AttributeError):
            return value
        return Vehicle.objects.filter(pk=value).first() or value


class TripSerializer(serializers.Serializer):
    vehicle = serializers.SlugField(max_length=140)
    vehicle_id = serializers.SlugField(max_length=140, required=False)
    vehicle_snapshot = VehicleSnapshotInputSerializer(required=False)
    daily_rate = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, required=False)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, required=False)
    pickup_date = serializers.DateField()
    pickup_time = serializers.TimeField()
    return_date = serializers.DateField()
    return_time = serializers.TimeField()
    pickup_type = serializers.ChoiceField(choices=LocationType.choices)
    return_type = serializers.ChoiceField(choices=LocationType.choices)
    extras = ExtrasField(required=False, default=dict)

    def validate(self, attrs):
        slug = attrs["vehicle"]
        submitted_snapshot = attrs.get("vehicle_snapshot")
        submitted_id = attrs.get("vehicle_id")
        daily_rate = attrs.get("daily_rate")
        if submitted_snapshot is not None:
            authoritative_rate = STATIC_VEHICLE_RATES.get(slug)
            if authoritative_rate is None:
                raise serializers.ValidationError({"vehicle": "This vehicle is not in the approved booking catalogue."})
            if submitted_id != slug or submitted_snapshot["id"] != slug or submitted_snapshot["slug"] != slug:
                raise serializers.ValidationError({"vehicle_id": "Vehicle ID and slug must match the selected catalogue vehicle."})
            if submitted_snapshot["price_per_day"] != authoritative_rate or daily_rate != authoritative_rate:
                raise serializers.ValidationError({"daily_rate": "The vehicle rate has changed. Refresh the fleet and try again."})
            snapshot = dict(submitted_snapshot)
            snapshot["price_per_day"] = str(authoritative_rate)
            vehicle_model = None
        else:
            # Compatibility for existing clients and historical database vehicles.
            vehicle_model = Vehicle.objects.filter(slug=slug, is_active=True).first()
            if vehicle_model is None:
                raise serializers.ValidationError({"vehicle_snapshot": "Vehicle details are required for this booking."})
            if daily_rate is not None and daily_rate != vehicle_model.price_per_day:
                raise serializers.ValidationError({"daily_rate": "The submitted rate does not match the vehicle's current rate."})
            snapshot = model_vehicle_snapshot(vehicle_model)
            snapshot["price_per_day"] = str(vehicle_model.price_per_day)
            submitted_id = slug

        attrs["vehicle_slug"] = slug
        attrs["vehicle_id"] = submitted_id or slug
        attrs["vehicle_model"] = vehicle_model
        attrs["vehicle_snapshot"] = snapshot
        return attrs


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

    def validate_payment_method(self, value):
        if value == PaymentMethodChoice.ONLINE:
            from apps.payments.gateways import available_gateways

            if not available_gateways():
                raise serializers.ValidationError(
                    "Online payment is temporarily unavailable. Please choose manual payment."
                )
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
                  "bulk_min_quantity", "bulk_unit_price", "requires_documents"]


class ExtraServiceAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtraService
        fields = ["id", "code", "name", "description", "price", "pricing_type", "max_quantity", "bulk_min_quantity",
                  "bulk_unit_price", "requires_documents", "is_active", "is_system", "display_order"]
        read_only_fields = ["id", "is_system"]

    def validate(self, attrs):
        inst = self.instance
        if inst and inst.is_system and "code" in attrs and attrs["code"] != inst.code:
            raise serializers.ValidationError({"code": "System service codes cannot be changed."})
        if attrs.get("price") is not None and attrs["price"] < 0:
            raise serializers.ValidationError({"price": "Price cannot be negative."})
        bmin = attrs.get("bulk_min_quantity", getattr(inst, "bulk_min_quantity", None))
        bprice = attrs.get("bulk_unit_price", getattr(inst, "bulk_unit_price", None))
        if bool(bmin) != (bprice is not None):
            raise serializers.ValidationError({"bulk_unit_price": "Set both the bulk quantity and the bulk price, or neither."})
        if bmin is not None and bmin < 2:
            raise serializers.ValidationError({"bulk_min_quantity": "Bulk pricing must start at 2 or more."})
        return attrs


class BookingExtraSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingExtra
        fields = ["code", "service_name", "pricing_type", "quantity", "unit_price", "total_price"]


class FlightSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingFlight
        fields = ["airline_name", "flight_number", "arrival_date", "arrival_time", "arrival_airport", "notes"]


def _vehicle_brief(booking):
    from .vehicle_data import booking_vehicle_snapshot

    snapshot = booking_vehicle_snapshot(booking)
    return {**snapshot, "image": snapshot.get("main_image") or snapshot.get("image") or None,
            "transmission": snapshot.get("transmission_display") or snapshot.get("transmission", "")}


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
        return _vehicle_brief(obj)


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
    vehicle = BookingVehicleReferenceField(max_length=140, required=False)
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
