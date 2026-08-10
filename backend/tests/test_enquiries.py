from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.core.entity_registry import registered_entity
from apps.crm.models import CrmActivity, Customer
from apps.enquiries.models import Enquiry, EnquiryItem, EnquiryRequirement
from apps.masters.models import Currency, UnitOfMeasure
from apps.notifications.models import Notification
from apps.numbering.models import DocumentSequence
from apps.numbering.services import financial_year_label
from apps.organization.models import Company
from apps.rbac.models import Permission, Role, RoleAssignment, RolePermission, ScopeType


@pytest.fixture
def currency(db):
    return Currency.objects.get(code="INR")


@pytest.fixture
def uom(db):
    return UnitOfMeasure.objects.create(code="NOS", name="Numbers")


@pytest.fixture
def admin(db):
    return User.objects.create_superuser(
        email="enquiry-admin@example.test",
        password="SafePassword-2741",
    )


@pytest.fixture
def customer(company, currency, admin):
    return Customer.objects.create(
        company=company,
        customer_code="CUST-ENQUIRY",
        legal_name="ABC Industries Pvt. Ltd.",
        default_currency=currency,
        status=Customer.Status.ACTIVE,
        created_by=admin,
        updated_by=admin,
    )


@pytest.fixture
def enquiry_sequence(company):
    return DocumentSequence.objects.create(
        company=company,
        code="ENQUIRY",
        financial_year=financial_year_label(company),
        template="ENQ-2026-{number}",
        padding=4,
    )


@pytest.fixture
def enquiry(company, customer, currency, employee, admin):
    return Enquiry.objects.create(
        company=company,
        enquiry_number="ENQ-EXISTING",
        customer=customer,
        subject="MCC Control Panel - Line 2",
        responsible_salesperson=employee,
        estimated_value=Decimal("825000.00"),
        currency=currency,
        created_by=admin,
        updated_by=admin,
    )


@pytest.mark.django_db
def test_enquiry_create_allocates_number_audits_and_notifies_owner(
    api_client,
    admin,
    employee,
    customer,
    enquiry_sequence,
    django_capture_on_commit_callbacks,
):
    api_client.force_authenticate(admin)
    with django_capture_on_commit_callbacks(execute=True):
        response = api_client.post(
            "/api/v1/enquiries/",
            {
                "customer": str(customer.pk),
                "subject": "VFD Control Panel - AHU",
                "responsible_salesperson": str(employee.pk),
                "estimated_value": "550000.00",
                "due_date": (timezone.localdate() + timedelta(days=7)).isoformat(),
                "priority": Enquiry.Priority.HIGH,
            },
            format="json",
        )

    assert response.status_code == 201, response.data
    assert response.data["enquiry_number"] == "ENQ-2026-0001"
    assert response.data["currency_code"] == "INR"
    assert response.data["status"] == Enquiry.Status.DRAFT
    assert Notification.objects.filter(
        recipient_user=employee.user,
        notification_type="ENQUIRY_ASSIGNED",
    ).exists()
    assert AuditEvent.objects.filter(
        entity_type="enquiry",
        entity_id=response.data["id"],
    ).exists()


@pytest.mark.django_db
def test_enquiry_requirements_and_items_are_structured_and_numbered(
    api_client, admin, enquiry, uom
):
    api_client.force_authenticate(admin)
    requirement = api_client.post(
        "/api/v1/enquiry-requirements/",
        {
            "enquiry": str(enquiry.pk),
            "requirement_type": EnquiryRequirement.RequirementType.TECHNICAL,
            "title": "Busbar rating",
            "description": "Copper busbar rated for 50 kA.",
            "is_mandatory": True,
            "customer_specification_reference": "RFQ section 4.2",
        },
        format="json",
    )
    assert requirement.status_code == 201, requirement.data

    first = api_client.post(
        "/api/v1/enquiry-items/",
        {
            "enquiry": str(enquiry.pk),
            "description": "MCC panel",
            "quantity": "1.0000",
            "uom": str(uom.pk),
        },
        format="json",
    )
    second = api_client.post(
        "/api/v1/enquiry-items/",
        {
            "enquiry": str(enquiry.pk),
            "description": "VFD feeder",
            "quantity": "2.0000",
            "uom": str(uom.pk),
        },
        format="json",
    )

    assert first.status_code == second.status_code == 201
    assert [first.data["line_number"], second.data["line_number"]] == [1, 2]
    assert EnquiryItem.objects.filter(enquiry=enquiry).count() == 2


