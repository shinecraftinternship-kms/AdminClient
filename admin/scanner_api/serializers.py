from rest_framework import serializers
from .models import (
    Client, ScanResult, AddonDevice, ActivityLog, ClientGroup, Setting,
    Location, Department, Employee, EmployeeAssetAssignment, OrgAuditLog,
    AssetCategory, AssetVendor, Asset, AssetAssignment, AssetTransfer,
    AssetHistory, AssetDocument,
)


class ClientGroupSerializer(serializers.ModelSerializer):
    client_count = serializers.SerializerMethodField()

    class Meta:
        model = ClientGroup
        fields = ["id", "name", "description", "client_count", "created_at"]

    def get_client_count(self, obj):
        return obj.clients.filter(deleted=False).count()


class ScanResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScanResult
        fields = ["id", "scan_type", "scan_data", "created_at"]


class ScanHistorySerializer(serializers.ModelSerializer):
    client_hostname = serializers.CharField(source="client.hostname", read_only=True, default="")
    client_key = serializers.CharField(source="client.registration_key", read_only=True, default="")
    client_platform = serializers.CharField(source="client.platform", read_only=True, default="")

    class Meta:
        model = ScanResult
        fields = ["id", "scan_type", "scan_data", "created_at", "client_hostname", "client_key", "client_platform"]


class AddonDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AddonDevice
        fields = "__all__"


class ActivityLogSerializer(serializers.ModelSerializer):
    client_hostname = serializers.CharField(source="client.hostname", read_only=True, default="")

    class Meta:
        model = ActivityLog
        fields = ["id", "action", "client_hostname", "details", "created_at"]


class ClientListSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source="group.name", read_only=True, default=None)
    owner_username = serializers.CharField(source="owner.username", read_only=True, default=None)
    tags_list = serializers.ListField(child=serializers.CharField(), source="tag_list", read_only=True)
    is_stale = serializers.BooleanField(read_only=True)

    class Meta:
        model = Client
        fields = [
            "id", "registration_key", "hostname", "platform", "status",
            "last_seen", "approved", "group", "group_name", "tags_list",
            "is_stale", "last_ip", "deleted", "client_version", "cpu_model", "ram_info",
            "purchase_cost", "vendor_name", "notes", "created_at",
            "owner", "owner_username",
        ]


class ClientDetailSerializer(serializers.ModelSerializer):
    scans = ScanResultSerializer(many=True, read_only=True)
    addons = AddonDeviceSerializer(many=True, read_only=True)
    group_name = serializers.CharField(source="group.name", read_only=True, default=None)
    tags_list = serializers.ListField(child=serializers.CharField(), source="tag_list", read_only=True)
    is_stale = serializers.BooleanField(read_only=True)

    class Meta:
        model = Client
        fields = "__all__"


class ManualUpdateSerializer(serializers.Serializer):
    hostname = serializers.CharField(required=False, allow_blank=True)
    purchase_cost = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    purchase_date = serializers.DateField(required=False, allow_null=True)
    vendor_name = serializers.CharField(required=False, allow_blank=True)
    vendor_contact = serializers.CharField(required=False, allow_blank=True)
    warranty_expiry = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    group = serializers.PrimaryKeyRelatedField(queryset=ClientGroup.objects.all(), required=False, allow_null=True)
    tags = serializers.CharField(required=False, allow_blank=True)
    deleted = serializers.BooleanField(required=False)
    status = serializers.CharField(required=False)


class ScanConfigSerializer(serializers.Serializer):
    interval_seconds = serializers.IntegerField(min_value=60, max_value=604800, default=3600)
    enabled = serializers.BooleanField(default=True)


class RegisterRequestSerializer(serializers.Serializer):
    registration_key = serializers.CharField()
    hostname = serializers.CharField(required=False, default="")
    platform = serializers.CharField(required=False, default="")
    client_version = serializers.CharField(required=False, default="")
    device_fingerprint = serializers.CharField(required=False, default="")


class ApproveRequestSerializer(serializers.Serializer):
    registration_key = serializers.CharField()


class ApproveMultipleSerializer(serializers.Serializer):
    registration_keys = serializers.ListField(child=serializers.CharField())


