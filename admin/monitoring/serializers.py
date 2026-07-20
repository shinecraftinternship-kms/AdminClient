from rest_framework import serializers
from .models import (
    DeviceMonitoringInfo, HardwareInventory, SoftwareInventory,
    DeviceHeartbeat, DeviceMetrics, DeviceHistory, DeviceAlert,
    AgentVersion, AgentSecret,
)


class DeviceMonitoringInfoSerializer(serializers.ModelSerializer):
    hostname = serializers.CharField(source="client.hostname", read_only=True, default="")
    registration_key = serializers.CharField(source="client.registration_key", read_only=True, default="")
    platform = serializers.CharField(source="client.platform", read_only=True, default="")
    last_seen = serializers.DateTimeField(source="client.last_seen", read_only=True)
    tag_list = serializers.ListField(child=serializers.CharField(), source="tag_list", read_only=True)

    class Meta:
        model = DeviceMonitoringInfo
        fields = "__all__"


class DeviceMonitoringInfoListSerializer(serializers.ModelSerializer):
    hostname = serializers.CharField(source="client.hostname", read_only=True, default="")
    registration_key = serializers.CharField(source="client.registration_key", read_only=True, default="")
    platform = serializers.CharField(source="client.platform", read_only=True, default="")
    last_seen = serializers.DateTimeField(source="client.last_seen", read_only=True)
    tag_list = serializers.ListField(child=serializers.CharField(), source="tag_list", read_only=True)
    latest_cpu = serializers.SerializerMethodField()
    latest_ram = serializers.SerializerMethodField()
    latest_disk = serializers.SerializerMethodField()

    class Meta:
        model = DeviceMonitoringInfo
        fields = [
            "id", "client", "hostname", "registration_key", "platform",
            "monitoring_status", "health_level", "health_score",
            "ip_address", "device_type", "department", "location_name",
            "current_user", "agent_version", "last_heartbeat",
            "heartbeat_count", "last_seen", "tag_list",
            "latest_cpu", "latest_ram", "latest_disk",
            "created_at", "updated_at",
        ]

    def get_latest_cpu(self, obj):
        hb = DeviceHeartbeat.objects.filter(client=obj.client).order_by("-created_at").first()
        return hb.cpu_usage_pct if hb else 0

    def get_latest_ram(self, obj):
        hb = DeviceHeartbeat.objects.filter(client=obj.client).order_by("-created_at").first()
        return hb.ram_usage_pct if hb else 0

    def get_latest_disk(self, obj):
        hb = DeviceHeartbeat.objects.filter(client=obj.client).order_by("-created_at").first()
        return hb.disk_usage_pct if hb else 0


class HardwareInventorySerializer(serializers.ModelSerializer):
    hostname = serializers.CharField(source="client.hostname", read_only=True, default="")

    class Meta:
        model = HardwareInventory
        fields = "__all__"


class SoftwareInventorySerializer(serializers.ModelSerializer):
    hostname = serializers.CharField(source="client.hostname", read_only=True, default="")

    class Meta:
        model = SoftwareInventory
        fields = "__all__"


class DeviceHeartbeatSerializer(serializers.ModelSerializer):
    hostname = serializers.CharField(source="client.hostname", read_only=True, default="")

    class Meta:
        model = DeviceHeartbeat
        fields = "__all__"


class DeviceMetricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceMetrics
        fields = "__all__"


class DeviceHistorySerializer(serializers.ModelSerializer):
    hostname = serializers.CharField(source="client.hostname", read_only=True, default="")
    registration_key = serializers.CharField(source="client.registration_key", read_only=True, default="")

    class Meta:
        model = DeviceHistory
        fields = "__all__"


class DeviceAlertSerializer(serializers.ModelSerializer):
    hostname = serializers.CharField(source="client.hostname", read_only=True, default="")
    registration_key = serializers.CharField(source="client.registration_key", read_only=True, default="")

    class Meta:
        model = DeviceAlert
        fields = "__all__"


class AgentVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentVersion
        fields = "__all__"


class AgentSecretSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentSecret
        fields = ["id", "client", "agent_id", "device_fingerprint", "is_active", "last_used", "created_at"]
        read_only_fields = ["agent_id", "secret_key"]


class MonitorRegisterSerializer(serializers.Serializer):
    agent_id = serializers.CharField(max_length=128)
    fingerprint = serializers.CharField(max_length=64, required=False, default="")
    hostname = serializers.CharField(max_length=255, required=False, default="")
    platform = serializers.CharField(max_length=128, required=False, default="")
    agent_version = serializers.CharField(max_length=32, required=False, default="")


class MonitorHeartbeatRequestSerializer(serializers.Serializer):
    cpu_usage_pct = serializers.FloatField(min_value=0, max_value=100, default=0)
    ram_usage_pct = serializers.FloatField(min_value=0, max_value=100, default=0)
    disk_usage_pct = serializers.FloatField(min_value=0, max_value=100, default=0)
    disk_free_gb = serializers.FloatField(default=0)
    disk_total_gb = serializers.FloatField(default=0)
    network_connected = serializers.BooleanField(default=True)
    uptime_seconds = serializers.IntegerField(default=0)
    load_average = serializers.FloatField(default=0)
    agent_version = serializers.CharField(required=False, default="")
    hostname = serializers.CharField(required=False, default="")
    current_user = serializers.CharField(required=False, default="")
    ip_address = serializers.IPAddressField(required=False, allow_null=True)
    fingerprint = serializers.CharField(required=False, default="")


class MonitorScanSubmitSerializer(serializers.Serializer):
    hardware = serializers.JSONField(required=False, default=dict)
    software = serializers.JSONField(required=False, default=list)
    hostname = serializers.CharField(required=False, default="")
    fingerprint = serializers.CharField(required=False, default="")


class MonitorStatusUpdateSerializer(serializers.Serializer):
    monitoring_status = serializers.ChoiceField(choices=DeviceMonitoringInfo.STATUS_CHOICES)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class AlertActionSerializer(serializers.Serializer):
    ACTION_CHOICES = [("acknowledge", "Acknowledge"), ("resolve", "Resolve"), ("dismiss", "Dismiss")]
    action = serializers.ChoiceField(choices=ACTION_CHOICES)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class UnauthorizedSoftwareSerializer(serializers.Serializer):
    software_list = serializers.ListField(child=serializers.CharField())
