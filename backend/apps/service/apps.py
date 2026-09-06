from django.apps import AppConfig, apps


class ServiceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.service"

    def ready(self):
        from apps.core.entity_registry import register_entity

        register_entity(
            "service_ticket",
            lambda: apps.get_model("service", "ServiceTicket"),
            {"audit", "documents", "notifications"},
            {"status", "priority", "technician_id"},
        )
        register_entity(
            "equipment",
            lambda: apps.get_model("service", "Equipment"),
            {"audit", "documents"},
            {"is_active"},
        )
