from django.apps import AppConfig, apps


class CrmConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.crm"

    def ready(self):
        from apps.core.entity_registry import register_entity

        register_entity(
            "customer",
            lambda: apps.get_model("crm", "Customer"),
            {"audit", "documents", "approvals", "notifications"},
            {"status", "account_manager_id", "credit_limit"},
        )
        register_entity(
            "customer_contact",
            lambda: apps.get_model("crm", "CustomerContact"),
            {"audit"},
            {"is_primary", "is_active"},
        )
        register_entity(
            "customer_site",
            lambda: apps.get_model("crm", "CustomerSite"),
            {"audit"},
            {"address_type", "is_default", "is_active"},
        )
        register_entity(
            "crm_activity",
            lambda: apps.get_model("crm", "CrmActivity"),
            {"audit", "notifications"},
            {"activity_type", "status", "priority", "follow_up_owner_id"},
        )
