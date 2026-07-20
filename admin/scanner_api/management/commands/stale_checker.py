import time
import logging
from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand
from AdminClient.admin.scanner_api.models import Client, Setting

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Marks clients as offline after a timeout period"

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval", type=int, default=30,
            help="Check interval in seconds (default: 30)",
        )
        parser.add_argument(
            "--timeout", type=int, default=120,
            help="Seconds without ping before marking offline (default: 120)",
        )

    def handle(self, *args, **options):
        interval = options["interval"]
        timeout = int(Setting.get("stale_threshold_seconds", options["timeout"]))
        self.stdout.write(f"Stale checker started (interval={interval}s, timeout={timeout}s)")

        while True:
            try:
                cutoff = timezone.now() - timedelta(seconds=timeout)
                updated = Client.objects.filter(
                    status="online", deleted=False, last_seen__lt=cutoff
                ).update(status="offline")
                if updated:
                    logger.info(f"Marked {updated} stale client(s) offline")
            except Exception as exc:
                logger.error("Stale checker error: %s", exc)
            time.sleep(interval)
