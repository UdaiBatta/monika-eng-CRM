from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.crm.models import CrmActivity, Customer, CustomerContact, CustomerSite
from apps.crm.tasks import notify_due_follow_ups
from apps.masters.models import Currency
from apps.notifications.models import Notification
from apps.numbering.models import DocumentSequence
from apps.numbering.services import financial_year_label
from apps.organization.models import Company, Employee
from apps.rbac.models import Permission, Role, RoleAssignment, RolePermission, ScopeType


@pytest.fixture
def currency(db):
    return Currency.objects.get(code="INR")


@pytest.fixture
def customer_sequence(company):
    return DocumentSequence.objects.create(
        company=company,
        code="CUSTOMER",
        financial_year=financial_year_label(company),
        template="CUST-{number}",
        padding=5,
    )


@pytest.fixture
def admin(db):
    return User.objects.create_superuser(email="crm-admin@example.test", password="SafePassword-2741")


@pytest.fixture
def customer(company, currency, admin):
    return Customer.objects.create(
        company=company,
        customer_code="CUST-EXISTING",
        legal_name="ABC Industries Pvt. Ltd.",
        gstin="27AAECA1234F1Z5",
        primary_email="procurement@abc.example",
        primary_phone="+91 98765 43210",
        default_currency=currency,
        credit_limit=Decimal("2500000.00"),
        created_by=admin,
        updated_by=admin,
    )


@pytest.mark.django_db
def test_customer_api_allocates_number_and_records_audit(
    api_client, admin, company, currency, customer_sequence
):
    api_client.force_authenticate(admin)

    response = api_client.post(
        "/api/v1/customers/",
        {
            "company": str(company.pk),
            "legal_name": "Delta Control Systems Pvt. Ltd.",
            "default_currency": str(currency.pk),
            "primary_email": "purchase@delta.example",
        },
        format="json",
    )

    assert response.status_code == 201, response.data
    assert response.data["customer_code"] == "CUST-00001"
    assert response.data["status"] == Customer.Status.PROSPECT
    assert AuditEvent.objects.filter(
        entity_type="customer",
        entity_id=response.data["id"],
        action=AuditEvent.Action.CREATE,
    ).exists()


@pytest.mark.django_db
def test_customer_history_import_accepts_csv(
    api_client, admin, company, currency, customer_sequence
):
    api_client.force_authenticate(admin)
    upload = SimpleUploadedFile(
        "customers.csv",
        (
            "company_code,legal_name,trade_name,customer_type,primary_email,"
            "default_currency_code,source\n"
            f"{company.code},Delta Control Systems,Delta Controls,ORGANIZATION,"
            f"sales@delta.example,{currency.code},Existing spreadsheet\n"
        ).encode(),
        content_type="text/csv",
    )

    response = api_client.post(
        "/api/v1/customers/import-history/",
        {"file": upload},
        format="multipart",
    )

    assert response.status_code == 201, response.data
    assert response.data == {"imported": 1}
    imported = Customer.objects.get(legal_name="Delta Control Systems")
    assert imported.company == company
    assert imported.default_currency == currency
    assert imported.source == "Existing spreadsheet"


@pytest.mark.django_db
def test_customer_duplicate_warning_requires_explanation(
    api_client, admin, company, currency, customer_sequence, customer
):
    api_client.force_authenticate(admin)
    payload = {
        "company": str(company.pk),
        "legal_name": "ABC Industries Private Limited",
        "default_currency": str(currency.pk),
    }

    blocked = api_client.post("/api/v1/customers/", payload, format="json")
    assert blocked.status_code == 400, blocked.data
    assert blocked.data["error"]["details"]["possible_matches"]

    accepted = api_client.post(
        "/api/v1/customers/",
        {**payload, "duplicate_override_reason": "Confirmed separate legal entity."},
        format="json",
    )
    assert accepted.status_code == 201
    assert AuditEvent.objects.filter(event_type="crm.customer.duplicate_override").exists()


