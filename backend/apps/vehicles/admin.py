from django.contrib import admin

from .models import Vehicle, VehicleFeature, VehicleImage


class ImageInline(admin.TabularInline):
    model = VehicleImage
    extra = 0


class FeatureInline(admin.TabularInline):
    model = VehicleFeature
    extra = 0


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price_per_day", "availability_status", "is_featured", "is_active")
    list_filter = ("category", "availability_status", "is_active")
    search_fields = ("name", "brand", "model")
    prepopulated_fields = {"slug": ("brand", "model")}
    inlines = [ImageInline, FeatureInline]
