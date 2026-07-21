import logging
import hashlib
import secrets
from datetime import timedelta
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone as tz
from django.db import models
from django.db.models import Count, Avg, F, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from scanner_api.models import Client, Setting, ActivityLog
from .models import (
    DeviceMonitoringInfo, HardwareInventory, SoftwareInventory,
    DeviceHeartbeat, DeviceMetrics, DeviceHistory, DeviceAlert,
    AgentVersion, AgentSecret,
)
from .serializers import (
    DeviceMonitoringInfoSerializer, DeviceMonitoringInfoListSerializer,
    HardwareInventorySerializer, SoftwareInventorySerializer,
    DeviceHeartbeatSerializer, DeviceMetricsSerializer,
    DeviceHistorySerializer, DeviceAlertSerializer,
    AgentVersionSerializer, AgentSecretSerializer,
    MonitorRegisterSerializer, MonitorHeartbeatRequestSerializer,
    MonitorScanSubmitSerializer, MonitorStatusUpdateSerializer,
    AlertActionSerializer, UnauthorizedSoftwareSerializer,
)
from .security import (
    authenticate_agent, generate_api_secret, get_client_ip,
    validate_fingerprint_match, RateLimiter,
)
from .health import calculate_health_score
from .change_detection import (
    detect_hardware_changes, detect_software_changes,
    detect_antivirus_status, component_fingerprint,
)
from .alerts import (
    check_and_create_alerts, check_offline_alerts,
    acknowledge_alert, resolve_alert, dismiss_alert, get_active_alert_count,
)
from .event_bus import Event, EventType, event_bus

logger = logging.getLogger("monitoring")


def _record_history(client, category, event_type, description="", severity="info",
                    previous=None, new=None, source="system"):
    """Create a DeviceHistory record."""
    DeviceHistory.objects.create(
        client=client, category=category, event_type=event_type,
        description=description, severity=severity,
        previous_value=previous or {}, new_value=new or {},
        source=source,
    )


def _get_or_create_monitoring_info(client):
    """Get or create DeviceMonitoringInfo for a client."""
    info, created = DeviceMonitoringInfo.objects.get_or_create(
        client=client,
        defaults={"monitoring_status": "pending"},
    )
    return info


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT-FACING VIEWS
# ═══════════════════════════════════════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class AgentRegisterView(APIView):
    """Agent registers and receives an API secret for authenticated communication."""

    def post(self, request):
        serializer = MonitorRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        agent_id = data["agent_id"]
        fingerprint = data.get("fingerprint", "")
        hostname = data.get("hostname", "")
        platform_name = data.get("platform", "")
        agent_version = data.get("agent_version", "")

        existing_secret = AgentSecret.objects.filter(agent_id=agent_id).first()
        if existing_secret:
            return Response({
                "status": "ok",
                "secret_key": existing_secret.secret_key,
                "agent_id": agent_id,
                "monitoring_status": existing_secret.client.monitoring_info.monitoring_status
                if hasattr(existing_secret.client, "monitoring_info") else "unknown",
            })

        client = Client.objects.filter(device_fingerprint=fingerprint, deleted=False).first()
        if not client:
            client = Client.objects.filter(hostname=hostname, deleted=False).first()
        if not client:
            client = Client.objects.create(
                registration_key=secrets.token_hex(4).upper()[:8],
                hostname=hostname, platform=platform_name,
                client_version=agent_version,
                device_fingerprint=fingerprint,
                status="pending", approved=False,
                last_seen=tz.now(), last_ip=get_client_ip(request),
            )
            ActivityLog.objects.create(
                action="register",
                details=f"Monitoring agent registered new client {hostname}",
            )

        secret = generate_api_secret()
        agent_secret = AgentSecret.objects.create(
            client=client, agent_id=agent_id,
            secret_key=secret, device_fingerprint=fingerprint,
        )

        info = _get_or_create_monitoring_info(client)
        info.agent_version = agent_version
        info.ip_address = get_client_ip(request)
        info.save(update_fields=["agent_version", "ip_address", "updated_at"])

        _record_history(client, "registration", "agent_registered",
                        f"Monitoring agent registered with ID {agent_id}")

        event_bus.publish(Event(
            event_type=EventType.DEVICE_REGISTERED,
            client_id=client.id,
            client_key=str(client.key),
            hostname=client.hostname,
            severity="info",
            title=f"Agent registered: {agent_id}",
            description=f"Monitoring agent registered with ID {agent_id}",
            data={"agent_id": agent_id},
            source="agent",
        ))

        return Response({
            "status": "ok",
            "secret_key": secret,
            "agent_id": agent_id,
            "client_key": client.registration_key,
        }, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name="dispatch")