class PingRequestSerializer(serializers.Serializer):
    registration_key = serializers.CharField()
    hostname = serializers.CharField(required=False, default="")
    client_version = serializers.CharField(required=False, default="")
    device_fingerprint = serializers.CharField(required=False, default="")


class ScanSubmitSerializer(serializers.Serializer):
    registration_key = serializers.CharField()
    hostname = serializers.CharField(required=False, default="")
    scan_type = serializers.CharField(required=False, default="scheduled")
    platform = serializers.CharField(required=False, default="")
    platform_version = serializers.CharField(required=False, default="")
    scan_timestamp = serializers.CharField(required=False, default="")
    scanned_by = serializers.CharField(required=False, default="")
    processor = serializers.JSONField(required=False, default=dict)
    ram = serializers.JSONField(required=False, default=dict)
    storage = serializers.JSONField(required=False, default=dict)
    gpu = serializers.ListField(required=False, default=list)
    motherboard = serializers.JSONField(required=False, default=dict)
    os_info = serializers.JSONField(required=False, default=dict)
    accounts = serializers.ListField(required=False, default=list)
    network = serializers.JSONField(required=False, default=dict)
    peripherals = serializers.JSONField(required=False, default=dict)
    software = serializers.ListField(required=False, default=list)
    updates = serializers.ListField(required=False, default=list)
    antivirus = serializers.JSONField(required=False, default=dict)

    def validate(self, attrs):
        known = set(self.fields.keys())
        extra = {}
        for k, v in self.initial_data.items():
            if k not in known:
                extra[k] = v
        if extra:
            attrs['_extra'] = extra
        return attrs


class SettingSerializer(serializers.Serializer):
    auto_approve = serializers.BooleanField(required=False)
    stale_threshold_seconds = serializers.IntegerField(required=False, min_value=300)
    scan_all_interval = serializers.IntegerField(required=False, min_value=300)


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField()
    remember_me = serializers.BooleanField(required=False, default=False)


class ProfileUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    timezone = serializers.CharField(required=False, default="UTC")
    currency = serializers.CharField(required=False, default="USD")
    date_format = serializers.CharField(required=False, default="YYYY-MM-DD")
    notification_email = serializers.BooleanField(required=False)
    notification_in_app = serializers.BooleanField(required=False)
    notification_daily_summary = serializers.BooleanField(required=False)
    dashboard_default = serializers.CharField(required=False)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField()


class AdminUserCreateSerializer(serializers.Serializer):
    username = serializers.CharField()
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField()
    is_superuser = serializers.BooleanField(required=False, default=False)


class OrganizationSettingsSerializer(serializers.Serializer):
    org_name = serializers.CharField(required=False, allow_blank=True)
    org_logo_url = serializers.URLField(required=False, allow_blank=True)
    org_timezone = serializers.CharField(required=False, default="UTC")
    org_currency = serializers.CharField(required=False, default="USD")
    org_date_format = serializers.CharField(required=False, default="YYYY-MM-DD")


class SecuritySettingsSerializer(serializers.Serializer):
    session_timeout_minutes = serializers.IntegerField(required=False, min_value=5, max_value=1440)
    max_login_attempts = serializers.IntegerField(required=False, min_value=3, max_value=20)
    lock_duration_minutes = serializers.IntegerField(required=False, min_value=5, max_value=1440)
    password_expiry_days = serializers.IntegerField(required=False, min_value=0)


class NotificationSettingsSerializer(serializers.Serializer):
    notification_email = serializers.BooleanField(required=False)
    notification_in_app = serializers.BooleanField(required=False)
    notification_daily_summary = serializers.BooleanField(required=False)


class DashboardSettingsSerializer(serializers.Serializer):
    dashboard_default = serializers.CharField(required=False)
    dashboard_filters = serializers.JSONField(required=False)


class AuditLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True, default="")

    class Meta:
        from .models import AuditLog
        model = AuditLog
        fields = [
            "id", "user", "username", "event_type", "ip_address",
            "user_agent", "device_info", "details", "success", "created_at",
        ]


class LoginHistorySerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True, default="")

    class Meta:
        from .models import LoginHistory
        model = LoginHistory
        fields = [
            "id", "user", "username", "ip_address", "browser", "os",
            "device_type", "location", "login_time", "logout_time",
            "session_duration", "is_current",
        ]


