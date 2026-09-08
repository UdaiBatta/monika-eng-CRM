from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.core.permissions import HasFoundationPermission, ScopedQuerysetMixin
from apps.inventory.models import Product, StockLocation

from .models import PanelJob
from .serializers import (
    AddMaterialLineInputSerializer,
    MaterialMovementInputSerializer,
    NotesInputSerializer,
    PanelJobMaterialLineSerializer,
    PanelJobSerializer,
    QualityCheckInputSerializer,
    ReasonInputSerializer,
    ReserveMaterialsInputSerializer,
)
from .services import (
    add_material_line,
    advance_panel_job_stage,
    cancel_panel_job,
    handover_panel_job,
    hold_panel_job,
    record_material_movement,
    record_quality_check,
    reserve_panel_job_materials,
    resume_panel_job,
)


def _raise_from_django_validation(exc):
    detail = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
    raise ValidationError(detail) from exc


class PanelJobViewSet(ScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = PanelJob.objects.select_related(
        "company", "project", "warehouse", "workshop_owner"
    ).prefetch_related("material_lines", "stage_events")
    serializer_class = PanelJobSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "list": "workshop.panel_job.view",
        "retrieve": "workshop.panel_job.view",
        "add_material": "workshop.panel_job.plan_material",
        "reserve_materials": "workshop.panel_job.reserve_stock",
        "record_material_movement_action": "workshop.panel_job.record_material",
        "advance": "workshop.panel_job.advance",
        "quality_check": "workshop.panel_job.quality_check",
        "handover": "workshop.panel_job.handover",
        "hold": "workshop.panel_job.hold",
        "resume": "workshop.panel_job.hold",
        "cancel": "workshop.panel_job.cancel",
        "default": "workshop.panel_job.view",
    }
    search_fields = ["panel_job_number", "panel_name", "project__project_number"]
    filterset_fields = ["company", "status", "project", "workshop_owner", "warehouse"]
    ordering_fields = ["created_at", "updated_at", "panel_job_number", "status"]

    @action(detail=True, methods=["post"], url_path="material-lines")
    def add_material(self, request, pk=None):
        serializer = AddMaterialLineInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = Product.objects.get(pk=serializer.validated_data["product"])
        try:
            line = add_material_line(
                panel_job_id=self.get_object().pk,
                actor=request.user,
                product=product,
                required_quantity=serializer.validated_data["required_quantity"],
                notes=serializer.validated_data.get("notes", ""),
            )
        except DjangoValidationError as exc:
            _raise_from_django_validation(exc)
        return Response(PanelJobMaterialLineSerializer(line).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="reserve-materials")
    def reserve_materials(self, request, pk=None):
        serializer = ReserveMaterialsInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        location = StockLocation.objects.get(pk=serializer.validated_data["location"])
        try:
            panel_job = reserve_panel_job_materials(
                panel_job_id=self.get_object().pk, actor=request.user, location=location
            )
        except DjangoValidationError as exc:
            _raise_from_django_validation(exc)
        return Response(PanelJobSerializer(panel_job).data)

    @action(detail=True, methods=["post"], url_path="material-movements")
    def record_material_movement_action(self, request, pk=None):
        serializer = MaterialMovementInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        location = StockLocation.objects.get(pk=serializer.validated_data["location"])
        try:
            line = record_material_movement(
                panel_job_id=self.get_object().pk,
                actor=request.user,
                material_line_id=serializer.validated_data["material_line"],
                movement_type=serializer.validated_data["movement_type"],
                quantity=serializer.validated_data["quantity"],
                location=location,
            )
        except DjangoValidationError as exc:
            _raise_from_django_validation(exc)
        return Response(PanelJobMaterialLineSerializer(line).data)

    @action(detail=True, methods=["post"])
    def advance(self, request, pk=None):
        serializer = NotesInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            panel_job = advance_panel_job_stage(
                panel_job_id=self.get_object().pk,
                actor=request.user,
                notes=serializer.validated_data.get("notes", ""),
            )
        except DjangoValidationError as exc:
            _raise_from_django_validation(exc)
        return Response(PanelJobSerializer(panel_job).data)

    @action(detail=True, methods=["post"], url_path="quality-check")
    def quality_check(self, request, pk=None):
        serializer = QualityCheckInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            panel_job = record_quality_check(
                panel_job_id=self.get_object().pk,
                actor=request.user,
                passed=serializer.validated_data["passed"],
                notes=serializer.validated_data.get("notes", ""),
            )
        except DjangoValidationError as exc:
            _raise_from_django_validation(exc)
        return Response(PanelJobSerializer(panel_job).data)

    @action(detail=True, methods=["post"])
    def handover(self, request, pk=None):
        serializer = NotesInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            panel_job = handover_panel_job(
                panel_job_id=self.get_object().pk,
                actor=request.user,
                notes=serializer.validated_data.get("notes", ""),
            )
        except DjangoValidationError as exc:
            _raise_from_django_validation(exc)
        return Response(PanelJobSerializer(panel_job).data)

    @action(detail=True, methods=["post"])
    def hold(self, request, pk=None):
        serializer = ReasonInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            panel_job = hold_panel_job(
                panel_job_id=self.get_object().pk,
                actor=request.user,
                reason=serializer.validated_data["reason"],
            )
        except DjangoValidationError as exc:
            _raise_from_django_validation(exc)
        return Response(PanelJobSerializer(panel_job).data)

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        try:
            panel_job = resume_panel_job(panel_job_id=self.get_object().pk, actor=request.user)
        except DjangoValidationError as exc:
            _raise_from_django_validation(exc)
        return Response(PanelJobSerializer(panel_job).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        serializer = ReasonInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            panel_job = cancel_panel_job(
                panel_job_id=self.get_object().pk,
                actor=request.user,
                reason=serializer.validated_data["reason"],
            )
        except DjangoValidationError as exc:
            _raise_from_django_validation(exc)
        return Response(PanelJobSerializer(panel_job).data)
