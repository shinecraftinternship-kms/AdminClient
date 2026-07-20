import logging
from django.utils import timezone
from .models import AuditLog, LoginHistory, LoginAttempt, Setting
from .validators import parse_user_agent_string

logger = logging.getLogger("scanner_api")


def get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "127.0.0.1")


def get_user_agent(request):
    return request.META.get("HTTP_USER_AGENT", "")


def parse_device_info(request):
    ua = get_user_agent(request)
    browser, os_name, device_type = parse_user_agent_string(ua)
    return {
        "browser": browser,
        "os": os_name,
        "device_type": device_type,
        "user_agent": ua,
    }


def check_account_lock(identifier):
    max_attempts = int(Setting.get("max_login_attempts", "5"))
    lock_duration = int(Setting.get("lock_duration_minutes", "30"))

    cutoff = timezone.now() - timezone.timedelta(minutes=lock_duration)
    recent_failures = LoginAttempt.objects.filter(
        identifier=identifier, success=False, created_at__gte=cutoff
    ).count()

    if recent_failures >= max_attempts:
        last_failure = LoginAttempt.objects.filter(
            identifier=identifier, success=False
        ).order_by("-created_at").first()
        if last_failure:
            unlock_time = last_failure.created_at + timezone.timedelta(minutes=lock_duration)
            if timezone.now() < unlock_time:
                remaining = (unlock_time - timezone.now()).total_seconds() / 60
                return True, round(remaining, 1)
    return False, 0


def record_login_attempt(identifier, ip_address, success):
    LoginAttempt.objects.create(
        identifier=identifier, ip_address=ip_address, success=success
    )
    if not success:
        max_attempts = int(Setting.get("max_login_attempts", "5"))
        recent = LoginAttempt.objects.filter(
            identifier=identifier, success=False,
            created_at__gte=timezone.now() - timezone.timedelta(minutes=30)
        ).count()
        if recent >= max_attempts:
            log_audit_event(
                None, "account_locked", None,
                details=f"Account {identifier} locked after {recent} failed attempts"
            )


def log_audit_event(user, event_type, request, details="", success=True):
    ip = None
    ua = ""
    device_info = {}
    if request:
        ip = get_client_ip(request)
        ua = get_user_agent(request)
        device_info = parse_device_info(request)
    return AuditLog.objects.create(
        user=user, event_type=event_type, ip_address=ip,
        user_agent=ua, device_info=device_info,
        details=details, success=success,
    )


def create_login_history(user, request):
    device = parse_device_info(request)
    return LoginHistory.objects.create(
        user=user,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        browser=device["browser"],
        os=device["os"],
        device_type=device["device_type"],
        is_current=True,
    )


def close_login_history(user):
    active = LoginHistory.objects.filter(user=user, is_current=True).first()
    if active:
        active.logout_time = timezone.now()
        active.is_current = False
        if active.login_time:
            active.session_duration = active.logout_time - active.login_time
        active.save(update_fields=["logout_time", "is_current", "session_duration"])


def get_or_create_profile(user):
    from .models import AdministratorProfile
    profile, _ = AdministratorProfile.objects.get_or_create(user=user)
    return profile
