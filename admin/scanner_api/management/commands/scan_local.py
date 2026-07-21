import logging
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from scanner_api.models import ScanResult
from scanner_api.scanner import collect_all, get_hostname, detect_platform

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Scans the local system and stores the result in the database"

    def handle(self, *args, **options):
        self.stdout.write("Scanning local system...")
        try:
            data = collect_all()
            hostname = get_hostname()
            platform_name, _ = detect_platform()

            scan_data = {
                "hostname": hostname,
                "platform": platform_name,
                "scan_timestamp": datetime.now().isoformat(),
                "scanned_by": "admin_local",
                **data,
            }

            ScanResult.objects.create(
                client=None,
                scan_type="local",
                scan_data=scan_data,
            )

            self.stdout.write(self.style.SUCCESS(
                f"Scan complete. System: {hostname} | Platform: {platform_name}"
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Scan failed: {e}"))
            logger.exception("Local scan failed")
