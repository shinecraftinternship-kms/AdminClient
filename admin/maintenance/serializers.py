from rest_framework import serializers
from .models import (
    MaintenanceRecord, MaintenanceHistory, MaintenanceDocument,
    WarrantyRecord, DowntimeRecord,
    SoftwareLicense, LicenseAssignment, LicenseHistory,
    ComplianceRecord, MaintenanceAlert,
)


# ── Maintenance Serializers ─────────────────────────────────────────────────


class MaintenanceHistorySerializer(serializers.ModelSerializer):
    maintenance_id = serializers.CharField(source="maintenance.maintenance_id", read_only=True, default="")
    asset_name = serializers.CharField(source="maintenance.asset.asset_name", read_only=True, default="")

    class Meta:
        model = MaintenanceHistory
        fields = "__all__"
        read_only_fields = ["id", "maintenance", "action", "description", "previous_value",
                            "new_value", "performed_by", "ip_address", "timestamp"]


class MaintenanceDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceDocument
        fields = "__all__"


class MaintenanceRecordSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source="asset.asset_name", read_only=True, default="")
    asset_tag = serializers.CharField(source="asset.asset_tag", read_only=True, default="")
    asset_id_display = serializers.CharField(source="asset.asset_id", read_only=True, default="")
    department_name = serializers.CharField(source="department.name", read_only=True, default="")
    is_overdue = serializers.BooleanField(read_only=True)
    duration_days = serializers.IntegerField(read_only=True)
    history = MaintenanceHistorySerializer(many=True, read_only=True)
    documents = MaintenanceDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = MaintenanceRecord
        fields = "__all__"


class MaintenanceRecordListSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source="asset.asset_name", read_only=True, default="")
    asset_tag = serializers.CharField(source="asset.asset_tag", read_only=True, default="")
    asset_id_display = serializers.CharField(source="asset.asset_id", read_only=True, default="")
    department_name = serializers.CharField(source="department.name", read_only=True, default="")
    is_overdue = serializers.BooleanField(read_only=True)
    duration_days = serializers.IntegerField(read_only=True)

    class Meta:
        model = MaintenanceRecord
        fields = [
            "id", "maintenance_id", "asset", "asset_name", "asset_tag", "asset_id_display",
            "asset_category_name", "maintenance_type", "status", "approval_status",
            "vendor_name", "technician", "description", "scheduled_date", "start_date",
            "completion_date", "due_date", "estimated_cost", "actual_cost", "downtime_hours",
            "priority", "department", "department_name", "is_overdue", "duration_days",
            "created_by", "created_at",
        ]


# ── Warranty Serializers ────────────────────────────────────────────────────


class WarrantyRecordSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source="asset.asset_name", read_only=True, default="")
    asset_tag = serializers.CharField(source="asset.asset_tag", read_only=True, default="")
    days_remaining = serializers.IntegerField(read_only=True)
    computed_status = serializers.CharField(read_only=True)

    class Meta:
        model = WarrantyRecord
        fields = "__all__"


# ── Downtime Serializers ────────────────────────────────────────────────────


class DowntimeRecordSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source="asset.asset_name", read_only=True, default="")
    asset_tag = serializers.CharField(source="asset.asset_tag", read_only=True, default="")
    is_ongoing = serializers.BooleanField(read_only=True)

    class Meta:
        model = DowntimeRecord
        fields = "__all__"


# ── Software License Serializers ────────────────────────────────────────────


class LicenseAssignmentSerializer(serializers.ModelSerializer):
    license_software_name = serializers.CharField(source="license.software_name", read_only=True, default="")
    license_id_display = serializers.CharField(source="license.license_id", read_only=True, default="")
    asset_name = serializers.CharField(source="asset.asset_name", read_only=True, default="")
    employee_name = serializers.CharField(source="employee.full_name", read_only=True, default="")
    department_name = serializers.CharField(source="department.name", read_only=True, default="")

    class Meta:
        model = LicenseAssignment
        fields = "__all__"


class LicenseHistorySerializer(serializers.ModelSerializer):
    license_software_name = serializers.CharField(source="license.software_name", read_only=True, default="")

    class Meta:
        model = LicenseHistory
        fields = "__all__"
        read_only_fields = ["id", "license", "action", "description", "previous_value",
                            "new_value", "performed_by", "timestamp"]


