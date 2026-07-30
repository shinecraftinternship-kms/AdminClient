"""Default event bus subscribers.

These subscribers connect the EventBus to:
  1. Alert generation (DeviceAlert creation for critical/warning changes)
  2. WebSocket broadcasts (real-time dashboard updates)
  3. Intelligence notifications (in-app notifications for admin users)

They are registered once at module import time and operate on the
global `event_bus` singleton from event_bus.py.
"""

import logging
from django.utils import timezone as tz

from .event_bus import Event, EventType, event_bus

logger = logging.getLogger("monitoring")


# ── Helper: Intelligence Notifications ──────────────────────────────────────

def _notify_all_admins(title, message, severity="information", module="monitoring", source_url=""):
    """Create an in-app notification for all active admin users."""
    try:
        from django.contrib.auth.models import User
        from intelligence.notifications import create_notification
        users = User.objects.filter(is_active=True, is_superuser=True)
        for user in users:
            try:
                create_notification(
                    user=user,
                    title=title,
                    message=message,
                    severity=severity,
                    module=module,
                    source_url=source_url,
                )
            except Exception:
                continue
    except Exception as e:
        logger.warning("Failed to create admin notifications: %s", e)


# ── Alert Subscribers ────────────────────────────────────────────────────────

def _on_hardware_change_alert(event: Event):
    """Create a DeviceAlert for critical or warning hardware changes."""
    from .alerts import _create_or_update_alert
    from .models import Client

    if event.severity not in ("warning", "critical"):
        return

    try:
        client = Client.objects.get(id=event.client_id)
    except Client.DoesNotExist:
        return

    hostname = event.hostname or client.hostname
    alert_type = f"hw_{event.data.get('change_type', 'change')}"
    title = event.title or f"Hardware change: {event.description}"
    message = (
        f"Hardware change detected on {hostname}: "
        f"{event.description}"
    )

    _create_or_update_alert(
        client, alert_type, event.severity,
        title, message,
    )

    _notify_all_admins(
        title=f"Hardware Alert: {hostname}",
        message=message,
        severity=event.severity,
        module="monitoring",
        source_url=f"/client/{event.client_key}" if event.client_key else "/",
    )


def _on_software_change_alert(event: Event):
    """Create a DeviceAlert for software change events."""
    from .alerts import _create_or_update_alert
    from .models import Client

    change_type = event.data.get("change_type", "")

    # Only alert on meaningful software changes
    if change_type not in ("unauthorized", "antivirus_removed", "removed"):
        return

    if event.severity not in ("warning", "critical"):
        return

    try:
        client = Client.objects.get(id=event.client_id)
    except Client.DoesNotExist:
        return

    hostname = event.hostname or client.hostname
    alert_type = f"sw_{change_type}"
    title = event.title or f"Software change: {event.description}"
    message = (
        f"Software change on {hostname}: "
        f"{event.description}"
    )

    _create_or_update_alert(
        client, alert_type, event.severity,
        title, message,
    )

    _notify_all_admins(
        title=f"Software Alert: {hostname}",
        message=message,
        severity=event.severity,
        module="monitoring",
        source_url=f"/client/{event.client_key}" if event.client_key else "/",
    )


def _on_all_hw_sw_changes(event: Event):
    """Create notifications for all HW/SW changes including info-level."""
    is_hw_sw = (
        event.event_type.value.startswith("hw_")
        or event.event_type.value.startswith("sw_")
    )
    if not is_hw_sw:
        return

    module_name = "Hardware" if event.event_type.value.startswith("hw_") else "Software"
    _notify_all_admins(
        title=f"{module_name} Change: {event.hostname or 'Unknown'}",
        message=event.description or f"{module_name.lower()} change detected",
        severity=event.severity,
        module="monitoring",
        source_url=f"/client/{event.client_key}" if event.client_key else "/",
    )


def _on_device_offline_alert(event: Event):
    """Create a DeviceAlert when a device goes offline."""
    from .alerts import _create_or_update_alert
    from .models import Client

    if event.severity not in ("warning", "critical"):
        return

    try:
        client = Client.objects.get(id=event.client_id)
    except Client.DoesNotExist:
        return

    _create_or_update_alert(
        client, "device_offline", event.severity,
        event.title or "Device offline",
        event.description or f"{event.hostname} is offline",
    )


def _on_device_deleted(event: Event):
    """Create alert + notification when a device is deleted."""
    from .alerts import _create_or_update_alert
    from .models import Client
    from scanner_api.models import ActivityLog

    try:
        client = Client.objects.get(id=event.client_id)
    except Client.DoesNotExist:
        return

    hostname = event.hostname or client.hostname

    _create_or_update_alert(
        client, "device_deleted", "critical",
        f"Client deleted: {hostname}",
        f"Client {hostname} ({event.client_key}) has been deleted/removed.",
    )

    ActivityLog.objects.create(
        action="delete",
        details=f"Client {hostname} deleted - notified via event bus",
    )

    _notify_all_admins(
        title=f"Client Deleted: {hostname}",
        message=f"Client {hostname} ({event.client_key}) has been deleted from the system.",
        severity="critical",
        module="monitoring",
        source_url="/",
    )


