from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.core.models import TimeStampedModel
from apps.organization.models import Company, Employee


class Notification(TimeStampedModel):
    class Severity(models.TextChoices):
        INFO = "INFO", "Information"
        SUCCESS = "SUCCESS", "Success"
        WARNING = "WARNING", "Warning"
        ACTION_REQUIRED = "ACTION_REQUIRED", "Action required"
        CRITICAL = "CRITICAL", "Critical"

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="notifications")
    recipient_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="notifications",
    )
    recipient_employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    recipient_name = models.CharField(max_length=200)
    notification_type = models.CharField(max_length=100)
    severity = models.CharField(max_length=30, choices=Severity.choices, default=Severity.INFO)
    title = models.CharField(max_length=180)
    message = models.CharField(max_length=500)
    entity_type = models.CharField(max_length=80, blank=True)
    entity_id = models.CharField(max_length=100, blank=True)
    action_url = models.CharField(max_length=500, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    deduplication_key = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["recipient_user", "archived_at", "read_at", "-created_at"],
                name="notification_inbox_idx",
            ),
            models.Index(fields=["company", "-created_at"], name="notification_company_idx"),
            models.Index(fields=["entity_type", "entity_id"], name="notification_entity_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["recipient_user", "deduplication_key"],
                condition=~Q(deduplication_key=""),
                name="unique_recipient_notification_dedup",
            )
        ]

    def clean(self):
        errors = {}
        if self.recipient_employee_id and self.recipient_employee.company_id != self.company_id:
            errors["recipient_employee"] = "Recipient employee must belong to the notification company."
        if self.action_url and (
            not self.action_url.startswith("/app/")
            or self.action_url.startswith("//")
            or "://" in self.action_url
        ):
            errors["action_url"] = "Notification actions must use a safe internal ERP route."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class NotificationPreference(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preference",
    )
    in_app_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=False)
    sms_enabled = models.BooleanField(default=False)
    whatsapp_enabled = models.BooleanField(default=False)
    push_enabled = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification preferences for {self.user.email}"
