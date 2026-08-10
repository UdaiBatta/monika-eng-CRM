from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"

    def ready(self):
        from apps.core.domain_events import subscribe

        from .services import record_domain_event

        subscribe("audit", record_domain_event)
