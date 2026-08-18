from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.pagination import StandardPagination
from apps.core.permissions import HasFoundationPermission
from apps.organization.models import Employee

from .owner_serializers import FeatureChangeSerializer, WorkReassignSerializer
from .owner_services import (
    bulk_reassign,
    change_owner_feature,
    data_quality_issues,
    owner_feature_controls,
    owner_overview,
    reassign_work,
    resolve_owner_company,
    system_health,
    work_items,
)


class OwnerControlViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [HasFoundationPermission]
    pagination_class = StandardPagination
    permission_map = {
        "list": "system.owner_control.view",
        "work_items": "system.owner_control.view",
        "employees": "system.owner_control.view",
        "data_quality": "system.data_quality.view",
        "system_health": "system.system_health.view",
        "features": "configuration.feature_flag.view",
        "change_feature": "configuration.feature_flag.manage",
        "reassign_work": "system.work.reassign",
    }

    def _company(self, request):
        return resolve_owner_company(
            request.user,
            request.query_params.get("company") or request.data.get("company"),
        )

    def list(self, request, *args, **kwargs):
        return Response(owner_overview(self._company(request)))

    @action(detail=False, methods=["get"], url_path="work-items")
    def work_items(self, request):
        records = work_items(
            self._company(request),
            work_type=request.query_params.get("work_type", ""),
            employee_id=request.query_params.get("employee", None),
            queue=request.query_params.get("queue", ""),
        )
        page = self.paginate_queryset(records)
        return self.get_paginated_response(page)

    @action(detail=False, methods=["post"], url_path="reassign-work")
    def reassign_work(self, request):
        serializer = WorkReassignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        company = self._company(request)
        if data.get("items"):
            records = bulk_reassign(
                company=company,
                items=data["items"],
                employee_id=data["employee_id"],
                reason=data["reason"],
                actor=request.user,
            )
            return Response({"reassigned": len(records), "results": records})
        record, changed = reassign_work(
            company=company,
            work_type=data["work_type"],
            record_id=data["record_id"],
            employee_id=data["employee_id"],
            reason=data["reason"],
            actor=request.user,
        )
        return Response({"reassigned": 1 if changed else 0, "result": record})

    @action(detail=False, methods=["get"])
    def employees(self, request):
        employees = Employee.objects.select_related("user").filter(
            company=self._company(request),
            employment_status=Employee.EmploymentStatus.ACTIVE,
            user__is_active=True,
        )
        return Response(
            [
                {
                    "id": str(employee.pk),
                    "employee_code": employee.employee_code,
                    "display_name": employee.display_name,
                }
                for employee in employees
            ]
        )

    @action(detail=False, methods=["get"], url_path="data-quality")
    def data_quality(self, request):
        return Response({"issues": data_quality_issues(self._company(request))})

    @action(detail=False, methods=["get"], url_path="system-health")
    def system_health(self, request):
        return Response(system_health(self._company(request)))

    @action(detail=False, methods=["get"])
    def features(self, request):
        return Response({"features": owner_feature_controls(self._company(request))})

    @action(detail=False, methods=["post"], url_path="change-feature")
    def change_feature(self, request):
        serializer = FeatureChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        company = self._company(request)
        change_owner_feature(company=company, actor=request.user, data=serializer.validated_data)
        return Response({"features": owner_feature_controls(company)})

