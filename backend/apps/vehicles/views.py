from datetime import timedelta

import django_filters
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.accounts.permissions import ALL_ROLES, FINANCE_ROLES
from apps.bookings import availability
from apps.bookings.availability import turnaround
from apps.bookings.models import Booking
from apps.core.utils import audit

from .models import AvailabilityStatus, Vehicle, VehicleImage
from .serializers import (AdminVehicleSerializer, PublicVehicleSerializer, VehicleImageSerializer,
                          VehicleImageUploadSerializer)


def _parse_range(params):
    start, end = params.get("pickup_at"), params.get("return_at")
    if not start and not end:
        return None, None
    s, e = parse_datetime(start or ""), parse_datetime(end or "")
    if not s or not e:
        raise ValidationError({"pickup_at": "Use ISO-8601 datetimes for pickup_at and return_at."})
    if timezone.is_naive(s):
        s = timezone.make_aware(s)
    if timezone.is_naive(e):
        e = timezone.make_aware(e)
    if e <= s:
        raise ValidationError({"return_at": "Return must be after pickup."})
    return s, e


class VehicleFilter(django_filters.FilterSet):
    min_price = django_filters.NumberFilter(field_name="price_per_day", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price_per_day", lookup_expr="lte")
    min_passengers = django_filters.NumberFilter(field_name="passenger_capacity", lookup_expr="gte")
    category = django_filters.MultipleChoiceFilter(choices=Vehicle._meta.get_field("category").choices)
    transmission = django_filters.ChoiceFilter(choices=Vehicle._meta.get_field("transmission").choices)
    fuel_type = django_filters.ChoiceFilter(choices=Vehicle._meta.get_field("fuel_type").choices)
    featured = django_filters.BooleanFilter(field_name="is_featured")
    available = django_filters.BooleanFilter(method="filter_available")

    class Meta:
        model = Vehicle
        fields = ["category", "transmission", "fuel_type"]

    def filter_available(self, qs, name, value):
        if value is None:
            return qs
        cond = {"availability_status": AvailabilityStatus.AVAILABLE}
        return qs.filter(**cond) if value else qs.exclude(**cond)


def _vehicle_qs():
    return Vehicle.objects.prefetch_related("images", "features")


class PublicVehicleViewSet(viewsets.ReadOnlyModelViewSet):
    """Website fleet. Only active vehicles; no internal fields."""

    permission_classes = [AllowAny]
    serializer_class = PublicVehicleSerializer
    filterset_class = VehicleFilter
    search_fields = ["name", "brand", "model"]
    ordering_fields = ["price_per_day", "passenger_capacity", "name", "display_order"]
    lookup_field = "slug"
    pagination_class = None

    def get_queryset(self):
        qs = _vehicle_qs().filter(is_active=True)
        start, end = _parse_range(self.request.query_params)
        if start:
            busy = Booking.objects.filter(vehicle_slug=OuterRef("slug"), blocks_inventory=True,
                                          pickup_at__lt=end + turnaround(), blocked_until__gt=start)
            qs = qs.filter(availability_status=AvailabilityStatus.AVAILABLE).exclude(Exists(busy))
        return qs

    @action(detail=True, methods=["get"])
    def availability(self, request, slug=None):
        vehicle = self.get_object()
        start, end = _parse_range(request.query_params)
        if start:
            ok = availability.is_available(vehicle, start, end)
            reason = "" if ok else ("This vehicle is not currently bookable." if not vehicle.is_bookable
                                    else "Already reserved for some or all of these dates.")
            return Response({"available": ok, "reason": reason})
        now = timezone.now()
        return Response({
            "bookable": vehicle.is_bookable,
            "busy": availability.blocked_periods(vehicle, now, now + timedelta(days=365)),
        })


class AdminVehicleViewSet(viewsets.ModelViewSet):
    serializer_class = AdminVehicleSerializer
    filterset_class = VehicleFilter
    search_fields = ["name", "brand", "model", "slug"]
    ordering_fields = ["price_per_day", "name", "display_order", "created_at"]
    action_roles = {"create": FINANCE_ROLES, "update": FINANCE_ROLES, "partial_update": FINANCE_ROLES,
                    "destroy": FINANCE_ROLES, "upload_images": FINANCE_ROLES, "image": FINANCE_ROLES,
                    "list": ALL_ROLES, "retrieve": ALL_ROLES}

    def get_queryset(self):
        qs = _vehicle_qs().annotate(booking_count=Count("bookings"))
        active = self.request.query_params.get("is_active")
        if active in ("true", "false"):
            qs = qs.filter(is_active=active == "true")
        return qs

    def perform_create(self, serializer):
        v = serializer.save()
        audit("vehicle.created", actor=self.request.user, target=v, summary=v.name, request=self.request)

    def perform_update(self, serializer):
        before = {"price_per_day": str(serializer.instance.price_per_day),
                  "availability_status": serializer.instance.availability_status,
                  "is_active": serializer.instance.is_active}
        v = serializer.save()
        audit("vehicle.updated", actor=self.request.user, target=v, summary=v.name, request=self.request,
              before=before, after={"price_per_day": str(v.price_per_day),
                                    "availability_status": v.availability_status, "is_active": v.is_active})

    def destroy(self, request, *args, **kwargs):
        """Delete only if never booked; otherwise deactivate to preserve history."""
        v = self.get_object()
        if v.bookings.exists():
            v.is_active = False
            v.save(update_fields=["is_active", "updated_at"])
            audit("vehicle.deactivated", actor=request.user, target=v, summary=v.name, request=request)
            return Response({"deactivated": True, "detail": "Vehicle has bookings, so it was deactivated instead."})
        audit("vehicle.deleted", actor=request.user, target=v, summary=v.name, request=request)
        for img in v.images.all():
            img.image.delete(save=False)
        v.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="images")
    def upload_images(self, request, pk=None):
        v = self.get_object()
        s = VehicleImageUploadSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        start = (v.images.order_by("-display_order").values_list("display_order", flat=True).first() or 0) + 1
        alt = s.validated_data.get("alt_text") or f"{v.brand} {v.model} — Rafiki Car Hire Zanzibar"
        with transaction.atomic():
            created = [VehicleImage.objects.create(vehicle=v, image=f, alt_text=alt, display_order=start + i)
                       for i, f in enumerate(s.validated_data["images"])]
        return Response(VehicleImageSerializer(created, many=True, context={"request": request}).data,
                        status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch", "delete"], url_path=r"images/(?P<image_id>[0-9a-f-]+)")
    def image(self, request, pk=None, image_id=None):
        v = self.get_object()
        img = get_object_or_404(VehicleImage, pk=image_id, vehicle=v)
        if request.method == "DELETE":
            img.image.delete(save=False)
            img.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        if request.data.get("make_cover"):
            with transaction.atomic():
                for i, other in enumerate(v.images.exclude(pk=img.pk).order_by("display_order", "created_at"), start=1):
                    other.display_order = i
                    other.save(update_fields=["display_order"])
                img.display_order = 0
                img.save(update_fields=["display_order"])
        else:
            if "alt_text" in request.data:
                img.alt_text = str(request.data["alt_text"])[:160]
            if "display_order" in request.data:
                try:
                    img.display_order = max(0, int(request.data["display_order"]))
                except (TypeError, ValueError):
                    raise ValidationError({"display_order": "Must be a whole number."})
            img.save()
        return Response(VehicleImageSerializer(img, context={"request": request}).data)
