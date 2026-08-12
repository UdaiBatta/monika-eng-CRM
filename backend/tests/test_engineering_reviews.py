import threading
from datetime import date

import pytest
from django.db import connections
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.approvals.models import ApprovalRequest, ApprovalStepDefinition
from apps.approvals.services import activate_workflow_version, approve_request, create_workflow
from apps.crm.models import Customer
from apps.engineering_reviews.models import EngineeringClarification, EngineeringFeasibilityReview
from apps.engineering_reviews.services import (
    assign_review,
    close_clarification,
    complete_review,
    is_ready_for_estimation,
    mark_not_feasible,
    reassess_review,
    request_clarification,
    respond_to_clarification,
    start_review,
    update_assessment,
)
from apps.enquiries.models import Enquiry
from apps.enquiries.services import transition_enquiry
from apps.masters.models import Currency
from apps.notifications.models import Notification
from apps.organization.models import Company, Employee
from apps.rbac.models import Permission, Role, RoleAssignment, RolePermission, ScopeType


@pytest.fixture
def admin(db):
    return User.objects.create_superuser(email="engineering-admin@example.test", password="SafePassword-2741")


@pytest.fixture
def enquiry(company, employee, admin):
    currency, _ = Currency.objects.get_or_create(
        code="INR",
        defaults={"name": "Indian Rupee", "symbol": "₹"},
    )
    customer = Customer.objects.create(
        company=company,
        customer_code="CUST-ENG-001",
        legal_name="Engineering Customer Pvt. Ltd.",
        default_currency=currency,
        created_by=admin,
        updated_by=admin,
    )
    return Enquiry.objects.create(
        company=company,
        enquiry_number="ENQ-ENG-001",
        customer=customer,
        subject="Automation control panel",
        responsible_salesperson=employee,
        status=Enquiry.Status.RECEIVED,
        created_by=admin,
        updated_by=admin,
    )


def grant(user, company, *codes):
    role = Role.objects.create(
        company=company, code=f"ENG-{Role.objects.count()}", name="Engineering test role"
    )
    for code in codes:
        permission, _ = Permission.objects.get_or_create(code=code, defaults={"name": code})
        RolePermission.objects.create(role=role, permission=permission)
    RoleAssignment.objects.create(user=user, role=role, scope_type=ScopeType.COMPANY, company=company)


def active_review(enquiry, employee, admin):
    transition_enquiry(
        enquiry_id=enquiry.pk,
        actor=admin,
        target_status=Enquiry.Status.ENGINEERING_REVIEW,
        permission="enquiry.enquiry.submit_engineering",
    )
    review = enquiry.engineering_reviews.get(is_current=True)
    assign_review(review_id=review.pk, engineer_id=employee.pk, actor=admin)
    return start_review(review_id=review.pk, actor=admin)


@pytest.mark.django_db
def test_send_to_engineering_creates_one_controlled_review(enquiry, admin):
    transition_enquiry(
        enquiry_id=enquiry.pk,
        actor=admin,
        target_status=Enquiry.Status.ENGINEERING_REVIEW,
        permission="enquiry.enquiry.submit_engineering",
    )

    review = enquiry.engineering_reviews.get()
    assert review.status == EngineeringFeasibilityReview.Status.PENDING
    assert review.revision_number == 1
    assert review.is_current is True

    with pytest.raises(ValidationError, match="cannot move"):
        transition_enquiry(
            enquiry_id=enquiry.pk,
            actor=admin,
            target_status=Enquiry.Status.ENGINEERING_REVIEW,
            permission="enquiry.enquiry.submit_engineering",
        )
    assert enquiry.engineering_reviews.count() == 1


