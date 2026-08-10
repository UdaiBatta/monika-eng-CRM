from django.apps import AppConfig, apps


class EnquiriesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.enquiries"

    def ready(self):
        from apps.core.entity_registry import register_entity

        register_entity(
            "enquiry",
            lambda: apps.get_model("enquiries", "Enquiry"),
            {"audit", "documents", "approvals", "notifications"},
            {"status", "priority", "estimated_value", "responsible_salesperson_id"},
        )
        register_entity(
            "enquiry_requirement",
            lambda: apps.get_model("enquiries", "EnquiryRequirement"),
            {"audit"},
            {"requirement_type", "is_mandatory"},
        )
        register_entity(
            "enquiry_item",
            lambda: apps.get_model("enquiries", "EnquiryItem"),
            {"audit"},
            {"quantity", "uom_id", "requested_delivery"},
        )