@pytest.mark.django_db
def test_only_one_active_primary_contact_is_allowed(customer):
    CustomerContact.objects.create(
        customer=customer,
        first_name="Vikram",
        email="vikram@abc.example",
        is_primary=True,
    )

    with pytest.raises(DjangoValidationError):
        CustomerContact.objects.create(
            customer=customer,
            first_name="Sneha",
            email="sneha@abc.example",
            is_primary=True,
        )


@pytest.mark.django_db
def test_site_contact_must_belong_to_same_customer(customer, company, currency, admin):
    other = Customer.objects.create(
        company=company,
        customer_code="CUST-00002",
        legal_name="Other Customer",
        default_currency=currency,
        created_by=admin,
        updated_by=admin,
    )
    contact = CustomerContact.objects.create(
        customer=other,
        first_name="Other",
        email="other@example.test",
    )

    with pytest.raises(DjangoValidationError):
        CustomerSite.objects.create(
            customer=customer,
            address_type=CustomerSite.AddressType.SITE,
            label="Pune Plant",
            address_line_1="Chakan MIDC",
            city="Pune",
            state="Maharashtra",
            postal_code="410501",
            contact=contact,
        )


@pytest.mark.django_db
def test_customer_rejects_cross_company_account_manager(customer, admin):
    other_company = Company.objects.create(name="Other Company", code="OTHER")
    other_employee = Employee.objects.create(
        user=User.objects.create_user(email="other@example.test"),
        company=other_company,
        employee_code="OTHER-001",
        first_name="Other",
        joining_date=date(2026, 1, 1),
        employment_type=Employee.EmploymentType.PERMANENT,
    )
    customer.account_manager = other_employee
    customer.updated_by = admin

    with pytest.raises(DjangoValidationError):
        customer.save()


@pytest.mark.django_db
def test_sensitive_customer_fields_require_separate_permission(
    api_client, user, employee, company, customer
):
    permission = Permission.objects.get(code="crm.customer.view")
    role = Role.objects.create(company=company, code="SALES", name="Sales")
    RolePermission.objects.create(role=role, permission=permission)
    RoleAssignment.objects.create(
        user=user,
        role=role,
        scope_type=ScopeType.COMPANY,
        company=company,
    )
    api_client.force_authenticate(user)

    response = api_client.get(f"/api/v1/customers/{customer.pk}/")

    assert response.status_code == 200
    assert "credit_limit" not in response.data
    assert "gstin" not in response.data


@pytest.mark.django_db
def test_customer_status_uses_explicit_command(api_client, admin, customer):
    api_client.force_authenticate(admin)

    missing_reason = api_client.post(f"/api/v1/customers/{customer.pk}/block/", {}, format="json")
    assert missing_reason.status_code == 400

    blocked = api_client.post(
        f"/api/v1/customers/{customer.pk}/block/",
        {"reason": "Credit hold requested by finance."},
        format="json",
    )
    assert blocked.status_code == 200
    assert blocked.data["status"] == Customer.Status.BLOCKED
    assert AuditEvent.objects.filter(
        entity_type="customer",
        entity_id=str(customer.pk),
        event_type="crm.customer.status_changed",
    ).exists()


