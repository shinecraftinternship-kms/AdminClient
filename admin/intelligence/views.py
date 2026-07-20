import csv
import io
import logging
from datetime import timedelta
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import models
from django.db.models import Count, Q, Sum
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import (
    Alert, AlertHistory, AlertRule,
    Notification, NotificationPreference,
    Report, ScheduledReport,
    AuditLogEntry, ComplianceLog,
    DashboardAnalytics, RetentionPolicy,
)
from .serializers import (
    AlertSerializer, AlertListSerializer, AlertHistorySerializer, AlertRuleSerializer,
    NotificationSerializer, NotificationPreferenceSerializer,
    ReportSerializer, ReportListSerializer, ScheduledReportSerializer,
    AuditLogEntrySerializer, AuditLogEntryListSerializer,
    ComplianceLogSerializer, DashboardAnalyticsSerializer, RetentionPolicySerializer,
)
from .alerts import (
    create_alert, acknowledge_alert, resolve_alert, dismiss_alert,
    assign_alert, escalate_alerts, run_alert_checks, get_dashboard_analytics,
)
from .notifications import (
    create_notification, create_alert_notifications,
    mark_as_read, mark_all_as_read, archive_notification,
)
from .reports import generate_report
from .audit import log_audit_entry

logger = logging.getLogger("intelligence")


def _client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class IntelligenceDashboardView(APIView):
    def get(self, request):
        analytics = get_dashboard_analytics()
        alerts_by_severity = dict(
            Alert.objects.values_list("severity").annotate(
                c=Count("id")
            ).values_list("severity", "c")
        )
        alerts_by_category = list(
            Alert.objects.values("category").annotate(
                count=Count("id")
            ).order_by("-count")[:10]
        )
        alerts_trend = []
        for i in range(7):
            day = timezone.now() - timedelta(days=i)
            count = Alert.objects.filter(
                generated_time__date=day.date()
            ).count()
            alerts_trend.append({
                "date": day.strftime("%Y-%m-%d"),
                "count": count,
            })
        alerts_trend.reverse()

        recent_alerts = AlertListSerializer(
            Alert.objects.order_by("-generated_time")[:10], many=True
        ).data
        recent_notifications = NotificationSerializer(
            Notification.objects.order_by("-created_time")[:10], many=True
        ).data
        recent_audit = AuditLogEntryListSerializer(
            AuditLogEntry.objects.order_by("-timestamp")[:10], many=True
        ).data

        return Response({
            **analytics,
            "alerts_by_severity": alerts_by_severity,
            "alerts_by_category": alerts_by_category,
            "alerts_trend": alerts_trend,
            "recent_alerts": recent_alerts,
            "recent_notifications": recent_notifications,
            "recent_audit_events": recent_audit,
        })


# ═══════════════════════════════════════════════════════════════════════════════
# ALERT MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class AlertListView(APIView):
    def get(self, request):
        qs = Alert.objects.all()
        severity = request.query_params.get("severity", "").strip()
        category = request.query_params.get("category", "").strip()
        module = request.query_params.get("module", "").strip()
        alert_status = request.query_params.get("status", "").strip()
        search = request.query_params.get("search", "").strip()
        assigned = request.query_params.get("assigned", "").strip()
        date_from = request.query_params.get("date_from", "").strip()
        date_to = request.query_params.get("date_to", "").strip()

        if severity:
            qs = qs.filter(severity=severity)
        if category:
            qs = qs.filter(category=category)
        if module:
            qs = qs.filter(module=module)
        if alert_status:
            qs = qs.filter(status=alert_status)
        if search:
            qs = qs.filter(
                Q(title__icontains=search) | Q(description__icontains=search) |
                Q(source_object_id__icontains=search)
            )
        if assigned == "unassigned":
            qs = qs.filter(assigned_user="")
        elif assigned:
            qs = qs.filter(assigned_user__icontains=assigned)
        if date_from:
            qs = qs.filter(generated_time__gte=date_from)
        if date_to:
            qs = qs.filter(generated_time__lte=date_to)

        limit = int(request.query_params.get("limit", 100))
        offset = int(request.query_params.get("offset", 0))
        total = qs.count()
        entries = qs[offset:offset + limit]
        return Response({
            "total": total,
            "offset": offset,
            "limit": limit,
            "results": AlertListSerializer(entries, many=True).data,
        })

    def post(self, request):
        serializer = AlertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        alert = create_alert(
            title=data["title"],
            description=data.get("description", ""),
            module=data["module"],
            category=data["category"],
            severity=data.get("severity", "warning"),
            source_object_id=data.get("source_object_id", ""),
            source_object_type=data.get("source_object_type", ""),
            assigned_user=data.get("assigned_user", ""),
        )
        return Response(AlertSerializer(alert).data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name="dispatch")
