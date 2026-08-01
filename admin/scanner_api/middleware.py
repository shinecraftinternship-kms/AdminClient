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
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info

        skip_paths = ("/api/", "/static/", "/download-client/", "/favicon")
        if any(path.startswith(p) for p in skip_paths):
            return self.get_response(request)

        if path in ("/login/", "/signup/", "/logout/"):
            return self.get_response(request)

        # Ensure we have a user (fallback to cookie if AuthenticationMiddleware missed it)
        if not getattr(request.user, "is_authenticated", False):
            cookie_user = _get_user_from_cookie(request)
            if cookie_user:
                request.user = cookie_user

        prefix = self._get_prefix(request, path)

        # Persist prefix in session for later requests
        if prefix and request.session.get("url_prefix") != prefix:
            request.session["url_prefix"] = prefix

        if prefix:
            expected = "/" + prefix
            if path == expected:
                return redirect(expected + "/")
            if path.startswith(expected + "/"):
                suffix = path[len(expected):]
                request.path_info = suffix or "/"
                request.path = suffix or "/"
                return self.get_response(request)
            # Authenticated user but missing prefix → redirect to prefixed URL
            if request.user.is_authenticated:
                target = expected + path
                if target.endswith("//"):
                    target = target.rstrip("/") + "/"
                return redirect(target)

        # No prefix in URL and user authenticated → compute prefix and redirect
        if request.user.is_authenticated and not prefix:
            computed = self._compute_prefix_from_user(request.user)
            if computed:
                request.session["url_prefix"] = computed
                target = f"/{computed}{path}"
                if target.endswith("//"):
                    target = target.rstrip("/") + "/"
                return redirect(target)

        return self.get_response(request)

    def _get_prefix(self, request, path):
        # 1️⃣ session
        prefix_from_session = request.session.get("url_prefix", "")
        if prefix_from_session:
            return prefix_from_session

        # 2️⃣ URL
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

    def _compute_prefix_from_user(self, user):
        from django.utils.text import slugify
        from .models import AdministratorProfile
        profile = AdministratorProfile.objects.filter(user=user).select_related("company").first()
        if not profile or not profile.company:
            return ""
        user_part = slugify(user.username) or "admin"
        company_part = slugify(profile.company.slug) or slugify(profile.company.name) or "default"
        return f"{user_part}-{company_part}"


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
