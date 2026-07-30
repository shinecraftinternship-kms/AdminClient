import time
import re
from django.contrib.auth import logout
from django.shortcuts import redirect
from .models import Setting


class CompanyPrefixMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        prefix = request.session.get("url_prefix", "")

        if prefix:
            expected = "/" + prefix
            if path == expected:
                return redirect(expected + "/")
            if path.startswith(expected + "/"):
                suffix = path[len(expected):]
                request.META["SCRIPT_NAME"] = expected
                request.path_info = suffix
                request.path = suffix
            elif request.user.is_authenticated:
                if not any(path.startswith(p) for p in ("/api/", "/static/", "/download-client/", "/favicon")):
                    if path not in ("/login/", "/signup/", "/logout/"):
                        return redirect(expected + path)
                    elif path == "/":
                        return redirect(expected + "/")

        response = self.get_response(request)
        return response


def url_prefix_context(request):
    return {"url_prefix": request.session.get("url_prefix", "")}


class SessionTimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            timeout_str = Setting.get("session_timeout_minutes", "120")
            try:
                timeout_seconds = int(timeout_str) * 60
            except (ValueError, TypeError):
                timeout_seconds = 7200
            if timeout_seconds < 60:
                timeout_seconds = 7200

            last_activity = request.session.get("last_activity_ts")
            if last_activity:
                try:
                    elapsed = time.time() - float(last_activity)
                    if elapsed > timeout_seconds:
                        logout(request)
                        return redirect("/login/?timeout=1")
                except (ValueError, TypeError):
                    pass
            request.session["last_activity_ts"] = str(time.time())

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
