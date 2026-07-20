"""PDF and CSV report generation for the Monitoring module.

Uses ReportLab for PDF and Python csv module for CSV exports.
All reports include device fleet summaries, individual device details,
alert histories, and health trends.
"""

import csv
import io
import logging
from datetime import timedelta

from django.http import HttpResponse, JsonResponse
from django.utils import timezone as tz

logger = logging.getLogger("monitoring")


def _get_fleet_summary():
    """Compute fleet-wide summary statistics."""
    from .models import DeviceMonitoringInfo, DeviceAlert, DeviceHeartbeat

    now = tz.now()
    devices = DeviceMonitoringInfo.objects.select_related("client")

    total = devices.count()
    online = devices.filter(monitoring_status="online").count()
    offline = devices.filter(monitoring_status="offline").count()
    pending = devices.filter(monitoring_status="pending").count()
    blocked = devices.filter(monitoring_status="blocked").count()

    avg_health = 0
    health_scores = list(devices.values_list("health_score", flat=True).filter(health_score__isnull=False))
    if health_scores:
        avg_health = sum(health_scores) / len(health_scores)

    alerts_active = DeviceAlert.objects.filter(status="active").count()
    alerts_critical = DeviceAlert.objects.filter(status="active", severity="critical").count()
    alerts_warning = DeviceAlert.objects.filter(status="active", severity="warning").count()

    return {
        "generated_at": now.isoformat(),
        "total_devices": total,
        "online": online,
        "offline": offline,
        "pending": pending,
        "blocked": blocked,
        "avg_health_score": round(avg_health, 1),
        "alerts_active": alerts_active,
        "alerts_critical": alerts_critical,
        "alerts_warning": alerts_warning,
    }


def _get_device_details(client=None):
    """Get detailed info for all devices or a specific one."""
    from .models import DeviceMonitoringInfo, DeviceAlert, DeviceHistory
    from AdminClient.admin.scanner_api.models import Client as ClientModel

    if client:
        devices = DeviceMonitoringInfo.objects.filter(client=client)
    else:
        devices = DeviceMonitoringInfo.objects.select_related("client").all()

    results = []
    for info in devices:
        c = info.client
        recent_alerts = list(
            DeviceAlert.objects.filter(client=c, status="active")
            .order_by("-created_at")[:5]
            .values("alert_type", "severity", "title", "created_at")
        )
        results.append({
            "hostname": c.hostname,
            "registration_key": str(c.key),
            "platform": c.platform,
            "status": c.status,
            "monitoring_status": info.monitoring_status,
            "health_score": info.health_score,
            "health_level": info.health_level,
            "ip_address": info.ip_address,
            "current_user": info.current_user,
            "agent_version": info.agent_version,
            "last_heartbeat": str(info.last_heartbeat) if info.last_heartbeat else None,
            "heartbeat_count": info.heartbeat_count,
            "recent_alerts": recent_alerts,
        })

    return results


def _get_alert_history(days=30, client=None):
    """Get alert history for the specified period."""
    from .models import DeviceAlert

    since = tz.now() - timedelta(days=days)
    qs = DeviceAlert.objects.filter(created_at__gte=since).select_related("client")
    if client:
        qs = qs.filter(client=client)

    return list(qs.order_by("-created_at").values(
        "client__hostname", "alert_type", "severity", "status",
        "title", "message", "created_at", "resolved_at",
    )[:500])


# ── PDF Generation ───────────────────────────────────────────────────────────

