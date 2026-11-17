from django.contrib import admin

from .models import Invoice


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "booking", "issue_date", "total_amount", "invoice_status", "revision_number")
    list_filter = ("invoice_status",)
    search_fields = ("invoice_number", "booking__booking_reference")

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in Invoice._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
