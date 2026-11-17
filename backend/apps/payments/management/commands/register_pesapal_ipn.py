from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.payments.gateways.base import GatewayError
from apps.payments.gateways.pesapal import PesapalGateway


class Command(BaseCommand):
    help = "Register this backend's IPN URL with Pesapal and print the IPN id to put in PESAPAL_IPN_ID."

    def add_arguments(self, parser):
        parser.add_argument("--url", help="Override the IPN URL (default: BACKEND_URL/api/v1/webhooks/payments/pesapal/)")

    def handle(self, *args, **opts):
        if not (settings.PESAPAL_CONSUMER_KEY and settings.PESAPAL_CONSUMER_SECRET):
            raise CommandError("Set PESAPAL_CONSUMER_KEY and PESAPAL_CONSUMER_SECRET first.")
        url = opts.get("url") or f"{settings.BACKEND_URL}/api/v1/webhooks/payments/pesapal/"
        try:
            data = PesapalGateway().register_ipn(url)
        except GatewayError as exc:
            raise CommandError(str(exc))
        self.stdout.write(self.style.SUCCESS(f"Registered {data.get('url')}"))
        self.stdout.write(f"PESAPAL_IPN_ID={data.get('ipn_id')}")
