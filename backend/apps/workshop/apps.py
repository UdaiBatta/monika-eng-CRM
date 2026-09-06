from django.apps import AppConfig, apps


class WorkshopConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.workshop"

    def ready(self):
        from apps.core.entity_registry import register_entity

        register_entity(
            "panel_job",
            lambda: apps.get_model("workshop", "PanelJob"),
            {"audit", "documents", "notifications"},
            {"status", "workshop_owner_id"},
        )