# ── Organization Module Serializers ──────────────────────────────────────────


class LocationSerializer(serializers.ModelSerializer):
    department_count = serializers.SerializerMethodField()
    employee_count = serializers.SerializerMethodField()
    asset_count = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = "__all__"

    def get_department_count(self, obj):
        return obj.departments.filter(deleted=False).count()

    def get_employee_count(self, obj):
        return obj.employees.filter(deleted=False).count()

    def get_asset_count(self, obj):
        return EmployeeAssetAssignment.objects.filter(
            is_active=True, employee__location=obj
        ).values("client").distinct().count()


class LocationListSerializer(serializers.ModelSerializer):
    department_count = serializers.SerializerMethodField()
    employee_count = serializers.SerializerMethodField()
    asset_count = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = [
            "id", "office_name", "building_name", "floor", "city", "country",
            "status", "department_count", "employee_count", "asset_count", "created_at",
        ]

    def get_department_count(self, obj):
        return obj.departments.filter(deleted=False).count()

    def get_employee_count(self, obj):
        return obj.employees.filter(deleted=False).count()

    def get_asset_count(self, obj):
        return EmployeeAssetAssignment.objects.filter(
            is_active=True, employee__location=obj
        ).values("client").distinct().count()


class DepartmentSerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(source="location.office_name", read_only=True, default="")
    employee_count = serializers.SerializerMethodField()
    asset_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = "__all__"

    def get_employee_count(self, obj):
        return obj.employees.filter(deleted=False).count()

    def get_asset_count(self, obj):
        return EmployeeAssetAssignment.objects.filter(
            is_active=True, employee__department=obj
        ).values("client").distinct().count()


class DepartmentListSerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(source="location.office_name", read_only=True, default="")
    employee_count = serializers.SerializerMethodField()
    asset_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = [
            "id", "name", "code", "department_head", "location", "location_name",
            "status", "employee_count", "asset_count", "budget", "created_at",
        ]

    def get_employee_count(self, obj):
        return obj.employees.filter(deleted=False).count()

    def get_asset_count(self, obj):
        return EmployeeAssetAssignment.objects.filter(
            is_active=True, employee__department=obj
        ).values("client").distinct().count()


class EmployeeSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    location_name = serializers.CharField(source="location.office_name", read_only=True)
    manager_name_display = serializers.CharField(source="reports_to.full_name", read_only=True, default="")
    active_asset_count = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = "__all__"

    def get_active_asset_count(self, obj):
        return obj.asset_assignments.filter(is_active=True).count()


class EmployeeListSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    location_name = serializers.CharField(source="location.office_name", read_only=True)
    active_asset_count = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            "id", "employee_code", "full_name", "email", "department", "department_name",
            "designation", "location", "location_name", "status", "active_asset_count",
            "joining_date", "created_at",
        ]

    def get_active_asset_count(self, obj):
        return obj.asset_assignments.filter(is_active=True).count()


class EmployeeAssetAssignmentSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    employee_code = serializers.CharField(source="employee.employee_code", read_only=True)
    client_hostname = serializers.CharField(source="client.hostname", read_only=True, default="")
    client_key = serializers.CharField(source="client.registration_key", read_only=True, default="")

    class Meta:
        model = EmployeeAssetAssignment
        fields = "__all__"


class OrgAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrgAuditLog
        fields = "__all__"


# ── Asset Management Module Serializers ─────────────────────────────────────


class AssetCategorySerializer(serializers.ModelSerializer):
    children_count = serializers.SerializerMethodField()
    asset_count = serializers.SerializerMethodField()

    class Meta:
        model = AssetCategory
        fields = "__all__"

    def get_children_count(self, obj):
        return obj.children.filter(is_active=True).count()

    def get_asset_count(self, obj):
        return obj.assets.filter(deleted=False).count()


class AssetCategoryListSerializer(serializers.ModelSerializer):
    asset_count = serializers.SerializerMethodField()

    class Meta:
        model = AssetCategory
        fields = ["id", "name", "code", "description", "parent", "icon", "is_active", "asset_count", "created_at"]

    def get_asset_count(self, obj):
        return obj.assets.filter(deleted=False).count()


