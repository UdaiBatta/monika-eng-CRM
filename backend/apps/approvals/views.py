from django.db import transaction
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.domain_events import publish
from apps.core.permissions import HasFoundationPermission, ScopedQuerysetMixin
from apps.documents.models import Document
from apps.documents.serializers import DocumentSerializer
from apps.rbac.services import authorized_queryset

from .models import (
    ApprovalCondition,
    ApprovalRequest,
    ApprovalStepDefinition,
    ApprovalWorkflow,
    ApprovalWorkflowVersion,
)
from .serializers import (
    ApprovalCancelSerializer,
    ApprovalConditionSerializer,
    ApprovalDecisionCommandSerializer,
    ApprovalReassignSerializer,
    ApprovalRequestCreateSerializer,
    ApprovalRequestSerializer,
    ApprovalRequiredCommentSerializer,
    ApprovalStepDefinitionSerializer,
    ApprovalWorkflowSerializer,
    ApprovalWorkflowVersionSerializer,
)
from .services import (
    activate_workflow_version,
    approve_request,
    cancel_request,
    clone_workflow_version,
    reassign_request,
    reject_request,
    return_request,
    workflow_event,
)


class ApprovalWorkflowViewSet(
    ScopedQuerysetMixin,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ApprovalWorkflow.objects.select_related("company", "current_version").prefetch_related(
        "versions__steps__specific_users",
        "versions__conditions",
    )
    serializer_class = ApprovalWorkflowSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "list": "approvals.workflow.view",
        "retrieve": "approvals.workflow.view",
        "default": "approvals.workflow.manage",
    }
    search_fields = ["code", "name", "description", "entity_type"]
    filterset_fields = ["company", "entity_type", "is_active"]
    ordering_fields = ["code", "name", "created_at", "updated_at"]

    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        workflow = serializer.save()
        publish(
            workflow_event(
                "approval.workflow_updated",
                workflow,
                self.request.user,
                "UPDATE",
                f"Approval workflow updated: {workflow.name}",
            )
        )

    @action(detail=True, methods=["post"], url_path="versions")
    def create_version(self, request, pk=None):
        version = clone_workflow_version(workflow_id=self.get_object().pk, actor=request.user)
        return Response(ApprovalWorkflowVersionSerializer(version).data, status=status.HTTP_201_CREATED)


class WorkflowConfigurationViewSet(ScopedQuerysetMixin, viewsets.ModelViewSet):
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "list": "approvals.workflow.view",
        "retrieve": "approvals.workflow.view",
        "default": "approvals.workflow.manage",
    }

    def workflow_for(self, instance):
        version = instance if isinstance(instance, ApprovalWorkflowVersion) else instance.workflow_version
        return version.workflow

    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        with transaction.atomic():
            return super().destroy(request, *args, **kwargs)

    def configuration_event(self, instance, action):
        workflow = self.workflow_for(instance)
        publish(
            workflow_event(
                "approval.workflow_configuration_changed",
                workflow,
                self.request.user,
                action,
                f"Approval workflow configuration changed: {workflow.name}",
            )
        )

    def perform_create(self, serializer):
        instance = serializer.save()
        self.configuration_event(instance, "CREATE")

    def perform_update(self, serializer):
        instance = serializer.save()
        self.configuration_event(instance, "UPDATE")

    def perform_destroy(self, instance):
        self.configuration_event(instance, "DELETE")
        instance.delete()


class ApprovalWorkflowVersionViewSet(WorkflowConfigurationViewSet):
    queryset = ApprovalWorkflowVersion.objects.select_related(
        "workflow", "workflow__company"
    ).prefetch_related("steps__specific_users", "conditions")
    serializer_class = ApprovalWorkflowVersionSerializer
    filterset_fields = ["workflow", "status"]
    ordering_fields = ["version_number", "created_at"]
    http_method_names = ["get", "patch", "head", "options", "post"]

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        version = activate_workflow_version(version_id=self.get_object().pk, actor=request.user)
        return Response(self.get_serializer(version).data)