class AgentHeartbeatView(APIView):
    """Enhanced heartbeat with CPU/RAM/disk metrics."""

    def post(self, request):
        agent_secret, err = authenticate_agent(request)
        if not agent_secret:
            return Response({"status": "error", "message": err},
                            status=status.HTTP_401_UNAUTHORIZED)

        client = agent_secret.client

        if not RateLimiter.check(f"hb:{client.registration_key}", max_requests=60, window_seconds=60):
            return Response({"status": "error", "message": "Rate limit exceeded"},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)

        serializer = MonitorHeartbeatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        heartbeat = DeviceHeartbeat.objects.create(
            client=client,
            cpu_usage_pct=data.get("cpu_usage_pct", 0),
            ram_usage_pct=data.get("ram_usage_pct", 0),
            disk_usage_pct=data.get("disk_usage_pct", 0),
            disk_free_gb=data.get("disk_free_gb", 0),
            disk_total_gb=data.get("disk_total_gb", 0),
            network_connected=data.get("network_connected", True),
            uptime_seconds=data.get("uptime_seconds", 0),
            load_average=data.get("load_average", 0),
            agent_version=data.get("agent_version", ""),
            ip_address=data.get("ip_address") or get_client_ip(request),
        )

        client.status = "online"
        client.last_seen = tz.now()
        client.last_ip = get_client_ip(request)
        if data.get("agent_version"):
            client.client_version = data["agent_version"]
        client.save(update_fields=["status", "last_seen", "last_ip", "client_version"])

        info = _get_or_create_monitoring_info(client)
        prev_health = info.health_score
        prev_level = info.health_level

        sw_data = list(SoftwareInventory.objects.filter(
            client=client, is_present=True
        ).values("name", "version", "publisher")[:200])

        score, level = calculate_health_score(
            {
                "cpu_usage_pct": data.get("cpu_usage_pct", 0),
                "ram_usage_pct": data.get("ram_usage_pct", 0),
                "disk_usage_pct": data.get("disk_usage_pct", 0),
                "network_connected": data.get("network_connected", True),
            },
            sw_data,
        )

        info.health_score = score
        info.health_level = level
        info.last_heartbeat = tz.now()
        info.heartbeat_count = F("heartbeat_count") + 1
        info.ip_address = data.get("ip_address") or get_client_ip(request)
        info.monitoring_status = "online"
        if data.get("agent_version"):
            info.agent_version = data["agent_version"]
        if data.get("hostname"):
            client.hostname = data["hostname"]
            client.save(update_fields=["hostname"])
        if data.get("current_user"):
            info.current_user = data["current_user"]
        info.save(update_fields=[
            "health_score", "health_level", "last_heartbeat",
            "heartbeat_count", "ip_address", "monitoring_status",
            "agent_version", "current_user", "updated_at",
        ])

        if prev_level != level and prev_level != "unknown":
            severity = "warning" if level == "critical" else "info"
            event_bus.publish(Event(
                event_type=EventType.HEALTH_LEVEL_CHANGED,
                client_id=client.id,
                client_key=str(client.key),
                hostname=client.hostname,
                severity=severity,
                title=f"Health level changed: {prev_level} → {level}",
                description=f"Health level changed: {prev_level} → {level} (score: {score})",
                data={
                    "previous_level": prev_level,
                    "previous_score": prev_health,
                    "new_level": level,
                    "new_score": score,
                },
                source="heartbeat",
            ))

        check_and_create_alerts(client, heartbeat, sw_data)

        return Response({
            "status": "ok",
            "health_score": score,
            "health_level": level,
            "pending_commands": [],
        })


