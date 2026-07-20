from django.urls import path, include
from AdminClient.admin.scanner_api import templates
from AdminClient.admin.monitoring import templates as mon_templates
from AdminClient.admin.maintenance import templates as mnt_templates
from AdminClient.admin.intelligence import templates as intel_templates

urlpatterns = [
    path("api/", include("scanner_api.urls")),
    path("api/monitoring/", include("monitoring.urls")),
    path("api/maintenance/", include("maintenance.urls")),
    path("api/intelligence/", include("intelligence.urls")),
    path("login/", templates.login_view, name="login"),
    path("signup/", templates.signup_view, name="signup"),
    path("logout/", templates.logout_view, name="logout"),
    path("download-client/", templates.download_client_view, name="download-client"),
    path("", templates.dashboard, name="dashboard"),
    path("client/<str:key>/", templates.client_detail, name="client-detail"),
    path("settings/", templates.settings_page, name="settings"),
    path("admin-page/", templates.admin_page, name="admin-page"),
    path("executive-dashboard/", templates.executive_dashboard, name="executive-dashboard"),
    path("account/", templates.account_view, name="account"),
    path("scans/", templates.scan_history, name="scan-history"),
    path("audit-log/", templates.audit_log_view, name="audit-log"),
    path("employees/", templates.employees_page, name="employees"),
    path("departments/", templates.departments_page, name="departments"),
    path("locations/", templates.locations_page, name="locations"),
    path("assets/", templates.assets_page, name="assets"),
    path("assets/<uuid:key>/", templates.asset_detail_page, name="asset-detail"),
    path("asset-dashboard/", templates.asset_dashboard_page, name="asset-dashboard"),
    path("monitoring/", mon_templates.monitoring_page, name="monitoring"),
    path("intelligence/", intel_templates.intelligence_dashboard_page, name="intel-dashboard-page"),
    path("intelligence/alerts/", intel_templates.alerts_page, name="intel-alerts-page"),
    path("intelligence/notifications/", intel_templates.notifications_page, name="intel-notifications-page"),
    path("intelligence/reports/", intel_templates.reports_page, name="intel-reports-page"),
    path("intelligence/scheduled-reports/", intel_templates.scheduled_reports_page, name="intel-scheduled-reports-page"),
    path("intelligence/audit-logs/", intel_templates.audit_logs_page, name="intel-audit-logs-page"),
    path("intelligence/compliance/", intel_templates.compliance_page, name="intel-compliance-page"),
    path("maintenance/", mnt_templates.maintenance_page, name="maintenance"),
    path("licenses/", mnt_templates.licenses_page, name="licenses"),
    path("maintenance-alerts/", mnt_templates.maintenance_alerts_page, name="maintenance-alerts"),
]

# WebSocket routes are handled by ASGI/Channels (monitoring/routing.py)
# Run with: daphne -b 0.0.0.0 -p 8000 django_admin.asgi:application
# Or: uvicorn django_admin.asgi:application --host 0.0.0.0 --port 8000