class ApprovalStepDefinitionViewSet(WorkflowConfigurationViewSet):
    queryset = ApprovalStepDefinition.objects.select_related(
        "workflow_version",
        "workflow_version__workflow",
    ).prefetch_related("specific_users")
    serializer_class = ApprovalStepDefinitionSerializer
    filterset_fields = ["workflow_version", "resolver_type", "is_active"]
    ordering_fields = ["sequence", "created_at"]


class ApprovalConditionViewSet(WorkflowConfigurationViewSet):
    queryset = ApprovalCondition.objects.select_related(
        "workflow_version",
        "workflow_version__workflow",
    )
    serializer_class = ApprovalConditionSerializer
    filterset_fields = ["workflow_version", "field", "operator"]


class ApprovalRequestViewSet(ScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = ApprovalRequest.objects.select_related(
        "company",
        "workflow_version",
        "requested_by",
        "current_step",
    ).prefetch_related(
        "steps__assignments__approver",
        "steps__decisions__decided_by",
    )
    serializer_class = ApprovalRequestSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "list": "approvals.request.view",
        "retrieve": "approvals.request.view",
        "create": "approvals.request.submit",
        "approve": "approvals.request.approve",
        "reject": "approvals.request.reject",
        "return_for_changes": "approvals.request.return",
        "cancel": "approvals.request.cancel",
        "reassign": "approvals.workflow.manage",
        "supporting_documents": "approvals.request.view",
        "default": "approvals.request.view",
    }
    search_fields = [
        "entity_reference",
        "workflow_name",
        "requested_by_name",
        "submission_comment",
    ]
    filterset_fields = ["company", "status", "entity_type", "workflow_version", "requested_by"]
    ordering_fields = ["requested_at", "completed_at", "status"]

    def get_queryset(self):
        queryset = super().get_queryset()
        bucket = self.request.query_params.get("bucket")
        if bucket == "needs-action":
            queryset = queryset.filter(
                current_step__assignments__approver=self.request.user,
                current_step__assignments__status="PENDING",
                status=ApprovalRequest.Status.IN_PROGRESS,
            )
        elif bucket == "submitted":
            queryset = queryset.filter(requested_by=self.request.user)
        elif bucket == "completed":
            queryset = queryset.exclude(
                status__in=[ApprovalRequest.Status.PENDING, ApprovalRequest.Status.IN_PROGRESS]
            )
        return queryset.distinct()

    def create(self, request):
        serializer = ApprovalRequestCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        approval_request = serializer.save()
        return Response(self.get_serializer(approval_request).data, status=status.HTTP_201_CREATED)

    def command(self, request, serializer_class, callback):
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        approval_request = callback(
            request_id=self.get_object().pk,
            actor=request.user,
            **serializer.validated_data,
        )
        return Response(self.get_serializer(approval_request).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return self.command(request, ApprovalDecisionCommandSerializer, approve_request)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self.command(request, ApprovalRequiredCommentSerializer, reject_request)

    @action(detail=True, methods=["post"], url_path="return")
    def return_for_changes(self, request, pk=None):
        return self.command(request, ApprovalRequiredCommentSerializer, return_request)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return self.command(request, ApprovalCancelSerializer, cancel_request)

    @action(detail=True, methods=["post"])
    def reassign(self, request, pk=None):
        serializer = ApprovalReassignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        approval_request = reassign_request(
            request_id=self.get_object().pk,
            actor=request.user,
            **serializer.validated_data,
        )
        return Response(self.get_serializer(approval_request).data)

    @action(detail=True, methods=["get"], url_path="supporting-documents")
    def supporting_documents(self, request, pk=None):
        approval_request = self.get_object()
        queryset = Document.objects.filter(
            links__entity_type="approval_request",
            links__entity_id=str(approval_request.pk),
        ).select_related("company", "category", "current_version")
        if not request.user.is_superuser:
            queryset = authorized_queryset(
                request.user,
                "documents.document.view",
                queryset,
            )
        return Response(DocumentSerializer(queryset.distinct(), many=True).data)
