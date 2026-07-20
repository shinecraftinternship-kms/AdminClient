from django.urls import path
from . import views
from . import templates

urlpatterns = [
    # Template routes
    path("dashboard/", templates.intelligence_dashboard_page, name="intel-dashboard-page"),
    path("alerts/", templates.alerts_page, name="intel-alerts-page"),
    path("notifications/", templates.notifications_page, name="intel-notifications-page"),
    path("reports/", templates.reports_page, name="intel-reports-page"),
    path("scheduled-reports/", templates.scheduled_reports_page, name="intel-scheduled-reports-page"),
    path("audit-logs/", templates.audit_logs_page, name="intel-audit-logs-page"),
    path("compliance/", templates.compliance_page, name="intel-compliance-page"),

    # API routes
    # Dashboard Analytics
    path("dashboard", views.IntelligenceDashboardView.as_view(), name="intel-dashboard"),

    # Alert Management
    path("alerts", views.AlertListView.as_view(), name="intel-alerts"),
    path("alerts/run-checks", views.AlertsRunChecksView.as_view(), name="intel-alerts-run-checks"),
    path("alerts/export", views.AlertExportView.as_view(), name="intel-alerts-export"),
    path("alerts/bulk", views.AlertBulkActionView.as_view(), name="intel-alerts-bulk"),
    path("alerts/rules", views.AlertRulesView.as_view(), name="intel-alert-rules"),
    path("alerts/rules/<uuid:key>", views.AlertRuleDetailView.as_view(), name="intel-alert-rule-detail"),
    path("alerts/<uuid:key>", views.AlertDetailView.as_view(), name="intel-alert-detail"),
    path("alerts/<uuid:key>/action", views.AlertActionView.as_view(), name="intel-alert-action"),
    path("alerts/<uuid:key>/history", views.AlertHistoryView.as_view(), name="intel-alert-history"),

    # Notification Center
    path("notifications", views.NotificationListView.as_view(), name="intel-notifications"),
    path("notifications/mark-all-read", views.NotificationMarkAllReadView.as_view(), name="intel-notifications-mark-all-read"),
    path("notifications/preferences", views.NotificationPreferenceView.as_view(), name="intel-notification-preferences"),
    path("notifications/<uuid:key>/action", views.NotificationActionView.as_view(), name="intel-notification-action"),

    # Report Engine
    path("reports", views.ReportListView.as_view(), name="intel-reports"),
    path("reports/generate", views.ReportGenerateView.as_view(), name="intel-reports-generate"),
    path("reports/types", views.ReportTypesView.as_view(), name="intel-report-types"),
    path("reports/<uuid:key>", views.ReportDetailView.as_view(), name="intel-report-detail"),
    path("reports/<uuid:key>/export", views.ReportExportView.as_view(), name="intel-report-export"),

    # Scheduled Reports
    path("scheduled-reports", views.ScheduledReportListView.as_view(), name="intel-scheduled-reports"),
    path("scheduled-reports/<uuid:key>", views.ScheduledReportDetailView.as_view(), name="intel-scheduled-report-detail"),

    # Audit Logs
    path("audit-logs", views.AuditLogListView.as_view(), name="intel-audit-logs"),
    path("audit-logs/export", views.AuditLogExportView.as_view(), name="intel-audit-log-export"),
    path("audit-logs/modules", views.AuditLogModulesView.as_view(), name="intel-audit-log-modules"),
    path("audit-logs/actions", views.AuditLogActionsView.as_view(), name="intel-audit-log-actions"),
    path("audit-logs/<uuid:key>", views.AuditLogDetailView.as_view(), name="intel-audit-log-detail"),
    path("audit-logs/user/<int:user_id>", views.AuditUserActivityView.as_view(), name="intel-audit-user-activity"),

    # Compliance
    path("compliance", views.ComplianceLogListView.as_view(), name="intel-compliance"),
    path("compliance/dashboard", views.ComplianceDashboardView.as_view(), name="intel-compliance-dashboard"),
    path("compliance/<uuid:key>", views.ComplianceLogDetailView.as_view(), name="intel-compliance-detail"),

    # Retention Policies
    path("retention-policies", views.RetentionPolicyListView.as_view(), name="intel-retention-policies"),

    # Settings
    path("settings", views.IntelligenceSettingsView.as_view(), name="intel-settings"),
]
