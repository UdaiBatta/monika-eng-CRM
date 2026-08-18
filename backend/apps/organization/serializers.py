from rest_framework import serializers

from apps.core.tabular_imports import TabularImportUploadSerializer

from .models import Branch, Company, Department, Designation, Employee, Warehouse


class OrganizationImportUploadSerializer(TabularImportUploadSerializer):
    pass


class EmployeeDeactivateSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=3, max_length=500)
    open_work_action = serializers.ChoiceField(
        choices=["LEAVE_TEMPORARILY", "REASSIGN"], required=False
    )
    replacement_employee_id = serializers.UUIDField(required=False)

    def validate(self, attrs):
        if attrs.get("open_work_action") == "REASSIGN" and not attrs.get("replacement_employee_id"):
            raise serializers.ValidationError(
                {"replacement_employee_id": "Choose who will receive the open work."}
            )
        return attrs


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
        read_only_fields = ["id", "record_version", "created_at", "updated_at"]


class BranchSerializer(CleanModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = Branch
        fields = "__all__"
        read_only_fields = ["id", "record_version", "created_at", "updated_at"]


class DepartmentSerializer(CleanModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = Department
        fields = "__all__"
        read_only_fields = ["id", "record_version", "created_at", "updated_at"]


class DesignationSerializer(CleanModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = Designation
        fields = "__all__"
        read_only_fields = ["id", "record_version", "created_at", "updated_at"]


class WarehouseSerializer(CleanModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = Warehouse
        fields = "__all__"
        read_only_fields = ["id", "record_version", "created_at", "updated_at"]


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
        read_only_fields = ["id", "record_version", "created_at", "updated_at"]

    def validate(self, attrs):
        if (
            self.instance
            and attrs.get("employment_status") == Employee.EmploymentStatus.INACTIVE
            and self.instance.employment_status != Employee.EmploymentStatus.INACTIVE
        ):
            raise serializers.ValidationError(
                {"employment_status": "Use Deactivate employee so open work is handled safely."}
            )
        return super().validate(attrs)
