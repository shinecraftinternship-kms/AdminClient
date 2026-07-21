import uuid
from django.db import models
from django.utils import timezone


class Alert(models.Model):
    SEVERITY_CHOICES = [
        ("information", "Information"),
        ("warning", "Warning"),
        ("critical", "Critical"),
        ("emergency", "Emergency"),
    ]
    CATEGORY_CHOICES = [
        ("asset", "Asset"),
        ("monitoring", "Monitoring"),
        ("maintenance", "Maintenance"),
        ("license", "License"),
        ("security", "Security"),
        ("compliance", "Compliance"),
        ("system", "System"),
    ]
    STATUS_CHOICES = [
        ("open", "Open"),
        ("acknowledged", "Acknowledged"),
        ("resolved", "Resolved"),
        ("dismissed", "Dismissed"),
    ]
    MODULE_CHOICES = [
        ("asset", "Asset Management"),
        ("monitoring", "Monitoring"),
        ("maintenance", "Maintenance"),
        ("license", "License Management"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=256)
    description = models.TextField(blank=True, default="")
    module = models.CharField(max_length=20, choices=MODULE_CHOICES, db_index=True)
    source_object_id = models.CharField(max_length=64, blank=True, default="")
    source_object_type = models.CharField(max_length=64, blank=True, default="")
    severity = models.CharField(max_length=16, choices=SEVERITY_CHOICES, default="warning", db_index=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="system", db_index=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="open", db_index=True)
    assigned_user = models.CharField(max_length=128, blank=True, default="")
    generated_time = models.DateTimeField(auto_now_add=True)
    resolved_time = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True, default="")
    escalation_level = models.IntegerField(default=0, help_text="0=normal, 1=warning escalated, 2=critical escalated, 3=emergency escalated")

    dedup_hash = models.CharField(max_length=64, blank=True, default="", db_index=True, help_text="SHA256 hash for deduplication")
    notification_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "intelligence_alerts"
        ordering = ["-generated_time"]
        indexes = [
            models.Index(fields=["severity", "status"]),
            models.Index(fields=["category", "status"]),
            models.Index(fields=["module", "status"]),
            models.Index(fields=["-generated_time"]),
            models.Index(fields=["dedup_hash"]),
            models.Index(fields=["assigned_user"]),
        ]

    def __str__(self):
        return f"[{self.severity}] {self.title}"

    def save(self, *args, **kwargs):
        from django.utils import timezone
        if self.status in ("resolved", "dismissed") and not self.resolved_time:
            self.resolved_time = timezone.now()
        super().save(*args, **kwargs)


class AlertHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, related_name="history")
    action = models.CharField(max_length=32, db_index=True)
    previous_status = models.CharField(max_length=16, blank=True, default="")
    new_status = models.CharField(max_length=16, blank=True, default="")
    previous_severity = models.CharField(max_length=16, blank=True, default="")
    new_severity = models.CharField(max_length=16, blank=True, default="")
    performed_by = models.CharField(max_length=128, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "intelligence_alert_history"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["alert", "-timestamp"]),
        ]

    def __str__(self):
        return f"{self.action} on alert {self.alert_id} at {self.timestamp}"


