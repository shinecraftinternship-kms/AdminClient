import json
import time
import re
from django.contrib.auth import logout, get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.shortcuts import redirect
from django.urls import resolve, Resolver404
from .models import Setting


def build_url_prefix_path(prefix, path=""):
    if not prefix:
        return f"/{path.lstrip('/')}" if path else "/"

    clean_prefix = str(prefix).strip().strip("/")
    if not clean_prefix:
        return f"/{path.lstrip('/')}" if path else "/"

    clean_path = path.strip()
    if not clean_path:
        return f"/{clean_prefix}/"
    if clean_path.startswith("/"):
        clean_path = clean_path[1:]
    return f"/{clean_prefix}/{clean_path.lstrip('/')}"


def _get_user_from_cookie(request):
    """Return user from scanner_auth cookie if valid, else None."""
    cookie_value = request.COOKIES.get("scanner_auth")
    if not cookie_value:
        return None
    try:
        signer = TimestampSigner(salt="scanner-auth-cookie")
        data = signer.unsign(cookie_value, max_age=60 * 60 * 24 * 30)
        payload = json.loads(data)
        user_id = payload.get("user_id")
        if user_id:
            User = get_user_model()
            user = User.objects.filter(pk=user_id).first()
            if user and user.is_active:
                return user
    except (BadSignature, SignatureExpired, TypeError, ValueError, json.JSONDecodeError):
        pass
    return None


class CookieAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(request, "user", None):
            request.user = AnonymousUser()

        if not getattr(request.user, "is_authenticated", False):
            user = _get_user_from_cookie(request)
            if user:
                request.user = user
                request._cached_user = user

        response = self.get_response(request)
        return response


class CompanyPrefixMiddleware:
    """Strips any legacy /<user>-<company>/ URL prefix so the panel always
    lives at the root URL. Also handles /connect/<user>/<company>/ routes
    by stripping the company prefix when accessed via the prefixed URL."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info

        skip_paths = ("/api/", "/static/", "/download-client/", "/favicon")
        if any(path.startswith(p) for p in skip_paths):
            return self.get_response(request)

        # Never redirect connect pages - they are public
        if "/connect/" in path:
            return self.get_response(request)

        if path.count("/") >= 2:
            prefix = self._extract_prefix_from_url(path)
            if prefix:
                suffix = path[len(prefix) + 1:] or "/"
                if not suffix.startswith("/"):
                    suffix = "/" + suffix
                request.path_info = suffix
                request.path = suffix

        return self.get_response(request)

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
        "url_prefix": "",
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

            now = time.time()
            last_ts = None
            last_activity = request.session.get("last_activity_ts")
            if last_activity:
                try:
                    last_ts = float(last_activity)
                except (ValueError, TypeError):
                    last_ts = None

            if last_ts is not None and now - last_ts > timeout_seconds:
                logout(request)
                return redirect("/login/?timeout=1")

            # Only refresh the activity stamp periodically so we don't mark the
            # session modified (forcing a DB write) on every single request.
            if last_ts is None or now - last_ts >= 60:
                request.session["last_activity_ts"] = str(now)
                request.session.modified = True

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