@method_decorator(csrf_exempt, name="dispatch")
class AgentInventoryView(APIView):
    """Submit hardware and software inventory snapshot."""

    def post(self, request):
        agent_secret, err = authenticate_agent(request)
        if not agent_secret:
            return Response({"status": "error", "message": err},
                            status=status.HTTP_401_UNAUTHORIZED)

        client = agent_secret.client

        serializer = MonitorScanSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        hw_data = data.get("hardware", {})
        sw_data = data.get("software", [])

        scan_batch_id = tz.now().timestamp()

        prev_hw = list(HardwareInventory.objects.filter(client=client).order_by("-created_at").values(
            "component_type", "component_data"
        )[:50])
        prev_sw = list(SoftwareInventory.objects.filter(
            client=client, is_present=True
        ).order_by("-created_at").values("name", "version", "publisher")[:500])

        hw_records = []
        for comp_type in ["cpu", "ram", "storage", "gpu", "motherboard", "network"]:
            comp_data = hw_data.get(comp_type, {})
            if comp_data:
                fp = hashlib.md5(str(sorted(comp_data.items())).encode()).hexdigest()[:16]
                rec = HardwareInventory.objects.create(
                    client=client, component_type=comp_type,
                    component_data=comp_data, fingerprint=fp,
                    scan_id=scan_batch_id,
                )
                hw_records.append({"component_type": comp_type, "component_data": comp_data})

        unauthorized_sw = Setting.get("unauthorized_software_list", "").split(",")
        unauthorized_sw = [s.strip().lower() for s in unauthorized_sw if s.strip()]

        sw_changes = detect_software_changes(client, prev_sw, sw_data, unauthorized_sw)
        hw_changes = detect_hardware_changes(client, prev_hw, hw_records)

        SoftwareInventory.objects.filter(client=client, is_present=True).update(is_present=False)

        for sw in sw_data:
            if isinstance(sw, dict):
                name = sw.get("name", "")
                ver = sw.get("version", "")
                pub = sw.get("publisher", "")
            else:
                name = str(sw)
                ver = ""
                pub = ""
            SoftwareInventory.objects.create(
                client=client, name=name, version=ver, publisher=pub,
                raw_data=sw if isinstance(sw, dict) else {},
                scan_id=scan_batch_id, is_present=True,
            )

        _CHANGE_TYPE_TO_EVENT = {
            "added": EventType.HW_COMPONENT_ADDED,
            "removed": EventType.HW_COMPONENT_REMOVED,
            "modified": EventType.HW_COMPONENT_MODIFIED,
        }
        _SW_CHANGE_TYPE_TO_EVENT = {
            "added": EventType.SW_INSTALLED,
            "removed": EventType.SW_REMOVED,
            "version_changed": EventType.SW_VERSION_CHANGED,
            "unauthorized": EventType.SW_UNAUTHORIZED,
            "antivirus_removed": EventType.SW_ANTIVIRUS_REMOVED,
        }

        for change in hw_changes:
            event_type = _CHANGE_TYPE_TO_EVENT.get(change["change_type"])
            if event_type:
                event_bus.publish(Event(
                    event_type=event_type,
                    client_id=client.id,
                    client_key=str(client.key),
                    hostname=client.hostname,
                    severity=change["severity"],
                    title=change["description"],
                    description=change["description"],
                    data={
                        "change_type": change["change_type"],
                        "component_type": change.get("component_type", ""),
                        "previous": change.get("previous"),
                        "new": change.get("new"),
                    },
                    source="inventory_scan",
                ))

        for change in sw_changes:
            event_type = _SW_CHANGE_TYPE_TO_EVENT.get(change["change_type"])
            if event_type:
                event_bus.publish(Event(
                    event_type=event_type,
                    client_id=client.id,
                    client_key=str(client.key),
                    hostname=client.hostname,
                    severity=change["severity"],
                    title=change["description"],
                    description=change["description"],
                    data={
                        "change_type": change["change_type"],
                        "previous": change.get("previous"),
                        "new": change.get("new"),
                    },
                    source="inventory_scan",
                ))

        client.status = "online"
        client.last_seen = tz.now()
        client.save(update_fields=["status", "last_seen"])

        return Response({
            "status": "ok",
            "hw_changes_detected": len(hw_changes),
            "sw_changes_detected": len(sw_changes),
            "changes": [
                {"type": c["change_type"], "desc": c["description"], "severity": c["severity"]}
                for c in hw_changes + sw_changes
            ],
        })


