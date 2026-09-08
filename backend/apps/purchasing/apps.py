from django.apps import AppConfig, apps


class PurchasingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.purchasing"

    def ready(self):
        from apps.core.domain_events import subscribe
        from apps.core.entity_registry import register_entity

        register_entity(
            "purchase_requisition",
            lambda: apps.get_model("purchasing", "PurchaseRequisition"),
            {"audit", "documents", "approvals", "notifications"},
            {"status"},
        )
        register_entity(
            "purchase_order",
            lambda: apps.get_model("purchasing", "PurchaseOrder"),
            {"audit", "documents", "approvals", "notifications"},
            {"status", "grand_total", "payment_status"},
        )
        register_entity(
            "goods_receipt",
            lambda: apps.get_model("purchasing", "GoodsReceipt"),
            {"audit", "documents"},
            {"status"},
        )

        from .services import sync_purchase_order_approval, sync_purchase_requisition_approval

        subscribe(
            "purchase-requisition.approval-sync",
            sync_purchase_requisition_approval,
            after_commit=True,
        )
        subscribe("purchase-order.approval-sync", sync_purchase_order_approval, after_commit=True)
