"""JWT token and API key management views."""

import json
import logging
from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .jwt_auth import (
    generate_access_token,
    generate_refresh_token,
    decode_token,
    get_user_from_token,
)
from .api_key_auth import ApiKey, create_api_key, authenticate_api_key

logger = logging.getLogger("scanner_api")


@method_decorator(csrf_exempt, name="dispatch")
class TokenObtainView(View):
    """POST /api/auth/token/obtain  —  Login, returns JWT pair."""

    def post(self, request):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

        username = data.get("username", "").strip()
        password = data.get("password", "")

        if not username or not password:
            return JsonResponse(
                {"status": "error", "message": "Username and password required"},
                status=400,
            )

        user = authenticate(request, username=username, password=password)
        if user is None:
            return JsonResponse(
                {"status": "error", "message": "Invalid credentials"},
                status=401,
            )

        if not user.is_active:
            return JsonResponse(
                {"status": "error", "message": "Account disabled"},
                status=403,
            )

        access_token = generate_access_token(user)
        refresh_token = generate_refresh_token(user)

        role = "admin"
        if hasattr(user, "administratorprofile"):
            role = getattr(user.administratorprofile, "role", "admin")
        if user.is_superuser:
            role = "super_admin"

        return JsonResponse({
            "status": "ok",
            "access": access_token,
            "refresh": refresh_token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": role,
                "is_superuser": user.is_superuser,
            },
        })


@method_decorator(csrf_exempt, name="dispatch")
class TokenRefreshView(View):
    """POST /api/auth/token/refresh  —  Exchange refresh token for new access token."""

    def post(self, request):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

        refresh_token = data.get("refresh", "")
        if not refresh_token:
            return JsonResponse(
                {"status": "error", "message": "Refresh token required"},
                status=400,
            )

        payload, err = decode_token(refresh_token)
        if payload is None:
            return JsonResponse(
                {"status": "error", "message": err or "Invalid or expired refresh token"},
                status=401,
            )

        if payload.get("type") != "refresh":
            return JsonResponse(
                {"status": "error", "message": "Token is not a refresh token"},
                status=401,
            )

        user, err = get_user_from_token(payload)
        if user is None:
            return JsonResponse(
                {"status": "error", "message": "User not found"},
                status=401,
            )

        new_access = generate_access_token(user)

        return JsonResponse({
            "status": "ok",
            "access": new_access,
            "token_type": "Bearer",
            "expires_in": 3600,
        })


@method_decorator(csrf_exempt, name="dispatch")
class TokenVerifyView(View):
    """POST /api/auth/token/verify  —  Validate an access token."""

    def post(self, request):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

        token = data.get("token", "")
        if not token:
            return JsonResponse(
                {"status": "error", "message": "Token required"},
                status=400,
            )

        payload, err = decode_token(token)
        if payload is None:
            return JsonResponse(
                {"valid": False, "status": "invalid"},
                status=401,
            )

        user, err = get_user_from_token(payload)
        if user is None:
            return JsonResponse(
                {"valid": False, "status": "invalid"},
                status=401,
            )

        return JsonResponse({
            "status": "ok",
            "valid": True,
            "user_id": user.id,
            "username": user.username,
            "expires": payload.get("exp"),
        })


@method_decorator(csrf_exempt, name="dispatch")
class ApiKeyListView(View):
    """GET  /api/auth/api-keys  —  List API keys for authenticated user.
       POST /api/auth/api-keys  —  Create a new API key."""

    def get(self, request):
        user, err = self._authenticate(request)
        if err:
            return JsonResponse({"status": "error", "message": err}, status=401)

        keys = ApiKey.objects.filter(user=user).values(
            "id", "name", "is_active", "rate_limit", "last_used", "created_at", "expires_at"
        )
        return JsonResponse({"status": "ok", "keys": list(keys)})

    def post(self, request):
        user, err = self._authenticate(request)
        if err:
            return JsonResponse({"status": "error", "message": err}, status=401)

        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

        name = data.get("name", "").strip()
        if not name:
            return JsonResponse(
                {"status": "error", "message": "Key name required"},
                status=400,
            )

        rate_limit = data.get("rate_limit", 60)
        expires_days = data.get("expires_days")
        allowed_ips = data.get("allowed_ips", "")

        api_key_obj, raw_key = create_api_key(
            user=user,
            name=name,
            rate_limit=rate_limit,
            expires_days=expires_days,
            allowed_ips=allowed_ips,
        )

        return JsonResponse({
            "status": "ok",
            "id": api_key_obj.id,
            "name": api_key_obj.name,
            "key": raw_key,
            "rate_limit": api_key_obj.rate_limit,
            "expires_at": str(api_key_obj.expires_at) if api_key_obj.expires_at else None,
            "message": "Store this key securely — it will not be shown again",
        }, status=201)

    @staticmethod
    def _authenticate(request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            payload, err = decode_token(token)
            if payload and payload.get("type") == "access":
                user, err = get_user_from_token(payload)
                if user:
                    return user, ""

        user, err = authenticate_api_key(request)
        return user, err


@method_decorator(csrf_exempt, name="dispatch")
class ApiKeyDeleteView(View):
    """DELETE /api/auth/api-keys/<key_id>  —  Revoke an API key."""

    def delete(self, request, key_id):
        user, err = ApiKeyListView._authenticate(request)
        if err:
            return JsonResponse({"status": "error", "message": err}, status=401)

        deleted, _ = ApiKey.objects.filter(id=key_id, user=user).delete()
        if deleted:
            return JsonResponse({"status": "ok", "message": "API key revoked"})
        return JsonResponse({"status": "error", "message": "Key not found"}, status=404)