@method_decorator(csrf_exempt, name="dispatch")
class AgentVersionCheckView(APIView):
    """Check for agent updates."""

    def get(self, request):
        current = request.query_params.get("v", "")
        latest = AgentVersion.objects.filter(is_active=True).order_by("-created_at").first()

        if not latest:
            return Response({"status": "ok", "update_available": False})

        mandatory = latest.is_mandatory
        update_available = current != latest.version if current else False

        return Response({
            "status": "ok",
            "update_available": update_available,
            "latest_version": latest.version,
            "is_mandatory": mandatory,
            "release_notes": latest.release_notes,
            "download_url": latest.download_url,
            "file_hash": latest.file_hash,
            "min_python_version": latest.min_python_version,
        })


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN-FACING VIEWS
# ═══════════════════════════════════════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class MonitorDashboardView(APIView):
    """Aggregate monitoring dashboard stats."""

    def get(self, request):
        infos = DeviceMonitoringInfo.objects.select_related("client").filter(
            client__deleted=False
        )

        total = infos.count()
        online = infos.filter(monitoring_status="online").count()
        offline = infos.filter(monitoring_status="offline").count()
        pending = infos.filter(monitoring_status="pending").count()
        blocked = infos.filter(monitoring_status="blocked").count()
        maintenance = infos.filter(monitoring_status="maintenance").count()

        avg_health = infos.exclude(health_score=0).aggregate(
            avg=Avg("health_score")
        )["avg"] or 0

        alerts_active = DeviceAlert.objects.filter(status="active").count()
        alerts_critical = DeviceAlert.objects.filter(status="active", severity="critical").count()
        alerts_warning = DeviceAlert.objects.filter(status="active", severity="warning").count()

        status_dist = dict(
            infos.values_list("monitoring_status").annotate(
                c=Count("id")
            ).values_list("monitoring_status", "c")
        )

        platform_dist = list(
            Client.objects.filter(deleted=False, monitoring_info__isnull=False)
            .values(name=models.F("platform"))
            .annotate(count=Count("id")).order_by("-count")[:10]
        )

        health_dist = dict(
            infos.values_list("health_level").annotate(
                c=Count("id")
            ).values_list("health_level", "c")
        )

        now = tz.now()
        recent_alerts = DeviceAlertSerializer(
            DeviceAlert.objects.order_by("-created_at")[:10], many=True
        ).data

        recent_changes = DeviceHistorySerializer(
            DeviceHistory.objects.order_by("-timestamp")[:10], many=True
        ).data

        cpu_trend = _get_trend_data("cpu", hours=24)
        ram_trend = _get_trend_data("ram", hours=24)
        disk_trend = _get_trend_data("disk", hours=24)
        health_trend = _get_health_trend(days=7)

        return Response({
            "total_devices": total,
            "online_count": online,
            "offline_count": offline,
            "pending_count": pending,
            "blocked_count": blocked,
            "maintenance_count": maintenance,
            "avg_health_score": round(avg_health, 1),
            "alerts_active": alerts_active,
            "alerts_critical": alerts_critical,
            "alerts_warning": alerts_warning,
            "status_distribution": status_dist,
            "platform_distribution": platform_dist,
            "health_distribution": health_dist,
            "recent_alerts": recent_alerts,
            "recent_changes": recent_changes,
            "cpu_trend": cpu_trend,
            "ram_trend": ram_trend,
            "disk_trend": disk_trend,
            "health_trend": health_trend,
        })