@pytest.mark.django_db
def test_enquiry_lifecycle_uses_commands_and_rejects_invalid_transition(
    api_client, admin, enquiry
):
    api_client.force_authenticate(admin)

    direct_patch = api_client.patch(
        f"/api/v1/enquiries/{enquiry.pk}/",
        {"status": Enquiry.Status.WON},
        format="json",
    )
    assert direct_patch.status_code == 400

    received = api_client.post(f"/api/v1/enquiries/{enquiry.pk}/receive/", {}, format="json")
    assert received.status_code == 200
    assert received.data["status"] == Enquiry.Status.RECEIVED

    engineering = api_client.post(
        f"/api/v1/enquiries/{enquiry.pk}/send-to-engineering/",
        {},
        format="json",
    )
    assert engineering.status_code == 200
    assert engineering.data["status"] == Enquiry.Status.ENGINEERING_REVIEW

    repeated = api_client.post(f"/api/v1/enquiries/{enquiry.pk}/receive/", {}, format="json")
    assert repeated.status_code == 400

    estimation = api_client.post(
        f"/api/v1/enquiries/{enquiry.pk}/send-to-estimation/",
        {},
        format="json",
    )
    assert estimation.status_code == 400
    assert "engineering feasibility" in estimation.data["error"]["message"].lower()


@pytest.mark.django_db
def test_mark_lost_requires_and_persists_business_reason(api_client, admin, enquiry):
    enquiry.status = Enquiry.Status.RECEIVED
    enquiry.save(update_fields=["status", "updated_at"])
    api_client.force_authenticate(admin)

    missing = api_client.post(f"/api/v1/enquiries/{enquiry.pk}/mark-lost/", {}, format="json")
    assert missing.status_code == 400

    lost = api_client.post(
        f"/api/v1/enquiries/{enquiry.pk}/mark-lost/",
        {
            "reason": "Commercial terms not accepted.",
            "competitor": "Alternative Panels Ltd.",
            "customer_feedback": "Delivery lead time was too long.",
        },
        format="json",
    )
    assert lost.status_code == 200
    assert lost.data["status"] == Enquiry.Status.LOST
    assert lost.data["lost_reason"] == "Commercial terms not accepted."
    assert lost.data["closed_at"]


@pytest.mark.django_db
def test_company_scoped_creator_cannot_create_enquiry_for_other_company(
    api_client, user, employee, company, currency
):
    permission = Permission.objects.get(code="enquiry.enquiry.create")
    role = Role.objects.create(company=company, code="ENQ-CREATE", name="Enquiry creator")
    RolePermission.objects.create(role=role, permission=permission)
    RoleAssignment.objects.create(
        user=user,
        role=role,
        scope_type=ScopeType.COMPANY,
        company=company,
    )
    other_company = Company.objects.create(name="Other Company", code="OTHER-ENQ")
    other_customer = Customer.objects.create(
        company=other_company,
        customer_code="OTHER-CUST",
        legal_name="Other Customer",
        default_currency=currency,
        status=Customer.Status.ACTIVE,
        created_by=user,
        updated_by=user,
    )
    api_client.force_authenticate(user)

    response = api_client.post(
        "/api/v1/enquiries/",
        {
            "customer": str(other_customer.pk),
            "subject": "Unauthorized enquiry",
            "responsible_salesperson": str(employee.pk),
        },
        format="json",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_enquiry_is_registered_for_shared_documents():
    registration = registered_entity("enquiry", "documents")
    assert registration.key == "enquiry"


@pytest.mark.django_db
def test_enquiry_workspace_and_customer_360_use_real_enquiry_data(
    api_client, admin, employee, enquiry
):
    CrmActivity.objects.create(
        company=enquiry.company,
        customer=enquiry.customer,
        enquiry=enquiry,
        activity_type=CrmActivity.ActivityType.CALL,
        subject="Clarified panel incomer rating",
        status=CrmActivity.Status.COMPLETED,
        created_by=admin,
    )
    api_client.force_authenticate(admin)

    workspace = api_client.get(f"/api/v1/enquiries/{enquiry.pk}/workspace/")
    customer_360 = api_client.get(f"/api/v1/customers/{enquiry.customer_id}/360/")

    assert workspace.status_code == 200, workspace.data
    assert workspace.data["enquiry"]["enquiry_number"] == enquiry.enquiry_number
    assert workspace.data["activities"][0]["subject"] == "Clarified panel incomer rating"
    assert workspace.data["timeline"][0]["kind"] == "CRM_ACTIVITY"
    assert customer_360.status_code == 200, customer_360.data
    assert customer_360.data["overview"]["open_enquiries"] == 1
    assert customer_360.data["recent_enquiries"][0]["id"] == str(enquiry.pk)
