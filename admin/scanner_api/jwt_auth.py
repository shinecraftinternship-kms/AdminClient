"""JWT Authentication for the Scanner API.

Provides token-based authentication alongside the existing session-based auth.
Supports access/refresh token pairs with configurable expiry.
"""

import jwt
import logging
import time
from datetime import timedelta
from functools import wraps

from django.conf import settings
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.utils import timezone as tz

logger = logging.getLogger("scanner_api")

JWT_SECRET = getattr(settings, "JWT_SECRET", settings.SECRET_KEY)
JWT_ALGORITHM = getattr(settings, "JWT_ALGORITHM", "HS256")
JWT_ACCESS_EXPIRY = getattr(settings, "JWT_ACCESS_EXPIRY_MINUTES", 60)
JWT_REFRESH_EXPIRY = getattr(settings, "JWT_REFRESH_EXPIRY_DAYS", 7)
JWT_ISSUER = getattr(settings, "JWT_ISSUER", "system-scanner-pro")


def generate_access_token(user, extra_claims=None):
    """Generate a JWT access token for a user."""
    now = tz.now()
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "email": user.email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=JWT_ACCESS_EXPIRY)).timestamp()),
        "iss": JWT_ISSUER,
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)

    if hasattr(user, "administratorprofile"):
        profile = user.administratorprofile
        payload["role"] = getattr(profile, "role", "admin")

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def generate_refresh_token(user):
    """Generate a JWT refresh token for a user."""
    now = tz.now()
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=JWT_REFRESH_EXPIRY)).timestamp()),
        "iss": JWT_ISSUER,
        "type": "refresh",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token):
    """Decode and verify a JWT token.

    Returns (payload_dict, error_string).
    """
    try:
        payload = jwt.decode(
            token, JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
        )
        return payload, None
    except jwt.ExpiredSignatureError:
        return None, "Token expired"
    except jwt.InvalidTokenError as e:
        return None, f"Invalid token: {str(e)}"


def get_user_from_token(token):
    """Get a Django User from a JWT access token.

    Returns (User, error_string).
    """
    payload, err = decode_token(token)
    if err:
        return None, err

    if payload.get("type") != "access":
        return None, "Not an access token"

    try:
        user = User.objects.get(id=int(payload["sub"]))
    except (User.DoesNotExist, ValueError, TypeError):
        return None, "User not found"

    if not user.is_active:
        return None, "User account disabled"

    return user, ""


def extract_token_from_request(request):
    """Extract JWT token from the Authorization header.

    Returns the token string or None.
    """
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None


def jwt_required(view_func):
    """Decorator that requires a valid JWT access token."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        token = extract_token_from_request(request)
        if not token:
            return JsonResponse(
                {"status": "error", "message": "Missing authorization token"},
                status=401,
            )

        user, err = get_user_from_token(token)
        if err:
            return JsonResponse(
                {"status": "error", "message": err},
                status=401,
            )

        request.user = user
        return view_func(request, *args, **kwargs)

    return wrapper


def jwt_optional(view_func):
    """Decorator that optionally authenticates via JWT (no error if missing)."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        token = extract_token_from_request(request)
        if token:
            user, err = get_user_from_token(token)
            if not err:
                request.user = user
        return view_func(request, *args, **kwargs)

    return wrapper
