import logging
from django.core.management.base import BaseCommand
from scanner_api.models import Client, ScanResult, AddonDevice, ActivityLog, ClientGroup

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Deletes all scan data, clients, activity logs, and groups (preserves admin users and settings)"

    def handle(self, *args, **options):
        self.stdout.write("Clearing scan data...")

        c1 = ScanResult.objects.all().delete()
        self.stdout.write(f"  Deleted {c1[0]} scan result(s)")

        c2 = AddonDevice.objects.all().delete()
        self.stdout.write(f"  Deleted {c2[0]} add-on device(s)")

        c3 = ActivityLog.objects.all().delete()
        self.stdout.write(f"  Deleted {c3[0]} activity log entr(ies)")

        c4 = Client.objects.all().delete()
        self.stdout.write(f"  Deleted {c4[0]} client(s)")

        c5 = ClientGroup.objects.all().delete()
        self.stdout.write(f"  Deleted {c5[0]} client group(s)")

        self.stdout.write(self.style.SUCCESS("All scanning data cleared."))