class AlertDetailView(APIView):
    def get(self, request, key):
        try:
            alert = Alert.objects.get(id=key)
        except Alert.DoesNotExist:
            return Response({"status": "error", "message": "Alert not found"},
                            status=status.HTTP_404_NOT_FOUND)
        return Response(AlertSerializer(alert).data)


@method_decorator(csrf_exempt, name="dispatch")
class AlertActionView(APIView):
    def post(self, request, key):
        action = request.data.get("action", "").strip()
        notes = request.data.get("notes", "")
        user = request.user.username if request.user.is_authenticated else "system"

        if action == "acknowledge":
            ok = acknowledge_alert(key, by_user=user)
        elif action == "resolve":
            ok = resolve_alert(key, notes=notes, by_user=user)
        elif action == "dismiss":
            ok = dismiss_alert(key, notes=notes, by_user=user)
        elif action == "assign":
            assigned_to = request.data.get("assigned_user", "")
            if not assigned_to:
                return Response({"status": "error", "message": "assigned_user required"},
                                status=status.HTTP_400_BAD_REQUEST)
            ok = assign_alert(key, assigned_to)
        else:
            return Response({"status": "error", "message": f"Unknown action: {action}"},
                            status=status.HTTP_400_BAD_REQUEST)

        if not ok:
            return Response({"status": "error", "message": "Alert not found or invalid state transition"},
                            status=status.HTTP_404_NOT_FOUND)
        return Response({"status": "ok"})


@method_decorator(csrf_exempt, name="dispatch")
class AlertHistoryView(APIView):
    def get(self, request, key):
        try:
            alert = Alert.objects.get(id=key)
        except Alert.DoesNotExist:
            return Response({"status": "error", "message": "Alert not found"},
                            status=status.HTTP_404_NOT_FOUND)
        qs = AlertHistory.objects.filter(alert=alert).order_by("-timestamp")
        return Response(AlertHistorySerializer(qs, many=True).data)


@method_decorator(csrf_exempt, name="dispatch")
class AlertBulkActionView(APIView):
    def post(self, request):
        action = request.data.get("action", "").strip()
        ids = request.data.get("ids", [])
        notes = request.data.get("notes", "")
        user = request.user.username if request.user.is_authenticated else "system"

        if not ids:
            return Response({"status": "error", "message": "No IDs provided"},
                            status=status.HTTP_400_BAD_REQUEST)

        count = 0
        for alert_id in ids:
            if action == "acknowledge":
                ok = acknowledge_alert(alert_id, by_user=user)
            elif action == "resolve":
                ok = resolve_alert(alert_id, notes=notes, by_user=user)
            elif action == "dismiss":
                ok = dismiss_alert(alert_id, notes=notes, by_user=user)
            else:
                return Response({"status": "error", "message": f"Unknown action: {action}"},
                                status=status.HTTP_400_BAD_REQUEST)
            if ok:
                count += 1

        return Response({"status": "ok", "count": count})


@method_decorator(csrf_exempt, name="dispatch")
class AlertExportView(APIView):
    def get(self, request):
        qs = Alert.objects.all()
        severity = request.query_params.get("severity", "").strip()
        category = request.query_params.get("category", "").strip()
        status_filter = request.query_params.get("status", "").strip()

        if severity:
            qs = qs.filter(severity=severity)
        if category:
            qs = qs.filter(category=category)
        if status_filter:
            qs = qs.filter(status=status_filter)

        response = __import__("django.http").HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="alerts.csv"'
        writer = csv.writer(response)
        writer.writerow(["Title", "Severity", "Category", "Module", "Status",
                          "Assigned User", "Generated Time", "Resolved Time"])
        for a in qs:
            writer.writerow([
                a.title, a.severity, a.category, a.module, a.status,
                a.assigned_user,
                a.generated_time.isoformat() if a.generated_time else "",
                a.resolved_time.isoformat() if a.resolved_time else "",
            ])
        return response


