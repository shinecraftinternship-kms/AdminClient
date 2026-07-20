import uuid
from django.db import models
from AdminClient.admin.scanner_api.models import Client, Setting


class DeviceMonitoringInfo(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("blocked", "Blocked"),
        ("online", "Online"),
        ("offline", "Offline"),
        ("inactive", "Inactive"),
        ("maintenance", "Maintenance"),
        ("unknown", "Unknown"),
    ]
    HEALTH_CHOICES = [
        ("healthy", "Healthy"),
        ("warning", "Warning"),
        ("critical", "Critical"),
        ("unknown", "Unknown"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.OneToOneField(
        Client, on_delete=models.CASCADE,
        related_name="monitoring_info", db_index=True,
    )
    monitoring_status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True,
    )
    health_level = models.CharField(
        max_length=20, choices=HEALTH_CHOICES, default="unknown",
    )
    health_score = models.IntegerField(default=0, help_text="0-100")

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    mac_address = models.CharField(max_length=32, default="", blank=True)
    public_ip = models.CharField(max_length=45, default="", blank=True)

    os_name = models.CharField(max_length=256, default="", blank=True)
    os_build = models.CharField(max_length=128, default="", blank=True)
    os_architecture = models.CharField(max_length=64, default="", blank=True)

    agent_version = models.CharField(max_length=32, default="", blank=True)
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    heartbeat_count = models.IntegerField(default=0)

    device_type = models.CharField(
        max_length=32, default="desktop", blank=True,
        choices=[
            ("laptop", "Laptop"), ("desktop", "Desktop"), ("server", "Server"),
            ("workstation", "Workstation"), ("vm", "Virtual Machine"),
            ("cloud", "Cloud Instance"),
        ],
    )
    department = models.CharField(max_length=256, default="", blank=True)
    location_name = models.CharField(max_length=256, default="", blank=True)
    current_user = models.CharField(max_length=256, default="", blank=True)

    tags = models.CharField(max_length=512, default="", blank=True)
    notes = models.TextField(default="", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "monitoring_device_info"
        ordering = ["-created_at"]

    def __str__(self):
        return f"MonitorInfo({self.client.hostname if self.client else '?'})"

    @property
    def tag_list(self):
        return [t.strip() for t in self.tags.split(",") if t.strip()] if self.tags else []


class HardwareInventory(models.Model):
    COMPONENT_CHOICES = [
        ("cpu", "CPU"),
        ("ram", "RAM"),
        ("storage", "Storage"),
        ("gpu", "GPU"),
        ("motherboard", "Motherboard"),
        ("network", "Network Adapter"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="hw_inventories")
    component_type = models.CharField(max_length=20, choices=COMPONENT_CHOICES, db_index=True)
    component_data = models.JSONField(default=dict)
    fingerprint = models.CharField(max_length=64, default="", blank=True, help_text="Hash of component data for quick diffing")
    scan_id = models.UUIDField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "monitoring_hardware_inventory"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["client", "component_type", "-created_at"]),
        ]

    def __str__(self):
        return f"HW {self.component_type} for {self.client_id}"


class SoftwareInventory(models.Model):
    CATEGORY_CHOICES = [
        ("application", "Application"),
        ("driver", "Driver"),
        ("update", "Windows Update"),
        ("browser", "Browser"),
        ("office", "Office Suite"),
        ("antivirus", "Antivirus"),
        ("service", "Service"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="sw_inventories")
    name = models.CharField(max_length=512, db_index=True)
    version = models.CharField(max_length=128, default="", blank=True)
    publisher = models.CharField(max_length=256, default="", blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="other", db_index=True)
    raw_data = models.JSONField(default=dict)
    scan_id = models.UUIDField(null=True, blank=True, db_index=True)
    is_present = models.BooleanField(default=True, help_text="False = removed in latest scan")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "monitoring_software_inventory"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["client", "category", "-created_at"]),
            models.Index(fields=["client", "name", "-created_at"]),
        ]

    def __str__(self):
        return f"SW {self.name} v{self.version}"


class DeviceHeartbeat(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="monitoring_heartbeats")
    cpu_usage_pct = models.FloatField(default=0)
    ram_usage_pct = models.FloatField(default=0)
    disk_usage_pct = models.FloatField(default=0)
    disk_free_gb = models.FloatField(default=0)
    disk_total_gb = models.FloatField(default=0)
    network_connected = models.BooleanField(default=True)
    uptime_seconds = models.IntegerField(default=0)
    load_average = models.FloatField(default=0)
    agent_version = models.CharField(max_length=32, default="", blank=True)
    scan_running = models.BooleanField(default=False)
    pending_commands = models.IntegerField(default=0)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    response_time_ms = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "monitoring_device_heartbeat"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["client", "-created_at"]),
        ]

    def __str__(self):
        return f"Heartbeat {self.client_id} at {self.created_at}"


