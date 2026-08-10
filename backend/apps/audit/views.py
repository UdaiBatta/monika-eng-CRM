from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.dateparse import parse_datetime
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.core.entity_registry import resolve_entity
from apps.core.permissions import HasFoundationPermission, ScopedQuerysetMixin
from apps.rbac.services import has_permission

from .models import AuditEvent
from .serializers import AuditEventSerializer


class AuditEventViewSet(ScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = AuditEvent.objects.select_related("company", "actor_user", "actor_employee")
    serializer_class = AuditEventSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "list": "audit.event.view",
        "retrieve": "audit.event.view",
        "entity_timeline": "audit.event.view",
        "default": "audit.event.view",
    }
    search_fields = [
        "summary",
        "entity_reference",
        "actor_user__email",
        "actor_employee__first_name",
        "actor_employee__last_name",
        "actor_employee__employee_code",
    ]
    filterset_fields = [
        "company",
        "actor_user",
        "actor_employee",
        "action",
        "module",
        "entity_type",
        "entity_id",
    ]
    ordering_fields = ["occurred_at", "action", "module", "created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        date_from = parse_datetime(self.request.query_params.get("date_from", ""))
        date_to = parse_datetime(self.request.query_params.get("date_to", ""))
        if date_from:
            queryset = queryset.filter(occurred_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(occurred_at__lte=date_to)
        return queryset

    @action(
        detail=False,
        methods=["get"],
        url_path=r"entities/(?P<entity_type>[^/.]+)/(?P<entity_id>[^/.]+)",
    )
    def entity_timeline(self, request, entity_type=None, entity_id=None):
        try:
            entity = resolve_entity(entity_type, entity_id, "audit")
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages) from exc
        if not request.user.is_superuser and not has_permission(request.user, "audit.event.view", entity):
            self.permission_denied(
                request, message="You do not have permission to view this activity history."
            )
        queryset = self.filter_queryset(
            self.get_queryset().filter(entity_type=entity_type, entity_id=str(entity_id))
        )
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page if page is not None else queryset, many=True)
        return self.get_paginated_response(serializer.data) if page is not None else Response(serializer.data)
