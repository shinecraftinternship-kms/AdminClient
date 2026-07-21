import time
import logging
from django.utils import timezone
from django.core.management.base import BaseCommand
from scanner_api.models import Setting
from monitoring.models import DeviceMonitoringInfo, DeviceHistory

logger = logging.getLogger("monitoring")


class Command(BaseCommand):
    help = "Periodically recalculates health scores for all monitored devices"

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=int, default=300, help="Check interval in seconds (default: 300)")

    def handle(self, *args, **options):
        interval = options["interval"]
        self.stdout.write(f"Health checker started (interval={interval}s)")

        while True:
            try:
                from monitoring.health import calculate_health_score
                from monitoring.models import DeviceHeartbeat, SoftwareInventory

                infos = DeviceMonitoringInfo.objects.filter(
                    client__deleted=False,
                ).exclude(monitoring_status__in=["blocked", "inactive"])

                for info in infos:
                    hb = DeviceHeartbeat.objects.filter(client=info.client).order_by("-created_at").first()
                    if not hb:
                        continue

                    sw_data = list(SoftwareInventory.objects.filter(
                        client=info.client, is_present=True
                    ).values("name", "version", "publisher")[:200])

                    score, level = calculate_health_score(
                        {
                            "cpu_usage_pct": hb.cpu_usage_pct,
                            "ram_usage_pct": hb.ram_usage_pct,
                            "disk_usage_pct": hb.disk_usage_pct,
                            "network_connected": hb.network_connected,
                        },
                        sw_data,
                    )

                    prev_level = info.health_level
                    info.health_score = score
                    info.health_level = level
                    info.save(update_fields=["health_score", "health_level", "updated_at"])

                    if prev_level != level and prev_level != "unknown":
                        DeviceHistory.objects.create(
                            client=info.client,
                            category="health_change",
                            event_type="health_level_changed",
                            description=f"Health level: {prev_level} → {level} (score: {score})",
                            severity="warning" if level == "critical" else "info",
                            previous_value={"level": prev_level},
                            new_value={"level": level, "score": score},
                        )

            except Exception as exc:
                logger.error("Health checker error: %s", exc)
            time.sleep(interval)
