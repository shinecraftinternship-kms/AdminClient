import time
import re
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import resolve, Resolver404
from .models import Setting


class CompanyPrefixMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info

        skip_paths = ("/api/", "/static/", "/download-client/", "/favicon")
        if any(path.startswith(p) for p in skip_paths):
            return self.get_response(request)

        if path in ("/login/", "/signup/", "/logout/"):
            return self.get_response(request)

        prefix = self._get_prefix(request, path)

        if prefix:
            expected = "/" + prefix
            if path == expected:
                return redirect(expected + "/")
            if path.startswith(expected + "/"):
                suffix = path[len(expected):]
                request.path_info = suffix or "/"
                request.path = suffix or "/"
                request.session["url_prefix"] = prefix
                return self.get_response(request)
            if request.user.is_authenticated:
                target = expected + path
                if target.endswith("//"):
                    target = target.rstrip("/") + "/"
                return redirect(target)

        return self.get_response(request)

    def _get_prefix(self, request, path):
        prefix_from_session = request.session.get("url_prefix", "")
        if prefix_from_session:
            return prefix_from_session

        prefix_from_url = self._extract_prefix_from_url(path)
        if prefix_from_url:
            return prefix_from_url

        return ""

    def _extract_prefix_from_url(self, path):
        try:
            resolve(path)
            return ""
        except Resolver404:
            pass
        if path.count("/") >= 2:
            first_slash = path.index("/", 1)
            if first_slash > 0:
                candidate = path[1:first_slash]
                if candidate and "/" not in candidate:
                    suffix = path[first_slash:]
                    if suffix in ("", "/"):
                        return ""
                    try:
                        resolve(suffix)
                        return candidate
                    except Resolver404:
                        pass
        return ""


def url_prefix_context(request):
    from django.conf import settings
    return {
        "url_prefix": request.session.get("url_prefix", ""),
        "IS_VERCEL": getattr(settings, "IS_VERCEL", False),
    }


class SessionTimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            timeout_seconds = 7200
            try:
                timeout_str = Setting.get("session_timeout_minutes", "120")
                timeout_seconds = int(timeout_str) * 60
                if timeout_seconds < 60:
                    timeout_seconds = 7200
            except Exception:
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