class DeviceMetrics(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="device_metrics")
    period = models.CharField(
        max_length=8, default="hourly",
        choices=[("hourly", "Hourly"), ("daily", "Daily")],
        db_index=True,
    )
    avg_cpu_pct = models.FloatField(default=0)
    avg_ram_pct = models.FloatField(default=0)
    avg_disk_pct = models.FloatField(default=0)
    max_cpu_pct = models.FloatField(default=0)
    max_ram_pct = models.FloatField(default=0)
    max_disk_pct = models.FloatField(default=0)
    min_cpu_pct = models.FloatField(default=0)
    min_ram_pct = models.FloatField(default=0)
    min_disk_pct = models.FloatField(default=0)
    health_score = models.IntegerField(default=0)
    health_level = models.CharField(max_length=20, default="unknown")
    uptime_pct = models.FloatField(default=100)
    total_heartbeats = models.IntegerField(default=0)
    missed_heartbeats = models.IntegerField(default=0)
    period_start = models.DateTimeField(db_index=True)
    period_end = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "monitoring_device_metrics"
        ordering = ["-period_start"]
        indexes = [
            models.Index(fields=["client", "period", "-period_start"]),
        ]

    def __str__(self):
        return f"Metrics {self.client_id} {self.period} {self.period_start}"


class DeviceHistory(models.Model):
    CATEGORY_CHOICES = [
        ("registration", "Device Registration"),
        ("status_change", "Status Change"),
        ("hardware_change", "Hardware Change"),
        ("software_change", "Software Change"),
        ("health_change", "Health Change"),
        ("security_event", "Security Event"),
        ("alert_generated", "Alert Generated"),
        ("admin_action", "Admin Action"),
        ("agent_update", "Agent Version Update"),
        ("remote_command", "Remote Command"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="device_history")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, db_index=True)
    event_type = models.CharField(max_length=64, db_index=True)
    description = models.TextField(default="")
    previous_value = models.JSONField(default=dict, blank=True)
    new_value = models.JSONField(default=dict, blank=True)
    severity = models.CharField(
        max_length=16, default="info",
        choices=[("info", "Info"), ("warning", "Warning"), ("critical", "Critical")],
    )
    source = models.CharField(max_length=64, default="system")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "monitoring_device_history"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["client", "-timestamp"]),
            models.Index(fields=["category", "-timestamp"]),
            models.Index(fields=["severity", "-timestamp"]),
        ]

    def __str__(self):
        return f"{self.category}: {self.event_type} @ {self.timestamp}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("DeviceHistory records are immutable and cannot be updated")
        super().save(*args, **kwargs)


class DeviceAlert(models.Model):
    SEVERITY_CHOICES = [
        ("info", "Info"),
        ("warning", "Warning"),
        ("critical", "Critical"),
    ]
    STATUS_CHOICES = [
        ("active", "Active"),
        ("acknowledged", "Acknowledged"),
        ("resolved", "Resolved"),
        ("dismissed", "Dismissed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="monitoring_alerts")
    alert_type = models.CharField(max_length=64, db_index=True)
    severity = models.CharField(max_length=16, choices=SEVERITY_CHOICES, default="warning", db_index=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="active", db_index=True)
    title = models.CharField(max_length=256)
    message = models.TextField(default="")
    details = models.JSONField(default=dict, blank=True)
    acknowledged_by = models.CharField(max_length=128, default="", blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "monitoring_device_alerts"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["client", "status", "-created_at"]),
            models.Index(fields=["severity", "status"]),
        ]

    def __str__(self):
        return f"[{self.severity}] {self.title}"


class AgentVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = models.CharField(max_length=32, unique=True)
    release_notes = models.TextField(default="", blank=True)
    download_url = models.URLField(max_length=500, default="", blank=True)
    is_mandatory = models.BooleanField(default=False)
    min_python_version = models.CharField(max_length=16, default="3.7")
    file_hash = models.CharField(max_length=128, default="", blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "monitoring_agent_versions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Agent v{self.version}"


class AgentSecret(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="agent_secrets")
    agent_id = models.CharField(max_length=128, unique=True, db_index=True)
    secret_key = models.CharField(max_length=128)
    device_fingerprint = models.CharField(max_length=64, default="", blank=True)
    is_active = models.BooleanField(default=True)
    last_used = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "monitoring_agent_secrets"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Secret({self.agent_id})"
