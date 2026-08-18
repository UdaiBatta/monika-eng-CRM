from django.apps import AppConfig, apps


class ProjectsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.projects"

    def ready(self):
        from apps.core.entity_registry import register_entity

        register_entity(
            "project",
            lambda: apps.get_model("projects", "Project"),
            {"audit", "documents", "notifications"},
            {"status", "priority", "sales_owner_id", "engineering_owner_id"},
        )
        register_entity(
            "project_engineering_handoff",
            lambda: apps.get_model("projects", "ProjectEngineeringHandoff"),
            {"audit", "documents", "notifications"},
            {"status", "assigned_engineer_id"},
        )
