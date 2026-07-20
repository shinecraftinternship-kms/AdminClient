from django.urls import path
from . import views
from . import scheduler_views
from . import report_views

urlpatterns = [
    # ── Agent API ──────────────────────────────────────────
    path("agent/register", views.AgentRegisterView.as_view(), name="mon-agent-register"),
    path("agent/heartbeat", views.AgentHeartbeatView.as_view(), name="mon-agent-heartbeat"),
    path("agent/inventory", views.AgentInventoryView.as_view(), name="mon-agent-inventory"),
    path("agent/version-check", views.AgentVersionCheckView.as_view(), name="mon-agent-version-check"),
    path("agent/pending-scans", scheduler_views.AgentPendingScansView.as_view(), name="mon-agent-pending-scans"),

    # ── Admin Dashboard ────────────────────────────────────
    path("dashboard", views.MonitorDashboardView.as_view(), name="mon-dashboard"),
    path("trends", views.MonitorTrendsView.as_view(), name="mon-trends"),

    # ── Devices ────────────────────────────────────────────
    path("devices", views.MonitorDeviceListView.as_view(), name="mon-devices"),
    path("devices/bulk", views.MonitorBulkActionView.as_view(), name="mon-devices-bulk"),
    path("devices/<uuid:key>", views.MonitorDeviceDetailView.as_view(), name="mon-device-detail"),
    path("devices/<uuid:key>/approve", views.MonitorDeviceApproveView.as_view(), name="mon-device-approve"),
    path("devices/<uuid:key>/block", views.MonitorDeviceBlockView.as_view(), name="mon-device-block"),
    path("devices/<uuid:key>/metrics", views.MonitorDeviceMetricsView.as_view(), name="mon-device-metrics"),
    path("devices/<uuid:key>/history", views.MonitorDeviceHistoryView.as_view(), name="mon-device-history"),
    path("devices/<uuid:key>/alerts", views.MonitorDeviceAlertsView.as_view(), name="mon-device-alerts"),
    path("devices/<uuid:key>/hardware", views.MonitorHardwareView.as_view(), name="mon-device-hw"),
    path("devices/<uuid:key>/software", views.MonitorSoftwareView.as_view(), name="mon-device-sw"),
    path("devices/<uuid:key>/heartbeats", views.MonitorHeartbeatHistoryView.as_view(), name="mon-device-heartbeats"),

    # ── Alerts ─────────────────────────────────────────────
    path("alerts", views.MonitorAlertListView.as_view(), name="mon-alerts"),
    path("alerts/<uuid:key>/action", views.MonitorAlertActionView.as_view(), name="mon-alert-action"),

    # ── Reports ────────────────────────────────────────────
    path("reports/fleet/pdf", report_views.ReportFleetPDFView.as_view(), name="mon-report-fleet-pdf"),
    path("reports/fleet/csv", report_views.ReportFleetCSVView.as_view(), name="mon-report-fleet-csv"),
    path("reports/device/<uuid:key>/pdf", report_views.ReportDevicePDFView.as_view(), name="mon-report-device-pdf"),
    path("reports/device/<uuid:key>/csv", report_views.ReportDeviceCSVView.as_view(), name="mon-report-device-csv"),
    path("reports/alerts/pdf", report_views.ReportAlertsPDFView.as_view(), name="mon-report-alerts-pdf"),
    path("reports/alerts/csv", report_views.ReportAlertsCSVView.as_view(), name="mon-report-alerts-csv"),

    # ── Schedules ──────────────────────────────────────────
    path("schedules/status", scheduler_views.SchedulerStatusView.as_view(), name="mon-scheduler-status"),
    path("schedules/pending", scheduler_views.PendingScansView.as_view(), name="mon-pending-scans"),
    path("schedules", scheduler_views.ScheduleListView.as_view(), name="mon-schedules"),
    path("schedules/<uuid:key>", scheduler_views.ScheduleDetailView.as_view(), name="mon-schedule-detail"),
    path("schedules/<uuid:key>/toggle", scheduler_views.ScheduleToggleView.as_view(), name="mon-schedule-toggle"),
    path("schedules/<uuid:key>/history", scheduler_views.ScheduleHistoryView.as_view(), name="mon-schedule-history"),

    # ── Settings / Versions ────────────────────────────────
    path("agent-versions", views.MonitorAgentVersionsView.as_view(), name="mon-agent-versions"),
    path("settings/unauthorized-software", views.MonitorUnauthorizedSwView.as_view(), name="mon-unauthorized-sw"),
]
