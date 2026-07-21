import logging
from datetime import timedelta
from django.utils import timezone as tz
from django.db.models import Q

from scanner_api.models import Asset
from .models import (
    MaintenanceRecord, WarrantyRecord, SoftwareLicense,
    ComplianceRecord, MaintenanceAlert,
)

logger = logging.getLogger("maintenance")


def check_and_generate_alerts():
    """Master function to generate all maintenance & license alerts."""
    now = tz.now()
    today = now.date()
    alerts_created = 0

    # ── Maintenance Overdue ─────────────────────────────────────────────
    overdue_records = MaintenanceRecord.objects.filter(
        status__in=("Scheduled", "In Progress", "Waiting Parts"),
        due_date__lt=today,
        deleted=False,
    )
    for record in overdue_records:
        if not MaintenanceAlert.objects.filter(
            maintenance=record, category="maintenance_overdue", status="active"
        ).exists():
            MaintenanceAlert.objects.create(
                category="maintenance_overdue",
                severity="critical",
                title=f"Maintenance Overdue: {record.maintenance_id}",
                message=f"Maintenance {record.maintenance_id} for {record.asset.asset_name} is overdue. "
                        f"Due date: {record.due_date}",
                asset=record.asset,
                maintenance=record,
                details={"maintenance_id": record.maintenance_id, "due_date": str(record.due_date)},
            )
            alerts_created += 1

    # ── Maintenance Due (within 7 days) ─────────────────────────────────
    upcoming = today + timedelta(days=7)
    due_records = MaintenanceRecord.objects.filter(
        status__in=("Approved", "Scheduled"),
        scheduled_date__lte=upcoming,
        scheduled_date__gte=today,
        deleted=False,
    )
    for record in due_records:
        if not MaintenanceAlert.objects.filter(
            maintenance=record, category="maintenance_due", status="active"
        ).exists():
            MaintenanceAlert.objects.create(
                category="maintenance_due",
                severity="warning",
                title=f"Maintenance Due: {record.maintenance_id}",
                message=f"Maintenance {record.maintenance_id} for {record.asset.asset_name} is due on {record.scheduled_date}",
                asset=record.asset,
                maintenance=record,
                details={"maintenance_id": record.maintenance_id, "scheduled_date": str(record.scheduled_date)},
            )
            alerts_created += 1

    # ── Warranty Expiring (30, 60, 90 days) ─────────────────────────────
    warranty_thresholds = [
        (30, "warning", "Warranty Expiring Soon"),
        (60, "info", "Warranty Expiring in 60 Days"),
        (90, "info", "Warranty Expiring in 90 Days"),
    ]
    for days, severity, title_prefix in warranty_thresholds:
        target_date = today + timedelta(days=days)
        min_date = today + timedelta(days=days - 1) if days > 1 else today
        expiring_warranties = WarrantyRecord.objects.filter(
            warranty_end__lte=target_date,
            warranty_end__gt=min_date,
            status="Active",
            deleted=False,
        )
        for w in expiring_warranties:
            existing = MaintenanceAlert.objects.filter(
                warranty=w,
                category="warranty_expiring",
                status="active",
                title__startswith=f"{title_prefix}",
            ).exists()
            if not existing:
                MaintenanceAlert.objects.create(
                    category="warranty_expiring",
                    severity=severity,
                    title=f"{title_prefix}: {w.asset.asset_name}",
                    message=f"Warranty for {w.asset.asset_name} ({w.warranty_provider}) expires on {w.warranty_end}. "
                            f"{w.days_remaining} days remaining.",
                    asset=w.asset,
                    warranty=w,
                    details={"warranty_id": w.warranty_id, "expiry": str(w.warranty_end), "days_remaining": w.days_remaining},
                )
                alerts_created += 1

    # ── Warranty Expired ────────────────────────────────────────────────
    expired_warranties = WarrantyRecord.objects.filter(
        warranty_end__lt=today,
        status="Active",
        deleted=False,
    )
    for w in expired_warranties:
        if not MaintenanceAlert.objects.filter(
            warranty=w, category="warranty_expired", status="active"
        ).exists():
            w.status = "Expired"
            w.save(update_fields=["status"])
            MaintenanceAlert.objects.create(
                category="warranty_expired",
                severity="warning",
                title=f"Warranty Expired: {w.asset.asset_name}",
                message=f"Warranty for {w.asset.asset_name} ({w.warranty_provider}) expired on {w.warranty_end}",
                asset=w.asset,
                warranty=w,
                details={"warranty_id": w.warranty_id, "expiry": str(w.warranty_end)},
            )
            alerts_created += 1

    # ── License Expiration ──────────────────────────────────────────────
    license_thresholds = [
        (7, "critical", "License Expiring - URGENT"),
        (30, "warning", "License Expiring Soon"),
        (60, "info", "License Expiring in 60 Days"),
    ]
    for days, severity, title_prefix in license_thresholds:
        target_date = today + timedelta(days=days)
        min_date = today + timedelta(days=days - 1) if days > 1 else today
        expiring_licenses = SoftwareLicense.objects.filter(
            expiration_date__lte=target_date,
            expiration_date__gt=min_date,
            status__in=("Active", "Draft"),
            deleted=False,
        )
        for lic in expiring_licenses:
            existing = MaintenanceAlert.objects.filter(
                license=lic,
                category="license_expiration",
                status="active",
                title__startswith=f"{title_prefix}",
            ).exists()
            if not existing:
                MaintenanceAlert.objects.create(
                    category="license_expiration",
                    severity=severity,
                    title=f"{title_prefix}: {lic.software_name}",
                    message=f"License for {lic.software_name} ({lic.license_type}) expires on {lic.expiration_date}. "
                            f"{lic.days_until_expiration} days remaining.",
                    license=lic,
                    details={"license_id": lic.license_id, "software_name": lic.software_name,
                             "expiry": str(lic.expiration_date)},
                )
                alerts_created += 1

    # ── License Expired ─────────────────────────────────────────────────
    expired_licenses = SoftwareLicense.objects.filter(
        expiration_date__lt=today,
        status__in=("Active", "Draft", "Expiring Soon"),
        deleted=False,
    )
    for lic in expired_licenses:
        if not MaintenanceAlert.objects.filter(
            license=lic, category="license_expiration", status="active",
            title__startswith="License Expired"
        ).exists():
            lic.status = "Expired"
            lic.save(update_fields=["status"])
            MaintenanceAlert.objects.create(
                category="license_expiration",
                severity="critical",
                title=f"License Expired: {lic.software_name}",
                message=f"License for {lic.software_name} ({lic.license_type}) expired on {lic.expiration_date}",
                license=lic,
                details={"license_id": lic.license_id, "software_name": lic.software_name,
                         "expiry": str(lic.expiration_date)},
            )
            alerts_created += 1

    # ── License Seat Exhaustion ─────────────────────────────────────────
    exhausted = SoftwareLicense.objects.filter(
        seats_used__gte=models_F("purchased_seats"),
        status__in=("Active", "Draft"),
        deleted=False,
    )
    for lic in exhausted:
        if not MaintenanceAlert.objects.filter(
            license=lic, category="license_seat_exhaustion", status="active"
        ).exists():
            MaintenanceAlert.objects.create(
                category="license_seat_exhaustion",
                severity="warning",
                title=f"License Seats Exhausted: {lic.software_name}",
                message=f"All {lic.purchased_seats} seats for {lic.software_name} are in use "
                        f"({lic.seats_used}/{lic.purchased_seats})",
                license=lic,
                details={"license_id": lic.license_id, "seats_used": lic.seats_used,
                         "purchased_seats": lic.purchased_seats},
            )
            alerts_created += 1

    logger.info(f"Alert check completed. {alerts_created} new alerts created.")
    return alerts_created


