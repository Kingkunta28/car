from django.conf import settings
from django.core.management.base import BaseCommand

from apps.accounts.models import AdminUser
from apps.core.models import SiteSettings
from apps.payments.gateways import available_gateways
from apps.vehicles.models import Vehicle


class Command(BaseCommand):
    help = "List configuration the business owner still needs to complete."

    def handle(self, *args, **opts):
        site = SiteSettings.load()
        checks = [
            ("Business email", bool(site.business_email)),
            ("Business phone", bool(site.business_phone)),
            ("WhatsApp number", bool(site.whatsapp_number)),
            ("Owner notification email", bool(site.owner_email)),
            ("Manual payment instructions", bool(site.payment_instructions)),
            ("Logo uploaded", bool(site.logo)),
            ("SMTP configured", bool(settings.EMAIL_HOST) or "console" in settings.EMAIL_BACKEND),
            ("Online payment gateway configured", bool(available_gateways())),
            ("At least one admin user", AdminUser.objects.filter(is_active=True).exists()),
            ("At least one active vehicle", Vehicle.objects.filter(is_active=True).exists()),
            ("Vehicles all have photos", not Vehicle.objects.filter(is_active=True, images__isnull=True).exists()),
        ]
        for label, ok in checks:
            self.stdout.write(f"  [{'x' if ok else ' '}] {label}")
