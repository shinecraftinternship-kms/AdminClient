﻿import hashlib
import json
import logging
import threading
from datetime import timedelta
from django.utils import timezone
from django.db import models as db_models

logger = logging.getLogger("intelligence")


def _make_dedup_hash(module, category, title, source_obj_id=""):
    raw = f"{module}:{category}:{title}:{source_obj_id}"
    return hashlib.sha256(raw.encode()).hexdigest()


def create_alert(title, description, module, category, severity="warning",
                 source_object_id="", source_object_type="", assigned_user="",
                 resolution_notes="") -> object:
    from .models import Alert

    dedup = _make_dedup_hash(module, category, title, source_object_id)

    if dedup:
        existing = Alert.objects.filter(
            dedup_hash=dedup, status__in=["open", "acknowledged"]
        ).first()
        if existing:
            existing.updated_at = timezone.now()
            existing.description = description
            existing.save(update_fields=["description", "updated_at"])
            return existing

    alert = Alert.objects.create(
        title=title,
        description=description,
        module=module,
        category=category,
        severity=severity,
        source_object_id=source_object_id,
        source_object_type=source_object_type,
        assigned_user=assigned_user,
        dedup_hash=dedup,
    )
    logger.info(f"Alert created: [{severity}] {title}")
    return alert


def acknowledge_alert(alert_id, by_user="") -> bool:
    from .models import Alert, AlertHistory
    try:
        alert = Alert.objects.get(id=alert_id)
    except Alert.DoesNotExist:
        return False
    if alert.status != "open":
        return False
    old_status = alert.status
    alert.status = "acknowledged"
    alert.save(update_fields=["status", "updated_at"])
    AlertHistory.objects.create(
        alert=alert, action="acknowledged",
        previous_status=old_status, new_status="acknowledged",
        performed_by=by_user,
    )
    return True


def resolve_alert(alert_id, notes="", by_user="") -> bool:
    from .models import Alert, AlertHistory
    try:
        alert = Alert.objects.get(id=alert_id)
    except Alert.DoesNotExist:
        return False
    if alert.status in ("resolved", "dismissed"):
        return False
    old_status = alert.status
    alert.status = "resolved"
    alert.resolved_time = timezone.now()
    if notes:
        alert.resolution_notes = notes
    alert.save(update_fields=["status", "resolved_time", "resolution_notes", "updated_at"])
    AlertHistory.objects.create(
        alert=alert, action="resolved",
        previous_status=old_status, new_status="resolved",
        performed_by=by_user, notes=notes,
    )
    return True


def dismiss_alert(alert_id, notes="", by_user="") -> bool:
    from .models import Alert, AlertHistory
    try:
        alert = Alert.objects.get(id=alert_id)
    except Alert.DoesNotExist:
        return False
    if alert.status in ("resolved", "dismissed"):
        return False
    old_status = alert.status
    alert.status = "dismissed"
    alert.resolved_time = timezone.now()
    if notes:
        alert.resolution_notes = notes
    alert.save(update_fields=["status", "resolved_time", "resolution_notes", "updated_at"])
    AlertHistory.objects.create(
        alert=alert, action="dismissed",
        previous_status=old_status, new_status="dismissed",
        performed_by=by_user, notes=notes,
    )
    return True


def assign_alert(alert_id, user) -> bool:
    from .models import Alert, AlertHistory
    try:
        alert = Alert.objects.get(id=alert_id)
    except Alert.DoesNotExist:
        return False
    if alert.status in ("resolved", "dismissed"):
        return False
    old_user = alert.assigned_user
    alert.assigned_user = user
    alert.save(update_fields=["assigned_user", "updated_at"])
    AlertHistory.objects.create(
        alert=alert, action="assigned",
        performed_by=user, notes=f"Assigned from {old_user} to {user}",
    )
    return True


def escalate_alerts():
    from .models import Alert
    now = timezone.now()
    escalated = []

    for alert in Alert.objects.filter(status__in=["open", "acknowledged"]):
        age_hours = (now - alert.generated_time).total_seconds() / 3600
        new_level = alert.escalation_level

        if alert.severity == "emergency" and age_hours > 1 and new_level < 3:
            new_level = 3
        elif alert.severity == "critical" and age_hours > 4 and new_level < 2:
            new_level = 2
        elif alert.severity == "warning" and age_hours > 24 and new_level < 1:
            new_level = 1

        if new_level > alert.escalation_level:
            alert.escalation_level = new_level
            alert.save(update_fields=["escalation_level", "updated_at"])
            escalated.append(str(alert.id))
            logger.info(f"Alert {alert.id} escalated to level {new_level}")

    return escalated