@method_decorator(csrf_exempt, name="dispatch")
class AlertRulesView(APIView):
    def get(self, request):
        qs = AlertRule.objects.all()
        module = request.query_params.get("module", "").strip()
        if module:
            qs = qs.filter(module=module)
        return Response(AlertRuleSerializer(qs, many=True).data)

    def post(self, request):
        serializer = AlertRuleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rule = serializer.save()
        return Response(AlertRuleSerializer(rule).data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name="dispatch")
class AlertRuleDetailView(APIView):
    def get(self, request, key):
        try:
            rule = AlertRule.objects.get(id=key)
        except AlertRule.DoesNotExist:
            return Response({"status": "error", "message": "Rule not found"},
                            status=status.HTTP_404_NOT_FOUND)
        return Response(AlertRuleSerializer(rule).data)

    def put(self, request, key):
        try:
            rule = AlertRule.objects.get(id=key)
        except AlertRule.DoesNotExist:
            return Response({"status": "error", "message": "Rule not found"},
                            status=status.HTTP_404_NOT_FOUND)
        serializer = AlertRuleSerializer(rule, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(AlertRuleSerializer(rule).data)

    def delete(self, request, key):
        AlertRule.objects.filter(id=key).delete()
        return Response({"status": "ok"})


@method_decorator(csrf_exempt, name="dispatch")
class AlertsRunChecksView(APIView):
    def post(self, request):
        new_alerts = run_alert_checks()
        escalated = escalate_alerts()
        return Response({
            "status": "ok",
            "alerts_created": len(new_alerts),
            "alerts_escalated": len(escalated),
        })


# ═══════════════════════════════════════════════════════════════════════════════
# NOTIFICATION CENTER
# ═══════════════════════════════════════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class NotificationListView(APIView):
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"status": "error", "message": "Not authenticated"},
                            status=status.HTTP_401_UNAUTHORIZED)

        qs = Notification.objects.filter(user=request.user)
        status_filter = request.query_params.get("status", "").strip()
        severity = request.query_params.get("severity", "").strip()
        module = request.query_params.get("module", "").strip()

        if status_filter:
            qs = qs.filter(status=status_filter)
        if severity:
            qs = qs.filter(severity=severity)
        if module:
            qs = qs.filter(module=module)

        limit = int(request.query_params.get("limit", 50))
        offset = int(request.query_params.get("offset", 0))
        total = qs.count()
        unread_count = Notification.objects.filter(user=request.user, status="unread").count()
        entries = qs[offset:offset + limit]
        return Response({
            "total": total,
            "unread_count": unread_count,
            "offset": offset,
            "limit": limit,
            "results": NotificationSerializer(entries, many=True).data,
        })

    def post(self, request):
        if not request.user.is_authenticated:
            return Response({"status": "error", "message": "Not authenticated"},
                            status=status.HTTP_401_UNAUTHORIZED)
        serializer = NotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        notification = create_notification(
            user=request.user,
            title=data["title"],
            message=data.get("message", ""),
            severity=data.get("severity", "information"),
            module=data.get("module", ""),
            source_url=data.get("source_url", ""),
        )
        if notification:
            return Response(NotificationSerializer(notification).data, status=status.HTTP_201_CREATED)
        return Response({"status": "error", "message": "Notification preferences suppressed delivery"},
                        status=status.HTTP_200_OK)
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
# ═══════════════════════════════════════════════════════════════════════════════
# NOTIFICATION CENTER (continued)
# ═══════════════════════════════════════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class NotificationActionView(APIView):
    def post(self, request, key):
        action = request.data.get("action", "").strip()
        if action == "read":
            ok = mark_as_read(key)
        elif action == "archive":
            ok = archive_notification(key)
        else:
            return Response({"status": "error", "message": f"Unknown action: {action}"},
                            status=status.HTTP_400_BAD_REQUEST)
        if not ok:
            return Response({"status": "error", "message": "Notification not found"},
                            status=status.HTTP_404_NOT_FOUND)
        return Response({"status": "ok"})


@method_decorator(csrf_exempt, name="dispatch")
class NotificationMarkAllReadView(APIView):
    def post(self, request):
        if not request.user.is_authenticated:
            return Response({"status": "error", "message": "Not authenticated"},
                            status=status.HTTP_401_UNAUTHORIZED)
        count = mark_all_as_read(request.user)
        return Response({"status": "ok", "count": count})


