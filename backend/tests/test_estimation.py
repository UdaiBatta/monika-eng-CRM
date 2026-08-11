from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest
from django.db import connections
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.approvals.models import (
    ApprovalStepDefinition,
    ApprovalWorkflow,
    ApprovalWorkflowVersion,
)
from apps.approvals.services import approve_request
from apps.crm.models import Customer
from apps.engineering_reviews.models import EngineeringFeasibilityReview
from apps.enquiries.models import Enquiry
from apps.estimation.models import CommercialEstimate
from apps.estimation.services import (
    create_cost_line,
    create_estimate,
    revise_estimate,
    submit_estimate,
    update_estimate,
)
from apps.masters.models import Currency
from apps.numbering.models import DocumentSequence
from apps.numbering.services import financial_year_label
from apps.rbac.models import Permission, Role, RoleAssignment, RolePermission, ScopeType


@pytest.fixture
def admin(db):
    return User.objects.create_superuser(email="estimate-admin@example.test", password="SafePassword-2741")


@pytest.fixture
def currency(db):
    return Currency.objects.get_or_create(
        code="INR", defaults={"name": "Indian Rupee", "symbol": "₹", "decimal_places": 2}
    )[0]


@pytest.fixture
def enquiry(company, employee, admin, currency):
    customer = Customer.objects.create(
        company=company,
        customer_code="CUST-EST-001",
        legal_name="Estimate Customer Pvt. Ltd.",
        default_currency=currency,
        status=Customer.Status.ACTIVE,
        created_by=admin,
        updated_by=admin,
    )
    enquiry = Enquiry.objects.create(
        company=company,
        enquiry_number="ENQ-EST-001",
        customer=customer,
        subject="Control panel estimation",
        responsible_salesperson=employee,
        status=Enquiry.Status.ENGINEERING_REVIEW,
        created_by=admin,
        updated_by=admin,
    )
    EngineeringFeasibilityReview.objects.create(
        company=company,
        enquiry=enquiry,
        revision_number=1,
        is_current=True,
        status=EngineeringFeasibilityReview.Status.FEASIBLE,
        result=EngineeringFeasibilityReview.Result.FEASIBLE,
        technical_summary="Technically feasible using standard MCC architecture.",
        assumptions="Customer provides approved GA.",
        exclusions="Site cabling excluded.",
        engineering_hours=Decimal("24"),
        manufacturing_hours=Decimal("120"),
        completed_at=timezone.now(),
        completed_by=admin,
        created_by=admin,
    )
    DocumentSequence.objects.create(
        company=company,
        code="ESTIMATE",
        financial_year=financial_year_label(company),
        template="EST-2026-{number}",
        padding=4,
    )
    return enquiry


def add_costs(estimate, admin):
    create_cost_line(
        estimate_id=estimate.pk,
        actor=admin,
        data={
            "category": "MATERIAL",
            "description": "Switchgear and enclosure",
            "quantity": Decimal("2"),
            "unit_of_measure": "LOT",
            "unit_cost": Decimal("100"),
        },
    )
    create_cost_line(
        estimate_id=estimate.pk,
        actor=admin,
        data={
            "category": "LABOUR",
            "description": "Assembly labour",
            "quantity": Decimal("5"),
            "unit_of_measure": "HR",
            "unit_cost": Decimal("10"),
        },
    )
    create_cost_line(
        estimate_id=estimate.pk,
        actor=admin,
        data={
            "category": "FREIGHT",
            "description": "Optional express freight",
            "quantity": Decimal("1"),
            "unit_cost": Decimal("99"),
            "is_optional": True,
        },
    )


def approval_workflow(company, approver):
    workflow = ApprovalWorkflow.objects.create(
        company=company,
        code="EST-APPROVAL",
        name="Commercial estimate approval",
        entity_type="commercial_estimate",
    )
    version = ApprovalWorkflowVersion.objects.create(
        workflow=workflow,
        version_number=1,
        allow_self_approval=True,
        created_by=approver,
    )
    step = ApprovalStepDefinition.objects.create(
        workflow_version=version,
        sequence=1,
        name="Commercial approval",
        resolver_type=ApprovalStepDefinition.ResolverType.SPECIFIC_USERS,
    )
    step.specific_users.add(approver)
    version.status = ApprovalWorkflowVersion.Status.ACTIVE
    version.save(update_fields=["status", "updated_at"])
    workflow.current_version = version
    workflow.save(update_fields=["current_version", "updated_at"])
    return workflow


