import uuid
from django.db import models
from django.utils import timezone

from .api_key_auth import ApiKey  # noqa: F401 — registers ApiKey with Django ORM


class Company(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=128, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "companies"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ClientGroup(models.Model):
    name = models.CharField(max_length=128)
    description = models.TextField(default="", blank=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="client_groups", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "client_groups"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Client(models.Model):
    registration_key = models.CharField(max_length=64, unique=True, db_index=True)
    hostname = models.CharField(max_length=255, default="")
    platform = models.CharField(max_length=128, default="")
    status = models.CharField(max_length=32, default="pending")
    last_seen = models.DateTimeField(null=True, blank=True)
    approved = models.BooleanField(default=False)

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="clients", null=True, blank=True)
    group = models.ForeignKey(ClientGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name="clients")
    tags = models.CharField(max_length=512, default="", blank=True, help_text="Comma-separated tags")

    purchase_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    vendor_name = models.CharField(max_length=255, default="", blank=True)
    vendor_contact = models.CharField(max_length=255, default="", blank=True)
    warranty_expiry = models.DateField(null=True, blank=True)
    notes = models.TextField(default="", blank=True)

    scan_interval = models.IntegerField(default=3600)
    scan_enabled = models.BooleanField(default=True)
    scan_requested = models.BooleanField(default=False)

    last_ip = models.CharField(max_length=64, default="", blank=True)
    device_fingerprint = models.CharField(max_length=64, default="", blank=True, db_index=True,
        help_text="Hardware-based unique device identifier that survives IP changes")
    deleted = models.BooleanField(default=False)

    client_version = models.CharField(max_length=32, default="", blank=True)
    os_version = models.CharField(max_length=256, default="", blank=True)
    cpu_model = models.CharField(max_length=256, default="", blank=True)
    ram_info = models.CharField(max_length=128, default="", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "clients"
        ordering = ["-last_seen"]

    def __str__(self):
        return f"{self.hostname} ({self.registration_key})"

    @property
    def tag_list(self):
        return [t.strip() for t in self.tags.split(",") if t.strip()] if self.tags else []

    @property
    def is_stale(self):
        if self.deleted:
            return False
        if not self.last_seen:
            return True
        threshold_seconds = int(Setting.get("stale_threshold_seconds", "120"))
        threshold = timezone.now() - timezone.timedelta(seconds=max(self.scan_interval * 2, threshold_seconds))
        return self.last_seen < threshold


class ScanResult(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="scans", null=True, blank=True)
    scan_type = models.CharField(max_length=32, default="scheduled")
    scan_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "scan_results"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["client", "-created_at"])]

    def __str__(self):
        return f"Scan {self.scan_type} for {self.client_id} at {self.created_at}"


class AddonDevice(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="addons")
    name = models.CharField(max_length=255)
    description = models.TextField(default="", blank=True)
    serial_number = models.CharField(max_length=255, default="", blank=True)
    purchase_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    category = models.CharField(max_length=128, default="", blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "addon_devices"
        ordering = ["-added_at"]

    def __str__(self):
        return f"{self.name} ({self.serial_number})"


class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ("register", "Client Registered"),
        ("approve", "Client Approved"),
        ("scan", "Scan Completed"),
        ("scan_request", "Scan Requested"),
        ("delete", "Client Deleted"),
        ("update", "Client Updated"),
        ("login", "Admin Login"),
        ("setting_change", "Setting Changed"),
    ]

    action = models.CharField(max_length=32, choices=ACTION_CHOICES)
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, related_name="activity_logs")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="activity_logs", null=True, blank=True)
    details = models.TextField(default="", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "activity_logs"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["-created_at"])]

    def __str__(self):
        return f"{self.action} at {self.created_at}"


