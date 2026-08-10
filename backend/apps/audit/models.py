from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import UUIDModel
from apps.organization.models import Company, Employee


class ImmutableAuditQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Audit history cannot be changed.")

    def delete(self):
        raise ValidationError("Audit history cannot be deleted.")


class AuditEvent(UUIDModel):
    class Action(models.TextChoices):
        CREATE = "CREATE", "Created"
        UPDATE = "UPDATE", "Updated"
        DELETE = "DELETE", "Deleted"
        ARCHIVE = "ARCHIVE", "Archived"
        RESTORE = "RESTORE", "Restored"
        SUBMIT = "SUBMIT", "Submitted"
        APPROVE = "APPROVE", "Approved"
        REJECT = "REJECT", "Rejected"
        CANCEL = "CANCEL", "Cancelled"
        ACTIVATE = "ACTIVATE", "Activated"
        DEACTIVATE = "DEACTIVATE", "Deactivated"
        LOGIN = "LOGIN", "Signed in"
        LOGOUT = "LOGOUT", "Signed out"
        DOWNLOAD = "DOWNLOAD", "Downloaded"
        EXPORT = "EXPORT", "Exported"
        UPLOAD = "UPLOAD", "Uploaded"
        VERSION_CREATE = "VERSION_CREATE", "Version added"
        STATUS_CHANGE = "STATUS_CHANGE", "Status changed"
        ASSIGN = "ASSIGN", "Assigned"
        UNASSIGN = "UNASSIGN", "Unassigned"

    company = models.ForeignKey(Company, on_delete=models.PROTECT, null=True, blank=True)
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    actor_employee = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_events"
    )
    event_type = models.CharField(max_length=120)
    module = models.CharField(max_length=80)
    entity_type = models.CharField(max_length=80)
    entity_id = models.CharField(max_length=100)
    entity_reference = models.CharField(max_length=250, blank=True)
    action = models.CharField(max_length=30, choices=Action.choices)
    occurred_at = models.DateTimeField()
    source = models.CharField(max_length=40, default="ERP")
    request_id = models.CharField(max_length=64, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    summary = models.CharField(max_length=500)
    metadata = models.JSONField(default=dict, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    correlation_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ImmutableAuditQuerySet.as_manager()

    class Meta:
        ordering = ["-occurred_at", "-created_at"]
        indexes = [
            models.Index(fields=["company", "-occurred_at"], name="audit_company_time_idx"),
            models.Index(fields=["entity_type", "entity_id"], name="audit_entity_idx"),
            models.Index(fields=["actor_user", "-occurred_at"], name="audit_actor_idx"),
            models.Index(fields=["action", "-occurred_at"], name="audit_action_idx"),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Audit history cannot be changed.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Audit history cannot be deleted.")

    def __str__(self):
        return self.summary
