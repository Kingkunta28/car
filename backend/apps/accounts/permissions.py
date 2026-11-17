from rest_framework.permissions import BasePermission

from .models import Role

ALL_ROLES = (Role.ADMIN, Role.MANAGER, Role.STAFF)
FINANCE_ROLES = (Role.ADMIN, Role.MANAGER)
ADMIN_ONLY = (Role.ADMIN,)


class DashboardPermission(BasePermission):
    """Default permission for every API view.

    Requires an active staff member with dashboard access. Views narrow the
    allowed roles with ``required_roles`` or per-action ``action_roles``.
    Public views must explicitly declare ``permission_classes = [AllowAny]``.
    """

    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.is_active and getattr(user, "dashboard_access", False)):
            return False
        roles = getattr(view, "required_roles", ALL_ROLES)
        action = getattr(view, "action", None)
        roles = getattr(view, "action_roles", {}).get(action, roles)
        return user.has_role(*roles)