class Setting(models.Model):
    key = models.CharField(max_length=255, primary_key=True)
    value = models.TextField(blank=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="settings", null=True, blank=True)

    class Meta:
        db_table = "settings"

    def __str__(self):
        return self.key

    @classmethod
    def get(cls, key, default="", company=None):
        filters = {"key": key}
        if company:
            filters["company"] = company
        obj = cls.objects.filter(**filters).first()
        return obj.value if obj else default

    @classmethod
    def set(cls, key, value, company=None):
        defaults = {"value": str(value)}
        if company:
            defaults["company"] = company
        cls.objects.update_or_create(key=key, defaults=defaults)


class AdministratorProfile(models.Model):
    user = models.OneToOneField("auth.User", on_delete=models.CASCADE, related_name="admin_profile")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="admins", null=True, blank=True)
    phone_number = models.CharField(max_length=20, blank=True, default="")
    profile_picture_url = models.URLField(max_length=500, blank=True, default="")
    timezone = models.CharField(max_length=50, default="UTC")
    currency = models.CharField(max_length=10, default="USD")
    date_format = models.CharField(max_length=20, default="YYYY-MM-DD")
    dashboard_default = models.CharField(max_length=50, default="dashboard")
    notification_email = models.BooleanField(default=True)
    notification_in_app = models.BooleanField(default=True)
    notification_daily_summary = models.BooleanField(default=False)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    mfa_enabled = models.BooleanField(default=False)
    mfa_secret = models.CharField(max_length=128, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "administrator_profiles"

    def __str__(self):
        return f"Profile({self.user.username})"


class AuditLog(models.Model):
    EVENT_CHOICES = [
        ("login_success", "Login Success"),
        ("login_failure", "Login Failure"),
        ("logout", "Logout"),
        ("password_changed", "Password Changed"),
        ("password_reset_requested", "Password Reset Requested"),
        ("profile_updated", "Profile Updated"),
        ("settings_updated", "Settings Updated"),
        ("account_locked", "Account Locked"),
        ("account_unlocked", "Account Unlocked"),
        ("session_created", "Session Created"),
        ("session_expired", "Session Expired"),
    ]
    user = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="audit_logs", null=True, blank=True)
    event_type = models.CharField(max_length=32, choices=EVENT_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    device_info = models.JSONField(default=dict, blank=True)
    details = models.TextField(blank=True, default="")
    success = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["event_type"]),
        ]

    def __str__(self):
        return f"{self.event_type} at {self.created_at}"


class LoginHistory(models.Model):
    user = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="login_history", null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    browser = models.CharField(max_length=128, blank=True, default="")
    os = models.CharField(max_length=128, blank=True, default="")
    device_type = models.CharField(max_length=50, blank=True, default="")
    location = models.CharField(max_length=255, blank=True, default="")
    login_time = models.DateTimeField(auto_now_add=True)
    logout_time = models.DateTimeField(null=True, blank=True)
    session_duration = models.DurationField(null=True, blank=True)
    is_current = models.BooleanField(default=True)

    class Meta:
        db_table = "login_history"
        ordering = ["-login_time"]
        indexes = [models.Index(fields=["-login_time"])]

    def __str__(self):
        return f"{self.user} login at {self.login_time}"


class LoginAttempt(models.Model):
    identifier = models.CharField(max_length=255, db_index=True)
    ip_address = models.GenericIPAddressField()
    success = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "login_attempts"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{'Success' if self.success else 'Failure'} for {self.identifier}"


class DeviceFingerprint(models.Model):
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="devices")
    fingerprint = models.CharField(max_length=255)
    device_name = models.CharField(max_length=255, blank=True, default="")
    browser = models.CharField(max_length=128, blank=True, default="")
    os = models.CharField(max_length=128, blank=True, default="")
    last_seen = models.DateTimeField(auto_now=True)
    trusted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "device_fingerprints"

    def __str__(self):
        return f"{self.device_name} ({self.fingerprint})"


