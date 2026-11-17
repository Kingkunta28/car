from decimal import Decimal

from rest_framework import serializers

from .models import Channel, Payment, Refund


class RefundSerializer(serializers.ModelSerializer):
    recorded_by = serializers.CharField(source="recorded_by.full_name", default=None, read_only=True)

    class Meta:
        model = Refund
        fields = ["id", "amount", "reason", "status", "gateway_reference", "recorded_by", "created_at", "processed_at"]


class PaymentSerializer(serializers.ModelSerializer):
    booking_reference = serializers.CharField(source="booking.booking_reference", read_only=True)
    booking_id = serializers.UUIDField(source="booking.pk", read_only=True)
    customer_name = serializers.CharField(source="booking.customer.full_name", read_only=True)
    payment_status_display = serializers.CharField(source="get_payment_status_display", read_only=True)
    payment_method_display = serializers.CharField(source="get_payment_method_display", read_only=True)
    channel_display = serializers.CharField(source="get_channel_display", read_only=True)
    verification_source_display = serializers.CharField(source="get_verification_source_display", read_only=True)
    verified_by = serializers.CharField(source="verified_by.full_name", default=None, read_only=True)
    recorded_by = serializers.CharField(source="recorded_by.full_name", default=None, read_only=True)
    has_proof = serializers.SerializerMethodField()
    receipt_number = serializers.SerializerMethodField()
    refunds = RefundSerializer(many=True, read_only=True)

    class Meta:
        model = Payment
        fields = ["id", "payment_reference", "booking_id", "booking_reference", "customer_name", "payment_method",
                  "payment_method_display", "channel", "channel_display", "gateway", "amount", "refunded_amount",
                  "currency", "payment_status", "payment_status_display", "transaction_reference",
                  "gateway_order_id", "payer_note", "review_notes", "verification_source",
                  "verification_source_display", "verified_by", "verified_at", "recorded_by", "has_proof",
                  "receipt_number", "refunds", "created_at"]

    def get_has_proof(self, obj):
        return bool(obj.proof_file)

    def get_receipt_number(self, obj):
        return obj.receipt.receipt_number if hasattr(obj, "receipt") else None


class ManualPaymentSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    channel = serializers.ChoiceField(choices=[c for c in Channel.choices if c[0] != Channel.CARD])
    transaction_reference = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    note = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")
    proof = serializers.FileField(required=False, allow_null=True)


class OnlineInitiateSerializer(serializers.Serializer):
    gateway = serializers.CharField(max_length=30, required=False, default="pesapal")
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"), required=False)


class OnlineVerifySerializer(serializers.Serializer):
    order_tracking_id = serializers.CharField(max_length=120)


class VerifySerializer(serializers.Serializer):
    notes = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    confirm = serializers.BooleanField()

    def validate_confirm(self, v):
        if not v:
            raise serializers.ValidationError("Confirm that you have checked the funds were received.")
        return v


class RejectSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000)


class RecordPaymentSerializer(serializers.Serializer):
    booking = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    channel = serializers.ChoiceField(choices=Channel.choices)
    transaction_reference = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    notes = serializers.CharField(max_length=1000)


class RefundInputSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    reason = serializers.CharField(max_length=255)
    via_gateway = serializers.BooleanField(required=False, default=False)
