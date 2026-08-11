from rest_framework import serializers

from apps.core.tabular_imports import TabularImportUploadSerializer

from .models import Branch, Company, Department, Designation, Employee, Warehouse


class OrganizationImportUploadSerializer(TabularImportUploadSerializer):
    pass


class CleanModelSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        instance = self.instance or self.Meta.model()
        for field, value in attrs.items():
            setattr(instance, field, value)
        instance.full_clean()
        return attrs


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class BranchSerializer(CleanModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = Branch
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class DepartmentSerializer(CleanModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = Department
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class DesignationSerializer(CleanModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = Designation
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class WarehouseSerializer(CleanModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = Warehouse
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class EmployeeSerializer(CleanModelSerializer):
    display_name = serializers.CharField(read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    designation_name = serializers.CharField(source="designation.name", read_only=True)
    reporting_manager_name = serializers.CharField(source="reporting_manager.display_name", read_only=True)

    class Meta:
        model = Employee
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]