class AlertRule(models.Model):
    SEVERITY_CHOICES = [
        ("information", "Information"),
        ("warning", "Warning"),
        ("critical", "Critical"),
        ("emergency", "Emergency"),
    ]
    MODULE_CHOICES = [
        ("asset", "Asset Management"),
        ("monitoring", "Monitoring"),
        ("maintenance", "Maintenance"),
        ("license", "License Management"),
    ]
    CATEGORY_CHOICES = [
        ("asset", "Asset"),
        ("monitoring", "Monitoring"),
        ("maintenance", "Maintenance"),
        ("license", "License"),
        ("security", "Security"),
        ("compliance", "Compliance"),
        ("system", "System"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=256)
    description = models.TextField(blank=True, default="")
    module = models.CharField(max_length=20, choices=MODULE_CHOICES, db_index=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, db_index=True)
    severity = models.CharField(max_length=16, choices=SEVERITY_CHOICES, default="warning")
    condition_type = models.CharField(max_length=64, help_text="e.g., threshold_gt, threshold_lt, equals, contains")
    condition_field = models.CharField(max_length=128, blank=True, default="")
    condition_value = models.CharField(max_length=512, blank=True, default="")
    suppress_duplicates = models.BooleanField(default=True)
    suppress_window_minutes = models.IntegerField(default=60)
    auto_resolve_minutes = models.IntegerField(default=0, help_text="0 = no auto-resolve")
    is_active = models.BooleanField(default=True)
    created_by = models.CharField(max_length=128, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "intelligence_alert_rules"
        ordering = ["module", "name"]
        indexes = [
            models.Index(fields=["module", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.module}/{self.category})"


class Notification(models.Model):
    SEVERITY_CHOICES = [
        ("information", "Information"),
        ("warning", "Warning"),
        ("critical", "Critical"),
        ("emergency", "Emergency"),
    ]
    STATUS_CHOICES = [
        ("unread", "Unread"),
        ("read", "Read"),
        ("archived", "Archived"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="intelligence_notifications")
    title = models.CharField(max_length=256)
    message = models.TextField(blank=True, default="")
    severity = models.CharField(max_length=16, choices=SEVERITY_CHOICES, default="information")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="unread", db_index=True)
    module = models.CharField(max_length=64, blank=True, default="")
    source_alert = models.ForeignKey(Alert, on_delete=models.SET_NULL, null=True, blank=True, related_name="notifications")
    source_url = models.CharField(max_length=512, blank=True, default="")
    created_time = models.DateTimeField(auto_now_add=True)
    read_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "intelligence_notifications"
        ordering = ["-created_time"]
        indexes = [
            models.Index(fields=["user", "status", "-created_time"]),
            models.Index(fields=["severity", "status"]),
        ]

    def __str__(self):
        return f"[{self.severity}] {self.title} for {self.user_id}"


class NotificationPreference(models.Model):
    FREQUENCY_CHOICES = [
        ("instant", "Instant"),
        ("daily", "Daily Digest"),
        ("weekly", "Weekly Digest"),
        ("never", "Never"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField("auth.User", on_delete=models.CASCADE, related_name="notification_preferences")
    email_enabled = models.BooleanField(default=True)
    in_app_enabled = models.BooleanField(default=True)
    severity_information = models.BooleanField(default=True)
    severity_warning = models.BooleanField(default=True)
    severity_critical = models.BooleanField(default=True)
    severity_emergency = models.BooleanField(default=True)
    module_asset = models.BooleanField(default=True)
    module_monitoring = models.BooleanField(default=True)
    module_maintenance = models.BooleanField(default=True)
    module_license = models.BooleanField(default=True)
    module_security = models.BooleanField(default=True)
    module_compliance = models.BooleanField(default=True)
    module_system = models.BooleanField(default=True)
    frequency = models.CharField(max_length=16, choices=FREQUENCY_CHOICES, default="instant")
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "intelligence_notification_preferences"
        verbose_name = "Notification Preference"
        verbose_name_plural = "Notification Preferences"

    def __str__(self):
        return f"Preferences for {self.user_id}"


class Report(models.Model):
    REPORT_TYPE_CHOICES = [
        ("asset_inventory", "Asset Inventory Report"),
        ("asset_assignment", "Asset Assignment Report"),
        ("asset_lifecycle", "Asset Lifecycle Report"),
        ("asset_utilization", "Asset Utilization Report"),
        ("online_devices", "Online Devices Report"),
        ("device_health", "Device Health Report"),
        ("hardware_change", "Hardware Change Report"),
        ("software_inventory", "Software Inventory Report"),
        ("upcoming_maintenance", "Upcoming Maintenance"),
        ("maintenance_cost", "Maintenance Cost Report"),
        ("downtime_analysis", "Downtime Analysis"),
        ("vendor_performance", " Vendor Performance"),
        ("expiring_licenses", "Expiring Licenses"),
        ("compliance_report", "Compliance Reports"),
        ("seat_utilization", "Seat Utilization Reports"),
        ("cost_analysis", "Cost Analysis Reports"),
        ("unauthorized_software", "Unauthorized Software"),
        ("security_violations", "Security Violations"),
        ("device_risk", "Device Risk Reports"),
        ("audit_report", "Audit Reports"),
        ("monthly_summary", "Monthly Summary"),
        ("department_performance", "Department Performance"),
        ("top_problematic_assets", "Top Problematic Assets"),
        ("cost_overview", "Cost Overview"),
        ("compliance_summary", "Compliance Summary"),
    ]
    FORMAT_CHOICES = [
        ("pdf", "PDF"),
        ("excel", "Excel"),
        ("csv", "CSV"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=256)
    report_type = models.CharField(max_length=32, choices=REPORT_TYPE_CHOICES, db_index=True)
    format = models.CharField(max_length=8, choices=FORMAT_CHOICES, default="csv")
    filters = models.JSONField(default=dict, blank=True, help_text="JSON filter criteria")
    generated_by = models.CharField(max_length=128, blank=True, default="")
    file_data = models.TextField(blank=True, default="", help_text="Base64 encoded file data")
    file_size = models.IntegerField(default=0)
    row_count = models.IntegerField(default=0)
    status = models.CharField(max_length=16, default="pending", choices=[
        ("pending", "Pending"),
        ("generating", "Generating"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ])
    error_message = models.TextField(blank=True, default="")
    generated_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "intelligence_reports"
        ordering = ["-generated_at"]
        indexes = [
            models.Index(fields=["report_type", "-generated_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.report_type})"


class ScheduledReport(models.Model):
    FREQUENCY_CHOICES = [
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
    ]
    FORMAT_CHOICES = [
        ("pdf", "PDF"),
        ("excel", "Excel"),
        ("csv", "CSV"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=256)
    report_type = models.CharField(max_length=32, choices=Report.REPORT_TYPE_CHOICES, db_index=True)
    format = models.CharField(max_length=8, choices=FORMAT_CHOICES, default="csv")
    frequency = models.CharField(max_length=16, choices=FREQUENCY_CHOICES, db_index=True)
    filters = models.JSONField(default=dict, blank=True)
    recipients = models.TextField(default="", blank=True, help_text="Comma-separated email addresses")
    next_run = models.DateTimeField(null=True, blank=True)
    last_run = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.CharField(max_length=128, blank=True, default="")
    retention_policy = models.CharField(max_length=16, default="1_year", choices=[
        ("1_year", "1 Year"),
        ("3_years", "3 Years"),
        ("permanent", "Permanent"),
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "intelligence_scheduled_reports"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["frequency", "is_active"]),
            models.Index(fields=["-next_run"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.frequency})"


class AuditLogEntry(models.Model):
    MODULE_CHOICES = [
        ("auth", "Authentication"),
        ("asset", "Asset Management"),
        ("monitoring", "Monitoring"),
        ("maintenance", "Maintenance"),
        ("license", "License Management"),
        ("settings", "Settings"),
        ("admin", "Admin"),
        ("intelligence", "Intelligence"),
        ("organization", "Organization"),
    ]
    ACTION_CHOICES = [
        ("login", "Login"),
        ("logout", "Logout"),
        ("login_failed", "Failed Login"),
        ("asset_created", "Asset Creation"),
        ("asset_updated", "Asset Update"),
        ("asset_assigned", "Asset Assignment"),
        ("asset_deleted", "Asset Deletion"),
        ("maintenance_changed", "Maintenance Changes"),
        ("license_changed", "License Changes"),
        ("user_created", "User Management"),
        ("alert_resolved", "Alert Resolution"),
        ("settings_changed", "Settings Changes"),
        ("report_downloaded", "Report Downloads"),
        ("report_generated", "Report Generated"),
        ("employee_created", "Employee Created"),
        ("employee_updated", "Employee Updated"),
        ("department_changed", "Department Changed"),
        ("location_changed", "Location Changed"),
        ("data_exported", "Data Exported"),
        ("data_imported", "Data Imported"),
        ("system_action", "System Action"),
    ]
    SEVERITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.IntegerField(null=True, blank=True, db_index=True)
    username = models.CharField(max_length=150, blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    browser_info = models.CharField(max_length=256, blank=True, default="")
    device_info = models.CharField(max_length=256, blank=True, default="")
    module = models.CharField(max_length=20, choices=MODULE_CHOICES, db_index=True)
    action = models.CharField(max_length=24, choices=ACTION_CHOICES, db_index=True)
    object_type = models.CharField(max_length=64, blank=True, default="")
    object_id = models.CharField(max_length=64, blank=True, default="")
    object_repr = models.CharField(max_length=256, blank=True, default="")
    old_value = models.JSONField(default=dict, blank=True)
    new_value = models.JSONField(default=dict, blank=True)
    severity = models.CharField(max_length=16, choices=SEVERITY_CHOICES, default="low", db_index=True)
    description = models.TextField(blank=True, default="")

    class Meta:
        db_table = "intelligence_audit_logs"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["-timestamp"]),
            models.Index(fields=["module", "-timestamp"]),
            models.Index(fields=["action", "-timestamp"]),
            models.Index(fields=["user_id", "-timestamp"]),
            models.Index(fields=["severity", "-timestamp"]),
            models.Index(fields=["ip_address"]),
        ]

    def __str__(self):
        return f"{self.action} by {self.username} at {self.timestamp}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("AuditLogEntry records are immutable and cannot be updated")
        super().save(*args, **kwargs)


class ComplianceLog(models.Model):
    FRAMEWORK_CHOICES = [
        ("iso_27001", "ISO 27001"),
        ("itil", "ITIL"),
        ("soc2", "SOC 2"),
        ("internal", "Internal Security Policy"),
        ("gdpr", "GDPR"),
    ]
    SEVERITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    framework = models.CharField(max_length=16, choices=FRAMEWORK_CHOICES, db_index=True)
    control_id = models.CharField(max_length=64, blank=True, default="")
    control_name = models.CharField(max_length=256, blank=True, default="")
    status = models.CharField(max_length=16, default="compliant", choices=[
        ("compliant", "Compliant"),
        ("non_compliant", "Non-Compliant"),
        ("partial", "Partially Compliant"),
        ("not_applicable", "Not Applicable"),
        ("not_audited", "Not Audited"),
    ])
    severity = models.CharField(max_length=16, choices=SEVERITY_CHOICES, default="medium")
    description = models.TextField(blank=True, default="")
    finding_details = models.JSONField(default=dict, blank=True)
    asset = models.ForeignKey("scanner_api.Asset", on_delete=models.SET_NULL, null=True, blank=True, related_name="compliance_logs")
    audited_by = models.CharField(max_length=128, blank=True, default="")
    audited_at = models.DateTimeField(auto_now_add=True)
    next_audit_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "intelligence_compliance_logs"
        ordering = ["-audited_at"]
        indexes = [
            models.Index(fields=["framework", "status"]),
            models.Index(fields=["-audited_at"]),
            models.Index(fields=["severity"]),
        ]

    def __str__(self):
        return f"{self.framework}/{self.control_id}: {self.status}"


class DashboardAnalytics(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    total_alerts = models.IntegerField(default=0)
    open_alerts = models.IntegerField(default=0)
    critical_alerts = models.IntegerField(default=0)
    notifications_today = models.IntegerField(default=0)
    reports_generated = models.IntegerField(default=0)
    security_violations = models.IntegerField(default=0)
    audit_events_today = models.IntegerField(default=0)
    compliance_violations = models.IntegerField(default=0)
    pending_notifications = models.IntegerField(default=0)
    snapshot_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "intelligence_dashboard_analytics"
        ordering = ["-snapshot_time"]

    def __str__(self):
        return f"Analytics snapshot at {self.snapshot_time}"


class RetentionPolicy(models.Model):
    PERIOD_CHOICES = [
        ("1_year", "1 Year"),
        ("3_years", "3 Years"),
        ("permanent", "Permanent"),
    ]
    SCOPE_CHOICES = [
        ("alerts", "Alerts"),
        ("notifications", "Notifications"),
        ("reports", "Reports"),
        ("audit_logs", "Audit Logs"),
        ("compliance_logs", "Compliance Logs"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES, unique=True)
    retention_period = models.CharField(max_length=16, choices=PERIOD_CHOICES, default="1_year")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "intelligence_retention_policies"
        verbose_name = "Retention Policy"
        verbose_name_plural = "Retention Policies"

    def __str__(self):
        return f"{self.scope}: {self.retention_period}"
