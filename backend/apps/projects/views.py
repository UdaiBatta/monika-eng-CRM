from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.permissions import HasFoundationPermission, ScopedQuerysetMixin

from .models import Project, ProjectHandoffClarification
from .serializers import (
    ClarificationRequestInputSerializer,
    ClarificationResponseInputSerializer,
    HandoffAssignInputSerializer,
    HandoffUpdateInputSerializer,
    ProjectClarificationSerializer,
    ProjectHandoffSerializer,
    ProjectSerializer,
    ProjectUpdateInputSerializer,
)
from .services import (
    accept_engineering_handoff,
    acknowledge_commercial_change,
    assign_engineering_handoff,
    prepare_engineering_handoff,
    request_project_clarification,
    respond_project_clarification,
    submit_engineering_handoff,
    take_engineering_handoff,
    update_project,
)


class ProjectViewSet(ScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Project.objects.select_related(
        "company",
        "customer",
        "site",
        "sales_owner",
        "sales_owner__user",
        "project_owner",
        "engineering_owner",
        "engineering_owner__user",
        "current_sales_order_revision__currency",
        "previous_sales_order_revision",
        "sales_order__customer",
        "sales_order__contact",
        "sales_order__site",
        "sales_order__accepted_quotation",
        "sales_order__customer_purchase_order__current_revision__currency",
        "sales_order__responsible_sales_employee",
        "sales_order__current_revision__currency",
        "engineering_handoff__assigned_engineer",
    ).prefetch_related(
        "sales_order__current_revision__lines",
        "sales_order__revisions__currency",
        "sales_order__revisions__lines",
        "sales_order__customer_purchase_order__revisions__currency",
        "engineering_handoff__clarifications__respond_to",
        "engineering_handoff__clarifications__requested_by",
        "engineering_handoff__clarifications__responded_by",
        "engineering_handoff__clarifications__response_document",
    )
    serializer_class = ProjectSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "list": "projects.project.view",
        "retrieve": "projects.project.view",
        "update_project": "projects.project.edit",
        "update_handoff": "projects.handoff.prepare",
        "submit_handoff": "projects.handoff.submit",
        "take_ownership": "projects.handoff.take_ownership",
        "assign": "projects.handoff.assign",
        "request_clarification": "projects.handoff.request_clarification",
        "accept_handoff": "projects.handoff.accept",
        "acknowledge_commercial_change": "projects.handoff.acknowledge_commercial_change",
        "default": "projects.project.view",
    }
    search_fields = [
        "project_number",
        "project_name",
        "customer__legal_name",
        "sales_order__sales_order_number",
        "customer_po_reference",
    ]
    filterset_fields = [
        "company",
        "customer",
        "status",
        "priority",
        "sales_owner",
        "project_owner",
        "engineering_owner",
        "commercial_change_pending",
    ]
    ordering_fields = ["created_at", "updated_at", "project_number", "target_completion", "status"]

    def get_queryset(self):
        queryset = super().get_queryset()
        queue = self.request.query_params.get("queue")
        employee = getattr(self.request.user, "employee", None)
        if queue == "mine":
            return queryset.filter(engineering_owner=employee) if employee else queryset.none()
        if queue == "unassigned":
            return queryset.filter(engineering_owner__isnull=True)
        if queue == "engineering":
            return queryset.filter(
                engineering_handoff__status__in=[
                    "READY_FOR_ENGINEERING",
                    "ENGINEERING_REVIEWING",
                    "CLARIFICATION_REQUIRED",
                ]
            )
        return queryset

    @action(detail=True, methods=["post"], url_path="update-project")
    def update_project(self, request, pk=None):
        serializer = ProjectUpdateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        record_version = data.pop("record_version")
        project = update_project(
            project_id=self.get_object().pk,
            actor=request.user,
            submitted_version=record_version,
            data=data,
        )
        return Response(ProjectSerializer(project, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="update-handoff")
    def update_handoff(self, request, pk=None):
        serializer = HandoffUpdateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        record_version = data.pop("record_version")
        handoff = prepare_engineering_handoff(
            project_id=self.get_object().pk,
            actor=request.user,
            submitted_version=record_version,
            data=data,
        )
        return Response(ProjectHandoffSerializer(handoff, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="submit-handoff")
    def submit_handoff(self, request, pk=None):
        handoff = submit_engineering_handoff(project_id=self.get_object().pk, actor=request.user)
        return Response(ProjectHandoffSerializer(handoff, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="take-ownership")
    def take_ownership(self, request, pk=None):
        handoff = take_engineering_handoff(project_id=self.get_object().pk, actor=request.user)
        return Response(ProjectHandoffSerializer(handoff, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        serializer = HandoffAssignInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        handoff = assign_engineering_handoff(
            project_id=self.get_object().pk,
            engineer_id=serializer.validated_data["engineer_id"],
            actor=request.user,
        )
        return Response(ProjectHandoffSerializer(handoff, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="request-clarification")
    def request_clarification(self, request, pk=None):
        serializer = ClarificationRequestInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        clarification = request_project_clarification(
            project_id=self.get_object().pk,
            actor=request.user,
            **serializer.validated_data,
        )
        return Response(ProjectClarificationSerializer(clarification).data)

    @action(detail=True, methods=["post"], url_path="accept-handoff")
    def accept_handoff(self, request, pk=None):
        handoff = accept_engineering_handoff(project_id=self.get_object().pk, actor=request.user)
        return Response(ProjectHandoffSerializer(handoff, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="acknowledge-commercial-change")
    def acknowledge_commercial_change(self, request, pk=None):
        project = acknowledge_commercial_change(project_id=self.get_object().pk, actor=request.user)
        return Response(ProjectSerializer(project, context={"request": request}).data)


class ProjectClarificationViewSet(ScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = ProjectHandoffClarification.objects.select_related(
        "handoff__project__company",
        "handoff__project__sales_owner",
        "handoff__project__engineering_owner",
        "respond_to",
        "requested_by",
        "responded_by",
        "response_document",
    )
    serializer_class = ProjectClarificationSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "list": "projects.handoff.view",
        "retrieve": "projects.handoff.view",
        "respond": "projects.handoff.respond_clarification",
        "default": "projects.handoff.view",
    }
    filterset_fields = ["handoff", "status", "respond_to"]

    @action(detail=True, methods=["post"])
    def respond(self, request, pk=None):
        serializer = ClarificationResponseInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        clarification = respond_project_clarification(
            clarification_id=self.get_object().pk,
            actor=request.user,
            **serializer.validated_data,
        )
        return Response(ProjectClarificationSerializer(clarification).data)
