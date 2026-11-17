from django.contrib import admin

from .models import Payment, Receipt, Refund


class ReadOnly(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Payment)
class PaymentAdmin(ReadOnly):
    list_display = ("payment_reference", "booking", "amount", "payment_method", "payment_status", "verified_at")
    list_filter = ("payment_status", "payment_method", "gateway")
    search_fields = ("payment_reference", "transaction_reference", "booking__booking_reference")


admin.site.register(Refund, ReadOnly)
admin.site.register(Receipt, ReadOnly)
