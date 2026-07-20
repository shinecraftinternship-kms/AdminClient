import uuid
from django.db import models
from django.utils import timezone
from AdminClient.admin.scanner_api.models import Client


class ScheduledScan(models.Model):
    """Defines a recurring or one-time scan schedule."""

    SCHEDULE_TYPES = [
        ("interval", "Interval"),
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
        ("once", "One-Time"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=256)
    description = models.TextField(default="", blank=True)

    schedule_type = models.CharField(max_length=16, choices=SCHEDULE_TYPES, default="interval")
    interval_seconds = models.IntegerField(default=3600, help_text="For interval type: seconds between runs")
    cron_expression = models.CharField(max_length=128, default="", blank=True, help_text="For cron-type schedules")
    time_of_day = models.TimeField(null=True, blank=True, help_text="For daily/weekly/monthly: time to run")
    day_of_week = models.IntegerField(null=True, blank=True, help_text="0=Mon..6=Sun for weekly")
    day_of_month = models.IntegerField(null=True, blank=True, help_text="1-31 for monthly")

    target_all = models.BooleanField(default=True, help_text="Apply to all clients")
    target_clients = models.ManyToManyField(Client, blank=True, related_name="scheduled_scans")
    target_platforms = models.CharField(max_length=256, default="", blank=True, help_text="Comma-separated: Windows,Linux,Darwin")

    scan_type = models.CharField(max_length=32, default="full", choices=[
        ("full", "Full Scan"),
        ("quick", "Quick Scan"),
        ("hardware", "Hardware Only"),
        ("software", "Software Only"),
    ])

    enabled = models.BooleanField(default=True)
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
    run_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "monitoring_scheduled_scans"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Schedule({self.name} - {self.schedule_type})"


class PendingScan(models.Model):
    """A scan queued for a client that was offline when the schedule triggered."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="pending_scans")
    scheduled_scan = models.ForeignKey(ScheduledScan, on_delete=models.SET_NULL, null=True, blank=True)

    scan_type = models.CharField(max_length=32, default="full")
    priority = models.IntegerField(default=0, help_text="Higher = more urgent")
    status = models.CharField(max_length=16, default="pending", choices=[
        ("pending", "Pending"),
        ("sent", "Sent to Agent"),
        ("executed", "Executed"),
        ("failed", "Failed"),
        ("expired", "Expired"),
    ])

    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(default="", blank=True)

    class Meta:
        db_table = "monitoring_pending_scans"
        ordering = ["-priority", "created_at"]
        indexes = [
            models.Index(fields=["client", "status"]),
        ]

    def __str__(self):
        return f"PendingScan({self.client_id} - {self.scan_type} - {self.status})"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("PendingScan records cannot be updated after creation. Use status transitions.")
        super().save(*args, **kwargs)


class ScanScheduleLog(models.Model):
    """Execution log for scheduled scans."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scheduled_scan = models.ForeignKey(ScheduledScan, on_delete=models.SET_NULL, null=True, blank=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="scan_schedule_logs")

    triggered_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, default="triggered", choices=[
        ("triggered", "Triggered"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("skipped", "Skipped (offline)"),
    ])

    changes_detected = models.IntegerField(default=0)
    alerts_generated = models.IntegerField(default=0)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "monitoring_scan_schedule_logs"
        ordering = ["-triggered_at"]
        indexes = [
            models.Index(fields=["scheduled_scan", "-triggered_at"]),
        ]

    def __str__(self):
        return f"ScanLog({self.scheduled_scan_id} @ {self.triggered_at})"
