import threading
from datetime import date

import pytest
from django.db import connections
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.approvals.models import (
    ApprovalCondition,
    ApprovalDecision,
    ApprovalRequest,
    ApprovalStepDefinition,
)
from apps.approvals.services import (
    activate_workflow_version,
    approve_request,
    cancel_request,
    clone_workflow_version,
    create_approval_request,
    create_workflow,
    reassign_request,
    reject_request,
    return_request,
)
from apps.audit.models import AuditEvent
from apps.documents.models import DocumentCategory
from apps.documents.services import add_version, create_document, link_document
from apps.organization.models import Company, Employee
from apps.rbac.models import Permission, Role, RoleAssignment, RolePermission, ScopeType

from .test_documents import pdf


def grant(user, company, *codes):
    role = Role.objects.create(
        company=company,
        code=f"APP-{Role.objects.count()}",
        name=f"Approver {Role.objects.count()}",
    )
    for code in codes:
        permission, _ = Permission.objects.get_or_create(code=code, defaults={"name": code})
        RolePermission.objects.create(role=role, permission=permission)
    RoleAssignment.objects.create(
        user=user,
        role=role,
        scope_type=ScopeType.COMPANY,
        company=company,
    )


def make_employee_user(company, branch, department, number):
    user = User.objects.create_user(
        email=f"approver-{number}@example.test",
        password="SafePassword-2741",
    )
    Employee.objects.create(
        user=user,
        company=company,
        branch=branch,
        department=department,
        employee_code=f"ME-APP-{number}",
        first_name=f"Approver {number}",
        joining_date=date(2026, 1, 1),
        employment_type=Employee.EmploymentType.PERMANENT,
    )
    return user


def drawing(company, admin, tmp_path, title="Approval Drawing"):
    document_category = DocumentCategory.objects.create(
        company=company,
        code=f"APPROVAL-{DocumentCategory.objects.count()}",
        name="Approval documents",
        allowed_extensions=["pdf"],
    )
    from django.test import override_settings

    with override_settings(LOCAL_PRIVATE_STORAGE_ROOT=tmp_path):
        return create_document(
            category=document_category,
            title=title,
            file_object=pdf(),
            actor=admin,
        )


def workflow(company, admin, approvers, *, mode="SINGLE", minimum=1, allow_self=False):
    item = create_workflow(
        company=company,
        code=f"DRAWING-{company.code}-{ApprovalRequest.objects.count()}",
        name="Drawing Review",
        entity_type="document",
        actor=admin,
    )
    version = item.versions.get(version_number=1)
    version.allow_self_approval = allow_self
    version.save()
    step = ApprovalStepDefinition.objects.create(
        workflow_version=version,
        sequence=1,
        name="Engineering approval",
        approval_mode=mode,
        resolver_type=ApprovalStepDefinition.ResolverType.SPECIFIC_USERS,
        minimum_approvals=minimum,
    )
    step.specific_users.set(approvers)
    activate_workflow_version(version_id=version.pk, actor=admin)
    item.refresh_from_db()
    return item


def submit(workflow_item, document, actor):
    return create_approval_request(
        workflow_id=workflow_item.pk,
        entity_type="document",
        entity_id=document.pk,
        actor=actor,
        submission_comment="Please review this drawing.",
    )


@pytest.fixture
def admin(db):
    return User.objects.create_superuser(
        email="approval-admin@example.test",
        password="SafePassword-2741",
    )


@pytest.mark.django_db
def test_workflow_creation_activation_versioning_and_history(
    company,
    branch,
    department,
    admin,
):
    approver = make_employee_user(company, branch, department, 1)
    item = workflow(company, admin, [approver])
    first = item.current_version
    cloned = clone_workflow_version(workflow_id=item.pk, actor=admin)
    cloned.steps.get(sequence=1).name = "Revised engineering approval"
    revised_step = cloned.steps.get(sequence=1)
    revised_step.name = "Revised engineering approval"
    revised_step.save()
    activate_workflow_version(version_id=cloned.pk, actor=admin)

    first.refresh_from_db()
    assert cloned.version_number == 2
    assert first.status == first.Status.RETIRED
    assert first.steps.get(sequence=1).name == "Engineering approval"
    assert cloned.steps.get(sequence=1).name == "Revised engineering approval"
    assert AuditEvent.objects.filter(event_type="approval.workflow_version_created").exists()


@pytest.mark.django_db
def test_safe_conditions_only_allow_registered_fields(company, admin):
    item = create_workflow(
        company=company,
        code="CONDITIONAL",
        name="Conditional drawing review",
        entity_type="document",
        actor=admin,
    )
    version = item.versions.get()
    with pytest.raises(Exception, match="not approved"):
        ApprovalCondition.objects.create(
            workflow_version=version,
            field="__class__",
            operator=ApprovalCondition.Operator.EQ,
            value="anything",
        )


