import logging
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone as tz
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from scanner_api.models import Client
from .models import DeviceMonitoringInfo
from .scheduler_models import ScheduledScan, PendingScan, ScanScheduleLog
from .scheduler import (
    add_or_update_schedule, remove_schedule,
    get_pending_scans_for_client, mark_pending_scan_executed,
    get_scheduler_status,
)

logger = logging.getLogger("monitoring")


@method_decorator(csrf_exempt, name="dispatch")
class ScheduleListView(APIView):
    """List and create scan schedules."""

    def get(self, request):
        search = request.query_params.get("search", "").strip()
        enabled = request.query_params.get("enabled", "").strip()
        schedule_type = request.query_params.get("type", "").strip()

        qs = ScheduledScan.objects.all()
        if search:
            qs = qs.filter(name__icontains=search)
        if enabled:
            qs = qs.filter(enabled=enabled.lower() == "true")
        if schedule_type:
            qs = qs.filter(schedule_type=schedule_type)

        limit = int(request.query_params.get("limit", 50))
        schedules = qs[:limit]

        data = []
        for s in schedules:
            data.append({
                "id": str(s.id),
                "name": s.name,
                "description": s.description,
                "schedule_type": s.schedule_type,
                "interval_seconds": s.interval_seconds,
                "time_of_day": s.time_of_day.isoformat() if s.time_of_day else None,
                "day_of_week": s.day_of_week,
                "day_of_month": s.day_of_month,
                "target_all": s.target_all,
                "target_count": s.target_clients.count() if not s.target_all else 0,
                "target_platforms": s.target_platforms,
                "scan_type": s.scan_type,
                "enabled": s.enabled,
                "last_run": s.last_run.isoformat() if s.last_run else None,
                "next_run": s.next_run.isoformat() if s.next_run else None,
                "run_count": s.run_count,
                "created_at": s.created_at.isoformat(),
            })

        return Response({"schedules": data, "total": qs.count()})

    def post(self, request):
        data = request.data

        name = data.get("name", "").strip()
        if not name:
            return Response({"status": "error", "message": "Name is required"},
                            status=status.HTTP_400_BAD_REQUEST)

        schedule_type = data.get("schedule_type", "interval")

        schedule = ScheduledScan.objects.create(
            name=name,
            description=data.get("description", ""),
            schedule_type=schedule_type,
            interval_seconds=data.get("interval_seconds", 3600),
            time_of_day=data.get("time_of_day"),
            day_of_week=data.get("day_of_week"),
            day_of_month=data.get("day_of_month"),
            target_all=data.get("target_all", True),
            target_platforms=data.get("target_platforms", ""),
            scan_type=data.get("scan_type", "full"),
            enabled=data.get("enabled", True),
        )

        target_ids = data.get("target_clients", [])
        if target_ids and not schedule.target_all:
            clients = Client.objects.filter(registration_key__in=target_ids)
            schedule.target_clients.set(clients)

        add_or_update_schedule(schedule)

        return Response({
            "status": "ok",
            "schedule_id": str(schedule.id),
        }, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name="dispatch")
class ScheduleDetailView(APIView):
    """Get, update, or delete a schedule."""

    def get(self, request, key):
        try:
            schedule = ScheduledScan.objects.get(id=key)
        except ScheduledScan.DoesNotExist:
            return Response({"status": "error", "message": "Schedule not found"},
                            status=status.HTTP_404_NOT_FOUND)

        return Response({
            "id": str(schedule.id),
            "name": schedule.name,
            "description": schedule.description,
            "schedule_type": schedule.schedule_type,
            "interval_seconds": schedule.interval_seconds,
            "time_of_day": schedule.time_of_day.isoformat() if schedule.time_of_day else None,
            "day_of_week": schedule.day_of_week,
            "day_of_month": schedule.day_of_month,
            "target_all": schedule.target_all,
            "target_clients": [str(c.registration_key) for c in schedule.target_clients.all()],
            "target_platforms": schedule.target_platforms,
            "scan_type": schedule.scan_type,
            "enabled": schedule.enabled,
            "last_run": schedule.last_run.isoformat() if schedule.last_run else None,
            "next_run": schedule.next_run.isoformat() if schedule.next_run else None,
            "run_count": schedule.run_count,
            "created_at": schedule.created_at.isoformat(),
        })

    def put(self, request, key):
        try:
            schedule = ScheduledScan.objects.get(id=key)
        except ScheduledScan.DoesNotExist:
            return Response({"status": "error", "message": "Schedule not found"},
                            status=status.HTTP_404_NOT_FOUND)

        data = request.data
        for field in ["name", "description", "schedule_type", "interval_seconds",
                       "time_of_day", "day_of_week", "day_of_month",
                       "target_all", "target_platforms", "scan_type", "enabled"]:
            if field in data:
                setattr(schedule, field, data[field])

        if "target_clients" in data and not schedule.target_all:
            target_ids = data["target_clients"]
            clients = Client.objects.filter(registration_key__in=target_ids)
            schedule.target_clients.set(clients)

        schedule.save()
        add_or_update_schedule(schedule)

        return Response({"status": "ok"})

    def delete(self, request, key):
        try:
            schedule = ScheduledScan.objects.get(id=key)
        except ScheduledScan.DoesNotExist:
            return Response({"status": "error", "message": "Schedule not found"},
                            status=status.HTTP_404_NOT_FOUND)

        remove_schedule(schedule.id)
        schedule.delete()

        return Response({"status": "ok"})