def models_F(field_name):
    from django.db.models import F
    return F(field_name)


def acknowledge_alert(alert_id):
    try:
        alert = MaintenanceAlert.objects.get(id=alert_id, status="active")
        alert.status = "acknowledged"
        alert.acknowledged_by = "admin"
        alert.acknowledged_at = tz.now()
        alert.save(update_fields=["status", "acknowledged_by", "acknowledged_at", "updated_at"])
        return True
    except MaintenanceAlert.DoesNotExist:
        return False


def resolve_alert(alert_id):
    try:
        alert = MaintenanceAlert.objects.get(id=alert_id, status__in=("active", "acknowledged"))
        alert.status = "resolved"
        alert.resolved_at = tz.now()
        alert.save(update_fields=["status", "resolved_at", "updated_at"])
        return True
    except MaintenanceAlert.DoesNotExist:
        return False


def dismiss_alert(alert_id):
    try:
        alert = MaintenanceAlert.objects.get(id=alert_id, status__in=("active", "acknowledged"))
        alert.status = "dismissed"
        alert.save(update_fields=["status", "updated_at"])
        return True
    except MaintenanceAlert.DoesNotExist:
        return False


def acknowledge_compliance(record_id):
    try:
        record = ComplianceRecord.objects.get(id=record_id, status="active")
        record.status = "acknowledged"
        record.acknowledged_by = "admin"
        record.save(update_fields=["status", "acknowledged_by", "updated_at"])
        return True
    except ComplianceRecord.DoesNotExist:
        return False


def resolve_compliance(record_id):
    try:
        record = ComplianceRecord.objects.get(id=record_id, status__in=("active", "acknowledged"))
        record.status = "resolved"
        record.resolved_at = tz.now()
        record.save(update_fields=["status", "resolved_at", "updated_at"])
        return True
    except ComplianceRecord.DoesNotExist:
        return False
