from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.crm.models import Customer
from apps.enquiries.models import Enquiry
from apps.inventory.models import Product, ProductCategory, StockItem, StockLocation, StockMovement, Supplier
from apps.inventory.services import record_movement
from apps.masters.models import Currency, UnitOfMeasure
from apps.numbering.models import DocumentSequence
from apps.numbering.services import financial_year_label
from apps.organization.models import Warehouse
from apps.projects.models import Project
from apps.projects.services import (
    accept_engineering_handoff,
    submit_engineering_handoff,
    take_engineering_handoff,
)
from apps.quotations.models import CustomerCommercialConfirmation, Quotation
from apps.quotations.services import create_quotation
from apps.rbac.models import Permission, Role, RoleAssignment, RolePermission, ScopeType
from apps.sales.services import (
    create_sales_order_from_quotation,
    release_sales_order,
    submit_sales_order,
)
from apps.workshop.models import PanelJob
from apps.workshop.services import (
    add_material_line,
    advance_panel_job_stage,
    cancel_panel_job,
    create_panel_job_from_project,
    handover_panel_job,
    hold_panel_job,
    record_material_movement,
    record_quality_check,
    reserve_panel_job_materials,
    resume_panel_job,
)


def _grant(user, company, codes):
    role = Role.objects.create(company=company, code=f"ROLE-{'-'.join(codes)}"[:40], name="Test role")
    for code in codes:
        permission, _ = Permission.objects.get_or_create(code=code, defaults={"name": code})
        RolePermission.objects.create(role=role, permission=permission)
    RoleAssignment.objects.create(user=user, role=role, scope_type=ScopeType.COMPANY, company=company)


@pytest.fixture
def admin(db):
    return User.objects.create_superuser(email="workshop-admin@example.test", password="SafePassword-2741")


@pytest.fixture(autouse=True)
def sequences(company):
    financial_year = financial_year_label(company)
    for code, template in (
        ("QUOTATION", "QTN-{number}"),
        ("SO", "SO-{number}"),
        ("PRJ", "PRJ-{number}"),
        ("PANEL", "PANEL-{number}"),
        ("STK", "STK-{number}"),
    ):
        DocumentSequence.objects.create(
            company=company, code=code, financial_year=financial_year, template=template, padding=4
        )


@pytest.fixture
def uom(db):
    return UnitOfMeasure.objects.create(code="NOS", name="Numbers")


@pytest.fixture
def warehouse(company, branch):
    return Warehouse.objects.create(company=company, branch=branch, name="Main Store", code="MAIN")


@pytest.fixture
def location(warehouse):
    return StockLocation.objects.create(warehouse=warehouse, bin_code="")


@pytest.fixture
def product(company, uom):
    category = ProductCategory.objects.create(company=company, code="VFD", name="VFDs")
    supplier = Supplier.objects.create(company=company, code="SUP1", name="ABB Distributor")
    return Product.objects.create(
        company=company,
        category=category,
        default_supplier=supplier,
        unit_of_measure=uom,
        internal_code="PROD-001",
        description="ABB ACS550 5.5kW VFD",
    )