def _get_trend_data(metric_type, hours=24):
    """Get hourly trend data for CPU/RAM/Disk."""
    now = tz.now()
    results = []
    for i in range(hours):
        start = now - timedelta(hours=hours - i)
        end = now - timedelta(hours=hours - i - 1)
        hbs = DeviceHeartbeat.objects.filter(created_at__gte=start, created_at__lt=end)
        if metric_type == "cpu":
            avg = hbs.aggregate(avg=Avg("cpu_usage_pct"))["avg"]
        elif metric_type == "ram":
            avg = hbs.aggregate(avg=Avg("ram_usage_pct"))["avg"]
        else:
            avg = hbs.aggregate(avg=Avg("disk_usage_pct"))["avg"]
        results.append({
            "timestamp": start.isoformat(),
            "avg": round(avg, 1) if avg else 0,
        })
    return results


def _get_health_trend(days=7):
    """Get daily health score trend."""
    now = tz.now()
    results = []
    for i in range(days):
        start = (now - timedelta(days=days - i)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        avg = DeviceMetrics.objects.filter(
            period_start__gte=start, period_start__lt=end
        ).aggregate(avg=Avg("health_score"))["avg"]
        if not avg:
            avg = DeviceMonitoringInfo.objects.filter(
                last_heartbeat__gte=start, last_heartbeat__lt=end
            ).exclude(health_score=0).aggregate(avg=Avg("health_score"))["avg"]
        results.append({
            "date": start.strftime("%Y-%m-%d"),
            "avg": round(avg, 1) if avg else 0,
        })
    return results


@method_decorator(csrf_exempt, name="dispatch")
class MonitorDeviceListView(APIView):
    """List all monitored devices."""

    def get(self, request):
        qs = DeviceMonitoringInfo.objects.select_related("client").filter(
            client__deleted=False
        )

        search = request.query_params.get("search", "").strip()
        monitor_status = request.query_params.get("status", "").strip()
        health = request.query_params.get("health", "").strip()
        platform = request.query_params.get("platform", "").strip()
        device_type = request.query_params.get("device_type", "").strip()

        if search:
            qs = qs.filter(
                Q(client__hostname__icontains=search) |
                Q(client__registration_key__icontains=search) |
                Q(ip_address__icontains=search) |
                Q(current_user__icontains=search)
            )
        if monitor_status:
            qs = qs.filter(monitoring_status=monitor_status)
        if health:
            qs = qs.filter(health_level=health)
        if platform:
            qs = qs.filter(client__platform__icontains=platform)
        if device_type:
            qs = qs.filter(device_type=device_type)

        limit = int(request.query_params.get("limit", 200))
        return Response(DeviceMonitoringInfoListSerializer(qs[:limit], many=True).data)


@method_decorator(csrf_exempt, name="dispatch")
class MonitorDeviceDetailView(APIView):
    """Device detail with full info."""

    def get(self, request, key):
        try:
            info = DeviceMonitoringInfo.objects.select_related("client").get(id=key)
        except DeviceMonitoringInfo.DoesNotExist:
            return Response({"status": "error", "message": "Device not found"},
                            status=status.HTTP_404_NOT_FOUND)

        data = DeviceMonitoringInfoSerializer(info).data

        latest_hb = DeviceHeartbeat.objects.filter(client=info.client).order_by("-created_at").first()
        data["latest_heartbeat"] = DeviceHeartbeatSerializer(latest_hb).data if latest_hb else None

        data["recent_alerts"] = DeviceAlertSerializer(
            DeviceAlert.objects.filter(client=info.client).order_by("-created_at")[:5], many=True
        ).data

        data["recent_history"] = DeviceHistorySerializer(
            DeviceHistory.objects.filter(client=info.client).order_by("-timestamp")[:10], many=True
        ).data

        data["hardware"] = HardwareInventorySerializer(
            HardwareInventory.objects.filter(client=info.client).order_by("-created_at")[:20], many=True
        ).data

        data["software"] = SoftwareInventorySerializer(
            SoftwareInventory.objects.filter(client=info.client, is_present=True).order_by("name")[:100], many=True
        ).data

        return Response(data)

    def put(self, request, key):
        try:
            info = DeviceMonitoringInfo.objects.get(id=key)
        except DeviceMonitoringInfo.DoesNotExist:
            return Response({"status": "error", "message": "Device not found"},
                            status=status.HTTP_404_NOT_FOUND)

        serializer = MonitorStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        prev_status = info.monitoring_status
        new_status = data["monitoring_status"]
        notes = data.get("notes", "")

        info.monitoring_status = new_status
        info.save(update_fields=["monitoring_status", "updated_at"])

        if prev_status != new_status:
            _record_history(info.client, "status_change", "status_changed",
                            f"Status changed: {prev_status} → {new_status}",
                            previous={"status": prev_status}, new={"status": new_status})
            ActivityLog.objects.create(
                action="update",
                details=f"Device {info.client.hostname} status: {prev_status} → {new_status}",
            )
            event_bus.publish(Event(
                event_type=EventType.DEVICE_STATUS_CHANGED,
                client_id=info.client.id,
                client_key=str(info.client.key),
                hostname=info.client.hostname,
                severity="info",
                title=f"Status changed: {prev_status} → {new_status}",
                description=f"Status changed: {prev_status} → {new_status}",
                data={"previous_status": prev_status, "new_status": new_status},
                source="admin",
            ))

        return Response({"status": "ok"})


@method_decorator(csrf_exempt, name="dispatch")
class MonitorDeviceMetricsView(APIView):
    """Time-series metrics for charts."""

    def get(self, request, key):
        try:
            info = DeviceMonitoringInfo.objects.get(id=key)
        except DeviceMonitoringInfo.DoesNotExist:
            return Response({"status": "error", "message": "Device not found"},
                            status=status.HTTP_404_NOT_FOUND)

        hours = int(request.query_params.get("hours", 24))
        now = tz.now()
        since = now - timedelta(hours=hours)

        heartbeats = DeviceHeartbeat.objects.filter(
            client=info.client, created_at__gte=since
        ).order_by("created_at")

        data_points = []
        for hb in heartbeats:
            data_points.append({
                "timestamp": hb.created_at.isoformat(),
                "cpu": hb.cpu_usage_pct,
                "ram": hb.ram_usage_pct,
                "disk": hb.disk_usage_pct,
                "network": hb.network_connected,
            })

        return Response({
            "device_id": str(key),
            "period_hours": hours,
            "data_points": data_points,
        })


@method_decorator(csrf_exempt, name="dispatch")
class MonitorDeviceHistoryView(APIView):
    """Immutable audit trail for device."""

    def get(self, request, key):
        try:
            info = DeviceMonitoringInfo.objects.get(id=key)
        except DeviceMonitoringInfo.DoesNotExist:
            return Response({"status": "error", "message": "Device not found"},
                            status=status.HTTP_404_NOT_FOUND)

        limit = int(request.query_params.get("limit", 100))
        category = request.query_params.get("category", "").strip()

        qs = DeviceHistory.objects.filter(client=info.client)
        if category:
            qs = qs.filter(category=category)

        total = qs.count()
        entries = qs[:limit]
        return Response({
            "total": total,
            "entries": DeviceHistorySerializer(entries, many=True).data,
        })


@method_decorator(csrf_exempt, name="dispatch")
class MonitorDeviceAlertsView(APIView):
    """Alerts for a specific device."""

    def get(self, request, key):
        try:
            info = DeviceMonitoringInfo.objects.get(id=key)
        except DeviceMonitoringInfo.DoesNotExist:
            return Response({"status": "error", "message": "Device not found"},
                            status=status.HTTP_404_NOT_FOUND)

        qs = DeviceAlert.objects.filter(client=info.client).order_by("-created_at")
        alert_status = request.query_params.get("status", "").strip()
        if alert_status:
            qs = qs.filter(status=alert_status)

        limit = int(request.query_params.get("limit", 50))
        return Response(DeviceAlertSerializer(qs[:limit], many=True).data)


@method_decorator(csrf_exempt, name="dispatch")
class MonitorHardwareView(APIView):
    """Hardware inventory history."""

    def get(self, request, key):
        try:
            info = DeviceMonitoringInfo.objects.get(id=key)
        except DeviceMonitoringInfo.DoesNotExist:
            return Response({"status": "error", "message": "Device not found"},
                            status=status.HTTP_404_NOT_FOUND)

        comp_type = request.query_params.get("type", "").strip()
        qs = HardwareInventory.objects.filter(client=info.client)
        if comp_type:
            qs = qs.filter(component_type=comp_type)

        limit = int(request.query_params.get("limit", 50))
        return Response(HardwareInventorySerializer(qs[:limit], many=True).data)


@method_decorator(csrf_exempt, name="dispatch")
class MonitorSoftwareView(APIView):
    """Software inventory."""

    def get(self, request, key):
        try:
            info = DeviceMonitoringInfo.objects.get(id=key)
        except DeviceMonitoringInfo.DoesNotExist:
            return Response({"status": "error", "message": "Device not found"},
                            status=status.HTTP_404_NOT_FOUND)

        category = request.query_params.get("category", "").strip()
        qs = SoftwareInventory.objects.filter(client=info.client, is_present=True)
        if category:
            qs = qs.filter(category=category)

        limit = int(request.query_params.get("limit", 200))
        return Response(SoftwareInventorySerializer(qs[:limit], many=True).data)


@method_decorator(csrf_exempt, name="dispatch")
class MonitorHeartbeatHistoryView(APIView):
    """Heartbeat history."""

    def get(self, request, key):
        try:
            info = DeviceMonitoringInfo.objects.get(id=key)
        except DeviceMonitoringInfo.DoesNotExist:
            return Response({"status": "error", "message": "Device not found"},
                            status=status.HTTP_404_NOT_FOUND)

        limit = int(request.query_params.get("limit", 100))
        hbs = DeviceHeartbeat.objects.filter(client=info.client).order_by("-created_at")[:limit]
        return Response(DeviceHeartbeatSerializer(hbs, many=True).data)


@method_decorator(csrf_exempt, name="dispatch")
class MonitorDeviceApproveView(APIView):
    """Approve a device for monitoring."""

    def post(self, request, key):
        try:
            info = DeviceMonitoringInfo.objects.get(id=key)
        except DeviceMonitoringInfo.DoesNotExist:
            return Response({"status": "error", "message": "Device not found"},
                            status=status.HTTP_404_NOT_FOUND)

        info.monitoring_status = "online"
        info.save(update_fields=["monitoring_status", "updated_at"])

        client = info.client
        client.approved = True
        client.status = "online"
        client.save(update_fields=["approved", "status"])

        _record_history(client, "admin_action", "device_approved",
                        f"Device approved by admin")
        ActivityLog.objects.create(action="approve", details=f"Device {client.hostname} approved for monitoring")

        event_bus.publish(Event(
            event_type=EventType.DEVICE_APPROVED,
            client_id=client.id,
            client_key=str(client.key),
            hostname=client.hostname,
            severity="info",
            title=f"Device approved",
            description=f"Device {client.hostname} approved for monitoring",
            source="admin",
        ))

        return Response({"status": "ok"})


@method_decorator(csrf_exempt, name="dispatch")
class MonitorDeviceBlockView(APIView):
    """Block a device."""

    def post(self, request, key):
        try:
            info = DeviceMonitoringInfo.objects.get(id=key)
        except DeviceMonitoringInfo.DoesNotExist:
            return Response({"status": "error", "message": "Device not found"},
                            status=status.HTTP_404_NOT_FOUND)

        info.monitoring_status = "blocked"
        info.save(update_fields=["monitoring_status", "updated_at"])

        AgentSecret.objects.filter(client=info.client).update(is_active=False)

        _record_history(info.client, "security_event", "device_blocked",
                        "Device blocked by admin", severity="warning")

        event_bus.publish(Event(
            event_type=EventType.DEVICE_BLOCKED,
            client_id=info.client.id,
            client_key=str(info.client.key),
            hostname=info.client.hostname,
            severity="warning",
            title="Device blocked",
            description=f"Device {info.client.hostname} blocked by admin",
            source="admin",
        ))

        return Response({"status": "ok"})


@method_decorator(csrf_exempt, name="dispatch")
class MonitorAlertListView(APIView):
    """All alerts across fleet."""

    def get(self, request):
        qs = DeviceAlert.objects.select_related("client").all()

        severity = request.query_params.get("severity", "").strip()
        alert_status = request.query_params.get("status", "").strip()
        search = request.query_params.get("search", "").strip()

        if severity:
            qs = qs.filter(severity=severity)
        if alert_status:
            qs = qs.filter(status=alert_status)
        if search:
            qs = qs.filter(
                Q(title__icontains=search) |
                Q(client__hostname__icontains=search)
            )

        limit = int(request.query_params.get("limit", 100))
        return Response(DeviceAlertSerializer(qs[:limit], many=True).data)


@method_decorator(csrf_exempt, name="dispatch")
class MonitorAlertActionView(APIView):
    """Acknowledge, resolve, or dismiss an alert."""

    def post(self, request, key):
        serializer = AlertActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        action = data["action"]
        if action == "acknowledge":
            ok = acknowledge_alert(key)
        elif action == "resolve":
            ok = resolve_alert(key)
        elif action == "dismiss":
            ok = dismiss_alert(key)
        else:
            return Response({"status": "error", "message": "Invalid action"},
                            status=status.HTTP_400_BAD_REQUEST)

        if not ok:
            return Response({"status": "error", "message": "Alert not found or invalid state"},
                            status=status.HTTP_404_NOT_FOUND)

        return Response({"status": "ok"})


@method_decorator(csrf_exempt, name="dispatch")
class MonitorBulkActionView(APIView):
    """Bulk status changes on devices."""

    def post(self, request):
        action = request.data.get("action", "")
        ids = request.data.get("ids", [])
        if not ids:
            return Response({"status": "error", "message": "No device IDs provided"},
                            status=status.HTTP_400_BAD_REQUEST)

        infos = DeviceMonitoringInfo.objects.filter(id__in=ids)
        count = 0

        if action == "approve":
            for info in infos:
                info.monitoring_status = "online"
                info.save(update_fields=["monitoring_status", "updated_at"])
                info.client.approved = True
                info.client.status = "online"
                info.client.save(update_fields=["approved", "status"])
                count += 1
        elif action == "block":
            for info in infos:
                info.monitoring_status = "blocked"
                info.save(update_fields=["monitoring_status", "updated_at"])
                AgentSecret.objects.filter(client=info.client).update(is_active=False)
                count += 1
        elif action == "maintenance":
            count = infos.update(monitoring_status="maintenance")
        elif action == "inactive":
            count = infos.update(monitoring_status="inactive")

        return Response({"status": "ok", "count": count})


@method_decorator(csrf_exempt, name="dispatch")
class MonitorTrendsView(APIView):
    """Fleet-wide trend data for charts."""

    def get(self, request):
        hours = int(request.query_params.get("hours", 24))
        days = int(request.query_params.get("days", 7))

        cpu_trend = _get_trend_data("cpu", hours=hours)
        ram_trend = _get_trend_data("ram", hours=hours)
        disk_trend = _get_trend_data("disk", hours=hours)
        health_trend = _get_health_trend(days=days)

        return Response({
            "cpu_trend": cpu_trend,
            "ram_trend": ram_trend,
            "disk_trend": disk_trend,
            "health_trend": health_trend,
        })


@method_decorator(csrf_exempt, name="dispatch")
class MonitorAgentVersionsView(APIView):
    """Manage agent versions."""

    def get(self, request):
        versions = AgentVersion.objects.all()
        return Response(AgentVersionSerializer(versions, many=True).data)

    def post(self, request):
        serializer = AgentVersionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name="dispatch")
class MonitorUnauthorizedSwView(APIView):
    """Manage unauthorized software blocklist."""

    def get(self, request):
        raw = Setting.get("unauthorized_software_list", "")
        items = [s.strip() for s in raw.split(",") if s.strip()]
        return Response({"software_list": items})

    def put(self, request):
        serializer = UnauthorizedSoftwareSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        items = serializer.validated_data["software_list"]
        Setting.set("unauthorized_software_list", ", ".join(items))
        return Response({"status": "ok", "software_list": items})
