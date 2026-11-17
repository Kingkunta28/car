from django.core.management.base import BaseCommand

from apps.bookings.retention import purge_expired_documents


class Command(BaseCommand):
    help = "Securely delete identity documents past the retention period."

    def handle(self, *args, **opts):
        self.stdout.write(self.style.SUCCESS(f"Purged {purge_expired_documents()} document(s)."))