@method_decorator(csrf_exempt, name="dispatch")
class NotificationPreferenceView(APIView):
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"status": "error", "message": "Not authenticated"},
                            status=status.HTTP_401_UNAUTHORIZED)
        prefs, _ = NotificationPreference.objects.get_or_create(user=request.user)
        return Response(NotificationPreferenceSerializer(prefs).data)

    def put(self, request):
        if not request.user.is_authenticated:
            return Response({"status": "error", "message": "Not authenticated"},
                            status=status.HTTP_401_UNAUTHORIZED)
        prefs, _ = NotificationPreference.objects.get_or_create(user=request.user)
        serializer = NotificationPreferenceSerializer(prefs, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(NotificationPreferenceSerializer(prefs).data)


# ═══════════════════════════════════════════════════════════════════════════════
# REPORT ENGINE
# ═══════════════════════════════════════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class ReportListView(APIView):
    def get(self, request):
        qs = Report.objects.all()
        report_type = request.query_params.get("type", "").strip()
        status_filter = request.query_params.get("status", "").strip()
        if report_type:
            qs = qs.filter(report_type=report_type)
        if status_filter:
            qs = qs.filter(status=status_filter)
        limit = int(request.query_params.get("limit", 50))
        return Response(ReportListSerializer(qs[:limit], many=True).data)

    def post(self, request):
        serializer = ReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        result = generate_report(
            report_type=data["report_type"],
            filters=data.get("filters", {}),
            format=data.get("format", "csv"),
        )
        if result.get("status") == "error":
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name="dispatch")
class ReportGenerateView(APIView):
    def post(self, request):
        report_type = request.data.get("report_type", "").strip()
        fmt = request.data.get("format", "csv")
        filters = request.data.get("filters", {})
        if not report_type:
            return Response({"status": "error", "message": "report_type is required"},
                            status=status.HTTP_400_BAD_REQUEST)
        result = generate_report(report_type, filters=filters, format=fmt)
        if result.get("status") == "error":
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        if request.user.is_authenticated:
            log_audit_entry(
                request.user, "report_generated", module="intelligence",
                object_type="Report", object_repr=result.get("report_name", ""),
                severity="low", description=f"Report generated: {report_type}",
                request=request,
            )
        return Response(result)


@method_decorator(csrf_exempt, name="dispatch")
class ReportDetailView(APIView):
    def get(self, request, key):
        try:
            report = Report.objects.get(id=key)
        except Report.DoesNotExist:
            return Response({"status": "error", "message": "Report not found"},
                            status=status.HTTP_404_NOT_FOUND)

        if request.user.is_authenticated:
            log_audit_entry(
                request.user, "report_downloaded", module="intelligence",
                object_type="Report", object_id=str(report.id),
                object_repr=report.name, severity="low",
                description=f"Report {report.name} downloaded", request=request,
            )
        return Response(ReportSerializer(report).data)

    def delete(self, request, key):
        Report.objects.filter(id=key).delete()
        return Response({"status": "ok"})


@method_decorator(csrf_exempt, name="dispatch")
class ReportExportView(APIView):
    def get(self, request, key):
        try:
            report = Report.objects.get(id=key)
        except Report.DoesNotExist:
            return Response({"status": "error", "message": "Report not found"},
                            status=status.HTTP_404_NOT_FOUND)
        if not report.file_data:
            return Response({"status": "error", "message": "No file data"},
                            status=status.HTTP_404_NOT_FOUND)
        return Response({
            "file_data": report.file_data,
            "format": report.format,
            "name": report.name,
        })


@method_decorator(csrf_exempt, name="dispatch")
class ReportTypesView(APIView):
    def get(self, request):
        return Response(dict(Report.REPORT_TYPE_CHOICES))


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEDULED REPORTS
# ═══════════════════════════════════════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class ScheduledReportListView(APIView):
    def get(self, request):
        qs = ScheduledReport.objects.all()
        return Response(ScheduledReportSerializer(qs, many=True).data)

    def post(self, request):
        serializer = ScheduledReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report = serializer.save()
        return Response(ScheduledReportSerializer(report).data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name="dispatch")