@pytest.mark.django_db
def test_company_scoped_creator_cannot_create_cross_company_customer(
    api_client, user, employee, company, currency
):
    permission = Permission.objects.get(code="crm.customer.create")
    role = Role.objects.create(company=company, code="SALES-CREATE", name="Sales creator")
    RolePermission.objects.create(role=role, permission=permission)
    RoleAssignment.objects.create(
        user=user,
        role=role,
        scope_type=ScopeType.COMPANY,
        company=company,
    )
    other_company = Company.objects.create(name="Other Company", code="OTHER-CREATE")
    api_client.force_authenticate(user)

    response = api_client.post(
        "/api/v1/customers/",
        {
            "company": str(other_company.pk),
            "legal_name": "Unauthorized Customer",
            "default_currency": str(currency.pk),
        },
        format="json",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_follow_up_create_notifies_owner_and_complete_is_explicit(
    api_client,
    admin,
    employee,
    customer,
    django_capture_on_commit_callbacks,
):
    api_client.force_authenticate(admin)
    with django_capture_on_commit_callbacks(execute=True):
        created = api_client.post(
            "/api/v1/crm-activities/",
            {
                "customer": str(customer.pk),
                "activity_type": CrmActivity.ActivityType.FOLLOW_UP,
                "subject": "Confirm technical clarification",
                "next_follow_up_at": (timezone.now() + timedelta(days=1)).isoformat(),
                "follow_up_owner": str(employee.pk),
                "priority": CrmActivity.Priority.HIGH,
            },
            format="json",
        )

    assert created.status_code == 201, created.data
    assert created.data["status"] == CrmActivity.Status.OPEN
    assert Notification.objects.filter(
        recipient_user=employee.user,
        notification_type="FOLLOW_UP_ASSIGNED",
    ).exists()

    completed = api_client.post(
        f"/api/v1/crm-activities/{created.data['id']}/complete/",
        {},
        format="json",
    )
    assert completed.status_code == 200
    assert completed.data["status"] == CrmActivity.Status.COMPLETED
    assert completed.data["completed_at"]


@pytest.mark.django_db
def test_due_follow_up_reminder_is_deduplicated(employee, customer, admin):
    follow_up = CrmActivity.objects.create(
        company=customer.company,
        customer=customer,
        activity_type=CrmActivity.ActivityType.FOLLOW_UP,
        subject="Overdue quotation response",
        activity_date=timezone.now() - timedelta(days=2),
        next_follow_up_at=timezone.now() - timedelta(hours=3),
        follow_up_owner=employee,
        priority=CrmActivity.Priority.URGENT,
        status=CrmActivity.Status.OPEN,
        created_by=admin,
    )

    notify_due_follow_ups()
    notify_due_follow_ups()

    assert Notification.objects.filter(
        recipient_user=employee.user,
        entity_type="crm_activity",
        entity_id=str(follow_up.pk),
        notification_type="FOLLOW_UP_OVERDUE",
    ).count() == 1


@pytest.mark.django_db
def test_customer_360_returns_real_activity_and_follow_up_data(
    api_client, admin, employee, customer
):
    CrmActivity.objects.create(
        company=customer.company,
        customer=customer,
        activity_type=CrmActivity.ActivityType.FOLLOW_UP,
        subject="Review enquiry response",
        next_follow_up_at=timezone.now() + timedelta(hours=2),
        follow_up_owner=employee,
        status=CrmActivity.Status.OPEN,
        created_by=admin,
    )
    api_client.force_authenticate(admin)

    response = api_client.get(f"/api/v1/customers/{customer.pk}/360/")

    assert response.status_code == 200, response.data
    assert response.data["overview"]["open_follow_ups"] == 1
    assert response.data["open_follow_ups"][0]["subject"] == "Review enquiry response"
    assert response.data["timeline"][0]["kind"] == "CRM_ACTIVITY"


@pytest.mark.django_db
def test_customer_register_exposes_last_activity(api_client, admin, customer):
    occurred_at = timezone.now() - timedelta(hours=2)
    CrmActivity.objects.create(
        company=customer.company,
        customer=customer,
        activity_type=CrmActivity.ActivityType.CALL,
        subject="Reviewed new RFQ",
        activity_date=occurred_at,
        created_by=admin,
    )
    api_client.force_authenticate(admin)

    response = api_client.get("/api/v1/customers/")

    assert response.status_code == 200, response.data
    record = next(item for item in response.data["results"] if item["id"] == str(customer.pk))
    assert parse_datetime(record["last_activity_at"]) == occurred_at
