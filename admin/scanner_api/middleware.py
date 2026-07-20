from django.utils import timezone
from django.contrib.auth import logout
from django.shortcuts import redirect
from .models import Setting


class SessionTimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            timeout_minutes = int(Setting.get("session_timeout_minutes", "30"))
            last_activity = request.session.get("last_activity")
            if last_activity:
                from datetime import datetime
                try:
                    last = datetime.fromisoformat(last_activity)
                    elapsed = (timezone.now() - timezone.make_aware(last) if timezone.is_naive(last)
                               else timezone.now() - last)
                    if elapsed.total_seconds() > timeout_minutes * 60:
                        logout(request)
                        return redirect("/login/?timeout=1")
                except (ValueError, TypeError):
                    pass
            request.session["last_activity"] = timezone.now().isoformat()

        response = self.get_response(request)
        return response


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "DENY"
        response["X-XSS-Protection"] = "1; mode=block"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
