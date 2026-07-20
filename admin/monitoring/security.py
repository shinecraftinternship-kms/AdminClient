import hashlib
import hmac
import logging
import secrets
import time
from collections import defaultdict

from django.utils import timezone

logger = logging.getLogger("monitoring")


def generate_api_secret():
    """Generate a 64-char hex token for agent authentication."""
    return secrets.token_hex(32)


def compute_signature(body: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature of a request body."""
    return hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()


def verify_signature(body: bytes, signature: str, secret: str, max_age_seconds: int = 300) -> tuple:
    """Verify HMAC-SHA256 signature and timestamp freshness.

    Returns (is_valid: bool, error_message: str).
    """
    if not signature or not secret:
        return False, "Missing signature or secret"

    expected = compute_signature(body, secret)
    if not hmac.compare_digest(expected, signature):
        return False, "Invalid signature"

    return True, ""


def verify_timestamp(request, max_age_seconds: int = 300) -> tuple:
    """Validate the X-Timestamp header to prevent replay attacks.

    Returns (is_valid, error_message).
    """
    ts_header = request.META.get("HTTP_X_TIMESTAMP", "")
    if not ts_header:
        return False, "Missing X-Timestamp header"

    try:
        ts = float(ts_header)
    except (ValueError, TypeError):
        return False, "Invalid X-Timestamp"

    now = time.time()
    if abs(now - ts) > max_age_seconds:
        return False, f"Timestamp expired (max {max_age_seconds}s)"

    return True, ""


class RateLimiter:
    """Simple in-memory rate limiter keyed by device or IP."""

    _store = defaultdict(list)

    @classmethod
    def check(cls, key: str, max_requests: int = 60, window_seconds: int = 60) -> bool:
        """Return True if request is allowed (under limit)."""
        now = time.time()
        cutoff = now - window_seconds
        cls._store[key] = [t for t in cls._store[key] if t > cutoff]
        if len(cls._store[key]) >= max_requests:
            return False
        cls._store[key].append(now)
        return True

    @classmethod
    def cleanup(cls):
        """Remove expired entries."""
        now = time.time()
        keys_to_remove = []
        for key, timestamps in cls._store.items():
            cls._store[key] = [t for t in timestamps if t > now - 300]
            if not cls._store[key]:
                keys_to_remove.append(key)
        for key in keys_to_remove:
            del cls._store[key]


def authenticate_agent(request):
    """Authenticate an incoming agent request.

    Reads X-Agent-ID, X-Signature, X-Timestamp headers.
    Returns (agent_secret_or_None, error_message).
    """
    from .models import AgentSecret

    agent_id = request.META.get("HTTP_X_AGENT_ID", "")
    signature = request.META.get("HTTP_X_SIGNATURE", "")

    if not agent_id:
        return None, "Missing X-Agent-ID header"

    if not signature:
        return None, "Missing X-Signature header"

    ts_valid, ts_err = verify_timestamp(request)
    if not ts_valid:
        return None, ts_err

    try:
        agent_secret = AgentSecret.objects.select_related("client").get(
            agent_id=agent_id, is_active=True
        )
    except AgentSecret.DoesNotExist:
        return None, "Unknown or inactive agent"

    body = request.body or b""
    sig_valid, sig_err = verify_signature(body, signature, agent_secret.secret_key)
    if not sig_valid:
        return None, sig_err

    agent_secret.last_used = timezone.now()
    agent_secret.save(update_fields=["last_used"])

    return agent_secret, ""


def validate_fingerprint_match(agent_secret, incoming_fingerprint: str) -> bool:
    """Check if incoming fingerprint matches the stored one.

    Returns True if match or if no stored fingerprint.
    Logs warning on mismatch.
    """
    if not agent_secret.device_fingerprint:
        return True
    if not incoming_fingerprint:
        return True
    if agent_secret.device_fingerprint == incoming_fingerprint:
        return True

    logger.warning(
        "Fingerprint mismatch for agent %s: stored=%s incoming=%s",
        agent_secret.agent_id,
        agent_secret.device_fingerprint,
        incoming_fingerprint,
    )
    return False


def get_client_ip(request) -> str:
    """Extract client IP from request."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")
