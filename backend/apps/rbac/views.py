from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.permissions import HasFoundationPermission, ScopedQuerysetMixin

from .models import Permission, PermissionOverride, Role, RoleAssignment, RolePermission
from .serializers import (
    PermissionOverrideSerializer,
    PermissionSerializer,
    RoleAssignmentSerializer,
    RolePermissionSerializer,
    RoleSerializer,
)
from .services import effective_permission_codes


class PermissionViewSet(ScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "list": "rbac.permission.view",
        "retrieve": "rbac.permission.view",
        "effective": "rbac.permission.view",
        "default": "rbac.permission.manage",
    }
    search_fields = ["code", "name", "description"]
    filterset_fields = ["is_active"]
    ordering_fields = ["code", "name", "created_at"]

    @action(detail=False, methods=["get"])
    def effective(self, request):
        return Response({"permissions": effective_permission_codes(request.user)})


class RoleViewSet(ScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Role.objects.select_related("company").prefetch_related("role_permissions__permission")
    serializer_class = RoleSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {"list": "rbac.role.view", "retrieve": "rbac.role.view", "default": "rbac.role.manage"}
    search_fields = ["name", "code", "company__name"]
    filterset_fields = ["company", "is_active"]
    ordering_fields = ["name", "code", "created_at"]


class RolePermissionViewSet(ScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = RolePermission.objects.select_related("role", "permission")
    serializer_class = RolePermissionSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {"list": "rbac.role.view", "retrieve": "rbac.role.view", "default": "rbac.role.manage"}
    filterset_fields = ["role", "permission"]


class RoleAssignmentViewSet(ScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = RoleAssignment.objects.select_related(
        "user", "role", "company", "branch", "department", "warehouse"
    )
    serializer_class = RoleAssignmentSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "list": "rbac.assignment.view",
        "retrieve": "rbac.assignment.view",
        "default": "rbac.assignment.manage",
    }
    search_fields = ["user__email", "role__name"]
    filterset_fields = [
        "user",
        "role",
        "scope_type",
        "company",
        "branch",
        "department",
        "warehouse",
        "is_active",
    ]


class PermissionOverrideViewSet(ScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = PermissionOverride.objects.select_related(
        "user", "permission", "company", "branch", "department", "warehouse"
    )
    serializer_class = PermissionOverrideSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "list": "rbac.override.view",
        "retrieve": "rbac.override.view",
        "default": "rbac.override.manage",
    }
    search_fields = ["user__email", "permission__code", "reason"]
    filterset_fields = [
        "user",
        "permission",
        "effect",
        "scope_type",
        "company",
        "branch",
        "department",
        "warehouse",
        "is_active",
    ]
