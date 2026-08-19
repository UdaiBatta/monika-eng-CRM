from dataclasses import dataclass

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.audit.models import AuditEvent
from apps.audit.services import record_event
from apps.core.domain_events import DomainEvent, publish

from .models import FeatureFlag


@dataclass(frozen=True)
class FeatureDefinition:
    key: str
    name: str
    description: str
    implemented: bool
    action_url: str = ""


FEATURES = (
    FeatureDefinition(
        "quick_quotation",
        "Quick quotation",
        "Allow permitted Sales employees to start a quotation without an approved estimate.",
        True,
        "/app/crm/quotations",
    ),
    FeatureDefinition(
        "website_enquiries",
        "Website enquiries",
        "Receive and review quotation requests submitted from the company website.",
        True,
        "/app/crm/incoming-enquiries",
    ),
    FeatureDefinition(
        "drawing_management", "Drawing management", "Controlled drawing revisions and viewer.", False
    ),
    FeatureDefinition(
        "bom", "Bill of materials", "Structured product and project bills of materials.", False
    ),
    FeatureDefinition(
        "inventory_transactions",
        "Inventory transactions",
        "Stock receipts, issues and balances.",
        False,
    ),
    FeatureDefinition("production", "Production", "Production planning and execution.", False),
    FeatureDefinition("quality", "Quality", "Inspection plans and results.", False),
    FeatureDefinition("dispatch", "Dispatch", "Dispatch planning and proof of delivery.", False),
    FeatureDefinition("service_amc", "Service & AMC", "Installation, service and AMC operations.", False),
)

FEATURE_BY_KEY = {feature.key: feature for feature in FEATURES}


def is_feature_enabled(company, key):
    definition = FEATURE_BY_KEY.get(key)
    if not definition or not definition.implemented:
        return False
    flag = FeatureFlag.objects.filter(company=company, key=key).only("is_enabled").first()
    return bool(flag and flag.is_enabled)


def feature_controls(company):
    flags = {item.key: item for item in FeatureFlag.objects.filter(company=company)}
    return [
        {
            "key": definition.key,
            "name": definition.name,
            "description": definition.description,
            "implemented": definition.implemented,
            "status": (
                "Enabled"
                if definition.implemented and flags.get(definition.key) and flags[definition.key].is_enabled
                else "Disabled"
                if definition.implemented
                else "Not available yet"
            ),
            "is_enabled": bool(
                definition.implemented
                and flags.get(definition.key)
                and flags[definition.key].is_enabled
            ),
            "record_version": getattr(flags.get(definition.key), "record_version", None),
            "action_url": definition.action_url,
        }
        for definition in FEATURES
    ]


def enabled_feature_keys(company):
    return [
        definition.key
        for definition in FEATURES
        if definition.implemented and is_feature_enabled(company, definition.key)
    ]


@transaction.atomic
def set_feature(*, company, key, enabled, reason, actor, submitted_version=None):
    definition = FEATURE_BY_KEY.get(key)
    if not definition:
        raise ValidationError("Choose a recognized feature.")
    if not definition.implemented:
        raise ValidationError(f"{definition.name} is not available yet.")
    if len(reason.strip()) < 3:
        raise ValidationError({"reason": ["Explain why this feature is changing."]})

    flag, _created = FeatureFlag.objects.select_for_update().get_or_create(
        company=company,
        key=key,
        defaults={"description": definition.description, "is_enabled": False},
    )
    if submitted_version is not None and int(submitted_version) != flag.record_version:
        from apps.core.conflicts import VersionConflict

        raise VersionConflict(flag.record_version)
    if flag.is_enabled == enabled:
        return flag
    previous = flag.is_enabled
    flag.is_enabled = enabled
    flag.description = definition.description
    flag.record_version += 1
    flag.save(update_fields=["is_enabled", "description", "record_version", "updated_at"])
    record_event(
        actor=actor,
        company=company,
        action=AuditEvent.Action.ACTIVATE if enabled else AuditEvent.Action.DEACTIVATE,
        entity=flag,
        summary=f"{definition.name} {'enabled' if enabled else 'disabled'}",
        changes={"is_enabled": {"old": previous, "new": enabled}},
        metadata={"reason": reason.strip()},
    )
    publish(
        DomainEvent(
            event_name="configuration.feature_changed",
            entity_type="feature_flag",
            entity_id=flag.pk,
            company_id=company.pk,
            actor_user_id=actor.pk,
            actor_employee_id=getattr(getattr(actor, "employee", None), "pk", None),
            action="UPDATE",
            module="configuration",
            summary=f"{definition.name} {'enabled' if enabled else 'disabled'}",
            metadata={"status": "enabled" if enabled else "disabled"},
            changes={"is_enabled": {"old": previous, "new": enabled}},
        )
    )
    return flag
