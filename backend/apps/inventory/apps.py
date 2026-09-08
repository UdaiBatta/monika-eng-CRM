from django.apps import AppConfig, apps


class InventoryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.inventory"

    def ready(self):
        from apps.core.entity_registry import register_entity

        register_entity(
            "stock_movement",
            lambda: apps.get_model("inventory", "StockMovement"),
            {"audit"},
            {"movement_type"},
        )
        register_entity(
            "product",
            lambda: apps.get_model("inventory", "Product"),
            {"audit", "documents"},
            {"is_active"},
        )
