from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.audit.models import AuditEvent
from apps.audit.services import record_event
from apps.numbering.services import allocate_company_number

from .models import StockItem, StockLocation, StockMovement

REQUIRES_FROM = {
    StockMovement.MovementType.OUTWARD,
    StockMovement.MovementType.RESERVE,
    StockMovement.MovementType.RELEASE_RESERVE,
    StockMovement.MovementType.TRANSFER,
    StockMovement.MovementType.PANEL_CONSUMPTION,
    StockMovement.MovementType.SERVICE_CONSUMPTION,
}
REQUIRES_TO = {
    StockMovement.MovementType.INWARD,
    StockMovement.MovementType.RESERVE,
    StockMovement.MovementType.RELEASE_RESERVE,
    StockMovement.MovementType.RETURN,
    StockMovement.MovementType.TRANSFER,
}


def _adjust_balance(*, product, location, condition, delta):
    item, _ = StockItem.objects.select_for_update().get_or_create(
        product=product, location=location, condition=condition, defaults={"quantity": Decimal("0")}
    )
    new_quantity = item.quantity + delta
    if new_quantity < 0:
        raise ValidationError(
            f"Not enough {condition.title()} stock of {product} at {location} "
            f"(have {item.quantity}, need {-delta})."
        )
    item.quantity = new_quantity
    item.save(update_fields=["quantity", "updated_at"])
    return item


@transaction.atomic
def record_movement(
    *,
    company,
    movement_type,
    product,
    quantity,
    from_location: StockLocation | None = None,
    from_condition: str = "",
    to_location: StockLocation | None = None,
    to_condition: str = "",
    reference_type: str = "",
    reference_id=None,
    reason: str = "",
    actor,
):
    if quantity <= 0:
        raise ValidationError({"quantity": "Quantity must be greater than zero."})
    if movement_type == StockMovement.MovementType.ADJUSTMENT and not reason.strip():
        raise ValidationError({"reason": "Adjustments require a reason."})
    if movement_type in REQUIRES_FROM and not (from_location and from_condition):
        raise ValidationError("This movement type requires a source location and condition.")
    if movement_type in REQUIRES_TO and not (to_location and to_condition):
        raise ValidationError("This movement type requires a destination location and condition.")
    if movement_type == StockMovement.MovementType.ADJUSTMENT and not (
        (from_location and from_condition) or (to_location and to_condition)
    ):
        raise ValidationError("Adjustments require at least a source or destination.")

    if from_location and from_condition:
        _adjust_balance(product=product, location=from_location, condition=from_condition, delta=-quantity)
    if to_location and to_condition:
        _adjust_balance(product=product, location=to_location, condition=to_condition, delta=quantity)

    movement_number = allocate_company_number(company=company, code="STK")
    movement = StockMovement.objects.create(
        company=company,
        movement_number=movement_number,
        movement_type=movement_type,
        product=product,
        quantity=quantity,
        from_location=from_location,
        from_condition=from_condition,
        to_location=to_location,
        to_condition=to_condition,
        reference_type=reference_type,
        reference_id=reference_id,
        reason=reason,
        created_by=actor if getattr(actor, "pk", None) else None,
    )
    record_event(
        actor=actor,
        company=company,
        action=AuditEvent.Action.CREATE,
        entity=movement,
        summary=f"Stock movement {movement.movement_number}: {movement.get_movement_type_display()} "
        f"{quantity} of {product}",
        metadata={
            "from_location": str(from_location) if from_location else None,
            "from_condition": from_condition,
            "to_location": str(to_location) if to_location else None,
            "to_condition": to_condition,
            "reference_type": reference_type,
            "reference_id": str(reference_id) if reference_id else None,
        },
    )
    return movement
