from django.apps import AppConfig, apps


class ApprovalsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.approvals"

    def ready(self):
        from apps.core.entity_registry import register_entity

        register_entity(
            "approval_workflow",
            lambda: apps.get_model("approvals", "ApprovalWorkflow"),
            {"audit"},
        )
        register_entity(
            "approval_request",
            lambda: apps.get_model("approvals", "ApprovalRequest"),
            {"audit", "documents", "notifications"},
            {"status", "entity_type"},
        )
