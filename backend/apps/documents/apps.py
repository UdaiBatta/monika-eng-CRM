from django.apps import AppConfig, apps


class DocumentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.documents"

    def ready(self):
        from apps.core.entity_registry import register_entity

        register_entity(
            "document",
            lambda: apps.get_model("documents", "Document"),
            {"audit", "documents", "approvals", "notifications"},
            {"status", "category_id", "is_confidential"},
        )
