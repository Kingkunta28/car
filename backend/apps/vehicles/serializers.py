from django.db import transaction
from rest_framework import serializers

from apps.core.files import IMAGE_TYPES, validate_upload

from .models import Vehicle, VehicleFeature, VehicleImage


class VehicleImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = VehicleImage
        fields = ["id", "url", "alt_text", "display_order"]

    def get_url(self, obj):
        request = self.context.get("request")
        url = obj.image.url
        return request.build_absolute_uri(url) if request and url.startswith("/") else url


class _VehicleBase(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    transmission_display = serializers.CharField(source="get_transmission_display", read_only=True)
    fuel_type_display = serializers.CharField(source="get_fuel_type_display", read_only=True)
    availability_display = serializers.CharField(source="get_availability_status_display", read_only=True)
    images = VehicleImageSerializer(many=True, read_only=True)
    features = serializers.SerializerMethodField()

    def get_features(self, obj):
        return [f.feature_name for f in obj.features.all()]


PUBLIC_FIELDS = [
    "id", "slug", "name", "brand", "model", "year", "category", "category_display", "description",
    "price_per_day", "transmission", "transmission_display", "fuel_type", "fuel_type_display",
    "passenger_capacity", "luggage_capacity", "doors", "availability_status", "availability_display",
    "is_featured", "images", "features",
]


class PublicVehicleSerializer(_VehicleBase):
    class Meta:
        model = Vehicle
        fields = PUBLIC_FIELDS
        read_only_fields = fields


class AdminVehicleSerializer(_VehicleBase):
    features = serializers.ListField(child=serializers.CharField(max_length=80), required=False, write_only=True)
    feature_list = serializers.SerializerMethodField()
    booking_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = Vehicle
        fields = PUBLIC_FIELDS + ["feature_list", "is_active", "display_order", "created_at", "updated_at",
                                  "booking_count"]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {"slug": {"required": False}}

    def get_feature_list(self, obj):
        return [f.feature_name for f in obj.features.all()]

    def validate_price_per_day(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price per day must be greater than zero.")
        return value

    def _set_features(self, vehicle, features):
        if features is None:
            return
        clean = list(dict.fromkeys(f.strip() for f in features if f.strip()))
        vehicle.features.all().delete()
        VehicleFeature.objects.bulk_create([VehicleFeature(vehicle=vehicle, feature_name=f) for f in clean])

    @transaction.atomic
    def create(self, validated_data):
        features = validated_data.pop("features", None)
        vehicle = super().create(validated_data)
        self._set_features(vehicle, features)
        return vehicle

    @transaction.atomic
    def update(self, instance, validated_data):
        features = validated_data.pop("features", None)
        vehicle = super().update(instance, validated_data)
        self._set_features(vehicle, features)
        return vehicle

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["features"] = data.pop("feature_list")
        return data


class VehicleImageUploadSerializer(serializers.Serializer):
    images = serializers.ListField(child=serializers.ImageField(), allow_empty=False, max_length=12)
    alt_text = serializers.CharField(max_length=160, required=False, allow_blank=True)

    def validate_images(self, files):
        for f in files:
            try:
                validate_upload(f, allowed=IMAGE_TYPES, max_mb=10)
            except Exception as exc:
                raise serializers.ValidationError(f"{f.name}: {getattr(exc, 'messages', [exc])[0]}")
        return files
