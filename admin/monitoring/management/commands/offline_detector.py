import time
import logging
from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand
from scanner_api.models import Client, Setting
from monitoring.models import DeviceMonitoringInfo, DeviceAlert, DeviceHistory

logger = logging.getLogger("monitoring")


class Command(BaseCommand):
    help = "Enhanced offline detection for monitoring module"

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=int, default=30, help="Check interval in seconds (default: 30)")
        parser.add_argument("--timeout", type=int, default=120, help="Seconds before marking offline (default: 120)")

    def handle(self, *args, **options):
        interval = options["interval"]
        timeout = int(Setting.get("stale_threshold_seconds", options["timeout"]))
        self.stdout.write(f"Offline detector started (interval={interval}s, timeout={timeout}s)")

        while True:
            try:
                cutoff = timezone.now() - timedelta(seconds=timeout)
                infos = DeviceMonitoringInfo.objects.filter(
                    monitoring_status="online",
                    client__deleted=False,
                    last_heartbeat__lt=cutoff,
                )

                for info in infos:
                    info.monitoring_status = "offline"
                    info.save(update_fields=["monitoring_status", "updated_at"])

                    Client.objects.filter(id=info.client_id).update(status="offline")

                    DeviceHistory.objects.create(
                        client=info.client,
                        category="status_change",
                        event_type="device_offline",
                        description=f"Device went offline (no heartbeat for >{timeout}s)",
                        severity="warning",
                        new_value={"status": "offline"},
                    )

                    existing_alert = DeviceAlert.objects.filter(
                        client=info.client, alert_type="device_offline", status="active",
                    ).exists()
                    if not existing_alert:
                        DeviceAlert.objects.create(
                            client=info.client,
                            alert_type="device_offline",
                            severity="warning",
                            title=f"Device offline: {info.client.hostname}",
                            message=f"{info.client.hostname} has not sent a heartbeat in over {timeout} seconds.",
                        )

            except Exception as exc:
                logger.error("Offline detector error: %s", exc)
            time.sleep(interval)