class ScheduledReportDetailView(APIView):
    def get(self, request, key):
        try:
            report = ScheduledReport.objects.get(id=key)
        except ScheduledReport.DoesNotExist:
            return Response({"status": "error", "message": "Scheduled report not found"},
                            status=status.HTTP_404_NOT_FOUND)
        return Response(ScheduledReportSerializer(report).data)

    def put(self, request, key):
        try:
            report = ScheduledReport.objects.get(id=key)
        except ScheduledReport.DoesNotExist:
            return Response({"status": "error", "message": "Scheduled report not found"},
                            status=status.HTTP_404_NOT_FOUND)
        serializer = ScheduledReportSerializer(report, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ScheduledReportSerializer(report).data)

    def delete(self, request, key):
        ScheduledReport.objects.filter(id=key).delete()
        return Response({"status": "ok"})


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT LOGS
# ═══════════════════════════════════════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class AuditLogListView(APIView):
    def get(self, request):
        qs = AuditLogEntry.objects.all()

        user_id = request.query_params.get("user", "").strip()
        module = request.query_params.get("module", "").strip()
        action = request.query_params.get("action", "").strip()
        severity = request.query_params.get("severity", "").strip()
        date_from = request.query_params.get("date_from", "").strip()
        date_to = request.query_params.get("date_to", "").strip()
        search = request.query_params.get("search", "").strip()
        ip_addr = request.query_params.get("ip_address", "").strip()

        if user_id:
            qs = qs.filter(user_id=user_id)
        if module:
            qs = qs.filter(module=module)
        if action:
            qs = qs.filter(action=action)
        if severity:
            qs = qs.filter(severity=severity)
        if date_from:
            qs = qs.filter(timestamp__gte=date_from)
        if date_to:
            qs = qs.filter(timestamp__lte=date_to)
        if search:
            qs = qs.filter(
                Q(username__icontains=search) |
                Q(description__icontains=search) |
                Q(object_repr__icontains=search)
            )
        if ip_addr:
            qs = qs.filter(ip_address=ip_addr)

        limit = int(request.query_params.get("limit", 100))
        offset = int(request.query_params.get("offset", 0))
        total = qs.count()
        entries = qs[offset:offset + limit]
        return Response({
            "total": total,
            "offset": offset,
            "limit": limit,
            "results": AuditLogEntryListSerializer(entries, many=True).data,
        })


@method_decorator(csrf_exempt, name="dispatch")
class AuditLogDetailView(APIView):
    def get(self, request, key):
        try:
            entry = AuditLogEntry.objects.get(id=key)
        except AuditLogEntry.DoesNotExist:
            return Response({"status": "error", "message": "Audit log entry not found"},
                            status=status.HTTP_404_NOT_FOUND)
        return Response(AuditLogEntrySerializer(entry).data)


@method_decorator(csrf_exempt, name="dispatch")
class AuditLogExportView(APIView):
    def get(self, request):
        qs = AuditLogEntry.objects.all()
        module = request.query_params.get("module", "").strip()
        action = request.query_params.get("action", "").strip()
        severity = request.query_params.get("severity", "").strip()
        date_from = request.query_params.get("date_from", "").strip()
        date_to = request.query_params.get("date_to", "").strip()

        if module:
            qs = qs.filter(module=module)
        if action:
            qs = qs.filter(action=action)
        if severity:
            qs = qs.filter(severity=severity)
        if date_from:
            qs = qs.filter(timestamp__gte=date_from)
        if date_to:
            qs = qs.filter(timestamp__lte=date_to)

        response = __import__("django.http").HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="audit_log.csv"'
        writer = csv.writer(response)
        writer.writerow(["Timestamp", "Username", "Module", "Action", "Object Type",
                          "Object", "Severity", "IP Address", "Description"])
        for e in qs[:5000]:
            writer.writerow([
                e.timestamp.isoformat() if e.timestamp else "",
                e.username, e.module, e.action, e.object_type,
                e.object_repr, e.severity, e.ip_address or "", e.description,
            ])
        return response


@method_decorator(csrf_exempt, name="dispatch")
class AuditUserActivityView(APIView):
    def get(self, request, user_id):
        qs = AuditLogEntry.objects.filter(user_id=user_id).order_by("-timestamp")
        limit = int(request.query_params.get("limit", 100))
        return Response(AuditLogEntryListSerializer(qs[:limit], many=True).data)


