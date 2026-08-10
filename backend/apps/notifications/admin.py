from django.contrib import admin

from .models import Notification, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "recipient_name",
        "company",
        "severity",
        "read_at",
        "archived_at",
        "created_at",
    )
    list_filter = ("company", "severity", "notification_type", "read_at", "archived_at")
    search_fields = ("title", "message", "recipient_name")
    readonly_fields = [field.name for field in Notification._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "in_app_enabled", "email_enabled", "sms_enabled")
    search_fields = ("user__email",)