def run_alert_checks():
    from AdminClient.admin.scanner_api.models import Asset, Client
    from AdminClient.admin.maintenance.models import MaintenanceRecord, SoftwareLicense, WarrantyRecord
    from django.utils import timezone as tz
    today = tz.now().date()

    new_alerts = []

    assets = Asset.objects.filter(deleted=False)
    for asset in assets:
        if asset.warranty_end:
            days_left = (asset.warranty_end - today).days
            if days_left < 0:
                a = create_alert(
                    f"Warranty expired: {asset.asset_name}",
                    f"Warranty for {asset.asset_name} ({asset.asset_tag}) expired on {asset.warranty_end}.",
                    module="asset", category="asset", severity="warning",
                    source_object_id=str(asset.id), source_object_type="Asset",
                )
                if a: new_alerts.append(a)
            elif days_left <= 30:
                a = create_alert(
                    f"Warranty expiring soon: {asset.asset_name}",
                    f"Warranty for {asset.asset_name} expires in {days_left} days.",
                    module="asset", category="asset", severity="information",
                    source_object_id=str(asset.id), source_object_type="Asset",
                )
                if a: new_alerts.append(a)

    records = MaintenanceRecord.objects.filter(deleted=False, status__in=["Scheduled", "In Progress", "Pending Approval", "Approved"])
    for rec in records:
        if rec.due_date and rec.due_date < today:
            a = create_alert(
                f"Maintenance overdue: {rec.maintenance_id}",
                f"Maintenance {rec.maintenance_id} for {rec.asset.asset_name} was due on {rec.due_date}.",
                module="maintenance", category="maintenance", severity="critical",
                source_object_id=str(rec.id), source_object_type="MaintenanceRecord",
            )
            if a: new_alerts.append(a)
        elif rec.scheduled_date and rec.scheduled_date <= today + timedelta(days=7) and rec.scheduled_date >= today:
            a = create_alert(
                f"Maintenance due soon: {rec.maintenance_id}",
                f"Maintenance {rec.maintenance_id} for {rec.asset.asset_name} is scheduled on {rec.scheduled_date}.",
                module="maintenance", category="maintenance", severity="warning",
                source_object_id=str(rec.id), source_object_type="MaintenanceRecord",
            )
            if a: new_alerts.append(a)

    licenses = SoftwareLicense.objects.filter(deleted=False, status__in=["Active", "Expiring Soon"])
    for lic in licenses:
        if lic.expiration_date:
            days_left = (lic.expiration_date - today).days
            if days_left < 0:
                a = create_alert(
                    f"License expired: {lic.software_name}",
                    f"License for {lic.software_name} expired on {lic.expiration_date}.",
                    module="license", category="license", severity="critical",
                    source_object_id=str(lic.id), source_object_type="SoftwareLicense",
                )
                if a: new_alerts.append(a)
            elif days_left <= 30:
                a = create_alert(
                    f"License expiring soon: {lic.software_name}",
                    f"License for {lic.software_name} expires in {days_left} days.",
                    module="license", category="license", severity="warning",
                    source_object_id=str(lic.id), source_object_type="SoftwareLicense",
                )
                if a: new_alerts.append(a)

        if lic.seats_used > lic.purchased_seats:
            a = create_alert(
                f"License seat overuse: {lic.software_name}",
                f"License {lic.software_name} has {lic.seats_used} seats used out of {lic.purchased_seats} purchased.",
                module="license", category="license", severity="critical",
                source_object_id=str(lic.id), source_object_type="SoftwareLicense",
            )
            if a: new_alerts.append(a)

    online_clients = Client.objects.filter(approved=True, deleted=False)
    for client in online_clients:
        if client.is_stale:
            a = create_alert(
                f"Device offline: {client.hostname}",
                f"Client {client.hostname} ({client.registration_key}) is stale. Last seen: {client.last_seen}.",
                module="monitoring", category="monitoring", severity="warning",
                source_object_id=client.registration_key, source_object_type="Client",
            )
            if a: new_alerts.append(a)

    return new_alerts


def get_dashboard_analytics():
    from .models import Alert, Notification, Report, AuditLogEntry, ComplianceLog
    from django.utils import timezone as tz
    today = tz.now().date()
    today_start = tz.now().replace(hour=0, minute=0, second=0, microsecond=0)

    return {
        "total_alerts": Alert.objects.count(),
        "open_alerts": Alert.objects.filter(status="open").count(),
        "critical_alerts": Alert.objects.filter(severity__in=["critical", "emergency"], status__in=["open", "acknowledged"]).count(),
        "notifications_today": Notification.objects.filter(created_time__gte=today_start).count(),
        "reports_generated": Report.objects.count(),
        "security_violations": Alert.objects.filter(category="security", status__in=["open", "acknowledged"]).count(),
        "audit_events_today": AuditLogEntry.objects.filter(timestamp__gte=today_start).count(),
        "compliance_violations": ComplianceLog.objects.filter(status="non_compliant").count(),
        "pending_notifications": Notification.objects.filter(status="unread").count(),
    }
