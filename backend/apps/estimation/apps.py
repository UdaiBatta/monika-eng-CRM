from django.apps import AppConfig, apps


class EstimationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.estimation"

    def ready(self):
        from apps.core.domain_events import subscribe
        from apps.core.entity_registry import register_entity

        register_entity(
            "commercial_estimate",
            lambda: apps.get_model("estimation", "CommercialEstimate"),
            {"audit", "documents", "approvals", "notifications"},
            {
                "status",
                "total_cost",
                "proposed_selling_price",
                "gross_margin_percent",
                "pricing_method",
            },
        )

        from .services import sync_estimate_approval

        subscribe("estimation.approval-sync", sync_estimate_approval, after_commit=True)
