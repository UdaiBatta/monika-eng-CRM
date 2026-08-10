from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import UserViewSet
from apps.audit.views import AuditEventViewSet
from apps.configuration.views import CompanySettingsViewSet, FeatureFlagViewSet
from apps.core.views import HealthView
from apps.masters.views import (
    CurrencyViewSet,
    DeliveryTermViewSet,
    PaymentTermViewSet,
    TaxRateViewSet,
    UnitOfMeasureViewSet,
)
from apps.numbering.views import DocumentSequenceViewSet
from apps.organization.views import (
    BranchViewSet,
    CompanyViewSet,
    DepartmentViewSet,
    DesignationViewSet,
    EmployeeViewSet,
    WarehouseViewSet,
)
from apps.rbac.views import (
    PermissionOverrideViewSet,
    PermissionViewSet,
    RoleAssignmentViewSet,
    RolePermissionViewSet,
    RoleViewSet,
)

router = DefaultRouter()
router.register("users", UserViewSet)
router.register("companies", CompanyViewSet)
router.register("branches", BranchViewSet)
router.register("departments", DepartmentViewSet)
router.register("designations", DesignationViewSet)
router.register("warehouses", WarehouseViewSet)
router.register("employees", EmployeeViewSet)
router.register("permissions", PermissionViewSet)
router.register("roles", RoleViewSet)
router.register("role-permissions", RolePermissionViewSet)
router.register("role-assignments", RoleAssignmentViewSet)
router.register("permission-overrides", PermissionOverrideViewSet)
router.register("company-settings", CompanySettingsViewSet)
router.register("feature-flags", FeatureFlagViewSet)
router.register("currencies", CurrencyViewSet)
router.register("units-of-measure", UnitOfMeasureViewSet)
router.register("tax-rates", TaxRateViewSet)
router.register("payment-terms", PaymentTermViewSet)
router.register("delivery-terms", DeliveryTermViewSet)
router.register("document-sequences", DocumentSequenceViewSet)
router.register("audit/events", AuditEventViewSet, basename="audit-event")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", HealthView.as_view(), name="health"),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/", include(router.urls)),
]
