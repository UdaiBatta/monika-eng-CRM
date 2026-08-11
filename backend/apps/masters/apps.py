from django.apps import AppConfig, apps


class MastersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.masters"

    def ready(self):
        from apps.core.entity_registry import register_entity

        registrations = (
            ("currency", "Currency"),
            ("unit_of_measure", "UnitOfMeasure"),
            ("tax_rate", "TaxRate"),
            ("payment_term", "PaymentTerm"),
            ("delivery_term", "DeliveryTerm"),
        )
        for key, model_name in registrations:
            register_entity(
                key,
                lambda model=model_name: apps.get_model("masters", model),
                {"audit"},
            )
