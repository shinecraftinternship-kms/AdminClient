"""APScheduler integration for scheduled scanning.

Manages the background scheduler that triggers scans based on
configured schedules. Sends commands to online agents via WebSocket
and queues pending scans for offline agents.
"""

import logging
from datetime import timedelta, time as dt_time

from django.utils import timezone as tz
from django.db import transaction

logger = logging.getLogger("monitoring.scheduler")

_scheduler = None


def get_scheduler():
    """Get or create the APScheduler instance."""
    global _scheduler
    if _scheduler is None:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.jobstores.memory import MemoryJobStore

        _scheduler = BackgroundScheduler(
            jobstores={"default": MemoryJobStore()},
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 300,
            },
        )
    return _scheduler


def start_scheduler():
    """Start the background scheduler."""
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler started")
        _sync_schedules_to_jobs()


def stop_scheduler():
    """Stop the background scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")
    _scheduler = None


def _sync_schedules_to_jobs():
    """Load all enabled schedules from DB and create scheduler jobs."""
    from .scheduler_models import ScheduledScan

    scheduler = get_scheduler()

    existing_jobs = {job.id for job in scheduler.get_jobs()}
    active_schedules = ScheduledScan.objects.filter(enabled=True)

    for schedule in active_schedules:
        job_id = f"scan_{schedule.id}"
        if job_id not in existing_jobs:
            _add_schedule_job(scheduler, schedule)

    logger.info("Synced %d schedules to scheduler", active_schedules.count())


def _add_schedule_job(scheduler, schedule):
    """Add a single schedule as a scheduler job."""
    job_id = f"scan_{schedule.id}"

    try:
        if schedule.schedule_type == "interval":
            scheduler.add_job(
                _execute_schedule,
                "interval",
                seconds=max(schedule.interval_seconds, 60),
                id=job_id,
                args=[str(schedule.id)],
                replace_existing=True,
            )
        elif schedule.schedule_type == "daily":
            if schedule.time_of_day:
                scheduler.add_job(
                    _execute_schedule,
                    "cron",
                    hour=schedule.time_of_day.hour,
                    minute=schedule.time_of_day.minute,
                    id=job_id,
                    args=[str(schedule.id)],
                    replace_existing=True,
                )
        elif schedule.schedule_type == "weekly":
            if schedule.time_of_day and schedule.day_of_week is not None:
                day_map = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}
                day_name = day_map.get(schedule.day_of_week, "mon")
                scheduler.add_job(
                    _execute_schedule,
                    "cron",
                    day_of_week=day_name,
                    hour=schedule.time_of_day.hour,
                    minute=schedule.time_of_day.minute,
                    id=job_id,
                    args=[str(schedule.id)],
                    replace_existing=True,
                )
        elif schedule.schedule_type == "monthly":
            if schedule.time_of_day and schedule.day_of_month:
                scheduler.add_job(
                    _execute_schedule,
                    "cron",
                    day=schedule.day_of_month,
                    hour=schedule.time_of_day.hour,
                    minute=schedule.time_of_day.minute,
                    id=job_id,
                    args=[str(schedule.id)],
                    replace_existing=True,
                )
        elif schedule.schedule_type == "once":
            if schedule.next_run:
                scheduler.add_job(
                    _execute_schedule,
                    "date",
                    run_date=schedule.next_run,
                    id=job_id,
                    args=[str(schedule.id)],
                    replace_existing=True,
                )

        logger.info("Added job for schedule: %s (%s)", schedule.name, schedule.schedule_type)
    except Exception as e:
        logger.error("Failed to add job for schedule %s: %s", schedule.id, e)


def _execute_schedule(schedule_id):
    """Execute a scheduled scan - called by APScheduler."""
    from .scheduler_models import ScheduledScan, PendingScan, ScanScheduleLog
    from .signals_helpers import notify_agent, broadcast_to_dashboard

    try:
        schedule = ScheduledScan.objects.get(id=schedule_id, enabled=True)
    except ScheduledScan.DoesNotExist:
        logger.warning("Schedule %s not found or disabled", schedule_id)
        return

    logger.info("Executing schedule: %s", schedule.name)

    clients = _get_target_clients(schedule)
    online_clients = []
    offline_clients = []

    for client in clients:
        info = getattr(client, "monitoring_info", None)
        if info and info.monitoring_status == "online":
            online_clients.append(client)
        else:
            offline_clients.append(client)

    for client in online_clients:
        try:
            command_id = f"scan_{client.registration_key}_{tz.now().timestamp()}"
            notify_agent(
                agent_id=_get_agent_id(client),
                command_type="scan_now",
                payload={"scan_type": schedule.scan_type, "schedule_id": str(schedule.id)},
                command_id=command_id,
            )
            ScanScheduleLog.objects.create(
                scheduled_scan=schedule,
                client=client,
                status="triggered",
                details={"scan_type": schedule.scan_type, "trigger": "websocket"},
            )
        except Exception as e:
            logger.error("Failed to trigger scan on %s: %s", client.hostname, e)

    for client in offline_clients:
        try:
            PendingScan.objects.create(
                client=client,
                scheduled_scan=schedule,
                scan_type=schedule.scan_type,
                priority=1,
            )
            ScanScheduleLog.objects.create(
                scheduled_scan=schedule,
                client=client,
                status="skipped",
                details={"reason": "offline"},
            )
        except Exception as e:
            logger.error("Failed to create pending scan for %s: %s", client.hostname, e)

    schedule.last_run = tz.now()
    schedule.run_count += 1
    schedule.save(update_fields=["last_run", "run_count", "updated_at"])

    broadcast_to_dashboard("schedule_executed", {
        "schedule_id": str(schedule.id),
        "schedule_name": schedule.name,
        "online_count": len(online_clients),
        "offline_count": len(offline_clients),
        "timestamp": tz.now().isoformat(),
    })


def _get_target_clients(schedule):
    """Get the list of clients targeted by a schedule."""
    if schedule.target_all:
        from scanner_api.models import Client
        return list(Client.objects.filter(deleted=False, approved=True))

    clients = list(schedule.target_clients.all())

    if schedule.target_platforms:
        platforms = [p.strip().lower() for p in schedule.target_platforms.split(",") if p.strip()]
        if platforms:
            clients = [c for c in clients if c.platform.lower() in platforms]

    return clients


def _get_agent_id(client):
    """Get the monitoring agent_id for a client."""
    try:
        secret = client.agent_secrets.filter(is_active=True).first()
        return secret.agent_id if secret else None
    except Exception:
        return None


def add_or_update_schedule(schedule):
    """Add or update a schedule in the scheduler."""
    scheduler = get_scheduler()
    job_id = f"scan_{schedule.id}"

    existing = scheduler.get_job(job_id)
    if existing:
        existing.remove()

    if schedule.enabled:
        _add_schedule_job(scheduler, schedule)


def remove_schedule(schedule_id):
    """Remove a schedule from the scheduler."""
    scheduler = get_scheduler()
    job_id = f"scan_{schedule_id}"
    job = scheduler.get_job(job_id)
    if job:
        job.remove()
        logger.info("Removed scheduler job: %s", job_id)


def get_pending_scans_for_client(client):
    """Get pending scans for a reconnecting client."""
    from .scheduler_models import PendingScan
    return list(PendingScan.objects.filter(
        client=client, status="pending"
    ).select_related("scheduled_scan").order_by("-priority", "created_at"))


def mark_pending_scan_executed(pending_scan_id):
    """Mark a pending scan as executed."""
    from .scheduler_models import PendingScan
    try:
        ps = PendingScan.objects.get(id=pending_scan_id)
        ps.status = "executed"
        ps.executed_at = tz.now()
        PendingScan.objects.filter(pk=pending_scan_id).update(
            status="executed", executed_at=tz.now()
        )
    except PendingScan.DoesNotExist:
        pass


def get_scheduler_status():
    """Get scheduler status info."""
    scheduler = get_scheduler()
    jobs = scheduler.get_jobs() if scheduler.running else []
    return {
        "running": scheduler.running,
        "job_count": len(jobs),
        "jobs": [
            {
                "id": job.id,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
            }
            for job in jobs
        ],
    }