@pytest.fixture
def accepted_project(company, employee, user):
    user.is_superuser = True
    user.is_staff = True
    user.save(update_fields=["is_superuser", "is_staff"])
    currency, _ = Currency.objects.get_or_create(
        code="INR", defaults={"name": "Indian Rupee", "symbol": "₹", "decimal_places": 2}
    )
    customer = Customer.objects.create(
        company=company,
        customer_code="CUST-WS-001",
        legal_name="ABC Industries Pvt. Ltd.",
        default_currency=currency,
        created_by=user,
        updated_by=user,
    )
    enquiry = Enquiry.objects.create(
        company=company,
        enquiry_number="ENQ-WS-001",
        customer=customer,
        subject="One MCC control panel",
        responsible_salesperson=employee,
        status=Enquiry.Status.WON,
        closed_at=timezone.now(),
        closed_by=user,
        created_by=user,
        updated_by=user,
    )
    quotation = create_quotation(
        actor=user,
        data={
            "path": Quotation.Path.QUICK,
            "customer_id": customer.pk,
            "enquiry_id": enquiry.pk,
            "quick_reason": "Repeat configuration requested urgently.",
            "scope": "Supply of one MCC control panel.",
            "payment_terms": "30% advance",
            "delivery_terms": "8-10 weeks",
            "warranty_terms": "12 months",
            "lines": [
                {
                    "description": "MCC Control Panel",
                    "quantity": "1",
                    "unit_of_measure": "NOS",
                    "unit_price": "500000",
                    "tax_percent": "18",
                }
            ],
        },
    )
    quotation.status = Quotation.Status.READY_FOR_SALES_ORDER
    quotation.save(update_fields=["status", "updated_at"])
    CustomerCommercialConfirmation.objects.create(
        quotation=quotation,
        revision=quotation.current_revision,
        method=CustomerCommercialConfirmation.Method.VERBAL,
        confirmation_reference="Phone confirmation",
        po_pending=True,
        confirmed_by=user,
        ready_for_sales_order_at=timezone.now(),
        ready_for_sales_order_by=user,
    )
    order = create_sales_order_from_quotation(
        quotation_id=quotation.pk, actor=user, data={"project_required": True}
    )
    submit_sales_order(order_id=order.pk, actor=user)
    release_sales_order(order_id=order.pk, actor=user)
    project = Project.objects.get(sales_order=order)
    submit_engineering_handoff(project_id=project.pk, actor=user)
    take_engineering_handoff(project_id=project.pk, actor=user)
    accept_engineering_handoff(project_id=project.pk, actor=user)
    project.refresh_from_db()
    return project


@pytest.mark.django_db
def test_panel_job_full_lifecycle(company, accepted_project, warehouse, location, product, admin):
    record_movement(
        company=company,
        movement_type=StockMovement.MovementType.INWARD,
        product=product,
        quantity=Decimal("20"),
        to_location=location,
        to_condition=StockItem.Condition.AVAILABLE,
        actor=admin,
    )
    panel_job = create_panel_job_from_project(
        project_id=accepted_project.pk,
        actor=admin,
        data={"panel_name": "MCC Panel #1", "warehouse": warehouse},
        material_lines=[{"product": product, "required_quantity": Decimal("10")}],
    )
    assert panel_job.panel_job_number.startswith("PANEL-")
    assert panel_job.status == PanelJob.Status.MATERIAL_PLANNING

    add_material_line(
        panel_job_id=panel_job.pk, actor=admin, product=product, required_quantity=Decimal("5")
    )
    assert panel_job.material_lines.count() == 2

    reserved = reserve_panel_job_materials(panel_job_id=panel_job.pk, actor=admin, location=location)
    assert reserved.status == PanelJob.Status.READY_FOR_ASSEMBLY
    total_reserved = sum(line.reserved_quantity for line in reserved.material_lines.all())
    assert total_reserved == Decimal("15")

    advanced = advance_panel_job_stage(panel_job_id=panel_job.pk, actor=admin)
    assert advanced.status == PanelJob.Status.ASSEMBLY

    line = panel_job.material_lines.first()
    record_material_movement(
        panel_job_id=panel_job.pk,
        actor=admin,
        material_line_id=line.pk,
        movement_type="ISSUE",
        quantity=Decimal("10"),
        location=location,
    )
    line.refresh_from_db()
    assert line.issued_quantity == Decimal("10")

    record_material_movement(
        panel_job_id=panel_job.pk,
        actor=admin,
        material_line_id=line.pk,
        movement_type="CONSUME",
        quantity=Decimal("8"),
        location=location,
    )
    line.refresh_from_db()
    assert line.consumed_quantity == Decimal("8")

    advance_panel_job_stage(panel_job_id=panel_job.pk, actor=admin)  # -> WIRING
    advance_panel_job_stage(panel_job_id=panel_job.pk, actor=admin)  # -> TESTING
    advance_panel_job_stage(panel_job_id=panel_job.pk, actor=admin)  # -> QUALITY_CHECK
    panel_job.refresh_from_db()
    assert panel_job.status == PanelJob.Status.QUALITY_CHECK

    failed_check = record_quality_check(
        panel_job_id=panel_job.pk, actor=admin, passed=False, notes="Insulation test failed"
    )
    assert failed_check.status == PanelJob.Status.TESTING
    assert failed_check.quality_passed is False

    advance_panel_job_stage(panel_job_id=panel_job.pk, actor=admin)  # -> QUALITY_CHECK again
    passed_check = record_quality_check(
        panel_job_id=panel_job.pk, actor=admin, passed=True, notes="All tests passed"
    )
    assert passed_check.status == PanelJob.Status.FITTING_INSTALLATION

    advance_panel_job_stage(panel_job_id=panel_job.pk, actor=admin)  # -> HANDOVER
    panel_job.refresh_from_db()
    assert panel_job.status == PanelJob.Status.HANDOVER

    closed = handover_panel_job(panel_job_id=panel_job.pk, actor=admin, notes="Handed over to site team")
    assert closed.status == PanelJob.Status.CLOSED
    assert closed.handed_over_at is not None

    assert panel_job.stage_events.count() >= 6


