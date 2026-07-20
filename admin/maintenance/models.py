import uuid
from django.db import models
from django.utils import timezone
from AdminClient.admin.scanner_api.models import Asset, AssetCategory, Department, Location, Employee


# ═══════════════════════════════════════════════════════════════════════════════
# MAINTENANCE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════


class MaintenanceRecord(models.Model):
    TYPE_CHOICES = [
        ("Preventive", "Preventive"),
        ("Corrective", "Corrective"),
        ("Emergency", "Emergency"),
        ("Inspection", "Inspection"),
        ("Upgrade", "Upgrade"),
        ("Repair", "Repair"),
        ("Replacement", "Replacement"),
        ("Calibration", "Calibration"),
    ]
    STATUS_CHOICES = [
        ("Draft", "Draft"),
        ("Pending Approval", "Pending Approval"),
        ("Approved", "Approved"),
        ("Scheduled", "Scheduled"),
        ("In Progress", "In Progress"),
        ("Waiting Parts", "Waiting Parts"),
        ("Completed", "Completed"),
        ("Cancelled", "Cancelled"),
        ("Overdue", "Overdue"),
    ]
    APPROVAL_CHOICES = [
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    maintenance_id = models.CharField(max_length=32, unique=True, db_index=True, blank=True)

    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="maintenance_records")
    asset_category_name = models.CharField(max_length=128, blank=True, default="")

    maintenance_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default="Draft", db_index=True)
    approval_status = models.CharField(max_length=16, choices=APPROVAL_CHOICES, default="Pending")

    vendor_name = models.CharField(max_length=255, blank=True, default="")
    vendor_contact = models.CharField(max_length=255, blank=True, default="")
    technician = models.CharField(max_length=255, blank=True, default="")

    description = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")

    scheduled_date = models.DateField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    completion_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True, help_text="Deadline for completion")

    estimated_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    actual_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    downtime_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    priority = models.CharField(max_length=16, default="Medium", choices=[
        ("Low", "Low"), ("Medium", "Medium"), ("High", "High"), ("Critical", "Critical"),
    ])

    recurring = models.BooleanField(default=False)
    recurrence_interval_days = models.IntegerField(default=0, help_text="0 = not recurring")
    next_occurrence = models.DateField(null=True, blank=True)

    created_by = models.CharField(max_length=255, blank=True, default="")
    approved_by = models.CharField(max_length=255, blank=True, default="")

    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="maintenance_records")

    deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "maintenance_records"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["asset", "-created_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["maintenance_type"]),
            models.Index(fields=["scheduled_date"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"{self.maintenance_id} - {self.asset.asset_name} ({self.maintenance_type})"

    def save(self, *args, **kwargs):
        if not self.maintenance_id:
            last = MaintenanceRecord.objects.order_by("-created_at").first()
            if last and last.maintenance_id:
                try:
                    num = int(last.maintenance_id.replace("MNT", ""))
                except (ValueError, TypeError):
                    num = 0
            else:
                num = 0
            self.maintenance_id = f"MNT{num + 1:06d}"
        if not self.asset_category_name and self.asset and self.asset.category:
            self.asset_category_name = self.asset.category.name
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        if self.status in ("Completed", "Cancelled"):
            return False
        if self.due_date and timezone.now().date() > self.due_date:
            return True
        if self.scheduled_date and self.status in ("Draft", "Pending Approval", "Approved", "Scheduled"):
            if timezone.now().date() > self.scheduled_date:
                return True
        return False

    @property
    def duration_days(self):
        if self.start_date and self.completion_date:
            return (self.completion_date - self.start_date).days
        return None

    @property
    def asset_name_display(self):
        return self.asset.asset_name if self.asset else ""


class MaintenanceHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    maintenance = models.ForeignKey(MaintenanceRecord, on_delete=models.PROTECT, related_name="history")
    action = models.CharField(max_length=64, db_index=True)
    description = models.TextField(blank=True, default="")
    previous_value = models.JSONField(default=dict, blank=True)
    new_value = models.JSONField(default=dict, blank=True)
    performed_by = models.CharField(max_length=255, blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "maintenance_history"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["maintenance", "-timestamp"]),
            models.Index(fields=["action"]),
        ]

    def __str__(self):
        return f"{self.action} on {self.maintenance_id} at {self.timestamp}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("MaintenanceHistory records are immutable and cannot be updated")
        super().save(*args, **kwargs)


class MaintenanceDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    maintenance = models.ForeignKey(MaintenanceRecord, on_delete=models.PROTECT, related_name="documents")
    name = models.CharField(max_length=255)
    file_data = models.TextField(help_text="Base64 encoded file data")
    file_type = models.CharField(max_length=64, blank=True, default="")
    file_size = models.IntegerField(default=0)
    uploaded_by = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "maintenance_documents"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} for {self.maintenance.maintenance_id}"


# ═══════════════════════════════════════════════════════════════════════════════
# WARRANTY MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════


class WarrantyRecord(models.Model):
    STATUS_CHOICES = [
        ("Active", "Active"),
        ("Expiring Soon", "Expiring Soon"),
        ("Expired", "Expired"),
        ("Claimed", "Claimed"),
        ("Archived", "Archived"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    warranty_id = models.CharField(max_length=32, unique=True, db_index=True, blank=True)
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="warranty_records")

    warranty_start = models.DateField()
    warranty_end = models.DateField()
    warranty_provider = models.CharField(max_length=255)
    contract_number = models.CharField(max_length=255, blank=True, default="")

    amc_details = models.TextField(blank=True, default="")
    support_contact_name = models.CharField(max_length=255, blank=True, default="")
    support_contact_email = models.EmailField(blank=True, default="")
    support_contact_phone = models.CharField(max_length=30, blank=True, default="")

    coverage_type = models.CharField(max_length=50, default="Full", choices=[
        ("Full", "Full Coverage"),
        ("Parts", "Parts Only"),
        ("Labor", "Labor Only"),
        ("Limited", "Limited Warranty"),
    ])

    notes = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Active", db_index=True)
    cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "warranty_records"
        ordering = ["warranty_end"]
        indexes = [
            models.Index(fields=["asset", "status"]),
            models.Index(fields=["warranty_end"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"Warranty for {self.asset.asset_name} ({self.warranty_provider})"

    def save(self, *args, **kwargs):
        if not self.warranty_id:
            last = WarrantyRecord.objects.order_by("-created_at").first()
            if last and last.warranty_id:
                try:
                    num = int(last.warranty_id.replace("WAR", ""))
                except (ValueError, TypeError):
                    num = 0
            else:
                num = 0
            self.warranty_id = f"WAR{num + 1:06d}"
        super().save(*args, **kwargs)

    @property
    def days_remaining(self):
        from django.utils import timezone as tz
        today = tz.now().date()
        if self.warranty_end < today:
            return 0
        return (self.warranty_end - today).days

    @property
    def computed_status(self):
        from django.utils import timezone as tz
        today = tz.now().date()
        if self.warranty_end < today:
            return "Expired"
        days_left = (self.warranty_end - today).days
        if days_left <= 30:
            return "Expiring Soon"
        return "Active"


# ═══════════════════════════════════════════════════════════════════════════════
# DOWNTIME TRACKING
# ═══════════════════════════════════════════════════════════════════════════════


class DowntimeRecord(models.Model):
    REASON_CHOICES = [
        ("Maintenance", "Scheduled Maintenance"),
        ("Repair", "Repair"),
        ("Failure", "Unexpected Failure"),
        ("Upgrade", "Upgrade/Update"),
        ("Power", "Power Outage"),
        ("Network", "Network Issue"),
        ("Other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="downtime_records")
    maintenance = models.ForeignKey(MaintenanceRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name="downtime_records")

    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    duration_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    reason = models.CharField(max_length=20, choices=REASON_CHOICES, default="Maintenance")
    description = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "downtime_records"
        ordering = ["-start_time"]
        indexes = [
            models.Index(fields=["asset", "-start_time"]),
            models.Index(fields=["-start_time"]),
        ]

    def __str__(self):
        return f"Downtime for {self.asset.asset_name} at {self.start_time}"

    def save(self, *args, **kwargs):
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            self.duration_hours = round(delta.total_seconds() / 3600, 2)
        super().save(*args, **kwargs)

    @property
    def is_ongoing(self):
        return self.end_time is None


# ═══════════════════════════════════════════════════════════════════════════════
# SOFTWARE LICENSE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════


class SoftwareLicense(models.Model):
    LICENSE_TYPES = [
        ("Per User", "Per User"),
        ("Per Device", "Per Device"),
        ("Subscription", "Subscription"),
        ("OEM", "OEM"),
        ("Enterprise", "Enterprise"),
        ("Volume", "Volume"),
        ("Trial", "Trial"),
        ("Open Source", "Open Source"),
    ]
    STATUS_CHOICES = [
        ("Draft", "Draft"),
        ("Active", "Active"),
        ("Expiring Soon", "Expiring Soon"),
        ("Expired", "Expired"),
        ("Suspended", "Suspended"),
        ("Archived", "Archived"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    license_id = models.CharField(max_length=32, unique=True, db_index=True, blank=True)

    software_name = models.CharField(max_length=255, db_index=True)
    vendor = models.CharField(max_length=255, blank=True, default="")
    product_edition = models.CharField(max_length=255, blank=True, default="")
    version = models.CharField(max_length=128, blank=True, default="")

    license_key_encrypted = models.CharField(max_length=512, blank=True, default="", help_text="Encrypted full license key")
    license_key_masked = models.CharField(max_length=128, blank=True, default="", help_text="Masked display of license key")

    license_type = models.CharField(max_length=20, choices=LICENSE_TYPES, default="Per User")
    purchased_seats = models.IntegerField(default=1)
    seats_used = models.IntegerField(default=0)

    purchase_date = models.DateField(null=True, blank=True)
    expiration_date = models.DateField(null=True, blank=True)
    renewal_date = models.DateField(null=True, blank=True)

    cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Draft", db_index=True)

    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="licenses")

    notes = models.TextField(blank=True, default="")

    deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "software_licenses"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["software_name"]),
            models.Index(fields=["status"]),
            models.Index(fields=["expiration_date"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"{self.software_name} ({self.license_type})"

    def save(self, *args, **kwargs):
        if not self.license_id:
            last = SoftwareLicense.objects.order_by("-created_at").first()
            if last and last.license_id:
                try:
                    num = int(last.license_id.replace("LIC", ""))
                except (ValueError, TypeError):
                    num = 0
            else:
                num = 0
            self.license_id = f"LIC{num + 1:06d}"
        super().save(*args, **kwargs)

    @property
    def seats_available(self):
        return max(0, self.purchased_seats - self.seats_used)

    @property
    def utilization_pct(self):
        if self.purchased_seats <= 0:
            return 0
        return round((self.seats_used / self.purchased_seats) * 100, 1)

    @property
    def days_until_expiration(self):
        from django.utils import timezone as tz
        if not self.expiration_date:
            return None
        today = tz.now().date()
        if self.expiration_date < today:
            return 0
        return (self.expiration_date - today).days

    @property
    def is_expired(self):
        from django.utils import timezone as tz
        if not self.expiration_date:
            return False
        return self.expiration_date < tz.now().date()

    @property
    def computed_status(self):
        from django.utils import timezone as tz
        if self.status == "Archived":
            return "Archived"
        if self.status == "Suspended":
            return "Suspended"
        if self.status == "Draft":
            return "Draft"
        if not self.expiration_date:
            return self.status
        today = tz.now().date()
        if self.expiration_date < today:
            return "Expired"
        days_left = (self.expiration_date - today).days
        if days_left <= 30:
            return "Expiring Soon"
        return "Active"


class LicenseAssignment(models.Model):
    ASSIGNABLE_TYPES = [
        ("Asset", "Asset"),
        ("Employee", "Employee"),
        ("Department", "Department"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    license = models.ForeignKey(SoftwareLicense, on_delete=models.PROTECT, related_name="assignments")

    assignable_type = models.CharField(max_length=20, choices=ASSIGNABLE_TYPES)
    asset = models.ForeignKey(Asset, on_delete=models.SET_NULL, null=True, blank=True, related_name="license_assignments")
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="license_assignments")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="license_assignments")

    assigned_date = models.DateField(auto_now_add=True)
    removal_date = models.DateField(null=True, blank=True)
    assigned_by = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True)

    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "license_assignments"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["license", "is_active"]),
            models.Index(fields=["assignable_type", "is_active"]),
        ]

    def __str__(self):
        target = ""
        if self.assignable_type == "Asset" and self.asset:
            target = self.asset.asset_name
        elif self.assignable_type == "Employee" and self.employee:
            target = self.employee.full_name
        elif self.assignable_type == "Department" and self.department:
            target = self.department.name
        return f"{self.license.software_name} → {target}"


class LicenseHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    license = models.ForeignKey(SoftwareLicense, on_delete=models.PROTECT, related_name="history")
    action = models.CharField(max_length=64, db_index=True)
    description = models.TextField(blank=True, default="")
    previous_value = models.JSONField(default=dict, blank=True)
    new_value = models.JSONField(default=dict, blank=True)
    performed_by = models.CharField(max_length=255, blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "license_history"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["license", "-timestamp"]),
            models.Index(fields=["action"]),
        ]

    def __str__(self):
        return f"{self.action} on {self.license.software_name} at {self.timestamp}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("LicenseHistory records are immutable and cannot be updated")
        super().save(*args, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# COMPLIANCE & ALERTS
# ═══════════════════════════════════════════════════════════════════════════════


class ComplianceRecord(models.Model):
    CATEGORY_CHOICES = [
        ("license_expiration", "License Expiration"),
        ("seat_overuse", "Seat Overuse"),
        ("unauthorized_software", "Unauthorized Software"),
        ("missing_license", "Missing License"),
        ("compliance_violation", "Compliance Violation"),
    ]
    SEVERITY_CHOICES = [
        ("info", "Info"),
        ("warning", "Warning"),
        ("critical", "Critical"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, db_index=True)
    severity = models.CharField(max_length=16, choices=SEVERITY_CHOICES, default="warning", db_index=True)
    title = models.CharField(max_length=256)
    description = models.TextField(blank=True, default="")
    license = models.ForeignKey(SoftwareLicense, on_delete=models.SET_NULL, null=True, blank=True, related_name="compliance_records")
    asset = models.ForeignKey(Asset, on_delete=models.SET_NULL, null=True, blank=True, related_name="compliance_records")
    details = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, default="active", choices=[
        ("active", "Active"),
        ("acknowledged", "Acknowledged"),
        ("resolved", "Resolved"),
        ("dismissed", "Dismissed"),
    ])
    acknowledged_by = models.CharField(max_length=128, blank=True, default="")
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "compliance_records"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["category", "status"]),
            models.Index(fields=["severity", "status"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"[{self.severity}] {self.title}"


class MaintenanceAlert(models.Model):
    CATEGORY_CHOICES = [
        ("maintenance_due", "Maintenance Due"),
        ("maintenance_overdue", "Maintenance Overdue"),
        ("warranty_expiring", "Warranty Expiring"),
        ("warranty_expired", "Warranty Expired"),
        ("downtime_exceeded", "Downtime Exceeded"),
        ("license_expiration", "License Expiration"),
        ("license_seat_exhaustion", "License Seat Exhaustion"),
        ("compliance_violation", "Compliance Violation"),
        ("vendor_sla_violation", "Vendor SLA Violation"),
    ]
    SEVERITY_CHOICES = [
        ("info", "Info"),
        ("warning", "Warning"),
        ("critical", "Critical"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, db_index=True)
    severity = models.CharField(max_length=16, choices=SEVERITY_CHOICES, default="warning", db_index=True)
    title = models.CharField(max_length=256)
    message = models.TextField(blank=True, default="")

    asset = models.ForeignKey(Asset, on_delete=models.SET_NULL, null=True, blank=True, related_name="maintenance_alerts")
    maintenance = models.ForeignKey(MaintenanceRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name="alerts")
    license = models.ForeignKey(SoftwareLicense, on_delete=models.SET_NULL, null=True, blank=True, related_name="alerts")
    warranty = models.ForeignKey(WarrantyRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name="alerts")

    details = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, default="active", choices=[
        ("active", "Active"),
        ("acknowledged", "Acknowledged"),
        ("resolved", "Resolved"),
        ("dismissed", "Dismissed"),
    ])
    acknowledged_by = models.CharField(max_length=128, blank=True, default="")
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "maintenance_alerts"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["category", "status"]),
            models.Index(fields=["severity", "status"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"[{self.severity}] {self.title}"
