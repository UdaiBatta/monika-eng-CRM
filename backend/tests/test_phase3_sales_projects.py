from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal

import pytest
from django.db import close_old_connections, connections
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.core.conflicts import VersionConflict
from apps.crm.models import Customer
from apps.enquiries.models import Enquiry
from apps.masters.models import Currency
from apps.numbering.models import DocumentSequence
from apps.numbering.services import financial_year_label
from apps.organization.models import Employee
from apps.projects.models import Project, ProjectEngineeringHandoff, ProjectHandoffClarification
from apps.projects.services import (
    accept_engineering_handoff,
    cancel_project,
    hold_project,
    prepare_engineering_handoff,
    request_project_clarification,
    respond_project_clarification,
    resume_project,
    submit_engineering_handoff,
    take_engineering_handoff,
)
from apps.quotations.models import CustomerCommercialConfirmation, Quotation
from apps.quotations.services import create_quotation
from apps.rbac.models import Permission, Role, RoleAssignment, RolePermission, ScopeType
from apps.sales.models import CustomerPurchaseOrder, SalesOrder
from apps.sales.services import (
    create_direct_sales_order,
    create_sales_order_amendment,
    create_sales_order_from_quotation,
    record_customer_po,
    release_sales_order,
    submit_sales_order,
    update_sales_order_draft,
)


