from django.core.management.base import BaseCommand

from apps.bookings.availability import release_expired_holds


class Command(BaseCommand):
    help = "Expire pending bookings whose reservation hold has lapsed."

    def handle(self, *args, **opts):
        self.stdout.write(self.style.SUCCESS(f"Released {release_expired_holds()} expired hold(s)."))