@pytest.mark.django_db
def test_request_approval_preserves_snapshot_and_audits(
    company,
    branch,
    department,
    admin,
    tmp_path,
):
    approver = make_employee_user(company, branch, department, 2)
    grant(approver, company, "approvals.request.approve")
    item = workflow(company, admin, [approver])
    document = drawing(company, admin, tmp_path)
    request = submit(item, document, admin)

    approved = approve_request(request_id=request.pk, actor=approver, comment="Drawing is correct.")
    decision = approved.steps.get().decisions.get()

    assert approved.status == ApprovalRequest.Status.APPROVED
    assert approved.workflow_version_number == 1
    assert decision.decision == ApprovalDecision.Decision.APPROVED
    assert decision.decided_by_name == "Approver 2"
    assert AuditEvent.objects.filter(
        entity_id=str(request.pk),
        event_type="approval.request_approved",
    ).exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("command", "permission", "expected"),
    [
        (reject_request, "approvals.request.reject", ApprovalRequest.Status.REJECTED),
        (
            return_request,
            "approvals.request.return",
            ApprovalRequest.Status.RETURNED_FOR_CHANGES,
        ),
    ],
)
def test_reject_and_return_require_comments_and_close_request(
    command,
    permission,
    expected,
    company,
    branch,
    department,
    admin,
    tmp_path,
):
    approver = make_employee_user(company, branch, department, expected)
    grant(approver, company, permission)
    item = workflow(company, admin, [approver])
    request = submit(item, drawing(company, admin, tmp_path), admin)

    with pytest.raises(ValidationError, match="comment"):
        command(request_id=request.pk, actor=approver, comment="")
    decided = command(request_id=request.pk, actor=approver, comment="Please revise the drawing.")
    assert decided.status == expected
    assert decided.current_step is None


@pytest.mark.django_db
def test_cancel_self_approval_unauthorized_and_double_decision_guards(
    company,
    branch,
    department,
    user,
    employee,
    admin,
    tmp_path,
):
    grant(
        user,
        company,
        "approvals.request.submit",
        "approvals.request.approve",
        "approvals.request.cancel",
    )
    item = workflow(company, admin, [user])
    request = submit(item, drawing(company, admin, tmp_path), user)
    outsider = make_employee_user(company, branch, department, 9)
    grant(outsider, company, "approvals.request.approve")

    with pytest.raises(PermissionDenied, match="not assigned"):
        approve_request(request_id=request.pk, actor=outsider)
    with pytest.raises(PermissionDenied, match="submitted"):
        approve_request(request_id=request.pk, actor=user)

    cancelled = cancel_request(request_id=request.pk, actor=user, comment="Uploading a revision")
    assert cancelled.status == ApprovalRequest.Status.CANCELLED
    with pytest.raises(ValidationError, match="no longer awaiting"):
        approve_request(request_id=request.pk, actor=user)


@pytest.mark.django_db
def test_admin_can_reassign_inactive_pending_approver_and_preserve_history(
    company,
    branch,
    department,
    admin,
    tmp_path,
):
    original = make_employee_user(company, branch, department, 31)
    replacement = make_employee_user(company, branch, department, 32)
    grant(replacement, company, "approvals.request.approve")
    item = workflow(company, admin, [original])
    request = submit(item, drawing(company, admin, tmp_path), admin)
    assignment = request.current_step.assignments.get(approver=original)

    original.is_active = False
    original.save(update_fields=["is_active"])
    original.employee.employment_status = Employee.EmploymentStatus.INACTIVE
    original.employee.save(update_fields=["employment_status", "updated_at"])

    updated = reassign_request(
        request_id=request.pk,
        assignment_id=assignment.pk,
        approver_id=replacement.pk,
        actor=admin,
        reason="Original approver left the company.",
    )

    assignment.refresh_from_db()
    assert assignment.status == assignment.Status.SKIPPED
    assert assignment.approver_name == "Approver 31"
    assert updated.current_step.assignments.filter(
        approver=replacement,
        status="PENDING",
    ).exists()
    assert AuditEvent.objects.filter(event_type="approval.assignment_reassigned").exists()


@pytest.mark.django_db
def test_approval_api_preserves_business_error_code(
    api_client,
    company,
    user,
    employee,
    admin,
    tmp_path,
):
    grant(user, company, "approvals.request.submit", "approvals.request.approve")
    item = workflow(company, admin, [user])
    request = submit(item, drawing(company, admin, tmp_path), user)
    api_client.force_authenticate(user)

    response = api_client.post(f"/api/v1/approvals/requests/{request.pk}/approve/", {})

    assert response.status_code == 403
    assert response.data["error"]["code"] == "SELF_APPROVAL_NOT_ALLOWED"


