from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.core.permissions import HasFoundationPermission
from apps.sales.models import SalesOrderLine

from .models import StockLocation, StockMovement
from .serializers import StockMovementSerializer
from .services import record_movement


class ReserveLineInputSerializer(serializers.Serializer):
    location = serializers.PrimaryKeyRelatedField(queryset=StockLocation.objects.all())


class SalesOrderLineReservationViewSet(GenericViewSet):
    """Reserve/release stock against a Sales Order line's linked product."""

    queryset = SalesOrderLine.objects.select_related("revision__sales_order__company", "product")
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "reserve": "inventory.stock.reserve",
        "release": "inventory.stock.reserve",
    }

    def _movement(self, request, *, movement_type, from_condition, to_condition):
        line = self.get_object()
        if not line.product_id:
            raise ValidationError("This line has no linked product to reserve stock for.")
        serializer = ReserveLineInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        location = serializer.validated_data["location"]
        company = line.revision.sales_order.company
        try:
            movement = record_movement(
                company=company,
                movement_type=movement_type,
                product=line.product,
                quantity=line.quantity,
                from_location=location if from_condition else None,
                from_condition=from_condition,
                to_location=location if to_condition else None,
                to_condition=to_condition,
                reference_type="sales_order_line",
                reference_id=line.pk,
                actor=request.user,
            )
        except DjangoValidationError as exc:
            detail = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
            raise ValidationError(detail) from exc
        return Response(StockMovementSerializer(movement).data, status=201)

    @action(detail=True, methods=["post"])
    def reserve(self, request, pk=None):
        return self._movement(
            request,
            movement_type=StockMovement.MovementType.RESERVE,
            from_condition="AVAILABLE",
            to_condition="RESERVED",
        )

    @action(detail=True, methods=["post"])
    def release(self, request, pk=None):
        return self._movement(
            request,
            movement_type=StockMovement.MovementType.RELEASE_RESERVE,
            from_condition="RESERVED",
            to_condition="AVAILABLE",
        )
