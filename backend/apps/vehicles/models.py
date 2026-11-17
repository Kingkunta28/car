from django.db import models
from django.db.models import Q
from django.utils.text import slugify

from apps.core.files import RandomUploadPath
from apps.core.models import TimeStampedModel, UUIDModel


class Category(models.TextChoices):
    ECONOMY = "ECONOMY", "Economy"
    COMPACT = "COMPACT", "Compact"
    COMPACT_SUV = "COMPACT_SUV", "Compact SUV"
    SUV = "SUV", "SUV"
    FOUR_BY_FOUR = "4X4", "4x4 / Off-road"
    MINIVAN = "MINIVAN", "Minivan"
    LUXURY = "LUXURY", "Luxury"


class Transmission(models.TextChoices):
    AUTOMATIC = "AUTOMATIC", "Automatic"
    MANUAL = "MANUAL", "Manual"


class FuelType(models.TextChoices):
    PETROL = "PETROL", "Petrol"
    DIESEL = "DIESEL", "Diesel"
    HYBRID = "HYBRID", "Hybrid"
    ELECTRIC = "ELECTRIC", "Electric"


class AvailabilityStatus(models.TextChoices):
    AVAILABLE = "AVAILABLE", "Available"
    MAINTENANCE = "MAINTENANCE", "In maintenance"
    UNAVAILABLE = "UNAVAILABLE", "Unavailable"


class Vehicle(UUIDModel, TimeStampedModel):
    slug = models.SlugField(max_length=140, unique=True)
    name = models.CharField(max_length=120)
    brand = models.CharField(max_length=60)
    model = models.CharField(max_length=60)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    category = models.CharField(max_length=15, choices=Category.choices, db_index=True)
    description = models.TextField(blank=True)
    price_per_day = models.DecimalField(max_digits=10, decimal_places=2)
    transmission = models.CharField(max_length=10, choices=Transmission.choices)
    fuel_type = models.CharField(max_length=10, choices=FuelType.choices)
    passenger_capacity = models.PositiveSmallIntegerField()
    luggage_capacity = models.PositiveSmallIntegerField(default=2)
    doors = models.PositiveSmallIntegerField(default=4)
    availability_status = models.CharField(max_length=12, choices=AvailabilityStatus.choices,
                                           default=AvailabilityStatus.AVAILABLE)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, help_text="Inactive vehicles are hidden from the website.")
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "price_per_day", "name"]
        constraints = [
            models.CheckConstraint(condition=Q(price_per_day__gt=0), name="vehicle_price_positive"),
            models.CheckConstraint(condition=Q(passenger_capacity__gte=1), name="vehicle_passengers_positive"),
        ]
        indexes = [models.Index(fields=["is_active", "availability_status"])]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(f"{self.brand} {self.model} {self.name}")[:120] or "vehicle"
            slug, n = base, 2
            while Vehicle.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, n = f"{base}-{n}", n + 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def is_bookable(self) -> bool:
        return self.is_active and self.availability_status == AvailabilityStatus.AVAILABLE

    @property
    def primary_image(self):
        images = list(self.images.all())
        return images[0] if images else None


class VehicleImage(UUIDModel):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=RandomUploadPath("vehicles"))
    alt_text = models.CharField(max_length=160, blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "created_at"]

    def __str__(self):
        return self.alt_text or f"Image of {self.vehicle}"


class VehicleFeature(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="features")
    feature_name = models.CharField(max_length=80)

    class Meta:
        ordering = ["id"]
        constraints = [models.UniqueConstraint(fields=["vehicle", "feature_name"], name="vehicle_feature_unique")]

    def __str__(self):
        return self.feature_name