@pytest.mark.django_db
def test_feasibility_flow_clarification_and_ready_gate(
    enquiry,
    employee,
    admin,
    django_capture_on_commit_callbacks,
):
    with django_capture_on_commit_callbacks(execute=True):
        review = active_review(enquiry, employee, admin)
        update_assessment(
            review_id=review.pk,
            actor=admin,
            data={
                "technical_summary": "Panel can be manufactured with the proposed architecture.",
                "engineering_hours": "42.50",
                "manufacturing_hours": "120.00",
                "lead_time_days": 35,
                "risks": "Long-lead PLC module.",
            },
        )
        clarification = request_clarification(
            review_id=review.pk,
            actor=admin,
            subject="Confirm fault level",
            question="Confirm the incoming fault level in kA.",
            assigned_to_id=employee.pk,
        )
        assert review.clarifications.filter(status=EngineeringClarification.Status.OPEN).exists()
        with pytest.raises(ValidationError, match="outstanding clarification"):
            complete_review(
                review_id=review.pk,
                actor=admin,
                result=EngineeringFeasibilityReview.Result.FEASIBLE,
                completion_comment="Technically feasible.",
            )
        respond_to_clarification(
            clarification_id=clarification.pk, actor=admin, response="Customer confirmed 50 kA."
        )
        close_clarification(
            clarification_id=clarification.pk, actor=admin, closure_comment="Included in design basis."
        )
        review = complete_review(
            review_id=review.pk,
            actor=admin,
            result=EngineeringFeasibilityReview.Result.FEASIBLE_WITH_CONDITIONS,
            completion_comment="Proceed subject to the recorded design basis.",
        )

    assert review.status == EngineeringFeasibilityReview.Status.FEASIBLE
    assert review.engineering_hours == 42.50
    assert is_ready_for_estimation(review) is True
    assert Notification.objects.filter(notification_type="ENGINEERING_REVIEW_COMPLETED").exists()


@pytest.mark.django_db
def test_not_feasible_does_not_mark_enquiry_lost(enquiry, employee, admin):
    review = active_review(enquiry, employee, admin)
    update_assessment(
        review_id=review.pk,
        actor=admin,
        data={"technical_summary": "Required certification is outside current capability."},
    )

    review = mark_not_feasible(
        review_id=review.pk,
        actor=admin,
        completion_comment="Do not proceed without an approved external certification partner.",
    )

    enquiry.refresh_from_db()
    assert review.status == EngineeringFeasibilityReview.Status.NOT_FEASIBLE
    assert review.result == EngineeringFeasibilityReview.Result.NOT_FEASIBLE
    assert enquiry.status == Enquiry.Status.ENGINEERING_REVIEW
    assert enquiry.lost_reason == ""
    assert is_ready_for_estimation(review) is False


@pytest.mark.django_db
def test_reassessment_preserves_revision_history(enquiry, employee, admin):
    review = active_review(enquiry, employee, admin)
    update_assessment(
        review_id=review.pk, actor=admin, data={"technical_summary": "Initial concept feasible."}
    )
    review = complete_review(
        review_id=review.pk,
        actor=admin,
        result=EngineeringFeasibilityReview.Result.FEASIBLE,
        completion_comment="Release for next gate.",
    )

    revised = reassess_review(review_id=review.pk, actor=admin, reason="Customer increased the fault rating.")

    review.refresh_from_db()
    assert review.status == EngineeringFeasibilityReview.Status.SUPERSEDED
    assert review.is_current is False
    assert revised.revision_number == 2
    assert revised.is_current is True
    assert revised.supersedes_id == review.pk
    assert enquiry.engineering_reviews.count() == 2


@pytest.mark.django_db
def test_review_api_rejects_arbitrary_patch_and_invalid_decimal(api_client, enquiry, employee, admin):
    review = active_review(enquiry, employee, admin)
    api_client.force_authenticate(admin)

    status_patch = api_client.patch(
        f"/api/v1/engineering-reviews/{review.pk}/",
        {"status": EngineeringFeasibilityReview.Status.FEASIBLE},
        format="json",
    )
    invalid_hours = api_client.patch(
        f"/api/v1/engineering-reviews/{review.pk}/assessment/",
        {"engineering_hours": "-0.01"},
        format="json",
    )

    assert status_patch.status_code == 405
    assert invalid_hours.status_code == 400


