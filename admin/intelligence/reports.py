import csv
import io
import logging
from datetime import timedelta
from django.utils import timezone
from django.db import models

logger = logging.getLogger("intelligence")


def _format_date(d):
    return d.isoformat() if d else ""


def generate_report(report_type, filters=None, format="csv") -> dict:
    from .models import Report
    from scanner_api.models import Asset, Client
    from maintenance.models import MaintenanceRecord, SoftwareLicense, WarrantyRecord, ComplianceRecord
    from monitoring.models import DeviceAlert, DeviceMonitoringInfo

    filters = filters or {}
    report_name = dict(Report.REPORT_TYPE_CHOICES).get(report_type, report_type)

    data_rows = []
    headers = []

    if report_type == "asset_inventory":
        qs = Asset.objects.filter(deleted=False).select_related("category", "department", "location", "vendor")
        qs = _apply_asset_filters(qs, filters)
        headers = ["Asset ID", "Asset Name", "Asset Tag", "Serial Number", "Category", "Manufacturer",
                    "Model", "Status", "Department", "Location", "Purchase Date", "Purchase Cost",
                    "Current Value", "Warranty End", "Vendor"]
        for a in qs:
            data_rows.append([
                a.asset_id, a.asset_name, a.asset_tag, a.serial_number,
                a.category.name if a.category else "", a.manufacturer, a.model_name,
                a.asset_status, a.department.name if a.department else "",
                a.location.office_name if a.location else "",
                _format_date(a.purchase_date), str(a.purchase_cost or ""),
                str(a.current_value or ""), _format_date(a.warranty_end),
                a.vendor.name if a.vendor else "",
            ])

    elif report_type == "asset_assignment":
        from scanner_api.models import AssetAssignment
        qs = AssetAssignment.objects.select_related("asset", "employee", "department", "location")
        qs = _apply_assignment_filters(qs, filters)
        headers = ["Asset Tag", "Asset Name", "Employee", "Department", "Location",
                    "Assigned At", "Expected Return", "Status"]
        for a in qs:
            data_rows.append([
                a.asset.asset_tag if a.asset else "", a.asset.asset_name if a.asset else "",
                a.employee.full_name if a.employee else "",
                a.department.name if a.department else "",
                a.location.office_name if a.location else "",
                _format_date(a.assigned_at), _format_date(a.expected_return_date),
                "Active" if a.is_active else "Returned",
            ])

    elif report_type == "expiring_licenses":
        qs = SoftwareLicense.objects.filter(deleted=False).select_related("department")
        qs = _apply_date_filter(qs, "expiration_date", filters)
        headers = ["License ID", "Software Name", "Vendor", "License Type", "Purchased Seats",
                    "Seats Used", "Seats Available", "Expiration Date", "Days Remaining", "Status"]
        today = timezone.now().date()
        for l in qs:
            days = (l.expiration_date - today).days if l.expiration_date else ""
            data_rows.append([
                l.license_id, l.software_name, l.vendor, l.license_type,
                str(l.purchased_seats), str(l.seats_used), str(l.seats_available),
                _format_date(l.expiration_date), str(days), l.computed_status,
            ])

    elif report_type == "upcoming_maintenance":
        today = timezone.now().date()
        qs = MaintenanceRecord.objects.filter(deleted=False).select_related("asset")
        qs = _apply_date_filter(qs, "scheduled_date", filters)
        headers = ["Maintenance ID", "Asset", "Type", "Status", "Scheduled Date", "Due Date",
                    "Priority", "Technician", "Estimated Cost"]
        for m in qs:
            data_rows.append([
                m.maintenance_id, m.asset.asset_name if m.asset else "", m.maintenance_type,
                m.status, _format_date(m.scheduled_date), _format_date(m.due_date),
                m.priority, m.technician, str(m.estimated_cost or ""),
            ])

    elif report_type == "device_health":
        qs = DeviceMonitoringInfo.objects.select_related("client").filter(client__deleted=False)
        headers = ["Hostname", "IP Address", "Status", "Health Level", "Health Score",
                    "Last Heartbeat", "Agent Version", "Device Type"]
        for d in qs:
            data_rows.append([
                d.client.hostname if d.client else "", d.ip_address or "",
                d.monitoring_status, d.health_level, str(d.health_score),
                _format_date(d.last_heartbeat), d.agent_version, d.device_type,
            ])

    elif report_type == "compliance_report":
        from maintenance.models import ComplianceRecord
        qs = ComplianceRecord.objects.select_related("license", "asset")
        headers = ["Title", "Category", "Severity", "Status", "License", "Asset", "Created"]
        for c in qs:
            data_rows.append([
                c.title, c.category, c.severity, c.status,
                c.license.software_name if c.license else "",
                c.asset.asset_name if c.asset else "",
                _format_date(c.created_at),
            ])

    elif report_type == "monthly_summary":
        today = timezone.now().date()
        month_start = today.replace(day=1)
        last_month = month_start - timedelta(days=1)
        last_month_start = last_month.replace(day=1)

        new_assets = Asset.objects.filter(deleted=False, created_at__date__gte=last_month_start,
                                           created_at__date__lte=last_month).count()
        new_clients = Client.objects.filter(created_at__date__gte=last_month_start,
                                             created_at__date__lte=last_month).count()
        completed_maint = MaintenanceRecord.objects.filter(status="Completed",
            completion_date__gte=last_month_start, completion_date__lte=last_month).count()
        new_alerts = __import__("intelligence.models", fromlist=["Alert"]).Alert.objects.filter(
            generated_time__date__gte=last_month_start, generated_time__date__lte=last_month
        ).count()

        headers = ["Metric", "Value", "Period"]
        data_rows = [
            ["New Assets", str(new_assets), f"{last_month_start} to {last_month}"],
            ["New Clients", str(new_clients), f"{last_month_start} to {last_month}"],
            ["Completed Maintenance", str(completed_maint), f"{last_month_start} to {last_month}"],
            ["Alerts Generated", str(new_alerts), f"{last_month_start} to {last_month}"],
        ]

    elif report_type == "software_inventory":
        from monitoring.models import SoftwareInventory
        qs = SoftwareInventory.objects.filter(is_present=True).select_related("client")
        headers = ["Client Hostname", "Software Name", "Version", "Publisher", "Category"]
        for s in qs:
            data_rows.append([
                s.client.hostname if s.client else "", s.name, s.version,
                s.publisher, s.category,
            ])

    elif report_type == "audit_report":
        qs = __import__("intelligence.models", fromlist=["AuditLogEntry"]).AuditLogEntry.objects.all()
        qs = _apply_audit_filters(qs, filters)
        headers = ["Timestamp", "User", "Action", "Module", "Object Type", "Object", "Severity", "IP Address"]
        for a in qs[:1000]:
            data_rows.append([
                _format_date(a.timestamp), a.username, a.action, a.module,
                a.object_type, a.object_repr, a.severity, a.ip_address or "",
            ])

    else:
        return {"status": "error", "message": f"Unknown report type: {report_type}"}

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerows(data_rows)
        csv_data = output.getvalue()
        encoded = __import__("base64").b64encode(csv_data.encode()).decode()
    elif format == "excel":
        try:
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = report_name[:31]
            ws.append(headers)
            for row in data_rows:
                ws.append(row)
            buf = io.BytesIO()
            wb.save(buf)
            encoded = __import__("base64").b64encode(buf.getvalue()).decode()
        except ImportError:
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(headers)
            writer.writerows(data_rows)
            encoded = __import__("base64").b64encode(output.getvalue().encode()).decode()
    else:
        encoded = ""

    report = Report.objects.create(
        name=f"{report_name} - {timezone.now().strftime('%Y-%m-%d %H:%M')}",
        report_type=report_type, format=format, filters=filters,
        file_data=encoded, row_count=len(data_rows), status="completed",
        completed_at=timezone.now(),
    )

    return {
        "status": "ok",
        "report_id": str(report.id),
        "report_name": report.name,
        "row_count": len(data_rows),
        "format": format,
        "headers": headers,
        "data_preview": data_rows[:20],
    }


