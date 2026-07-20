"""Role-Based Access Control (RBAC) permission classes for DRF."""

from rest_framework.permissions import BasePermission


ROLE_HIERARCHY = {
    "super_admin": 3,
    "admin": 2,
    "viewer": 1,
}


def _get_user_role(user):
    """Extract the user's role from their profile."""
    if user.is_superuser:
        return "super_admin"
    if hasattr(user, "administratorprofile"):
        return getattr(user.administratorprofile, "role", "admin")
    return "admin" if user.is_staff else "viewer"


def _role_level(role):
    return ROLE_HIERARCHY.get(role, 0)


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = _get_user_role(request.user)
        return role == "super_admin" or request.user.is_superuser


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = _get_user_role(request.user)
        return _role_level(role) >= _role_level("admin")


class IsViewer(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return True


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return request.user and request.user.is_authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        role = _get_user_role(request.user)
        return _role_level(role) >= _role_level("admin")


class HasRole(BasePermission):
    """Permission that checks for specific roles."""

    required_role = "admin"

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = _get_user_role(request.user)
        if role == "super_admin":
            return True
        return _role_level(role) >= _role_level(self.required_role)


class CanManageDevices(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        role = _get_user_role(request.user)
        return _role_level(role) >= _role_level("admin")


class CanManageAlerts(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        role = _get_user_role(request.user)
        return _role_level(role) >= _role_level("admin")


class CanViewReports(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return True


class CanGenerateReports(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = _get_user_role(request.user)
        return _role_level(role) >= _role_level("admin")


class CanManageSchedules(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        role = _get_user_role(request.user)
        return _role_level(role) >= _role_level("admin")
