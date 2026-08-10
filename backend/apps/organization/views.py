from rest_framework import viewsets

from apps.audit.mixins import AuditModelViewSetMixin
from apps.core.permissions import HasFoundationPermission, ScopedQuerysetMixin

from .models import Branch, Company, Department, Designation, Employee, Warehouse
from .serializers import (
    BranchSerializer,
    CompanySerializer,
    DepartmentSerializer,
    DesignationSerializer,
    EmployeeSerializer,
    WarehouseSerializer,
)


class FoundationModelViewSet(AuditModelViewSetMixin, ScopedQuerysetMixin, viewsets.ModelViewSet):
    permission_classes = [HasFoundationPermission]
    filterset_fields = ["is_active"]
    ordering_fields = ["name", "code", "created_at", "updated_at"]


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
