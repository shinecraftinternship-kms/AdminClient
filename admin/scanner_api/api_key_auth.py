"""API Key authentication for programmatic access.

Provides API key-based authentication for third-party integrations
and automated systems that cannot use session or JWT auth.
"""

import hashlib
import secrets
import logging
from datetime import timedelta
from functools import wraps

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.http import JsonResponse
from django.utils import timezone as tz

logger = logging.getLogger("scanner_api")


class ApiKey(models.Model):
    """API key for programmatic access."""

    id = models.BigAutoField(primary_key=True)
    key = models.CharField(max_length=64, unique=True, db_index=True)
    key_hash = models.CharField(max_length=128, db_index=True)
    name = models.CharField(max_length=128)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="api_keys")

    is_active = models.BooleanField(default=True)
    rate_limit = models.IntegerField(default=60, help_text="Requests per minute")
    allowed_ips = models.TextField(default="", blank=True, help_text="Comma-separated IPs")

    expires_at = models.DateTimeField(null=True, blank=True)
    last_used = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "scanner_api"
        db_table = "api_keys"
        ordering = ["-created_at"]

    def __str__(self):
        return f"ApiKey({self.name} for {self.user.username})"

    @staticmethod
    def generate_key():
        return secrets.token_hex(32)

    @staticmethod
    def hash_key(key):
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def is_valid(self):
        if not self.is_active:
            return False
        if self.expires_at and tz.now() > self.expires_at:
            return False
        return True

    def check_ip(self, ip):
        if not self.allowed_ips:
            return True
        allowed = [a.strip() for a in self.allowed_ips.split(",") if a.strip()]
        return ip in allowed


def create_api_key(user, name, rate_limit=60, expires_days=None, allowed_ips=""):
    """Create a new API key for a user."""
    raw_key = ApiKey.generate_key()
    key_hash = ApiKey.hash_key(raw_key)

    expires_at = None
    if expires_days:
        expires_at = tz.now() + timedelta(days=expires_days)

    api_key = ApiKey.objects.create(
        key=raw_key[:8] + "..." + raw_key[-8:],
        key_hash=key_hash,
        name=name,
        user=user,
        rate_limit=rate_limit,
        allowed_ips=allowed_ips,
        expires_at=expires_at,
    )

    return api_key, raw_key


def authenticate_api_key(request):
    """Authenticate a request via API key header.

    Reads X-API-Key header.
    Returns (User, error_string).
    """
    api_key_str = request.META.get("HTTP_X_API_KEY", "")
    if not api_key_str:
        return None, "Missing X-API-Key header"

    key_hash = ApiKey.hash_key(api_key_str)

    try:
        api_key = ApiKey.objects.select_related("user").get(key_hash=key_hash)
    except ApiKey.DoesNotExist:
        return None, "Invalid API key"

    if not api_key.is_valid():
        return None, "API key expired or disabled"

    client_ip = _get_client_ip(request)
    if not api_key.check_ip(client_ip):
        return None, "IP not allowed"

    api_key.last_used = tz.now()
    api_key.save(update_fields=["last_used"])

    return api_key.user, ""


def _get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def api_key_required(view_func):
    """Decorator that requires a valid API key."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user, err = authenticate_api_key(request)
        if err:
            return JsonResponse(
                {"status": "error", "message": err},
                status=401,
            )
        request.user = user
        return view_func(request, *args, **kwargs)

    return wrapper
