from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"

    def ready(self):
        from apps.core.domain_events import subscribe

        from .handlers import handle_domain_event

        subscribe("notifications", handle_domain_event, after_commit=True)
