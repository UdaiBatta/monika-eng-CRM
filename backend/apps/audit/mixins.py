from django.db import transaction

from .models import AuditEvent
from .services import record_event


def _company(instance):
    if instance._meta.model_name == "company":
        return instance
    return getattr(instance, "company", None) or getattr(getattr(instance, "role", None), "company", None)


def _read(instance, field):
    value = getattr(instance, field, None)
    if hasattr(value, "all"):
        return list(value.values_list("pk", flat=True))
    return value


class AuditModelViewSetMixin:
    audit_enabled = True

    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        with transaction.atomic():
            return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        with transaction.atomic():
            return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        instance = serializer.save()
        if self.audit_enabled:
            record_event(
                actor=self.request.user,
                company=_company(instance),
                action=AuditEvent.Action.CREATE,
                entity=instance,
                summary=f"{instance._meta.verbose_name.title()} created: {instance}",
            )

    def perform_update(self, serializer):
        instance = serializer.instance
        fields = tuple(serializer.validated_data)
        before = {field: _read(instance, field) for field in fields}
        instance = serializer.save()
        changes = {
            field: {"old": before[field], "new": _read(instance, field)}
            for field in fields
            if before[field] != _read(instance, field)
        }
        if self.audit_enabled and changes:
            record_event(
                actor=self.request.user,
                company=_company(instance),
                action=AuditEvent.Action.UPDATE,
                entity=instance,
                summary=f"{instance._meta.verbose_name.title()} updated: {instance}",
                changes=changes,
            )

    def perform_destroy(self, instance):
        if self.audit_enabled:
            record_event(
                actor=self.request.user,
                company=_company(instance),
                action=AuditEvent.Action.DELETE,
                entity=instance,
                summary=f"{instance._meta.verbose_name.title()} removed: {instance}",
            )
        instance.delete()