class Location(models.Model):
    STATUS_CHOICES = [("Active", "Active"), ("Archived", "Archived"), ("Closed", "Closed")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="locations", null=True, blank=True)
    office_name = models.CharField(max_length=255)
    building_name = models.CharField(max_length=255, blank=True, default="")
    floor = models.CharField(max_length=50, blank=True, default="")
    room_number = models.CharField(max_length=50, blank=True, default="")
    address = models.TextField(blank=True, default="")
    city = models.CharField(max_length=128)
    state = models.CharField(max_length=128, blank=True, default="")
    country = models.CharField(max_length=128, default="USA")
    postal_code = models.CharField(max_length=20, blank=True, default="")
    contact_number = models.CharField(max_length=20, blank=True, default="")
    office_manager = models.CharField(max_length=255, blank=True, default="")
    timezone = models.CharField(max_length=50, default="UTC")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Active")
    notes = models.TextField(blank=True, default="")
    deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "locations"
        ordering = ["office_name"]
        unique_together = [("office_name", "city")]

    def __str__(self):
        return f"{self.office_name} - {self.city}"


class Department(models.Model):
    STATUS_CHOICES = [("Active", "Active"), ("Disabled", "Disabled"), ("Archived", "Archived")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="departments", null=True, blank=True)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50)
    description = models.TextField(blank=True, default="")
    department_head = models.CharField(max_length=255, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    phone_number = models.CharField(max_length=20, blank=True, default="")
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name="departments")
    budget = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Active")
    deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "departments"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class Employee(models.Model):
    STATUS_CHOICES = [
        ("Active", "Active"),
        ("Inactive", "Inactive"),
        ("Resigned", "Resigned"),
        ("On Leave", "On Leave"),
        ("Terminated", "Terminated"),
        ("Retired", "Retired"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="employees", null=True, blank=True)
    employee_code = models.CharField(max_length=50)
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20, blank=True, default="")
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="employees")
    designation = models.CharField(max_length=255)
    manager_name = models.CharField(max_length=255, blank=True, default="")
    reports_to = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="direct_reports")
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="employees")
    joining_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Active")
    profile_image = models.TextField(blank=True, default="", help_text="Base64 encoded image")
    notes = models.TextField(blank=True, default="")
    deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "employees"
        ordering = ["full_name"]
        unique_together = [("company", "email"), ("company", "employee_code")]

    def __str__(self):
        return f"{self.full_name} ({self.employee_code})"


class EmployeeAssetAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="asset_assignments")
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, related_name="employee_assignments")
    assigned_at = models.DateTimeField(auto_now_add=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    assigned_by = models.CharField(max_length=255, blank=True, default="")
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "employee_asset_assignments"
        ordering = ["-assigned_at"]

    def __str__(self):
        return f"{self.employee} - {self.client} ({'active' if self.is_active else 'returned'})"


class OrgAuditLog(models.Model):
    ENTITY_CHOICES = [("employee", "Employee"), ("department", "Department"), ("location", "Location")]
    ACTION_CHOICES = [
        ("created", "Created"),
        ("updated", "Updated"),
        ("deactivated", "Deactivated"),
        ("archived", "Archived"),
        ("disabled", "Disabled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="org_audit_logs", null=True, blank=True)
    entity_type = models.CharField(max_length=20, choices=ENTITY_CHOICES)
    entity_id = models.CharField(max_length=255)
    entity_name = models.CharField(max_length=255)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    previous_value = models.JSONField(default=dict, blank=True)
    new_value = models.JSONField(default=dict, blank=True)
    performed_by = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "org_audit_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"{self.action} {self.entity_type} {self.entity_name} at {self.created_at}"


# ═══════════════════════════════════════════════════════════════════════════════
# ASSET MANAGEMENT MODULE
# ═══════════════════════════════════════════════════════════════════════════════


class AssetCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="asset_categories", null=True, blank=True)
    name = models.CharField(max_length=128)
    code = models.CharField(max_length=50)
    description = models.TextField(blank=True, default="")
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children")
    icon = models.CharField(max_length=64, blank=True, default="", help_text="Bootstrap icon class")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "asset_categories"
        ordering = ["name"]
        verbose_name_plural = "asset categories"

    def __str__(self):
        return self.name


class AssetVendor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="asset_vendors", null=True, blank=True)
    name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=20, blank=True, default="")
    address = models.TextField(blank=True, default="")
    website = models.URLField(max_length=500, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "asset_vendors"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Asset(models.Model):
    STATUS_CHOICES = [
        ("Draft", "Draft"),
        ("Pending Approval", "Pending Approval"),
        ("Approved", "Approved"),
        ("Purchased", "Purchased"),
        ("Available", "Available"),
        ("Assigned", "Assigned"),
        ("Maintenance", "Maintenance"),
        ("Returned", "Returned"),
        ("Lost", "Lost"),
        ("Damaged", "Damaged"),
        ("Retired", "Retired"),
        ("Disposed", "Disposed"),
        ("Archived", "Archived"),
    ]

    VALID_TRANSITIONS = {
        "Draft": ["Pending Approval"],
        "Pending Approval": ["Approved", "Draft"],
        "Approved": ["Purchased", "Draft"],
        "Purchased": ["Available"],
        "Available": ["Assigned", "Maintenance", "Retired", "Lost", "Damaged"],
        "Assigned": ["Maintenance", "Returned", "Lost", "Damaged"],
        "Maintenance": ["Available", "Retired", "Damaged"],
        "Returned": ["Available", "Maintenance"],
        "Lost": [],
        "Damaged": ["Maintenance", "Retired"],
        "Retired": ["Disposed"],
        "Disposed": [],
        "Archived": [],
    }

    # Identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="assets", null=True, blank=True)
    asset_id = models.CharField(max_length=32, unique=True, db_index=True, blank=True)
    asset_name = models.CharField(max_length=255)
    asset_tag = models.CharField(max_length=128, unique=True, db_index=True)
    serial_number = models.CharField(max_length=255, unique=True, db_index=True)
    qr_code = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    barcode = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)

    # Classification
    category = models.ForeignKey(AssetCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="assets")
    manufacturer = models.CharField(max_length=255, blank=True, default="")
    model_name = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    specifications = models.JSONField(default=dict, blank=True)
    image = models.TextField(blank=True, default="", help_text="Base64 encoded image")

    # Financial
    purchase_date = models.DateField(null=True, blank=True)
    purchase_cost = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    current_value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    residual_value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    depreciation_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    invoice_number = models.CharField(max_length=128, blank=True, default="")
    purchase_order_number = models.CharField(max_length=128, blank=True, default="")
    vendor = models.ForeignKey(AssetVendor, on_delete=models.SET_NULL, null=True, blank=True, related_name="assets")

    # Ownership
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="assets")
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name="assets")

    # Warranty
    warranty_start = models.DateField(null=True, blank=True)
    warranty_end = models.DateField(null=True, blank=True)
    warranty_provider = models.CharField(max_length=255, blank=True, default="")
    amc_details = models.TextField(blank=True, default="")

    # Status
    asset_status = models.CharField(max_length=24, choices=STATUS_CHOICES, default="Draft", db_index=True)

    # Hierarchy
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children")

    # Link to scanned client (optional)
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, related_name="linked_assets")

    # Insurance
    is_insured = models.BooleanField(default=False)
    insurance_value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    insurance_expiry = models.DateField(null=True, blank=True)

    # Meta
    created_by = models.CharField(max_length=255, blank=True, default="")
    last_audit_date = models.DateField(null=True, blank=True)
    tags = models.CharField(max_length=512, blank=True, default="", help_text="Comma-separated tags")
    notes = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)
    assigned_to = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_assets")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assets"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["asset_status"]),
            models.Index(fields=["category"]),
            models.Index(fields=["department"]),
            models.Index(fields=["location"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"{self.asset_name} ({self.asset_tag})"

    def save(self, *args, **kwargs):
        if not self.asset_id:
            last = Asset.objects.order_by("-created_at").first()
            if last and last.asset_id:
                try:
                    num = int(last.asset_id.replace("AST", ""))
                except (ValueError, TypeError):
                    num = 0
            else:
                num = 0
            self.asset_id = f"AST{num + 1:06d}"
        super().save(*args, **kwargs)

    @property
    def tag_list(self):
        return [t.strip() for t in self.tags.split(",") if t.strip()] if self.tags else []

    @property
    def is_warranty_valid(self):
        if not self.warranty_end:
            return False
        from django.utils import timezone as tz
        return self.warranty_end >= tz.now().date()

    @property
    def warranty_status(self):
        if not self.warranty_end:
            return "No Warranty"
        from django.utils import timezone as tz
        today = tz.now().date()
        if self.warranty_end < today:
            return "Expired"
        days_left = (self.warranty_end - today).days
        if days_left <= 30:
            return "Expiring Soon"
        return "Valid"

    @property
    def age_days(self):
        if not self.purchase_date:
            return None
        from django.utils import timezone as tz
        return (tz.now().date() - self.purchase_date).days

    @property
    def full_path(self):
        parts = [self.asset_name]
        p = self.parent
        while p:
            parts.insert(0, p.asset_name)
            p = p.parent
        return " > ".join(parts)

    @staticmethod
    def validate_status_transition(current_status, new_status):
        allowed = Asset.VALID_TRANSITIONS.get(current_status, [])
        if new_status not in allowed:
            return False, f"Cannot transition from '{current_status}' to '{new_status}'. Allowed: {', '.join(allowed) if allowed else 'none'}"
        return True, ""


class AssetAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="assignments")
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="asset_assignments_v2")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="asset_assignments_v2")
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name="asset_assignments_v2")
    assigned_at = models.DateTimeField(auto_now_add=True)
    expected_return_date = models.DateField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    assigned_by = models.CharField(max_length=255, blank=True, default="")
    assignment_notes = models.TextField(blank=True, default="")
    return_notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "asset_assignments_v2"
        ordering = ["-assigned_at"]

    def __str__(self):
        return f"{self.asset} → {self.employee} ({'active' if self.is_active else 'returned'})"


