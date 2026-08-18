from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.audit.mixins import AuditModelViewSetMixin
from apps.audit.models import AuditEvent
from apps.audit.services import record_event
from apps.core.concurrency import VersionedUpdateMixin
from apps.core.owner_services import bulk_reassign, work_items
from apps.core.permissions import HasFoundationPermission, ScopedQuerysetMixin
from apps.rbac.safety import active_business_owners

from .imports import import_organization_records
from .models import Branch, Company, Department, Designation, Employee, Warehouse
from .serializers import (
    BranchSerializer,
    CompanySerializer,
    DepartmentSerializer,
    DesignationSerializer,
    EmployeeDeactivateSerializer,
    EmployeeSerializer,
    OrganizationImportUploadSerializer,
    WarehouseSerializer,
)


class FoundationModelViewSet(
    VersionedUpdateMixin, AuditModelViewSetMixin, ScopedQuerysetMixin, viewsets.ModelViewSet
):
    permission_classes = [HasFoundationPermission]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    filterset_fields = ["is_active"]
    ordering_fields = ["name", "code", "created_at", "updated_at"]

    @action(detail=False, methods=["post"], url_path="import-history")
    def import_history(self, request):
        upload_serializer = OrganizationImportUploadSerializer(data=request.data)
        upload_serializer.is_valid(raise_exception=True)
        created = import_organization_records(self, upload_serializer.validated_data["file"])
        return Response({"imported": len(created)}, status=status.HTTP_201_CREATED)


class CompanyViewSet(FoundationModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    search_fields = ["name", "legal_name", "code", "gstin", "pan"]
    permission_map = {
        "list": "organization.company.view",
        "retrieve": "organization.company.view",
        "default": "organization.company.manage",
    }


class BranchViewSet(FoundationModelViewSet):
    queryset = Branch.objects.select_related("company")
    serializer_class = BranchSerializer
    search_fields = ["name", "code", "company__name"]
    filterset_fields = ["is_active", "company"]
    permission_map = {
        "list": "organization.branch.view",
        "retrieve": "organization.branch.view",
        "default": "organization.branch.manage",
    }


class DepartmentViewSet(FoundationModelViewSet):
    queryset = Department.objects.select_related("company", "branch", "parent")
    serializer_class = DepartmentSerializer
    search_fields = ["name", "code", "company__name"]
    filterset_fields = ["is_active", "company", "branch"]
    permission_map = {
        "list": "organization.department.view",
        "retrieve": "organization.department.view",
        "default": "organization.department.manage",
    }


class DesignationViewSet(FoundationModelViewSet):
    queryset = Designation.objects.select_related("company")
    serializer_class = DesignationSerializer
    search_fields = ["name", "code", "company__name"]
    filterset_fields = ["is_active", "company"]
    permission_map = {
        "list": "organization.designation.view",
        "retrieve": "organization.designation.view",
        "default": "organization.designation.manage",
    }


class WarehouseViewSet(FoundationModelViewSet):
    queryset = Warehouse.objects.select_related("company", "branch")
    serializer_class = WarehouseSerializer
    search_fields = ["name", "code", "company__name", "branch__name"]
    filterset_fields = ["is_active", "company", "branch"]
    permission_map = {
        "list": "organization.warehouse.view",
        "retrieve": "organization.warehouse.view",
        "default": "organization.warehouse.manage",
    }


class EmployeeViewSet(FoundationModelViewSet):
    queryset = Employee.objects.select_related(
        "user", "company", "branch", "department", "designation", "reporting_manager"
    )
    serializer_class = EmployeeSerializer
    search_fields = ["employee_code", "first_name", "last_name", "company_email", "phone"]
    filterset_fields = [
        "company",
        "branch",
        "department",
        "designation",
        "employment_status",
        "employment_type",
    ]
    ordering_fields = ["employee_code", "first_name", "joining_date", "created_at", "updated_at"]
    permission_map = {
        "list": "organization.employee.view",
        "retrieve": "organization.employee.view",
        "default": "organization.employee.manage",
    }

    @action(detail=True, methods=["get"], url_path="deactivation-impact")
    def deactivation_impact(self, request, pk=None):
        employee = self.get_object()
        assigned_work = work_items(employee.company, employee_id=employee.pk)
        return Response(
            {
                "employee_id": str(employee.pk),
                "open_work_count": len(assigned_work),
                "work": assigned_work,
                "options": ["REASSIGN", "LEAVE_TEMPORARILY"] if assigned_work else [],
            }
        )

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def deactivate(self, request, pk=None):
        serializer = EmployeeDeactivateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        employee = Employee.objects.select_for_update().select_related("user", "company").get(
            pk=self.get_object().pk
        )
        if employee.user_id == request.user.pk:
            raise ValidationError("You cannot deactivate your own employee record.")
        owners = active_business_owners(employee.company)
        if employee.user in owners and len(owners) == 1:
            raise ValidationError(
                "This employee has the final business Owner account. Give Owner access to another "
                "active account first."
            )
        assigned_work = work_items(employee.company, employee_id=employee.pk)
        action_name = serializer.validated_data.get("open_work_action")
        if assigned_work and not action_name:
            raise ValidationError(
                {
                    "open_work_action": [
                        f"This employee has {len(assigned_work)} open work items. Reassign them or "
                        "choose Leave Temporarily."
                    ]
                }
            )
        if assigned_work and action_name == "REASSIGN":
            bulk_reassign(
                company=employee.company,
                items=[{"work_type": item["work_type"], "id": item["id"]} for item in assigned_work],
                employee_id=serializer.validated_data["replacement_employee_id"],
                reason=serializer.validated_data["reason"],
                actor=request.user,
            )
        previous_status = employee.employment_status
        employee.employment_status = Employee.EmploymentStatus.INACTIVE
        employee.record_version += 1
        employee.save(update_fields=["employment_status", "record_version", "updated_at"])
        if employee.user:
            employee.user.is_active = False
            employee.user.record_version += 1
            employee.user.save(update_fields=["is_active", "record_version"])
        record_event(
            actor=request.user,
            company=employee.company,
            action=AuditEvent.Action.DEACTIVATE,
            entity=employee,
            summary=f"Employee deactivated: {employee.display_name}",
            changes={
                "employment_status": {
                    "old": previous_status,
                    "new": Employee.EmploymentStatus.INACTIVE,
                }
            },
            metadata={
                "reason": serializer.validated_data["reason"],
                "open_work_action": action_name or "NO_OPEN_WORK",
            },
        )
        return Response(self.get_serializer(employee).data)