@pytest.mark.django_db
def test_estimate_requires_ready_engineering_and_uses_controlled_numbering(
    enquiry, admin
):
    review = enquiry.engineering_reviews.get()
    review.status = EngineeringFeasibilityReview.Status.IN_REVIEW
    review.result = ""
    review.completed_at = None
    review.completed_by = None
    review.save()

    with pytest.raises(ValidationError, match="feasible"):
        create_estimate(enquiry_id=enquiry.pk, actor=admin)

    review.status = EngineeringFeasibilityReview.Status.FEASIBLE
    review.result = EngineeringFeasibilityReview.Result.FEASIBLE
    review.completed_at = timezone.now()
    review.completed_by = admin
    review.save()
    estimate = create_estimate(enquiry_id=enquiry.pk, actor=admin)

    enquiry.refresh_from_db()
    assert estimate.estimate_number == "EST-2026-0001"
    assert estimate.engineering_review == review
    assert estimate.assumptions == "Customer provides approved GA."
    assert enquiry.status == Enquiry.Status.ESTIMATION
    assert create_estimate(enquiry_id=enquiry.pk, actor=admin).pk == estimate.pk


@pytest.mark.django_db
def test_cost_build_up_and_markup_are_decimal_and_server_calculated(enquiry, admin):
    estimate = create_estimate(enquiry_id=enquiry.pk, actor=admin)
    add_costs(estimate, admin)
    estimate = update_estimate(
        estimate_id=estimate.pk,
        actor=admin,
        data={"pricing_method": "MARKUP", "markup_percent": Decimal("20")},
    )

    assert estimate.total_cost == Decimal("250.00")
    assert estimate.category_totals == {"MATERIAL": "200.00", "LABOUR": "50.00"}
    assert estimate.proposed_selling_price == Decimal("300.00")
    assert estimate.gross_margin_amount == Decimal("50.00")
    assert estimate.gross_margin_percent == Decimal("16.6667")


@pytest.mark.django_db
def test_approval_locks_estimate_and_revision_preserves_history(
    enquiry, admin, employee, django_capture_on_commit_callbacks
):
    grant(employee.user, enquiry.company, "approvals.request.approve")
    approval_workflow(enquiry.company, employee.user)
    estimate = create_estimate(enquiry_id=enquiry.pk, actor=admin)
    add_costs(estimate, admin)
    update_estimate(
        estimate_id=estimate.pk,
        actor=admin,
        data={"pricing_method": "MARKUP", "markup_percent": Decimal("25")},
    )
    submitted = submit_estimate(estimate_id=estimate.pk, actor=admin, comment="Ready for approval")
    assert submitted.status == CommercialEstimate.Status.PENDING_APPROVAL

    with django_capture_on_commit_callbacks(execute=True):
        approve_request(
            request_id=submitted.approval_request_id,
            actor=employee.user,
            comment="Approved",
        )
    submitted.refresh_from_db()
    assert submitted.status == CommercialEstimate.Status.APPROVED
    assert submitted.approved_at is not None
    with pytest.raises(ValidationError, match="edited"):
        update_estimate(
            estimate_id=submitted.pk,
            actor=admin,
            data={"markup_percent": Decimal("30")},
        )

    revised = revise_estimate(
        estimate_id=submitted.pk,
        actor=admin,
        reason="Customer requested alternate enclosure",
    )
    submitted.refresh_from_db()
    assert submitted.is_current is False
    assert submitted.status == CommercialEstimate.Status.SUPERSEDED
    assert revised.revision_number == 2
    assert revised.cost_lines.count() == 3
    assert revised.approval_request is None
    assert revised.status == CommercialEstimate.Status.DRAFT


def grant(user, company, *codes):
    role = Role.objects.create(company=company, code="EST-VIEW", name="Estimate viewer")
    for code in codes:
        permission = Permission.objects.get(code=code)
        RolePermission.objects.create(role=role, permission=permission)
    RoleAssignment.objects.create(user=user, role=role, scope_type=ScopeType.COMPANY, company=company)


@pytest.mark.django_db
def test_cost_and_margin_fields_are_hidden_without_confidential_permissions(
    api_client, enquiry, admin, user, employee
):
    estimate = create_estimate(enquiry_id=enquiry.pk, actor=admin)
    add_costs(estimate, admin)
    grant(user, enquiry.company, "estimation.estimate.view")
    api_client.force_authenticate(user)

    response = api_client.get(f"/api/v1/commercial-estimates/{estimate.pk}/")

    assert response.status_code == 200
    assert "cost_lines" not in response.data
    assert "total_cost" not in response.data
    assert "proposed_selling_price" not in response.data
    assert "gross_margin_percent" not in response.data


@pytest.mark.django_db(transaction=True)
def test_concurrent_estimate_creation_returns_one_current_revision(enquiry, admin):
    barrier = Barrier(2)

    def attempt():
        connections.close_all()
        try:
            actor = User.objects.get(pk=admin.pk)
            barrier.wait(timeout=5)
            return str(create_estimate(enquiry_id=enquiry.pk, actor=actor).pk)
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(lambda _index: attempt(), range(2)))

    assert len(set(ids)) == 1
    assert CommercialEstimate.objects.filter(enquiry=enquiry, is_current=True).count() == 1
