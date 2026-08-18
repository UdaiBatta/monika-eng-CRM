from rest_framework import serializers

from .models import Permission, PermissionOverride, Role, RoleAssignment, RolePermission
from .safety import OWNER_PERMISSION, ensure_actor_can_grant, role_grants_owner


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = "__all__"
        read_only_fields = ["id", "record_version", "created_at", "updated_at"]


class RolePermissionSerializer(serializers.ModelSerializer):
    permission_code = serializers.CharField(source="permission.code", read_only=True)

    class Meta:
        model = RolePermission
        fields = "__all__"
        read_only_fields = ["id", "record_version", "created_at", "updated_at"]


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
            "record_version",
            "permission_ids",
            "permission_details",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "record_version", "created_at", "updated_at"]

    def validate(self, attrs):
        company = attrs.get("company") or getattr(self.instance, "company", None)
        permissions = attrs.get("permissions")
        request = self.context.get("request")
        if request and company and permissions is not None:
            ensure_actor_can_grant(request.user, permissions, company)
        return attrs

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
        read_only_fields = ["id", "record_version", "created_at", "updated_at"]

    def validate(self, attrs):
        instance = self.instance or RoleAssignment()
        for field, value in attrs.items():
            setattr(instance, field, value)
        instance.full_clean()
        request = self.context.get("request")
        if request and instance.role_id and role_grants_owner(instance.role):
            ensure_actor_can_grant(
                request.user,
                Permission.objects.filter(code=OWNER_PERMISSION),
                instance.role.company,
            )
        return attrs


class PermissionOverrideSerializer(serializers.ModelSerializer):
    permission_code = serializers.CharField(source="permission.code", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = PermissionOverride
        fields = "__all__"
        read_only_fields = ["id", "record_version", "created_at", "updated_at"]

    def validate(self, attrs):
        instance = self.instance or PermissionOverride()
        for field, value in attrs.items():
            setattr(instance, field, value)
        instance.full_clean()
        request = self.context.get("request")
        if (
            request
            and instance.permission_id
            and instance.permission.code == OWNER_PERMISSION
            and instance.effect == PermissionOverride.Effect.ALLOW
        ):
            ensure_actor_can_grant(request.user, [instance.permission], instance.company)
        return attrs
