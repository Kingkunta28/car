from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import AdminUser


class AdminUserCreationForm(UserCreationForm):
    class Meta:
        model = AdminUser
        fields = ("email", "full_name", "role")


class AdminUserChangeForm(UserChangeForm):
    class Meta:
        model = AdminUser
        fields = "__all__"


@admin.register(AdminUser)
class AdminUserAdmin(UserAdmin):
    add_form = AdminUserCreationForm
    form = AdminUserChangeForm
    ordering = ("full_name",)
    list_display = ("email", "full_name", "role", "dashboard_access", "is_active", "is_staff")
    list_filter = ("role", "dashboard_access", "is_active", "is_staff")
    search_fields = ("email", "full_name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("full_name", "role")}),
        ("Access", {"fields": ("dashboard_access", "is_active", "is_staff", "is_superuser", "groups")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "full_name", "role", "password1", "password2")}),)