class AssetTransfer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="transfers")
    from_employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="asset_transfers_from")
    to_employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="asset_transfers_to")
    from_department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="asset_transfers_from")
    to_department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="asset_transfers_to")
    from_location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name="asset_transfers_from")
    to_location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name="asset_transfers_to")
    transfer_date = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True, default="")
    transferred_by = models.CharField(max_length=255, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "asset_transfers"
        ordering = ["-transfer_date"]

    def __str__(self):
        return f"Transfer {self.asset} at {self.transfer_date}"


class AssetHistory(models.Model):
    ACTION_CHOICES = [
        ("created", "Asset Created"),
        ("updated", "Asset Updated"),
        ("status_changed", "Status Changed"),
        ("assigned", "Asset Assigned"),
        ("returned", "Asset Returned"),
        ("transferred", "Asset Transferred"),
        ("maintenance_started", "Maintenance Started"),
        ("maintenance_completed", "Maintenance Completed"),
        ("retired", "Asset Retired"),
        ("disposed", "Asset Disposed"),
        ("document_added", "Document Added"),
        ("hierarchy_changed", "Hierarchy Changed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="history")
    action = models.CharField(max_length=32, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    previous_value = models.JSONField(default=dict, blank=True)
    new_value = models.JSONField(default=dict, blank=True)
    performed_by = models.CharField(max_length=255, blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "asset_history"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["asset", "-timestamp"]),
            models.Index(fields=["action"]),
        ]
        # History records are IMMUTABLE - no updates allowed at application level

    def __str__(self):
        return f"{self.action} on {self.asset} at {self.timestamp}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("AssetHistory records are immutable and cannot be updated")
        super().save(*args, **kwargs)

    def update(self, *args, **kwargs):
        raise ValueError("AssetHistory records are immutable and cannot be updated")


class AssetDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="documents")
    name = models.CharField(max_length=255)
    file_data = models.TextField(help_text="Base64 encoded file data")
    file_type = models.CharField(max_length=64, blank=True, default="")
    file_size = models.IntegerField(default=0)
    uploaded_by = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "asset_documents"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} for {self.asset}"
