from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"

    def ready(self):
        from django.apps import apps

        from .entity_registry import register_entity

        registrations = (
            ("user", "accounts", "User", {"audit"}),
            ("company", "organization", "Company", {"audit"}),
            ("branch", "organization", "Branch", {"audit"}),
            ("department", "organization", "Department", {"audit"}),
            ("designation", "organization", "Designation", {"audit"}),
            ("warehouse", "organization", "Warehouse", {"audit"}),
            ("employee", "organization", "Employee", {"audit"}),
            ("role", "rbac", "Role", {"audit"}),
            ("role_assignment", "rbac", "RoleAssignment", {"audit"}),
            ("permission_override", "rbac", "PermissionOverride", {"audit"}),
            ("company_settings", "configuration", "CompanySettings", {"audit"}),
            ("feature_flag", "configuration", "FeatureFlag", {"audit"}),
            ("document_sequence", "numbering", "DocumentSequence", {"audit"}),
        )
        for key, app_label, model_name, capabilities in registrations:
            register_entity(key, lambda a=app_label, m=model_name: apps.get_model(a, m), capabilities)