def _on_agent_version_changed(event: Event):
    """Create alert + notification when agent version changes."""
    from .alerts import _create_or_update_alert
    from .models import Client

    try:
        client = Client.objects.get(id=event.client_id)
    except Client.DoesNotExist:
        return

    old_ver = event.data.get("old_version", "unknown")
    new_ver = event.data.get("new_version", "unknown")
    hostname = event.hostname or client.hostname

    _create_or_update_alert(
        client, "agent_version_changed", "info",
        f"Agent version changed on {hostname}",
        f"Agent on {hostname} updated from v{old_ver} to v{new_ver}",
    )

    _notify_all_admins(
        title=f"Agent Updated: {hostname}",
        message=f"Client agent on {hostname} updated from v{old_ver} to v{new_ver}.",
        severity="information",
        module="monitoring",
        source_url=f"/client/{event.client_key}" if event.client_key else "/",
    )


# ── WebSocket Broadcast Subscribers ──────────────────────────────────────────

def _broadcast_change(event: Event):
    """Broadcast change events to all connected dashboard clients."""
    from .signals_helpers import broadcast_to_dashboard, send_device_update

    event_data = event.to_dict()

    # Broadcast to all dashboard connections
    try:
        broadcast_to_dashboard(event.event_type.value, event_data)
    except Exception:
        logger.debug("Failed to broadcast %s to dashboard", event.event_type.value)

    # Also send device-specific update if we have a client key
    if event.client_key:
        try:
            send_device_update(event.client_key, event_data)
        except Exception:
            logger.debug("Failed to send device update for %s", event.client_key)


def _broadcast_alert(event: Event):
    """Broadcast new alerts to all connected dashboard clients."""
    from .signals_helpers import broadcast_alert

    try:
        broadcast_alert(event.data)
    except Exception:
        logger.debug("Failed to broadcast alert")


# ── History Audit Subscriber ─────────────────────────────────────────────────

def _record_change_history(event: Event):
    """Record change events to the DeviceHistory audit trail."""
    from .models import Client, DeviceHistory

    if not event.client_id:
        return

    try:
        client = Client.objects.get(id=event.client_id)
    except Client.DoesNotExist:
        return

    category = "hardware_change"
    if event.event_type.value.startswith("sw_"):
        category = "software_change"
    elif event.event_type.value.startswith("health_"):
        category = "health_change"
    elif event.event_type.value.startswith("device_"):
        category = "status_change"
    elif event.event_type.value.startswith("alert_"):
        category = "security_event"
    elif event.event_type.value.startswith("agent_"):
        category = "agent_update"

    DeviceHistory.objects.create(
        client=client,
        category=category,
        event_type=event.event_type.value,
        description=event.description,
        severity=event.severity,
        previous_value=event.data.get("previous", {}),
        new_value=event.data.get("new", {}),
    )


# ── Registration ─────────────────────────────────────────────────────────────

def register_default_subscribers():
    """Register all default subscribers on the global event bus.

    Called once at module import time and from apps.py ready().
    """
    # Alert generation
    event_bus.subscribe(EventType.HW_COMPONENT_REMOVED, _on_hardware_change_alert)
    event_bus.subscribe(EventType.HW_COMPONENT_ADDED, _on_hardware_change_alert)
    event_bus.subscribe(EventType.HW_COMPONENT_MODIFIED, _on_hardware_change_alert)
    event_bus.subscribe(EventType.SW_UNAUTHORIZED, _on_software_change_alert)
    event_bus.subscribe(EventType.SW_ANTIVIRUS_REMOVED, _on_software_change_alert)
    event_bus.subscribe(EventType.SW_REMOVED, _on_software_change_alert)
    event_bus.subscribe(EventType.DEVICE_OFFLINE, _on_device_offline_alert)
    event_bus.subscribe(EventType.DEVICE_DELETED, _on_device_deleted)
    event_bus.subscribe(EventType.AGENT_VERSION_CHANGED, _on_agent_version_changed)

    # All HW/SW change notifications (includes info-level changes too)
    for et in [
        EventType.HW_COMPONENT_ADDED,
        EventType.HW_COMPONENT_REMOVED,
        EventType.HW_COMPONENT_MODIFIED,
        EventType.SW_INSTALLED,
        EventType.SW_REMOVED,
        EventType.SW_VERSION_CHANGED,
        EventType.SW_UNAUTHORIZED,
        EventType.SW_ANTIVIRUS_REMOVED,
    ]:
        event_bus.subscribe(et, _on_all_hw_sw_changes)

    # WebSocket broadcasts
    event_bus.subscribe_all(_broadcast_change)

    # History audit trail (for change events only — not all events)
    for et in [
        EventType.HW_COMPONENT_ADDED,
        EventType.HW_COMPONENT_REMOVED,
        EventType.HW_COMPONENT_MODIFIED,
        EventType.SW_INSTALLED,
        EventType.SW_REMOVED,
        EventType.SW_VERSION_CHANGED,
        EventType.SW_UNAUTHORIZED,
        EventType.SW_ANTIVIRUS_REMOVED,
        EventType.HEALTH_LEVEL_CHANGED,
        EventType.DEVICE_STATUS_CHANGED,
        EventType.DEVICE_REGISTERED,
        EventType.DEVICE_APPROVED,
        EventType.DEVICE_BLOCKED,
        EventType.DEVICE_DELETED,
        EventType.AGENT_VERSION_CHANGED,
    ]:
        event_bus.subscribe(et, _record_change_history)

    logger.info(
        "Event bus subscribers registered (%d total handlers)",
        event_bus.subscriber_count(),
    )


# Auto-register on import
register_default_subscribers()
