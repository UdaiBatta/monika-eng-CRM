from decimal import Decimal
from uuid import UUID

from rest_framework.exceptions import ValidationError

from .models import ApprovalCondition


def _normalized(value):
    if isinstance(value, (UUID, Decimal)):
        return str(value)
    return value


def condition_matches(condition, entity):
    actual = _normalized(getattr(entity, condition.field))
    expected = condition.value
    operator = condition.operator
    try:
        if operator == ApprovalCondition.Operator.EQ:
            return actual == expected
        if operator == ApprovalCondition.Operator.NE:
            return actual != expected
        if operator == ApprovalCondition.Operator.GT:
            return actual > expected
        if operator == ApprovalCondition.Operator.GTE:
            return actual >= expected
        if operator == ApprovalCondition.Operator.LT:
            return actual < expected
        if operator == ApprovalCondition.Operator.LTE:
            return actual <= expected
        if operator == ApprovalCondition.Operator.IN:
            return actual in expected
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            {"conditions": [f"Condition for {condition.field} has an incompatible value."]}
        ) from exc
    raise ValidationError({"conditions": ["The workflow contains an unsupported condition operator."]})


def conditions_match(workflow_version, entity):
    return all(condition_matches(condition, entity) for condition in workflow_version.conditions.all())
