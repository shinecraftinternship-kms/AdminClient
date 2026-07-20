import logging
from django.utils import timezone

logger = logging.getLogger("intelligence")


def create_notification(user, title, message, severity="information",
                        module="", source_alert=None, source_url="") -> object:
    from .models import Notification, NotificationPreference

    try:
        prefs = NotificationPreference.objects.get(user=user)
    except NotificationPreference.DoesNotExist:
        prefs = None

    sev_map = {"information": "severity_information", "warning": "severity_warning",
               "critical": "severity_critical", "emergency": "severity_emergency"}
    sev_field = sev_map.get(severity, "severity_information")

    mod_map = {"asset": "module_asset", "monitoring": "module_monitoring",
               "maintenance": "module_maintenance", "license": "module_license",
               "security": "module_security", "compliance": "module_compliance",
               "system": "module_system"}
    mod_field = mod_map.get(module, "")

    if prefs:
        if not prefs.in_app_enabled:
            return None
        if not getattr(prefs, sev_field, True):
            return None
        if mod_field and not getattr(prefs, mod_field, True):
            return None

        if prefs.quiet_hours_start and prefs.quiet_hours_end:
            now = timezone.now().time()
            if prefs.quiet_hours_start <= prefs.quiet_hours_end:
                if prefs.quiet_hours_start <= now <= prefs.quiet_hours_end:
                    return None
            else:
                if now >= prefs.quiet_hours_start or now <= prefs.quiet_hours_end:
                    return None

    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
        severity=severity,
        module=module,
        source_alert=source_alert,
        source_url=source_url,
    )
    return notification


def create_alert_notifications(alert):
    from django.contrib.auth.models import User
    from .models import NotificationPreference

    users = User.objects.filter(is_active=True)
    for user in users:
        try:
            prefs = NotificationPreference.objects.get(user=user)
        except NotificationPreference.DoesNotExist:
            prefs = None

        if prefs and not prefs.in_app_enabled:
            continue

        sev_map = {"information": "severity_information", "warning": "severity_warning",
                   "critical": "severity_critical", "emergency": "severity_emergency"}
        sev_field = sev_map.get(alert.severity, "severity_information")
        if prefs and not getattr(prefs, sev_field, True):
            continue

        create_notification(
            user=user,
            title=alert.title,
            message=alert.description or alert.title,
            severity=alert.severity,
            module=alert.module,
            source_alert=alert,
            source_url="",
        )


def mark_as_read(notification_id) -> bool:
    from .models import Notification
    try:
        notification = Notification.objects.get(id=notification_id)
    except Notification.DoesNotExist:
        return False
    notification.status = "read"
    notification.read_time = timezone.now()
    notification.save(update_fields=["status", "read_time"])
    return True


def mark_all_as_read(user) -> int:
    from .models import Notification
    count = Notification.objects.filter(user=user, status="unread").update(
        status="read", read_time=timezone.now()
    )
    return count


def archive_notification(notification_id) -> bool:
    from .models import Notification
    try:
        notification = Notification.objects.get(id=notification_id)
    except Notification.DoesNotExist:
        return False
    notification.status = "archived"
    notification.save(update_fields=["status"])
    return True