class SoftwareLicenseSerializer(serializers.ModelSerializer):
    seats_available = serializers.IntegerField(read_only=True)
    utilization_pct = serializers.FloatField(read_only=True)
    days_until_expiration = serializers.IntegerField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    computed_status = serializers.CharField(read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True, default="")
    assignments = LicenseAssignmentSerializer(many=True, read_only=True)
    history = LicenseHistorySerializer(many=True, read_only=True)
    license_key_display = serializers.SerializerMethodField()

    class Meta:
        model = SoftwareLicense
        fields = "__all__"

    def get_license_key_display(self, obj):
        return obj.license_key_masked or "XXXXX-XXXXX-XXXXX-XXXXX"


class SoftwareLicenseListSerializer(serializers.ModelSerializer):
    seats_available = serializers.IntegerField(read_only=True)
    utilization_pct = serializers.FloatField(read_only=True)
    days_until_expiration = serializers.IntegerField(read_only=True)
    computed_status = serializers.CharField(read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True, default="")

    class Meta:
        model = SoftwareLicense
        fields = [
            "id", "license_id", "software_name", "vendor", "product_edition",
            "version", "license_type", "purchased_seats", "seats_used",
            "seats_available", "utilization_pct",
            "purchase_date", "expiration_date", "renewal_date",
            "cost", "status", "computed_status", "department", "department_name",
            "days_until_expiration", "created_at",
        ]


# ── Compliance & Alert Serializers ──────────────────────────────────────────


class ComplianceRecordSerializer(serializers.ModelSerializer):
    license_software_name = serializers.CharField(source="license.software_name", read_only=True, default="")
    asset_name = serializers.CharField(source="asset.asset_name", read_only=True, default="")

    class Meta:
        model = ComplianceRecord
        fields = "__all__"


class MaintenanceAlertSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source="asset.asset_name", read_only=True, default="")
    license_software_name = serializers.CharField(source="license.software_name", read_only=True, default="")
    warranty_asset_name = serializers.CharField(source="warranty.asset.asset_name", read_only=True, default="")

    class Meta:
        model = MaintenanceAlert
        fields = "__all__"


# ── Input Serializers ───────────────────────────────────────────────────────


class MaintenanceCreateSerializer(serializers.Serializer):
    asset = serializers.UUIDField()
    maintenance_type = serializers.ChoiceField(choices=MaintenanceRecord.TYPE_CHOICES)
    vendor_name = serializers.CharField(required=False, default="", allow_blank=True)
    vendor_contact = serializers.CharField(required=False, default="", allow_blank=True)
    technician = serializers.CharField(required=False, default="", allow_blank=True)
    description = serializers.CharField(required=False, default="", allow_blank=True)
    notes = serializers.CharField(required=False, default="", allow_blank=True)
    scheduled_date = serializers.DateField(required=False, allow_null=True)
    start_date = serializers.DateField(required=False, allow_null=True)
    completion_date = serializers.DateField(required=False, allow_null=True)
    due_date = serializers.DateField(required=False, allow_null=True)
    estimated_cost = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    actual_cost = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    downtime_hours = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, default=0)
    priority = serializers.ChoiceField(choices=["Low", "Medium", "High", "Critical"], default="Medium")
    recurring = serializers.BooleanField(required=False, default=False)
    recurrence_interval_days = serializers.IntegerField(required=False, default=0)
    department = serializers.UUIDField(required=False, allow_null=True)


class MaintenanceUpdateSerializer(serializers.Serializer):
    maintenance_type = serializers.ChoiceField(choices=MaintenanceRecord.TYPE_CHOICES, required=False)
    vendor_name = serializers.CharField(required=False, default="", allow_blank=True)
    vendor_contact = serializers.CharField(required=False, default="", allow_blank=True)
    technician = serializers.CharField(required=False, default="", allow_blank=True)
    description = serializers.CharField(required=False, default="", allow_blank=True)
    notes = serializers.CharField(required=False, default="", allow_blank=True)
    scheduled_date = serializers.DateField(required=False, allow_null=True)
    start_date = serializers.DateField(required=False, allow_null=True)
    completion_date = serializers.DateField(required=False, allow_null=True)
    due_date = serializers.DateField(required=False, allow_null=True)
    estimated_cost = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    actual_cost = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    downtime_hours = serializers.DecimalField(max_digits=8, decimal_places=2, required=False)
    priority = serializers.ChoiceField(choices=["Low", "Medium", "High", "Critical"], required=False)
    recurring = serializers.BooleanField(required=False)
    recurrence_interval_days = serializers.IntegerField(required=False)
    department = serializers.UUIDField(required=False, allow_null=True)


class MaintenanceStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=MaintenanceRecord.STATUS_CHOICES)
    notes = serializers.CharField(required=False, default="", allow_blank=True)


class MaintenanceApprovalSerializer(serializers.Serializer):
    approval_status = serializers.ChoiceField(choices=["Approved", "Rejected"])
    notes = serializers.CharField(required=False, default="", allow_blank=True)


class LicenseCreateSerializer(serializers.Serializer):
    software_name = serializers.CharField()
    vendor = serializers.CharField(required=False, default="", allow_blank=True)
    product_edition = serializers.CharField(required=False, default="", allow_blank=True)
    version = serializers.CharField(required=False, default="", allow_blank=True)
    license_key = serializers.CharField(required=False, default="", allow_blank=True)
    license_type = serializers.ChoiceField(choices=SoftwareLicense.LICENSE_TYPES, default="Per User")
    purchased_seats = serializers.IntegerField(default=1, min_value=1)
    purchase_date = serializers.DateField(required=False, allow_null=True)
    expiration_date = serializers.DateField(required=False, allow_null=True)
    renewal_date = serializers.DateField(required=False, allow_null=True)
    cost = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    department = serializers.UUIDField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, default="", allow_blank=True)


class LicenseUpdateSerializer(serializers.Serializer):
    software_name = serializers.CharField(required=False)
    vendor = serializers.CharField(required=False, allow_blank=True)
    product_edition = serializers.CharField(required=False, allow_blank=True)
    version = serializers.CharField(required=False, allow_blank=True)
    license_key = serializers.CharField(required=False, allow_blank=True)
    license_type = serializers.ChoiceField(choices=SoftwareLicense.LICENSE_TYPES, required=False)
    purchased_seats = serializers.IntegerField(required=False, min_value=1)
    purchase_date = serializers.DateField(required=False, allow_null=True)
    expiration_date = serializers.DateField(required=False, allow_null=True)
    renewal_date = serializers.DateField(required=False, allow_null=True)
    cost = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    department = serializers.UUIDField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class LicenseAssignmentCreateSerializer(serializers.Serializer):
    license = serializers.UUIDField()
    assignable_type = serializers.ChoiceField(choices=LicenseAssignment.ASSIGNABLE_TYPES)
    asset = serializers.UUIDField(required=False, allow_null=True)
    employee = serializers.UUIDField(required=False, allow_null=True)
    department = serializers.UUIDField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, default="", allow_blank=True)


class WarrantyCreateSerializer(serializers.Serializer):
    asset = serializers.UUIDField()
    warranty_start = serializers.DateField()
    warranty_end = serializers.DateField()
    warranty_provider = serializers.CharField()
    contract_number = serializers.CharField(required=False, default="", allow_blank=True)
    amc_details = serializers.CharField(required=False, default="", allow_blank=True)
    support_contact_name = serializers.CharField(required=False, default="", allow_blank=True)
    support_contact_email = serializers.EmailField(required=False, default="", allow_blank=True)
    support_contact_phone = serializers.CharField(required=False, default="", allow_blank=True)
    coverage_type = serializers.ChoiceField(choices=WarrantyRecord._meta.get_field("coverage_type").choices, default="Full")
    notes = serializers.CharField(required=False, default="", allow_blank=True)
    cost = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)


class DowntimeCreateSerializer(serializers.Serializer):
    asset = serializers.UUIDField()
    maintenance = serializers.UUIDField(required=False, allow_null=True)
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField(required=False, allow_null=True)
    reason = serializers.ChoiceField(choices=DowntimeRecord.REASON_CHOICES, default="Maintenance")
    description = serializers.CharField(required=False, default="", allow_blank=True)


class AlertActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["acknowledge", "resolve", "dismiss"])
    notes = serializers.CharField(required=False, default="", allow_blank=True)
