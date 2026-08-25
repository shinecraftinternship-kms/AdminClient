import time
import logging
from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand
from scanner_api.models import Client, Setting

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Marks clients as offline after a timeout period"

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval", type=int, default=30,
            help="Check interval in seconds (default: 30)",
        )
        parser.add_argument(
            "--timeout", type=int, default=300,
            help="Seconds without ping before marking offline (default: 300)",
        )

    def handle(self, *args, **options):
        interval = options["interval"]
        timeout = int(Setting.get("stale_threshold_seconds", options["timeout"]))
        self.stdout.write(f"Stale checker started (interval={interval}s, timeout={timeout}s)")

        while True:
            try:
                cutoff = timezone.now() - timedelta(seconds=timeout)
                stale_client_ids = set()

                # Check clients based on last_seen from ping
                for client in Client.objects.filter(status="online", deleted=False, approved=True):
                    last_activity = client.last_seen
                    # Also check monitoring heartbeat if available
                    try:
                        from monitoring.models import DeviceMonitoringInfo
                        info = DeviceMonitoringInfo.objects.filter(client=client).first()
                        if info and info.last_heartbeat and info.last_heartbeat > last_activity:
                            last_activity = info.last_heartbeat
                    except Exception:
                        pass

                    if last_activity and last_activity < cutoff:
                        stale_client_ids.add(client.id)

                if stale_client_ids:
                    Client.objects.filter(id__in=stale_client_ids).update(status="offline")
                    logger.info(f"Marked {len(stale_client_ids)} stale client(s) offline")

            except Exception as exc:
                logger.error("Stale checker error: %s", exc)
            time.sleep(interval)