class AssetVendorSerializer(serializers.ModelSerializer):
    asset_count = serializers.SerializerMethodField()

    class Meta:
        model = AssetVendor
        fields = "__all__"

    def get_asset_count(self, obj):
        return obj.assets.filter(deleted=False).count()


class AssetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, default="")
    vendor_name = serializers.CharField(source="vendor.name", read_only=True, default="")
    department_name = serializers.CharField(source="department.name", read_only=True, default="")
    location_name = serializers.CharField(source="location.office_name", read_only=True, default="")
    assigned_to_name = serializers.CharField(source="assigned_to.full_name", read_only=True, default="")
    assigned_to_code = serializers.CharField(source="assigned_to.employee_code", read_only=True, default="")
    parent_name = serializers.CharField(source="parent.asset_name", read_only=True, default="")
    client_hostname = serializers.CharField(source="client.hostname", read_only=True, default="")
    children = serializers.SerializerMethodField()
    tag_list = serializers.ListField(child=serializers.CharField(), source="tag_list", read_only=True)
    is_warranty_valid = serializers.BooleanField(read_only=True)
    warranty_status = serializers.CharField(read_only=True)
    age_days = serializers.IntegerField(read_only=True)
    full_path = serializers.CharField(read_only=True)

    class Meta:
        model = Asset
        fields = "__all__"

    def get_children(self, obj):
        kids = obj.children.filter(deleted=False)
        return AssetListSerializer(kids, many=True).data


class AssetListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, default="")
    department_name = serializers.CharField(source="department.name", read_only=True, default="")
    location_name = serializers.CharField(source="location.office_name", read_only=True, default="")
    assigned_to_name = serializers.CharField(source="assigned_to.full_name", read_only=True, default="")
    is_warranty_valid = serializers.BooleanField(read_only=True)
    warranty_status = serializers.CharField(read_only=True)

    class Meta:
        model = Asset
        fields = [
            "id", "asset_id", "asset_name", "asset_tag", "serial_number",
            "category", "category_name", "asset_status",
            "manufacturer", "model_name",
            "department", "department_name", "location", "location_name",
            "assigned_to", "assigned_to_name",
            "purchase_date", "purchase_cost", "current_value",
            "warranty_end", "warranty_status", "is_warranty_valid",
            "parent", "client", "is_active", "deleted", "created_at",
        ]


class AssetAssignmentSerializerV2(serializers.ModelSerializer):
    asset_tag = serializers.CharField(source="asset.asset_tag", read_only=True, default="")
    asset_name = serializers.CharField(source="asset.asset_name", read_only=True, default="")
    employee_name = serializers.CharField(source="employee.full_name", read_only=True, default="")
    employee_code = serializers.CharField(source="employee.employee_code", read_only=True, default="")
    department_name = serializers.CharField(source="department.name", read_only=True, default="")
    location_name = serializers.CharField(source="location.office_name", read_only=True, default="")

    class Meta:
        model = AssetAssignment
        fields = "__all__"


class AssetTransferSerializer(serializers.ModelSerializer):
    asset_tag = serializers.CharField(source="asset.asset_tag", read_only=True, default="")
    asset_name = serializers.CharField(source="asset.asset_name", read_only=True, default="")
    from_employee_name = serializers.CharField(source="from_employee.full_name", read_only=True, default="")
    to_employee_name = serializers.CharField(source="to_employee.full_name", read_only=True, default="")
    from_department_name = serializers.CharField(source="from_department.name", read_only=True, default="")
    to_department_name = serializers.CharField(source="to_department.name", read_only=True, default="")
    from_location_name = serializers.CharField(source="from_location.office_name", read_only=True, default="")
    to_location_name = serializers.CharField(source="to_location.office_name", read_only=True, default="")

    class Meta:
        model = AssetTransfer
        fields = "__all__"


class AssetHistorySerializer(serializers.ModelSerializer):
    asset_tag = serializers.CharField(source="asset.asset_tag", read_only=True, default="")
    asset_name = serializers.CharField(source="asset.asset_name", read_only=True, default="")

    class Meta:
        model = AssetHistory
        fields = "__all__"
        read_only_fields = ["id", "asset", "action", "timestamp", "previous_value",
                            "new_value", "performed_by", "ip_address", "user_agent", "notes"]


class AssetDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetDocument
        fields = "__all__"