@pytest.mark.django_db
def test_inactive_or_cross_company_engineer_cannot_be_assigned(enquiry, admin):
    other_company = Company.objects.create(name="Other Engineering Company", code="OTHER-ENG")
    other_user = User.objects.create_user(email="other-engineer@example.test")
    other_engineer = Employee.objects.create(
        user=other_user,
        company=other_company,
        employee_code="OTHER-ENG-001",
        first_name="Other",
        joining_date=date(2026, 1, 1),
        employment_type=Employee.EmploymentType.PERMANENT,
    )
    transition_enquiry(
        enquiry_id=enquiry.pk,
        actor=admin,
        target_status=Enquiry.Status.ENGINEERING_REVIEW,
        permission="enquiry.enquiry.submit_engineering",
    )
    review = enquiry.engineering_reviews.get()

    with pytest.raises(ValidationError, match="active engineer"):
        assign_review(review_id=review.pk, engineer_id=other_engineer.pk, actor=admin)


@pytest.mark.django_db
def test_configured_generic_approval_controls_ready_gate(enquiry, employee, admin):
    approver = User.objects.create_user(
        email="engineering-approver@example.test", password="SafePassword-2741"
    )
    Employee.objects.create(
        user=approver,
        company=enquiry.company,
        employee_code="ME-ENG-APP-001",
        first_name="Engineering Approver",
        joining_date=date(2026, 1, 1),
        employment_type=Employee.EmploymentType.PERMANENT,
    )
    grant(approver, enquiry.company, "approvals.request.approve")
    workflow = create_workflow(
        company=enquiry.company,
        code="ENG-FEASIBILITY",
        name="Engineering feasibility approval",
        entity_type="engineering_feasibility_review",
        actor=admin,
    )
    version = workflow.versions.get(version_number=1)
    step = ApprovalStepDefinition.objects.create(
        workflow_version=version,
        sequence=1,
        name="Engineering manager approval",
        resolver_type=ApprovalStepDefinition.ResolverType.SPECIFIC_USERS,
    )
    step.specific_users.set([approver])
    activate_workflow_version(version_id=version.pk, actor=admin)
    review = active_review(enquiry, employee, admin)
    update_assessment(
        review_id=review.pk,
        actor=admin,
        data={"technical_summary": "Feasible after engineering manager review."},
    )

    review = complete_review(
        review_id=review.pk,
        actor=admin,
        result=EngineeringFeasibilityReview.Result.FEASIBLE,
        completion_comment="Submit for manager decision.",
    )

    request = ApprovalRequest.objects.get(
        entity_type="engineering_feasibility_review", entity_id=str(review.pk)
    )
    assert request.status == ApprovalRequest.Status.IN_PROGRESS
    assert is_ready_for_estimation(review) is False
    approve_request(request_id=request.pk, actor=approver, comment="Approved for estimation handoff.")
    assert is_ready_for_estimation(review) is True


@pytest.mark.django_db(transaction=True)
def test_concurrent_start_is_idempotent(enquiry, employee, admin):
    transition_enquiry(
        enquiry_id=enquiry.pk,
        actor=admin,
        target_status=Enquiry.Status.ENGINEERING_REVIEW,
        permission="enquiry.enquiry.submit_engineering",
    )
    review = enquiry.engineering_reviews.get()
    assign_review(review_id=review.pk, engineer_id=employee.pk, actor=admin)
    barrier = threading.Barrier(2)
    successes = []
    errors = []

    def worker():
        try:
            actor = User.objects.get(pk=admin.pk)
            barrier.wait(timeout=5)
            successes.append(start_review(review_id=review.pk, actor=actor).status)
        except Exception as exc:  # pragma: no cover - asserted below
            errors.append(exc)
        finally:
            connections.close_all()

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    review.refresh_from_db()
    assert successes == [EngineeringFeasibilityReview.Status.IN_REVIEW]
    assert len(errors) == 1
    assert review.status == EngineeringFeasibilityReview.Status.IN_REVIEW
    assert review.started_at and review.started_by_id == admin.pk
