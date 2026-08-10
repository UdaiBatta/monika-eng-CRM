from collections.abc import Callable
from dataclasses import dataclass, field

from django.core.exceptions import ValidationError
from django.db.models import Model


@dataclass(frozen=True)
class EntityRegistration:
    key: str
    model_getter: Callable[[], type[Model]]
    capabilities: frozenset[str] = field(default_factory=frozenset)
    condition_fields: frozenset[str] = field(default_factory=frozenset)


_registry: dict[str, EntityRegistration] = {}


def register_entity(key, model_getter, capabilities, condition_fields=()):
    _registry[key] = EntityRegistration(
        key=key,
        model_getter=model_getter,
        capabilities=frozenset(capabilities),
        condition_fields=frozenset(condition_fields),
    )


def registered_entity(key, capability=None):
    registration = _registry.get(key)
    if registration is None or (capability and capability not in registration.capabilities):
        raise ValidationError({"entity_type": "This related record type is not available."})
    return registration


def resolve_entity(key, object_id, capability=None):
    registration = registered_entity(key, capability)
    try:
        return registration.model_getter().objects.get(pk=object_id)
    except (registration.model_getter().DoesNotExist, ValueError, TypeError) as exc:
        raise ValidationError({"entity_id": "The related record does not exist."}) from exc


def entity_company_id(entity):
    return entity.pk if entity._meta.model_name == "company" else getattr(entity, "company_id", None)


def entity_key(entity):
    model = entity._meta.model
    for key, registration in _registry.items():
        if registration.model_getter() is model:
            return key
    raise ValidationError("This record type is not registered for shared services.")


def entity_reference(entity):
    for field_name in ("document_number", "employee_code", "code", "name", "title", "email"):
        value = getattr(entity, field_name, None)
        if value:
            return str(value)
    return str(entity)
