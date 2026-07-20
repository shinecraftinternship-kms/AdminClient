from django.urls import path
from . import views

urlpatterns = [
    # ── Maintenance ─────────────────────────────────────────
    path("maintenance", views.MaintenanceListView.as_view(), name="mnt-list"),
    path("maintenance/<uuid:key>", views.MaintenanceDetailView.as_view(), name="mnt-detail"),
    path("maintenance/<uuid:key>/status", views.MaintenanceStatusView.as_view(), name="mnt-status"),
    path("maintenance/<uuid:key>/approve", views.MaintenanceApprovalView.as_view(), name="mnt-approve"),
    path("maintenance/<uuid:key>/upload", views.MaintenanceDocumentUploadView.as_view(), name="mnt-upload"),
    path("maintenance/export", views.MaintenanceExportView.as_view(), name="mnt-export"),

    # ── Warranty ────────────────────────────────────────────
    path("warranties", views.WarrantyListView.as_view(), name="warranty-list"),
    path("warranties/<uuid:key>", views.WarrantyDetailView.as_view(), name="warranty-detail"),

    # ── Downtime ────────────────────────────────────────────
    path("downtime", views.DowntimeListView.as_view(), name="downtime-list"),
    path("downtime/<uuid:key>/end", views.DowntimeEndView.as_view(), name="downtime-end"),

    # ── Software Licenses ───────────────────────────────────
    path("licenses", views.LicenseListView.as_view(), name="license-list"),
    path("licenses/<uuid:key>", views.LicenseDetailView.as_view(), name="license-detail"),
    path("licenses/<uuid:key>/archive", views.LicenseArchiveView.as_view(), name="license-archive"),
    path("licenses/assign", views.LicenseAssignView.as_view(), name="license-assign"),
    path("licenses/assignments/<uuid:key>/remove", views.LicenseRemoveAssignmentView.as_view(), name="license-unassign"),
    path("licenses/export", views.LicenseExportView.as_view(), name="license-export"),

    # ── Compliance & Alerts ─────────────────────────────────
    path("compliance", views.ComplianceListView.as_view(), name="compliance-list"),
    path("compliance/<uuid:key>/action", views.ComplianceActionView.as_view(), name="compliance-action"),
    path("alerts", views.MaintenanceAlertListView.as_view(), name="alert-list"),
    path("alerts/<uuid:key>/action", views.MaintenanceAlertActionView.as_view(), name="alert-action"),
    path("alerts/check", views.AlertCheckView.as_view(), name="alert-check"),

    # ── Dashboard & Analytics ───────────────────────────────
    path("dashboard", views.MaintenanceDashboardView.as_view(), name="mnt-dashboard"),
    path("analytics/cost-trend", views.MaintenanceCostTrendView.as_view(), name="cost-trend"),
    path("analytics/vendor-performance", views.VendorPerformanceView.as_view(), name="vendor-performance"),
    path("analytics/failure-rate", views.AssetFailureRateView.as_view(), name="failure-rate"),
    path("analytics/downtime", views.DowntimeAnalyticsView.as_view(), name="downtime-analytics"),
    path("analytics/license-dashboard", views.LicenseDashboardView.as_view(), name="license-dashboard"),
    path("analytics/license-utilization", views.LicenseUtilizationView.as_view(), name="license-utilization"),
    path("analytics/license-cost", views.LicenseCostAnalysisView.as_view(), name="license-cost-analysis"),
]
