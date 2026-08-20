from django.apps import AppConfig, apps


class SalesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.sales"

    def ready(self):
        from apps.core.domain_events import subscribe
        from apps.core.entity_registry import register_entity

        register_entity(
            "customer_purchase_order",
            lambda: apps.get_model("sales", "CustomerPurchaseOrder"),
            {"audit", "documents", "approvals", "notifications"},
            {"status", "customer_id"},
        )
        register_entity(
            "sales_order",
            lambda: apps.get_model("sales", "SalesOrder"),
            {"audit", "documents", "approvals", "notifications"},
            {"status", "order_mode", "project_required", "responsible_sales_employee_id"},
        )
        register_entity(
            "sales_order_revision",
            lambda: apps.get_model("sales", "SalesOrderRevision"),
            {"audit", "documents", "approvals", "notifications"},
            {"status", "grand_total", "revision_number"},
        )

        from .services import sync_sales_order_approval

        subscribe("sales-order.approval-sync", sync_sales_order_approval, after_commit=True)
