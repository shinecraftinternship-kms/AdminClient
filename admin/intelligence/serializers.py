from rest_framework import serializers
from .models import (
    Alert, AlertHistory, AlertRule,
    Notification, NotificationPreference,
    Report, ScheduledReport,
    AuditLogEntry, ComplianceLog,
    DashboardAnalytics, RetentionPolicy,
)


class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = "__all__"
        read_only_fields = ["id", "generated_time", "created_at", "updated_at", "dedup_hash"]


class AlertListSerializer(serializers.ModelSerializer):
    age_hours = serializers.SerializerMethodField()

    class Meta:
        model = Alert
        fields = [
            "id", "title", "module", "severity", "category", "status",
            "assigned_user", "generated_time", "escalation_level", "age_hours",
        ]

    def get_age_hours(self, obj):
        from django.utils import timezone
        delta = timezone.now() - obj.generated_time
        return round(delta.total_seconds() / 3600, 1)


class AlertHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertHistory
        fields = "__all__"
        read_only_fields = ["id", "timestamp"]


class AlertRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertRule
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"
        read_only_fields = ["id", "created_time", "created_at"]


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = "__all__"
        read_only_fields = ["id", "generated_at", "created_at"]


class ReportListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = [
            "id", "name", "report_type", "format", "generated_by",
            "file_size", "row_count", "status", "generated_at",
        ]


class ScheduledReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduledReport
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class AuditLogEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLogEntry
        fields = "__all__"
        read_only_fields = ["id", "timestamp"]


class AuditLogEntryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLogEntry
        fields = [
            "id", "user_id", "username", "timestamp", "ip_address",
            "module", "action", "object_type", "object_repr",
            "severity", "description",
        ]


class ComplianceLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceLog
        fields = "__all__"
        read_only_fields = ["id", "audited_at", "created_at"]


class DashboardAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardAnalytics
        fields = "__all__"


class RetentionPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = RetentionPolicy
        fields = "__all__"