def _apply_asset_filters(qs, filters):
    if not filters:
        return qs
    if filters.get("department"):
        qs = qs.filter(department_id=filters["department"])
    if filters.get("location"):
        qs = qs.filter(location_id=filters["location"])
    if filters.get("category"):
        qs = qs.filter(category_id=filters["category"])
    if filters.get("status"):
        qs = qs.filter(asset_status=filters["status"])
    if filters.get("severity"):
        qs = qs.filter(warranty_status=filters["severity"])
    return qs


def _apply_assignment_filters(qs, filters):
    if not filters:
        return qs
    if filters.get("department"):
        qs = qs.filter(department_id=filters["department"])
    if filters.get("location"):
        qs = qs.filter(location_id=filters["location"])
    if filters.get("active") == "true":
        qs = qs.filter(is_active=True)
    elif filters.get("active") == "false":
        qs = qs.filter(is_active=False)
    return qs


def _apply_date_filter(qs, field, filters):
    if not filters:
        return qs
    if filters.get("date_from"):
        qs = qs.filter(**{f"{field}__gte": filters["date_from"]})
    if filters.get("date_to"):
        qs = qs.filter(**{f"{field}__lte": filters["date_to"]})
    return qs


def _apply_audit_filters(qs, filters):
    if not filters:
        return qs
    if filters.get("user"):
        qs = qs.filter(user_id=filters["user"])
    if filters.get("module"):
        qs = qs.filter(module=filters["module"])
    if filters.get("action"):
        qs = qs.filter(action=filters["action"])
    if filters.get("severity"):
        qs = qs.filter(severity=filters["severity"])
    if filters.get("date_from"):
        qs = qs.filter(timestamp__gte=filters["date_from"])
    if filters.get("date_to"):
        qs = qs.filter(timestamp__lte=filters["date_to"])
    if filters.get("ip_address"):
        qs = qs.filter(ip_address=filters["ip_address"])
    return qs
