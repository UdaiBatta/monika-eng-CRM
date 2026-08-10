from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from django.utils import timezone

from apps.core.domain_events import DomainEvent
from apps.core.entity_registry import entity_key, entity_reference

from .context import get_audit_context
from .models import AuditEvent

REDACTED_KEYS = {
    "password",
    "password_hash",
    "token",
    "session",
    "sessionid",
    "csrf",
    "secret",
    "api_key",
    "private_key",
    "database_password",
}


def _safe_value(value, key=""):
    normalized = key.lower().replace("-", "_")
    if any(secret in normalized for secret in REDACTED_KEYS):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(item_key): _safe_value(item, str(item_key)) for item_key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_safe_value(item) for item in value]
    if isinstance(value, (UUID, Decimal, datetime, date)):
        return str(value)
    if hasattr(value, "pk"):
        return str(value.pk)
    return value


def record_event(
    *,
    actor=None,
    actor_id=None,
    actor_employee_id=None,
    company=None,
    company_id=None,
    action,
    entity=None,
    entity_type=None,
    entity_id=None,
    entity_reference_value="",
    event_type=None,
    module=None,
    summary,
    changes=None,
    metadata=None,
    occurred_at=None,
    correlation_id=None,
    source="ERP",
):
    context = get_audit_context()
    employee = None
    if actor is not None:
        try:
            employee = actor.employee
        except Exception:
            employee = None
    if entity is not None:
        entity_type = entity_type or entity_key(entity)
        entity_id = entity.pk
        entity_reference_value = entity_reference_value or entity_reference(entity)
        company = company or (
            entity if entity._meta.model_name == "company" else getattr(entity, "company", None)
        )
        module = module or entity._meta.app_label
    return AuditEvent.objects.create(
        company_id=getattr(company, "pk", company_id),
        actor_user_id=getattr(actor, "pk", actor_id),
        actor_employee_id=getattr(employee, "pk", actor_employee_id),
        event_type=event_type or f"{module}.{entity_type}.{action.lower()}",
        module=module or "core",
        entity_type=entity_type,
        entity_id=str(entity_id),
        entity_reference=entity_reference_value,
        action=action,
        occurred_at=occurred_at or timezone.now(),
        source=source,
        request_id=context.request_id,
        ip_address=context.ip_address,
        user_agent=context.user_agent,
        summary=summary,
        metadata=_safe_value(metadata or {}),
        changes=_safe_value(changes or {}),
        correlation_id=correlation_id,
    )


def record_domain_event(event: DomainEvent):
    return record_event(
        actor_id=event.actor_user_id,
        actor_employee_id=event.actor_employee_id,
        company_id=event.company_id,
        action=event.action,
        entity_type=event.entity_type,
        entity_id=event.entity_id,
        entity_reference_value=str(event.metadata.get("entity_reference", "")),
        event_type=event.event_name,
        module=event.module,
        summary=event.summary,
        changes=event.changes,
        metadata=event.metadata,
        occurred_at=event.occurred_at,
        correlation_id=event.correlation_id,
    )
