from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.accounts.models import User
from apps.audit.mixins import AuditModelViewSetMixin
from apps.core.concurrency import VersionedUpdateMixin
from apps.core.permissions import HasFoundationPermission, ScopedQuerysetMixin

from .models import Permission, PermissionOverride, Role, RoleAssignment, RolePermission
from .serializers import (
    PermissionOverrideSerializer,
    PermissionSerializer,
    RoleAssignmentSerializer,
    RolePermissionSerializer,
    RoleSerializer,
)
from .services import effective_permission_codes, explain_permission
from .view_mixins import OwnerContinuityMixin


class PermissionViewSet(
    VersionedUpdateMixin, AuditModelViewSetMixin, ScopedQuerysetMixin, viewsets.ModelViewSet
):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "list": "rbac.permission.view",
        "retrieve": "rbac.permission.view",
        "effective": "rbac.permission.view",
        "explain": "system.access_explanation.view",
        "default": "rbac.permission.manage",
    }
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    search_fields = ["code", "name", "description"]
    filterset_fields = ["is_active"]
    ordering_fields = ["code", "name", "created_at"]

    @action(detail=False, methods=["get"])
    def effective(self, request):
        return Response({"permissions": effective_permission_codes(request.user)})

    @action(detail=False, methods=["post"])
    def explain(self, request):
        user_id = request.data.get("user_id")
        permission_code = str(request.data.get("permission_code", "")).strip()
        if not user_id or not permission_code:
            raise ValidationError("Choose an employee account and an action to explain.")
        try:
            target = User.objects.select_related("employee__company").get(pk=user_id)
        except (User.DoesNotExist, ValueError) as exc:
            raise ValidationError("Choose a valid user account.") from exc
        target_employee = getattr(target, "employee", None)
        requester_employee = getattr(request.user, "employee", None)
        if not request.user.is_superuser and (
            not target_employee
            or not requester_employee
            or target_employee.company_id != requester_employee.company_id
        ):
            raise PermissionDenied("You can only explain access inside your company.")
        context = target_employee.company if target_employee else None
        return Response(explain_permission(target, permission_code, context))


class RoleViewSet(
    OwnerContinuityMixin, AuditModelViewSetMixin, ScopedQuerysetMixin, viewsets.ModelViewSet
):
    queryset = Role.objects.select_related("company").prefetch_related("role_permissions__permission")
    serializer_class = RoleSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {"list": "rbac.role.view", "retrieve": "rbac.role.view", "default": "rbac.role.manage"}
    search_fields = ["name", "code", "company__name"]
    filterset_fields = ["company", "is_active"]
    ordering_fields = ["name", "code", "created_at"]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]


class RolePermissionViewSet(ScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = RolePermission.objects.select_related("role", "permission")
    serializer_class = RolePermissionSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {"list": "rbac.role.view", "retrieve": "rbac.role.view"}
    filterset_fields = ["role", "permission"]


class RoleAssignmentViewSet(
    OwnerContinuityMixin, AuditModelViewSetMixin, ScopedQuerysetMixin, viewsets.ModelViewSet
):
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
    http_method_names = ["get", "post", "put", "patch", "head", "options"]


class PermissionOverrideViewSet(
    OwnerContinuityMixin, AuditModelViewSetMixin, ScopedQuerysetMixin, viewsets.ModelViewSet
):
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
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
