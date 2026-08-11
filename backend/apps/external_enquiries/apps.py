from django.apps import AppConfig, apps


class ExternalEnquiriesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.external_enquiries"

    def ready(self):
        from apps.core.entity_registry import register_entity

        register_entity(
            "external_enquiry_submission",
            lambda: apps.get_model("external_enquiries", "ExternalEnquirySubmission"),
            {"audit", "notifications"},
            {"review_status", "spam_status", "duplicate_status", "assigned_to_id"},
        )
