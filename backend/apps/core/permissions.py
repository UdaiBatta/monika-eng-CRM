from rest_framework.permissions import BasePermission

from apps.rbac.services import authorized_queryset, has_permission


class HasFoundationPermission(BasePermission):
    """Map view-set actions to data-driven permission codes."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        permission_map = getattr(view, "permission_map", {})
        code = permission_map.get(getattr(view, "action", None), permission_map.get("default"))
        return request.user.is_superuser or (bool(code) and has_permission(request.user, code))

    def has_object_permission(self, request, view, obj):
        permission_map = getattr(view, "permission_map", {})
        code = permission_map.get(getattr(view, "action", None), permission_map.get("default"))
        return request.user.is_superuser or (bool(code) and has_permission(request.user, code, obj))


class ScopedQuerysetMixin:
    def get_queryset(self):
        queryset = super().get_queryset()
        user = getattr(self.request, "user", None)
        if not user or not user.is_authenticated or user.is_superuser:
            return queryset
        permission_map = getattr(self, "permission_map", {})
        code = permission_map.get(getattr(self, "action", None), permission_map.get("default"))
        return authorized_queryset(user, code, queryset) if code else queryset.none()