@method_decorator(csrf_exempt, name="dispatch")
class AuditLogModulesView(APIView):
    def get(self, request):
        return Response(dict(AuditLogEntry.MODULE_CHOICES))


@method_decorator(csrf_exempt, name="dispatch")
class AuditLogActionsView(APIView):
    def get(self, request):
        return Response(dict(AuditLogEntry.ACTION_CHOICES))


# ═══════════════════════════════════════════════════════════════════════════════
# COMPLIANCE LOGGING
# ═══════════════════════════════════════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class ComplianceLogListView(APIView):
    def get(self, request):
        qs = ComplianceLog.objects.all()
        framework = request.query_params.get("framework", "").strip()
        status_filter = request.query_params.get("status", "").strip()
        severity = request.query_params.get("severity", "").strip()
        if framework:
            qs = qs.filter(framework=framework)
        if status_filter:
            qs = qs.filter(status=status_filter)
        if severity:
            qs = qs.filter(severity=severity)
        limit = int(request.query_params.get("limit", 100))
        return Response(ComplianceLogSerializer(qs[:limit], many=True).data)

    def post(self, request):
        serializer = ComplianceLogSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entry = serializer.save()
        return Response(ComplianceLogSerializer(entry).data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name="dispatch")
class ComplianceLogDetailView(APIView):
    def get(self, request, key):
        try:
            entry = ComplianceLog.objects.get(id=key)
        except ComplianceLog.DoesNotExist:
            return Response({"status": "error", "message": "Compliance log not found"},
                            status=status.HTTP_404_NOT_FOUND)
        return Response(ComplianceLogSerializer(entry).data)


@method_decorator(csrf_exempt, name="dispatch")
class ComplianceDashboardView(APIView):
    def get(self, request):
        total = ComplianceLog.objects.count()
        by_framework = dict(
            ComplianceLog.objects.values_list("framework").annotate(
                c=Count("id")
            ).values_list("framework", "c")
        )
        by_status = dict(
            ComplianceLog.objects.values_list("status").annotate(
                c=Count("id")
            ).values_list("status", "c")
        )
        non_compliant = ComplianceLog.objects.filter(status="non_compliant").count()
        compliant = ComplianceLog.objects.filter(status="compliant").count()
        return Response({
            "total_audits": total,
            "non_compliant": non_compliant,
            "compliant": compliant,
            "compliance_rate": round(compliant / total * 100, 1) if total else 100,
            "by_framework": by_framework,
            "by_status": by_status,
        })


# ═══════════════════════════════════════════════════════════════════════════════
# RETENTION POLICIES
# ═══════════════════════════════════════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class RetentionPolicyListView(APIView):
    def get(self, request):
        return Response(RetentionPolicySerializer(RetentionPolicy.objects.all(), many=True).data)

    def post(self, request):
        serializer = RetentionPolicySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        policy, created = RetentionPolicy.objects.update_or_create(
            scope=serializer.validated_data["scope"],
            defaults={"retention_period": serializer.validated_data["retention_period"],
                      "is_active": serializer.validated_data.get("is_active", True)},
        )
        return Response(RetentionPolicySerializer(policy).data,
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM-LEVEL ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class IntelligenceSettingsView(APIView):
    def get(self, request):
        from AdminClient.admin.scanner_api.models import Setting
        return Response({
            "alert_escalation_enabled": Setting.get("alert_escalation_enabled", "true"),
            "alert_auto_checks_enabled": Setting.get("alert_auto_checks_enabled", "true"),
            "notification_retention_days": Setting.get("notification_retention_days", "90"),
            "report_retention_days": Setting.get("report_retention_days", "365"),
            "audit_retention_days": Setting.get("audit_retention_days", "1095"),
        })

    def put(self, request):
        from AdminClient.admin.scanner_api.models import Setting
        data = request.data
        for key in ["alert_escalation_enabled", "alert_auto_checks_enabled",
                      "notification_retention_days", "report_retention_days",
                      "audit_retention_days"]:
            if key in data:
                Setting.set(key, str(data[key]))
        if request.user.is_authenticated:
            log_audit_entry(request.user, "settings_changed", module="intelligence",
                            object_type="Setting", severity="medium",
                            description="Intelligence settings updated", request=request)
        return Response({"status": "ok"})