@pytest.mark.django_db
def test_cross_company_workflow_is_rejected(company, admin, tmp_path):
    other = Company.objects.create(name="Other Approval Company", code="OTHER-APP")
    item = create_workflow(
        company=other,
        code="OTHER-WORKFLOW",
        name="Other workflow",
        entity_type="document",
        actor=admin,
    )
    with pytest.raises(ValidationError, match="same company"):
        create_approval_request(
            workflow_id=item.pk,
            entity_type="document",
            entity_id=drawing(company, admin, tmp_path).pk,
            actor=admin,
        )


@pytest.mark.django_db(transaction=True)
def test_concurrent_parallel_final_approval_is_consistent(company, branch, department, tmp_path):
    admin = User.objects.create_superuser(
        email="parallel-admin@example.test",
        password="SafePassword-2741",
    )
    approvers = [make_employee_user(company, branch, department, number) for number in (21, 22)]
    for approver in approvers:
        grant(approver, company, "approvals.request.approve")
    item = workflow(company, admin, approvers, mode="PARALLEL", minimum=2)
    request = submit(item, drawing(company, admin, tmp_path), admin)
    barrier = threading.Barrier(2)
    errors = []

    def worker(user_id):
        try:
            actor = User.objects.get(pk=user_id)
            barrier.wait(timeout=5)
            approve_request(request_id=request.pk, actor=actor, comment="Approved in parallel")
        except Exception as exc:  # pragma: no cover - asserted below
            errors.append(exc)
        finally:
            connections.close_all()

    threads = [threading.Thread(target=worker, args=(approver.pk,)) for approver in approvers]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    request.refresh_from_db()
    assert errors == []
    assert request.status == ApprovalRequest.Status.APPROVED
    assert request.steps.get().decisions.count() == 2


@pytest.mark.django_db
def test_request_status_cannot_be_patched(api_client, company, admin, tmp_path):
    item = create_workflow(
        company=company,
        code="NO-PATCH",
        name="No patch workflow",
        entity_type="document",
        actor=admin,
    )
    request = ApprovalRequest.objects.create(
        company=company,
        workflow_version=item.versions.get(),
        workflow_name=item.name,
        workflow_version_number=1,
        entity_type="document",
        entity_id=str(drawing(company, admin, tmp_path).pk),
        entity_reference="Drawing",
        requested_by=admin,
        requested_by_name=admin.email,
    )
    api_client.force_authenticate(admin)
    response = api_client.patch(
        f"/api/v1/approvals/requests/{request.pk}/",
        {"status": "APPROVED"},
        format="json",
    )
    assert response.status_code == 405


@pytest.mark.django_db
def test_approval_uses_shared_documents_with_independent_download_permission(
    api_client,
    company,
    branch,
    department,
    admin,
    tmp_path,
):
    from django.test import override_settings

    approver = make_employee_user(company, branch, department, 71)
    outsider = make_employee_user(company, branch, department, 72)
    grant(
        approver,
        company,
        "approvals.request.approve",
        "documents.document.view",
        "documents.document.download",
    )
    grant(outsider, company, "approvals.request.view")
    item = workflow(company, admin, [approver])
    with override_settings(LOCAL_PRIVATE_STORAGE_ROOT=tmp_path):
        document = drawing(company, admin, tmp_path, title="Linked approval document")
        request = submit(item, document, admin)
        link_document(
            document=document,
            entity_type="approval_request",
            entity_id=request.pk,
            relationship_type="SUPPORTING",
            actor=admin,
        )

        api_client.force_authenticate(approver)
        response = api_client.get(f"/api/v1/documents/{document.pk}/download/")
        assert response.status_code == 200
        b"".join(response.streaming_content)

        api_client.force_authenticate(outsider)
        assert api_client.get(f"/api/v1/documents/{document.pk}/download/").status_code == 403

        add_version(
            document_id=document.pk,
            file_object=pdf(name="drawing-rev-2.pdf", marker=b"revision two"),
            actor=admin,
        )

    request.refresh_from_db()
    assert request.entity_id == str(document.pk)
    assert request.steps.count() == 1
    assert document.links.filter(entity_type="approval_request", entity_id=str(request.pk)).exists()


@pytest.mark.django_db
def test_submit_can_atomically_link_supporting_document(
    company,
    branch,
    department,
    admin,
    tmp_path,
):
    approver = make_employee_user(company, branch, department, 81)
    item = workflow(company, admin, [approver])
    document = drawing(company, admin, tmp_path, title="Drawing submitted for approval")

    request = create_approval_request(
        workflow_id=item.pk,
        entity_type="document",
        entity_id=document.pk,
        supporting_document_ids=[document.pk],
        actor=admin,
    )

    assert document.links.filter(
        entity_type="approval_request",
        entity_id=str(request.pk),
        relationship_type="SUPPORTING",
    ).exists()
