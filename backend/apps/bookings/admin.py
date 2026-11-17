from django.contrib import admin

from .models import Booking, BookingExtra, BookingFlight, BookingNote, BookingStatusHistory, ExtraService


@admin.register(ExtraService)
class ExtraServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "price", "pricing_type", "max_quantity", "is_active", "is_system")
    readonly_fields = ("is_system",)

    def has_delete_permission(self, request, obj=None):
        return not (obj and obj.is_system)


class ExtraInline(admin.TabularInline):
    model = BookingExtra
    extra = 0
    can_delete = False
    readonly_fields = [f.name for f in BookingExtra._meta.fields]


class HistoryInline(admin.TabularInline):
    model = BookingStatusHistory
    extra = 0
    can_delete = False
    readonly_fields = ("status_field", "previous_status", "new_status", "changed_by", "notes", "created_at")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    """Read-only here: changes must go through the dashboard so prices,
    invoices and audit history stay consistent."""

    list_display = ("booking_reference", "customer", "vehicle", "pickup_date", "return_date", "grand_total",
                    "booking_status", "payment_status")
    list_filter = ("booking_status", "payment_status", "payment_method")
    search_fields = ("booking_reference", "customer__full_name", "customer__email")
    inlines = [ExtraInline, HistoryInline]

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in Booking._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(BookingFlight)
admin.site.register(BookingNote)
