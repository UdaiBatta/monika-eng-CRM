from rest_framework import serializers

from .models import Permission, PermissionOverride, Role, RoleAssignment, RolePermission


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class RolePermissionSerializer(serializers.ModelSerializer):
    permission_code = serializers.CharField(source="permission.code", read_only=True)

    class Meta:
        model = RolePermission
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class RoleSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    permission_ids = serializers.PrimaryKeyRelatedField(
        source="permissions",
        many=True,
        queryset=Permission.objects.filter(is_active=True),
        write_only=True,
        required=False,
    )
    permission_details = PermissionSerializer(source="permissions", many=True, read_only=True)

    class Meta:
        model = Role
        fields = [
            "id",
            "company",
            "company_name",
            "code",
            "name",
            "description",
            "is_active",
            "permission_ids",
            "permission_details",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        permissions = validated_data.pop("permissions", [])
        role = super().create(validated_data)
        RolePermission.objects.bulk_create(
            [RolePermission(role=role, permission=item) for item in permissions]
        )
        return role

    def update(self, instance, validated_data):
        permissions = validated_data.pop("permissions", None)
        role = super().update(instance, validated_data)
        if permissions is not None:
            role.role_permissions.all().delete()
            RolePermission.objects.bulk_create(
                [RolePermission(role=role, permission=item) for item in permissions]
            )
        return role


class RoleAssignmentSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source="role.name", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = RoleAssignment
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        instance = self.instance or RoleAssignment()
        for field, value in attrs.items():
            setattr(instance, field, value)
        instance.full_clean()
        return attrs


class PermissionOverrideSerializer(serializers.ModelSerializer):
    permission_code = serializers.CharField(source="permission.code", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = PermissionOverride
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        instance = self.instance or PermissionOverride()
        for field, value in attrs.items():
            setattr(instance, field, value)
        instance.full_clean()
        return attrs