@pytest.mark.django_db
def test_reserve_materials_reports_shortage(company, accepted_project, warehouse, location, product, admin):
    record_movement(
        company=company,
        movement_type=StockMovement.MovementType.INWARD,
        product=product,
        quantity=Decimal("3"),
        to_location=location,
        to_condition=StockItem.Condition.AVAILABLE,
        actor=admin,
    )
    panel_job = create_panel_job_from_project(
        project_id=accepted_project.pk,
        actor=admin,
        data={"panel_name": "MCC Panel #2", "warehouse": warehouse},
        material_lines=[{"product": product, "required_quantity": Decimal("10")}],
    )
    reserved = reserve_panel_job_materials(panel_job_id=panel_job.pk, actor=admin, location=location)
    assert reserved.status == PanelJob.Status.MATERIAL_SHORTAGE
    line = reserved.material_lines.get()
    assert line.reserved_quantity == Decimal("3")
    assert line.shortage_quantity == Decimal("7")


@pytest.mark.django_db
def test_hold_and_resume_panel_job(company, accepted_project, warehouse, admin):
    panel_job = create_panel_job_from_project(
        project_id=accepted_project.pk,
        actor=admin,
        data={"panel_name": "MCC Panel #3", "warehouse": warehouse},
    )
    held = hold_panel_job(
        panel_job_id=panel_job.pk, actor=admin, reason="Waiting on customer drawing sign-off"
    )
    assert held.status == PanelJob.Status.ON_HOLD

    resumed = resume_panel_job(panel_job_id=panel_job.pk, actor=admin)
    assert resumed.status == PanelJob.Status.REQUIREMENT_REVIEW


@pytest.mark.django_db
def test_cancel_panel_job(company, accepted_project, warehouse, admin):
    panel_job = create_panel_job_from_project(
        project_id=accepted_project.pk,
        actor=admin,
        data={"panel_name": "MCC Panel #4", "warehouse": warehouse},
    )
    cancelled = cancel_panel_job(panel_job_id=panel_job.pk, actor=admin, reason="Order cancelled by customer")
    assert cancelled.status == PanelJob.Status.CANCELLED

    with pytest.raises(ValidationError):
        cancel_panel_job(panel_job_id=panel_job.pk, actor=admin, reason="Again")


@pytest.mark.django_db
def test_create_panel_job_rejected_for_project_not_accepted(company, accepted_project, warehouse, admin):
    accepted_project.status = Project.Status.HANDOFF_PENDING
    accepted_project.save(update_fields=["status"])
    with pytest.raises(ValidationError, match="accepted Workshop handoff"):
        create_panel_job_from_project(
            project_id=accepted_project.pk,
            actor=admin,
            data={"panel_name": "Should fail", "warehouse": warehouse},
        )


@pytest.mark.django_db
def test_user_without_workshop_permission_forbidden_from_panel_job_view(api_client, user, employee, company):
    _grant(user, company, ["purchasing.requisition.view"])
    api_client.force_authenticate(user)
    response = api_client.get("/api/v1/workshop/panel-jobs/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_user_with_workshop_permission_can_list_panel_jobs(api_client, user, employee, company):
    _grant(user, company, ["workshop.panel_job.view"])
    api_client.force_authenticate(user)
    response = api_client.get("/api/v1/workshop/panel-jobs/")
    assert response.status_code == 200
    assert response.data["results"] == []
