"""Report generation views for the Monitoring module.

Provides PDF and CSV export endpoints for fleet summaries,
individual device reports, and alert histories.
"""

import logging
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .reports import (
    generate_fleet_pdf, generate_device_pdf, generate_alerts_pdf,
    generate_fleet_csv, generate_alerts_csv, generate_device_csv,
)

logger = logging.getLogger("monitoring")


@method_decorator(csrf_exempt, name="dispatch")
class ReportFleetPDFView(View):
    """GET /api/monitoring/reports/fleet/pdf"""

    def get(self, request):
        buf = generate_fleet_pdf()
        from django.http import HttpResponse
        response = HttpResponse(buf.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="fleet_report.pdf"'
        return response


@method_decorator(csrf_exempt, name="dispatch")
class ReportDevicePDFView(View):
    """GET /api/monitoring/reports/device/<key>/pdf"""

    def get(self, request, key):
        buf = generate_device_pdf(key)
        if buf is None:
            return JsonResponse({"status": "error", "message": "Device not found"}, status=404)
        from django.http import HttpResponse
        response = HttpResponse(buf.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="device_{key}.pdf"'
        return response


@method_decorator(csrf_exempt, name="dispatch")
class ReportAlertsPDFView(View):
    """GET /api/monitoring/reports/alerts/pdf?days=30"""

    def get(self, request):
        days = int(request.GET.get("days", 30))
        buf = generate_alerts_pdf(days)
        from django.http import HttpResponse
        response = HttpResponse(buf.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="alerts_report.pdf"'
        return response


@method_decorator(csrf_exempt, name="dispatch")
class ReportFleetCSVView(View):
    """GET /api/monitoring/reports/fleet/csv"""

    def get(self, request):
        return generate_fleet_csv()


@method_decorator(csrf_exempt, name="dispatch")
class ReportDeviceCSVView(View):
    """GET /api/monitoring/reports/device/<key>/csv"""

    def get(self, request, key):
        return generate_device_csv(key)


@method_decorator(csrf_exempt, name="dispatch")
class ReportAlertsCSVView(View):
    """GET /api/monitoring/reports/alerts/csv?days=30"""

    def get(self, request):
        days = int(request.GET.get("days", 30))
        return generate_alerts_csv(days)
