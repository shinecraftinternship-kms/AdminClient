import logging
from django.utils import timezone

logger = logging.getLogger("intelligence")


def log_audit_entry(user, action, module="system", object_type="", object_id="",
                    object_repr="", old_value=None, new_value=None,
                    severity="low", description="", request=None):
    from .models import AuditLogEntry

    ip_address = None
    browser_info = ""
    device_info = ""
    username = ""

    if request:
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        ip_address = xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR", "")
        browser_info = request.META.get("HTTP_USER_AGENT", "")[:256]
        device_info = request.META.get("HTTP_SEC_CH_UA_PLATFORM", "")[:256]

    if user and hasattr(user, "username"):
        username = user.username
        user_id = user.id
    else:
        user_id = None
        username = str(user) if user else "system"

    entry = AuditLogEntry.objects.create(
        user_id=user_id,
        username=username,
        ip_address=ip_address,
        browser_info=browser_info,
        device_info=device_info,
        module=module,
        action=action,
        object_type=object_type,
        object_id=str(object_id) if object_id else "",
        object_repr=object_repr[:256] if object_repr else "",
        old_value=old_value or {},
        new_value=new_value or {},
        severity=severity,
        description=description,
    )
    return entry


def log_login(user, request):
    return log_audit_entry(
        user, "login", module="auth",
        description=f"User {user.username} logged in",
        severity="low", request=request,
    )


def log_logout(user, request):
    return log_audit_entry(
        user, "logout", module="auth",
        description=f"User {user.username} logged out",
        severity="low", request=request,
    )


def log_failed_login(identifier, request):
    return log_audit_entry(
        None, "login_failed", module="auth",
        object_repr=identifier,
        description=f"Failed login attempt for {identifier}",
        severity="medium", request=request,
    )


def log_asset_created(user, asset, request=None):
    return log_audit_entry(
        user, "asset_created", module="asset",
        object_type="Asset", object_id=str(asset.id),
        object_repr=f"{asset.asset_name} ({asset.asset_tag})",
        new_value={"asset_name": asset.asset_name, "asset_tag": asset.asset_tag,
                    "serial_number": asset.serial_number},
        severity="low", description=f"Asset {asset.asset_name} created",
        request=request,
    )


def log_asset_updated(user, asset, old, new, request=None):
    return log_audit_entry(
        user, "asset_updated", module="asset",
        object_type="Asset", object_id=str(asset.id),
        object_repr=f"{asset.asset_name} ({asset.asset_tag})",
        old_value=old, new_value=new,
        severity="low", description=f"Asset {asset.asset_name} updated",
        request=request,
    )


def log_asset_assigned(user, assignment, request=None):
    return log_audit_entry(
        user, "asset_assigned", module="asset",
        object_type="AssetAssignment", object_id=str(assignment.id),
        object_repr=f"{assignment.asset.asset_name} -> {assignment.employee.full_name}",
        new_value={"asset_id": str(assignment.asset_id), "employee_id": str(assignment.employee_id)},
        severity="medium", description=f"Asset assigned to {assignment.employee.full_name}",
        request=request,
    )


def log_asset_deleted(user, asset, request=None):
    return log_audit_entry(
        user, "asset_deleted", module="asset",
        object_type="Asset", object_id=str(asset.id),
        object_repr=f"{asset.asset_name} ({asset.asset_tag})",
        severity="high", description=f"Asset {asset.asset_name} deleted",
        request=request,
    )


def log_report_downloaded(user, report, request=None):
    return log_audit_entry(
        user, "report_downloaded", module="intelligence",
        object_type="Report", object_id=str(report.id),
        object_repr=report.name,
        severity="low", description=f"Report {report.name} downloaded",
        request=request,
    )


def log_settings_changed(user, setting_key, old_val, new_val, request=None):
    return log_audit_entry(
        user, "settings_changed", module="settings",
        object_type="Setting", object_repr=setting_key,
        old_value={"value": old_val}, new_value={"value": new_val},
        severity="medium", description=f"Setting {setting_key} changed",
        request=request,
    )
