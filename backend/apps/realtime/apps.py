from django.apps import AppConfig


class RealtimeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.realtime"

    def ready(self):
        from apps.core.domain_events import subscribe

        from .events import broadcast_domain_event

        subscribe("realtime", broadcast_domain_event, after_commit=True)
