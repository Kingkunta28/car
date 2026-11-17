from django.contrib import admin

from .models import NotificationLog


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "notification_type", "recipient", "delivery_status", "attempts", "sent_at")
    list_filter = ("delivery_status", "notification_type")
    search_fields = ("recipient", "booking__booking_reference")
    readonly_fields = [f.name for f in NotificationLog._meta.fields]
