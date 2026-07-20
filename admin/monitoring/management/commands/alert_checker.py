import time
import logging
from django.utils import timezone
from django.core.management.base import BaseCommand
from AdminClient.admin.monitoring.models import DeviceMonitoringInfo, DeviceAlert
from AdminClient.admin.monitoring.alerts import check_and_create_alerts, check_offline_alerts

logger = logging.getLogger("monitoring")


class Command(BaseCommand):
    help = "Runs alert checks on all monitored devices"

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=int, default=60, help="Check interval in seconds (default: 60)")

    def handle(self, *args, **options):
        interval = options["interval"]
        self.stdout.write(f"Alert checker started (interval={interval}s)")

        while True:
            try:
                infos = DeviceMonitoringInfo.objects.filter(
                    client__deleted=False,
                ).exclude(monitoring_status__in=["blocked", "inactive"])

                for info in infos:
                    try:
                        check_offline_alerts(info.client)
                    except Exception as exc:
                        logger.error("Offline check error for %s: %s", info.client_id, exc)

            except Exception as exc:
                logger.error("Alert checker error: %s", exc)
            time.sleep(interval)