@method_decorator(csrf_exempt, name="dispatch")
class ScheduleToggleView(APIView):
    """Enable or disable a schedule."""

    def post(self, request, key):
        try:
            schedule = ScheduledScan.objects.get(id=key)
        except ScheduledScan.DoesNotExist:
            return Response({"status": "error", "message": "Schedule not found"},
                            status=status.HTTP_404_NOT_FOUND)

        schedule.enabled = not schedule.enabled
        schedule.save(update_fields=["enabled", "updated_at"])
        add_or_update_schedule(schedule)

        return Response({"status": "ok", "enabled": schedule.enabled})


@method_decorator(csrf_exempt, name="dispatch")
class ScheduleHistoryView(APIView):
    """Execution history for a schedule."""

    def get(self, request, key):
        try:
            schedule = ScheduledScan.objects.get(id=key)
        except ScheduledScan.DoesNotExist:
            return Response({"status": "error", "message": "Schedule not found"},
                            status=status.HTTP_404_NOT_FOUND)

        limit = int(request.query_params.get("limit", 50))
        logs = ScanScheduleLog.objects.filter(
            scheduled_scan=schedule
        ).select_related("client")[:limit]

        data = []
        for log in logs:
            data.append({
                "id": str(log.id),
                "client": log.client.hostname if log.client else "unknown",
                "client_key": log.client.registration_key if log.client else "",
                "triggered_at": log.triggered_at.isoformat(),
                "completed_at": log.completed_at.isoformat() if log.completed_at else None,
                "status": log.status,
                "changes_detected": log.changes_detected,
                "alerts_generated": log.alerts_generated,
            })

        return Response({"history": data, "total": logs.count()})


@method_decorator(csrf_exempt, name="dispatch")
class SchedulerStatusView(APIView):
    """Scheduler status and health."""

    def get(self, request):
        status_data = get_scheduler_status()
        from .scheduler_models import PendingScan
        status_data["pending_scans"] = PendingScan.objects.filter(status="pending").count()
        status_data["total_schedules"] = ScheduledScan.objects.count()
        status_data["enabled_schedules"] = ScheduledScan.objects.filter(enabled=True).count()
        return Response(status_data)


@method_decorator(csrf_exempt, name="dispatch")
class PendingScansView(APIView):
    """View and manage pending (queued) scans."""

    def get(self, request):
        client_key = request.query_params.get("client", "").strip()
        scan_status = request.query_params.get("status", "").strip()

        qs = PendingScan.objects.select_related("client", "scheduled_scan").all()
        if client_key:
            qs = qs.filter(client__registration_key=client_key)
        if scan_status:
            qs = qs.filter(status=scan_status)

        limit = int(request.query_params.get("limit", 100))
        pending = qs[:limit]

        data = []
        for p in pending:
            data.append({
                "id": str(p.id),
                "client": p.client.hostname if p.client else "unknown",
                "client_key": p.client.registration_key if p.client else "",
                "scan_type": p.scan_type,
                "priority": p.priority,
                "status": p.status,
                "created_at": p.created_at.isoformat(),
                "sent_at": p.sent_at.isoformat() if p.sent_at else None,
                "executed_at": p.executed_at.isoformat() if p.executed_at else None,
                "schedule_name": p.scheduled_scan.name if p.scheduled_scan else "manual",
            })

        return Response({"pending_scans": data, "total": qs.count()})

    def delete(self, request):
        ids = request.data.get("ids", [])
        if ids:
            PendingScan.objects.filter(id__in=ids, status="pending").delete()
        return Response({"status": "ok"})


@method_decorator(csrf_exempt, name="dispatch")
class AgentPendingScansView(APIView):
    """Agent-facing endpoint to fetch and acknowledge pending scans on reconnect."""

    def get(self, request):
        client_key = request.headers.get("X-Registration-Key", "")
        if not client_key:
            client_key = request.query_params.get("key", "")

        if not client_key:
            return Response({"status": "error", "message": "Missing client key"},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            client = Client.objects.get(registration_key=client_key, deleted=False)
        except Client.DoesNotExist:
            return Response({"status": "error", "message": "Client not found"},
                            status=status.HTTP_404_NOT_FOUND)

        pending = get_pending_scans_for_client(client)
        scans = []
        for ps in pending:
            scans.append({
                "id": str(ps.id),
                "scan_type": ps.scan_type,
                "priority": ps.priority,
                "created_at": ps.created_at.isoformat(),
            })

        return Response({
            "status": "ok",
            "pending_scans": scans,
            "count": len(scans),
        })

    def post(self, request):
        scan_id = request.data.get("scan_id", "")
        scan_status = request.data.get("status", "executed")

        if not scan_id:
            return Response({"status": "error", "message": "Missing scan_id"},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            ps = PendingScan.objects.get(id=scan_id)
        except PendingScan.DoesNotExist:
            return Response({"status": "error", "message": "Pending scan not found"},
                            status=status.HTTP_404_NOT_FOUND)

        if scan_status == "executed":
            mark_pending_scan_executed(scan_id)
        elif scan_status == "failed":
            PendingScan.objects.filter(pk=scan_id).update(
                status="failed",
                error_message=request.data.get("error", ""),
            )

        return Response({"status": "ok"})