@pytest.fixture
def phase3_context(company, employee, user):
    user.is_superuser = True
    user.is_staff = True
    user.save(update_fields=["is_superuser", "is_staff"])
    currency = Currency.objects.get_or_create(
        code="INR",
        defaults={"name": "Indian Rupee", "symbol": "₹", "decimal_places": 2},
    )[0]
    customer = Customer.objects.create(
        company=company,
        customer_code="CUST-P3-001",
        legal_name="ABC Industries Pvt. Ltd.",
        default_currency=currency,
        status=Customer.Status.ACTIVE,
        created_by=user,
        updated_by=user,
    )
    enquiry = Enquiry.objects.create(
        company=company,
        enquiry_number="ENQ-P3-001",
        customer=customer,
        subject="Two MCC control panels",
        responsible_salesperson=employee,
        status=Enquiry.Status.WON,
        closed_at=timezone.now(),
        closed_by=user,
        created_by=user,
        updated_by=user,
    )
    for code, template in (
        ("QUOTATION", "QTN-2026-{number}"),
        ("SO", "SO-2026-{number}"),
        ("PRJ", "PRJ-2026-{number}"),
        ("ENQUIRY", "ENQ-2026-{number}"),
    ):
        DocumentSequence.objects.create(
            company=company,
            code=code,
            financial_year=financial_year_label(company),
            template=template,
            padding=4,
        )
    quotation = create_quotation(
        actor=user,
        data={
            "path": Quotation.Path.QUICK,
            "customer_id": customer.pk,
            "enquiry_id": enquiry.pk,
            "quick_reason": "Repeat configuration requested urgently.",
            "scope": "Supply of two MCC control panels.",
            "payment_terms": "30% advance",
            "delivery_terms": "8–10 weeks",
            "warranty_terms": "12 months",
            "lines": [
                {
                    "description": "MCC Control Panel",
                    "quantity": "2",
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
    return {"currency": currency, "customer": customer, "quotation": quotation}


@pytest.mark.django_db
def test_customer_po_duplicate_and_variance(user, phase3_context):
    context = phase3_context
    payload = {
        "customer_id": context["customer"].pk,
        "po_number": "PO-ABC-107",
        "po_date": timezone.localdate(),
        "quotation_id": context["quotation"].pk,
        "currency_id": context["currency"].pk,
        "stated_total": "1200000",
        "delivery_information": "6 weeks",
        "payment_terms": "45 days",
    }
    po = record_customer_po(actor=user, data=payload)
    assert po.current_revision.match_status == "DIFFERENCES"
    assert {item["field"] for item in po.current_revision.variance_snapshot} >= {
        "order_value",
        "delivery",
        "payment_terms",
    }
    with pytest.raises(ValidationError, match="already exists"):
        record_customer_po(actor=user, data={**payload, "po_number": "po-abc-107"})
    assert CustomerPurchaseOrder.objects.count() == 1


@pytest.mark.django_db
def test_quote_release_creates_project_and_handoff(user, phase3_context):
    order = create_sales_order_from_quotation(
        quotation_id=phase3_context["quotation"].pk,
        actor=user,
        data={"project_required": True},
    )
    assert order.current_revision.grand_total == Decimal("1180000.00")
    submit_sales_order(order_id=order.pk, actor=user)
    release_sales_order(order_id=order.pk, actor=user)
    project = Project.objects.get(sales_order=order)
    assert project.project_number == "PRJ-2026-0001"
    submit_engineering_handoff(project_id=project.pk, actor=user)
    take_engineering_handoff(project_id=project.pk, actor=user)
    clarification = request_project_clarification(
        project_id=project.pk, actor=user, question="Confirm the final panel depth."
    )
    assert clarification.status == ProjectHandoffClarification.Status.OPEN
    respond_project_clarification(
        clarification_id=clarification.pk,
        actor=user,
        response="Customer confirmed 600 mm depth.",
    )
    handoff = accept_engineering_handoff(project_id=project.pk, actor=user)
    project.refresh_from_db()
    assert handoff.status == ProjectEngineeringHandoff.Status.ACCEPTED
    assert project.status == Project.Status.ENGINEERING_ACCEPTED
    assert handoff.accepted_snapshot["sales_order_revision"] == 0


@pytest.mark.django_db
def test_direct_order_permission_and_crm_history(user, employee, company, phase3_context):
    user.is_superuser = False
    user.save(update_fields=["is_superuser"])
    payload = {
        "customer_id": phase3_context["customer"].pk,
        "currency_id": phase3_context["currency"].pk,
        "confirmation_channel": "PHONE",
        "direct_reason": "REPEAT_ORDER",
        "po_pending": True,
        "project_required": False,
        "lines": [
            {
                "description": "Spare contactor",
                "quantity": "2",
                "unit_of_measure": "NOS",
                "unit_price": "2500",
                "tax_percent": "18",
            }
        ],
    }
    with pytest.raises(PermissionDenied):
        create_direct_sales_order(actor=user, data=payload)
    role = Role.objects.create(company=company, code="DIRECT-SALES", name="Direct Sales test")
    RolePermission.objects.create(
        role=role, permission=Permission.objects.get(code="sales.sales_order.direct_create")
    )
    RoleAssignment.objects.create(user=user, role=role, scope_type=ScopeType.COMPANY, company=company)
    order = create_direct_sales_order(actor=user, data=payload)
    assert order.order_mode == SalesOrder.Mode.DIRECT
    assert order.po_pending and not order.project_required
    assert order.enquiry.status == Enquiry.Status.WON


@pytest.mark.django_db
def test_amendment_updates_project_commercial_baseline(user, phase3_context):
    order = create_sales_order_from_quotation(
        quotation_id=phase3_context["quotation"].pk,
        actor=user,
        data={"project_required": True},
    )
    submit_sales_order(order_id=order.pk, actor=user)
    release_sales_order(order_id=order.pk, actor=user)
    released = order.current_revision
    with pytest.raises(ValidationError, match="current draft"):
        update_sales_order_draft(
            revision_id=released.pk,
            actor=user,
            submitted_version=released.record_version,
            data={"delivery_terms": "6 weeks"},
        )
    amendment = create_sales_order_amendment(
        order_id=order.pk, actor=user, reason="Customer changed delivery and quantity."
    )
    update_sales_order_draft(
        revision_id=amendment.pk,
        actor=user,
        submitted_version=amendment.record_version,
        data={"delivery_terms": "6 weeks"},
    )
    submit_sales_order(order_id=order.pk, actor=user)
    release_sales_order(order_id=order.pk, actor=user)
    project = Project.objects.get(sales_order=order)
    assert project.current_sales_order_revision.revision_number == 1
    assert project.previous_sales_order_revision.revision_number == 0
    assert project.commercial_change_pending is True


@pytest.mark.django_db
def test_project_hold_resume_and_cancel_are_command_controlled(user, phase3_context):
    order = create_sales_order_from_quotation(
        quotation_id=phase3_context["quotation"].pk,
        actor=user,
        data={"project_required": True},
    )
    submit_sales_order(order_id=order.pk, actor=user)
    release_sales_order(order_id=order.pk, actor=user)
    project = Project.objects.get(sales_order=order)

    hold_project(project_id=project.pk, actor=user, reason="Customer asked us to pause.")
    project.refresh_from_db()
    assert project.status == Project.Status.ON_HOLD

    resume_project(project_id=project.pk, actor=user)
    project.refresh_from_db()
    assert project.status == Project.Status.NEW

    cancel_project(project_id=project.pk, actor=user, reason="Customer cancelled the job.")
    project.refresh_from_db()
    assert project.status == Project.Status.CANCELLED


@pytest.mark.django_db
def test_project_360_api_serializes_the_real_commercial_baseline(
    api_client, user, phase3_context
):
    order = create_sales_order_from_quotation(
        quotation_id=phase3_context["quotation"].pk,
        actor=user,
        data={"project_required": True},
    )
    submit_sales_order(order_id=order.pk, actor=user)
    release_sales_order(order_id=order.pk, actor=user)
    project = Project.objects.get(sales_order=order)
    api_client.force_authenticate(user)

    response = api_client.get(f"/api/v1/projects/{project.pk}/")

    assert response.status_code == 200
    assert response.data["project_number"] == project.project_number
    assert response.data["sales_order_detail"]["sales_order_number"] == order.sales_order_number
    assert response.data["current_commercial_baseline"] == str(order.current_revision)
    assert response.data["engineering_handoff"]["status"] == "DRAFT"


@pytest.mark.django_db
def test_workflow_statuses_reject_direct_patch(api_client, user, phase3_context):
    order = create_sales_order_from_quotation(
        quotation_id=phase3_context["quotation"].pk,
        actor=user,
        data={"project_required": True},
    )
    submit_sales_order(order_id=order.pk, actor=user)
    release_sales_order(order_id=order.pk, actor=user)
    project = Project.objects.get(sales_order=order)
    api_client.force_authenticate(user)

    attempts = [
        (f"/api/v1/quotations/{phase3_context['quotation'].pk}/", {"status": "DRAFT"}),
        (f"/api/v1/sales/orders/{order.pk}/", {"status": "CANCELLED"}),
        (f"/api/v1/projects/{project.pk}/", {"status": "ENGINEERING_ACCEPTED"}),
    ]
    for path, payload in attempts:
        assert api_client.patch(path, payload, format="json").status_code == 405

    phase3_context["quotation"].refresh_from_db()
    order.refresh_from_db()
    project.refresh_from_db()
    assert phase3_context["quotation"].status == Quotation.Status.READY_FOR_SALES_ORDER
    assert order.status == SalesOrder.Status.RELEASED
    assert project.status == Project.Status.HANDOFF_PENDING


@pytest.mark.django_db(transaction=True)
def test_two_engineers_cannot_take_the_same_handoff(
    user, employee, company, branch, department, phase3_context
):
    second_user = User.objects.create_superuser(
        email="second-engineer@example.test", password="SafePassword-2741"
    )
    second_employee = Employee.objects.create(
        user=second_user,
        company=company,
        branch=branch,
        department=department,
        employee_code="ME-TEST-002",
        first_name="Second",
        last_name="Engineer",
        joining_date=date(2026, 1, 1),
        employment_type=Employee.EmploymentType.PERMANENT,
    )
    order = create_sales_order_from_quotation(
        quotation_id=phase3_context["quotation"].pk,
        actor=user,
        data={"project_required": True},
    )
    submit_sales_order(order_id=order.pk, actor=user)
    release_sales_order(order_id=order.pk, actor=user)
    project = Project.objects.get(sales_order=order)
    submit_engineering_handoff(project_id=project.pk, actor=user)

    def take(actor):
        close_old_connections()
        try:
            handoff = take_engineering_handoff(project_id=project.pk, actor=actor)
            return ("taken", handoff.assigned_engineer_id)
        except ValidationError as exc:
            return ("rejected", str(exc))
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(take, [user, second_user]))

    project.refresh_from_db()
    assert sorted(item[0] for item in outcomes) == ["rejected", "taken"]
    assert project.engineering_owner_id in {employee.pk, second_employee.pk}


@pytest.mark.django_db
def test_sales_order_and_handoff_reject_stale_edits(user, phase3_context):
    order = create_sales_order_from_quotation(
        quotation_id=phase3_context["quotation"].pk,
        actor=user,
        data={"project_required": True},
    )
    original_version = order.current_revision.record_version
    update_sales_order_draft(
        revision_id=order.current_revision_id,
        actor=user,
        submitted_version=original_version,
        data={"delivery_terms": "Confirmed 8 weeks"},
    )
    with pytest.raises(VersionConflict):
        update_sales_order_draft(
            revision_id=order.current_revision_id,
            actor=user,
            submitted_version=original_version,
            data={"delivery_terms": "Stale 6 week edit"},
        )

    order.refresh_from_db()
    submit_sales_order(order_id=order.pk, actor=user)
    release_sales_order(order_id=order.pk, actor=user)
    project = Project.objects.get(sales_order=order)
    handoff = ProjectEngineeringHandoff.objects.get(project=project)
    prepare_engineering_handoff(
        project_id=project.pk,
        actor=user,
        submitted_version=handoff.record_version,
        data={"project_scope_summary": "Confirmed MCC panel scope"},
    )
    with pytest.raises(VersionConflict):
        prepare_engineering_handoff(
            project_id=project.pk,
            actor=user,
            submitted_version=handoff.record_version,
            data={"project_scope_summary": "Stale handoff scope"},
        )
