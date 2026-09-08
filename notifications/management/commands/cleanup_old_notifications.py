from django.core.management.base import BaseCommand
from django.utils import timezone
import datetime
from notifications.models import Notification

class Command(BaseCommand):
    help = "Delete notifications older than 14 days"

    def handle(self, *args, **options):
        cutoff_14d = timezone.now() - datetime.timedelta(days=14)
        deleted, _ = Notification.objects.filter(created_at__lt=cutoff_14d).delete()
        self.stdout.write(self.style.SUCCESS(f"Successfully deleted {deleted} notifications older than 14 days."))
