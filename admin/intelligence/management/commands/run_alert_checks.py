from django.core.management.base import BaseCommand
from intelligence.alerts import run_alert_checks


class Command(BaseCommand):
    help = "Runs all automated alert checks and applies escalation rules"

    def add_arguments(self, parser):
        parser.add_argument(
            "--escalate-only",
            action="store_true",
            help="Only run escalation checks without generating new alerts",
        )

    def handle(self, *args, **options):
        self.stdout.write("Running alert checks...")
        results = run_alert_checks(escalate_only=options.get("escalate_only"))
        alerts_created = len(results.get("alerts_created", []))
        escalations = results.get("escalations", 0)
        self.stdout.write(self.style.SUCCESS(
            f"Done. Alerts created: {alerts_created}, Escalations: {escalations}"
        ))