def generate_fleet_pdf():
    """Generate a PDF fleet summary report."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle("Title2", parent=styles["Title"], fontSize=18, spaceAfter=20)
    elements.append(Paragraph("System Scanner Pro — Fleet Report", title_style))

    summary = _get_fleet_summary()
    elements.append(Paragraph(f"Generated: {summary['generated_at']}", styles["Normal"]))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Fleet Summary", styles["Heading2"]))
    summary_data = [
        ["Metric", "Value"],
        ["Total Devices", str(summary["total_devices"])],
        ["Online", str(summary["online"])],
        ["Offline", str(summary["offline"])],
        ["Pending", str(summary["pending"])],
        ["Blocked", str(summary["blocked"])],
        ["Avg Health Score", str(summary["avg_health_score"])],
        ["Active Alerts", str(summary["alerts_active"])],
        ["Critical Alerts", str(summary["alerts_critical"])],
        ["Warning Alerts", str(summary["alerts_warning"])],
    ]
    t = Table(summary_data, colWidths=[3 * inch, 2 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f0")]),
    ]))
    elements.append(t)
    elements.append(PageBreak())

    elements.append(Paragraph("Device Details", styles["Heading2"]))
    devices = _get_device_details()
    if devices:
        dev_header = ["Hostname", "Platform", "Status", "Health", "IP"]
        dev_rows = [dev_header]
        for d in devices:
            dev_rows.append([
                str(d.get("hostname", "")),
                str(d.get("platform", "")),
                str(d.get("monitoring_status", "")),
                str(d.get("health_score", "")),
                str(d.get("ip_address", "")),
            ])

        dt = Table(dev_rows, colWidths=[1.5 * inch, 1.2 * inch, 1 * inch, 0.8 * inch, 1.5 * inch])
        dt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f0")]),
        ]))
        elements.append(dt)
    else:
        elements.append(Paragraph("No devices registered.", styles["Normal"]))

    doc.build(elements)
    buf.seek(0)
    return buf


def generate_device_pdf(client_key):
    """Generate a PDF report for a single device."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from AdminClient.admin.scanner_api.models import Client

    try:
        client = Client.objects.get(key=client_key)
    except Client.DoesNotExist:
        return None

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle("Title2", parent=styles["Title"], fontSize=16, spaceAfter=12)
    elements.append(Paragraph(f"Device Report — {client.hostname}", title_style))

    devices = _get_device_details(client)
    if devices:
        d = devices[0]
        info_data = [
            ["Field", "Value"],
            ["Hostname", str(d.get("hostname", ""))],
            ["Platform", str(d.get("platform", ""))],
            ["Status", str(d.get("monitoring_status", ""))],
            ["Health Score", str(d.get("health_score", ""))],
            ["Health Level", str(d.get("health_level", ""))],
            ["IP Address", str(d.get("ip_address", ""))],
            ["Current User", str(d.get("current_user", ""))],
            ["Agent Version", str(d.get("agent_version", ""))],
            ["Last Heartbeat", str(d.get("last_heartbeat", ""))],
            ["Heartbeat Count", str(d.get("heartbeat_count", 0))],
        ]
        t = Table(info_data, colWidths=[2 * inch, 4 * inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f0")]),
        ]))
        elements.append(t)

        alerts = d.get("recent_alerts", [])
        if alerts:
            elements.append(Spacer(1, 16))
            elements.append(Paragraph("Active Alerts", styles["Heading2"]))
            alert_header = ["Type", "Severity", "Title", "Created"]
            alert_rows = [alert_header] + [
                [a.get("alert_type", ""), a.get("severity", ""), a.get("title", ""), str(a.get("created_at", ""))]
                for a in alerts
            ]
            at = Table(alert_rows, colWidths=[1.5 * inch, 1 * inch, 2.5 * inch, 1.5 * inch])
            at.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elements.append(at)

    doc.build(elements)
    buf.seek(0)
    return buf


def generate_alerts_pdf(days=30):
    """Generate a PDF alert history report."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle("Title2", parent=styles["Title"], fontSize=16, spaceAfter=12)
    elements.append(Paragraph(f"Alert History — Last {days} Days", title_style))
    elements.append(Spacer(1, 12))

    alerts = _get_alert_history(days)
    if alerts:
        header = ["Device", "Type", "Severity", "Status", "Title", "Created"]
        rows = [header]
        for a in alerts[:200]:
            rows.append([
                str(a.get("client__hostname", "")),
                str(a.get("alert_type", "")),
                str(a.get("severity", "")),
                str(a.get("status", "")),
                str(a.get("title", ""))[:40],
                str(a.get("created_at", ""))[:19],
            ])

        t = Table(rows, colWidths=[1.2 * inch, 1 * inch, 0.8 * inch, 0.8 * inch, 2 * inch, 1.2 * inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f0")]),
        ]))
        elements.append(t)
    else:
        elements.append(Paragraph("No alerts in the specified period.", styles["Normal"]))

    doc.build(elements)
    buf.seek(0)
    return buf


# ── CSV Generation ───────────────────────────────────────────────────────────

def generate_fleet_csv():
    """Generate CSV fleet export."""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="fleet_report_{tz.now().strftime("%Y%m%d")}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "Hostname", "Platform", "Monitoring Status", "Health Score", "Health Level",
        "IP Address", "Agent Version", "Current User", "Last Heartbeat", "Heartbeat Count",
    ])

    devices = _get_device_details()
    for d in devices:
        writer.writerow([
            d.get("hostname", ""),
            d.get("platform", ""),
            d.get("monitoring_status", ""),
            d.get("health_score", ""),
            d.get("health_level", ""),
            d.get("ip_address", ""),
            d.get("agent_version", ""),
            d.get("current_user", ""),
            d.get("last_heartbeat", ""),
            d.get("heartbeat_count", 0),
        ])

    return response


def generate_alerts_csv(days=30):
    """Generate CSV alert history export."""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="alerts_report_{tz.now().strftime("%Y%m%d")}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "Device", "Alert Type", "Severity", "Status", "Title", "Message", "Created", "Resolved",
    ])

    alerts = _get_alert_history(days)
    for a in alerts:
        writer.writerow([
            a.get("client__hostname", ""),
            a.get("alert_type", ""),
            a.get("severity", ""),
            a.get("status", ""),
            a.get("title", ""),
            a.get("message", ""),
            a.get("created_at", ""),
            a.get("resolved_at", ""),
        ])

    return response


def generate_device_csv(client_key):
    """Generate CSV export for a single device's alert history."""
    from AdminClient.admin.scanner_api.models import Client

    try:
        client = Client.objects.get(key=client_key)
    except Client.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Device not found"}, status=404)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="device_{client.hostname}_{tz.now().strftime("%Y%m%d")}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow(["Type", "Severity", "Status", "Title", "Message", "Created", "Resolved"])

    alerts = _get_alert_history(days=90, client=client)
    for a in alerts:
        writer.writerow([
            a.get("alert_type", ""),
            a.get("severity", ""),
            a.get("status", ""),
            a.get("title", ""),
            a.get("message", ""),
            a.get("created_at", ""),
            a.get("resolved_at", ""),
        ])

    return response
