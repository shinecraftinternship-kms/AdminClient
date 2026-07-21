"""Alert generation engine for the Monitoring module."""

import logging
from datetime import timedelta
from django.utils import timezone
from scanner_api.models import Setting

logger = logging.getLogger("monitoring")


def check_and_create_alerts(client, heartbeat, sw_data=None) -> list:
    """Run all alert checks against latest heartbeat data.

    Returns list of newly created DeviceAlert objects.
    """
    from .models import DeviceAlert

    new_alerts = []

    alert = _check_high_cpu(client, heartbeat.cpu_usage_pct)
    if alert:
        new_alerts.append(alert)

    alert = _check_low_disk(client, heartbeat.disk_usage_pct, heartbeat.disk_free_gb)
    if alert:
        new_alerts.append(alert)

    alert = _check_high_ram(client, heartbeat.ram_usage_pct)
    if alert:
        new_alerts.append(alert)

    return new_alerts


def check_offline_alerts(client) -> dict:
    """Check if device should trigger offline alert.

    Returns dict with action and optional alert.
    """
    from .models import DeviceAlert, DeviceMonitoringInfo
    from django.utils import timezone as tz

    threshold_warning = int(Setting.get("monitoring_warning_seconds", "300"))
    threshold_offline = int(Setting.get("monitoring_offline_seconds", "900"))
    threshold_critical = int(Setting.get("monitoring_critical_seconds", "1800"))

    try:
        info = DeviceMonitoringInfo.objects.get(client=client)
    except DeviceMonitoringInfo.DoesNotExist:
        return {}

    last_hb = info.last_heartbeat
    if not last_hb:
        return {}

    now = tz.now()
    elapsed = (now - last_hb).total_seconds()

    if elapsed >= threshold_critical:
        _create_or_update_alert(
            client, "device_offline", "critical",
            f"Device offline for {int(elapsed)}s",
            f"{client.hostname} has not sent a heartbeat in {int(elapsed)} seconds.",
        )
        return {"action": "critical_offline"}
    elif elapsed >= threshold_offline:
        _create_or_update_alert(
            client, "device_offline", "warning",
            f"Device appears offline",
            f"{client.hostname} has not sent a heartbeat in {int(elapsed)} seconds.",
        )
        return {"action": "offline"}
    elif elapsed >= threshold_warning:
        _create_or_update_alert(
            client, "device_offline", "info",
            f"Device heartbeat delayed",
            f"{client.hostname} heartbeat delayed by {int(elapsed)} seconds.",
        )
        return {"action": "warning"}

    _resolve_alerts_for_type(client, "device_offline")
    return {"action": "online"}


def _check_high_cpu(client, cpu_pct: float):
    from .models import DeviceAlert

    threshold = float(Setting.get("alert_cpu_threshold", "90"))
    if cpu_pct < threshold:
        return None

    existing = DeviceAlert.objects.filter(
        client=client, alert_type="high_cpu", status="active",
    ).exists()
    if existing:
        return None

    return DeviceAlert.objects.create(
        client=client,
        alert_type="high_cpu",
        severity="warning",
        title=f"High CPU usage: {cpu_pct:.1f}%",
        message=f"CPU usage on {client.hostname} is at {cpu_pct:.1f}%.",
        details={"cpu_usage_pct": cpu_pct},
    )


def _check_low_disk(client, disk_pct: float, free_gb: float):
    from .models import DeviceAlert

    pct_threshold = float(Setting.get("alert_disk_threshold", "95"))
    gb_threshold = float(Setting.get("alert_disk_free_gb", "5"))

    if disk_pct < pct_threshold and free_gb >= gb_threshold:
        return None

    existing = DeviceAlert.objects.filter(
        client=client, alert_type="disk_low", status="active",
    ).exists()
    if existing:
        return None

    severity = "critical" if disk_pct >= 98 or free_gb < 2 else "warning"
    return DeviceAlert.objects.create(
        client=client,
        alert_type="disk_low",
        severity=severity,
        title=f"Low disk space: {disk_pct:.1f}% used ({free_gb:.1f} GB free)",
        message=f"Disk on {client.hostname} is {disk_pct:.1f}% full with {free_gb:.1f} GB remaining.",
        details={"disk_usage_pct": disk_pct, "disk_free_gb": free_gb},
    )


def _check_high_ram(client, ram_pct: float):
    from .models import DeviceAlert

    threshold = float(Setting.get("alert_ram_threshold", "90"))
    if ram_pct < threshold:
        return None

    existing = DeviceAlert.objects.filter(
        client=client, alert_type="high_ram", status="active",
    ).exists()
    if existing:
        return None

    return DeviceAlert.objects.create(
        client=client,
        alert_type="high_ram",
        severity="warning",
        title=f"High RAM usage: {ram_pct:.1f}%",
        message=f"RAM usage on {client.hostname} is at {ram_pct:.1f}%.",
        details={"ram_usage_pct": ram_pct},
    )


def _create_or_update_alert(client, alert_type, severity, title, message):
    from .models import DeviceAlert

    existing = DeviceAlert.objects.filter(
        client=client, alert_type=alert_type, status="active",
    ).first()

    if existing:
        if existing.severity != severity:
            existing.severity = severity
            existing.title = title
            existing.message = message
            existing.save(update_fields=["severity", "title", "message", "updated_at"])
        return existing

    return DeviceAlert.objects.create(
        client=client, alert_type=alert_type, severity=severity,
        title=title, message=message,
    )


def _resolve_alerts_for_type(client, alert_type):
    from .models import DeviceAlert
    from django.utils import timezone as tz

    DeviceAlert.objects.filter(
        client=client, alert_type=alert_type, status="active",
    ).update(status="resolved", resolved_at=tz.now())


def acknowledge_alert(alert_id, by_user: str = "") -> bool:
    from .models import DeviceAlert
    from django.utils import timezone as tz

    try:
        alert = DeviceAlert.objects.get(id=alert_id)
    except DeviceAlert.DoesNotExist:
        return False
    if alert.status != "active":
        return False
    alert.status = "acknowledged"
    alert.acknowledged_by = by_user
    alert.acknowledged_at = tz.now()
    alert.save(update_fields=["status", "acknowledged_by", "acknowledged_at", "updated_at"])
    return True


def resolve_alert(alert_id) -> bool:
    from .models import DeviceAlert
    from django.utils import timezone as tz

    try:
        alert = DeviceAlert.objects.get(id=alert_id)
    except DeviceAlert.DoesNotExist:
        return False
    alert.status = "resolved"
    alert.resolved_at = tz.now()
    alert.save(update_fields=["status", "resolved_at", "updated_at"])
    return True


def dismiss_alert(alert_id) -> bool:
    from .models import DeviceAlert

    try:
        alert = DeviceAlert.objects.get(id=alert_id)
    except DeviceAlert.DoesNotExist:
        return False
    alert.status = "dismissed"
    alert.save(update_fields=["status", "updated_at"])
    return True


def get_active_alert_count(client=None) -> int:
    from .models import DeviceAlert

    qs = DeviceAlert.objects.filter(status="active")
    if client:
        qs = qs.filter(client=client)
    return qs.count()
