from django.core.management.base import BaseCommand

from apps.notifications.tasks import process_notification_queue


class Command(BaseCommand):
    help = "Deliver queued emails and retry failed ones (use when no Celery beat is running)."

    def handle(self, *args, **opts):
        self.stdout.write(self.style.SUCCESS(f"Processed {process_notification_queue()} notification(s)."))
