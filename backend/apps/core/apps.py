from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"

    def ready(self):
        from django.apps import apps
        from django.conf import settings

        from .entity_registry import register_entity

        if settings.DATABASES["default"]["ENGINE"].endswith("sqlite3"):
            from .sqlite_compat import patch_select_for_update_for_sqlite

            patch_select_for_update_for_sqlite()

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
