from django.apps import AppConfig, apps


class EngineeringReviewsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.engineering_reviews"

    def ready(self):
        from apps.core.entity_registry import register_entity

        register_entity(
            "engineering_feasibility_review",
            lambda: apps.get_model("engineering_reviews", "EngineeringFeasibilityReview"),
            {"audit", "documents", "approvals", "notifications"},
            {
                "status",
                "result",
                "assigned_engineer_id",
                "engineering_hours",
                "manufacturing_hours",
                "lead_time_days",
            },
        )
        register_entity(
            "engineering_clarification",
            lambda: apps.get_model("engineering_reviews", "EngineeringClarification"),
            {"audit", "notifications"},
            {"status", "assigned_to_id", "due_at"},
        )
