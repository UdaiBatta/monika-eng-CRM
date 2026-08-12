from django.apps import AppConfig, apps


class QuotationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.quotations"

    def ready(self):
        from apps.core.domain_events import subscribe
        from apps.core.entity_registry import register_entity

        register_entity(
            "quotation",
            lambda: apps.get_model("quotations", "Quotation"),
            {"audit", "documents", "approvals", "notifications"},
            {"status", "path", "owner_id"},
        )
        register_entity(
            "quotation_revision",
            lambda: apps.get_model("quotations", "QuotationRevision"),
            {"audit", "documents", "approvals", "notifications"},
            {"status", "grand_total", "revision_number"},
        )

        from .services import sync_quotation_approval

        subscribe("quotation.approval-sync", sync_quotation_approval, after_commit=True)
