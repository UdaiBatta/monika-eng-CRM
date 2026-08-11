import base64
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.core.cache import cache
from django.db import close_old_connections, connections

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.crm.models import Customer, CustomerContact
from apps.external_enquiries.authentication import sign_payload
from apps.external_enquiries.models import (
    ExternalEnquiryAttachment,
    ExternalEnquirySubmission,
    IncomingEnquirySourceEvent,
    IntegrationCredential,
)
from apps.external_enquiries.services import convert_submission
from apps.masters.models import Currency
from apps.notifications.models import Notification
from apps.numbering.models import DocumentSequence
from apps.numbering.services import financial_year_label
from apps.organization.models import Company
from apps.rbac.models import Permission, Role, RoleAssignment, RolePermission, ScopeType

SECRET = "local-website-test-secret"
PATH = "/api/v1/integrations/website/enquiries/"


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()


@pytest.fixture
def admin(db):
    return User.objects.create_superuser(email="website-admin@example.test", password="SafePassword-2741")


@pytest.fixture
def currency(db):
    return Currency.objects.get_or_create(
        code="INR",
        defaults={"name": "Indian Rupee", "symbol": "₹", "decimal_places": 2},
    )[0]


@pytest.fixture
def credential(company, settings):
    settings.INTEGRATION_SECRETS = {"monika-website": SECRET}
    return IntegrationCredential.objects.create(
        company=company,
        name="Monika website",
        integration_type=IntegrationCredential.IntegrationType.WEBSITE,
        key_id="monika-website",
        secret_hash=IntegrationCredential.hash_secret(SECRET),
        allowed_source="www.monikaengineers.co.in",
    )


@pytest.fixture
def sequences(company):
    financial_year = financial_year_label(company)
    for code, template in (("CUSTOMER", "CUST-{number}"), ("ENQUIRY", "ENQ-2026-{number}")):
        DocumentSequence.objects.create(
            company=company,
            code=code,
            financial_year=financial_year,
            template=template,
            padding=4,
        )


def payload(**overrides):
    return {
        "submission_id": "web-1001",
        "source_type": "CONTACT_FORM",
        "name": "Asha Rao",
        "company": "ABC Industries Pvt. Ltd.",
        "email": "PURCHASE@ABC.EXAMPLE",
        "phone": "+91 90000 00000",
        "subject": "MCC panel requirement",
        "message": "Please contact us regarding a new MCC panel.",
        "page_url": "https://www.monikaengineers.co.in/contact-monika-engineers/",
        **overrides,
    }


def signed_post(api_client, data, *, timestamp=None, request_id=None, signature=None):
    body = json.dumps(data, separators=(",", ":")).encode()
    timestamp = str(timestamp or int(time.time()))
    request_id = request_id or str(uuid.uuid4())
    signature = signature or sign_payload(SECRET, timestamp, request_id, body)
    return api_client.generic(
        "POST",
        PATH,
        body,
        content_type="application/json",
        HTTP_X_INTEGRATION_KEY="monika-website",
        HTTP_X_INTEGRATION_SOURCE="www.monikaengineers.co.in",
        HTTP_X_TIMESTAMP=timestamp,
        HTTP_X_REQUEST_ID=request_id,
        HTTP_X_SIGNATURE=signature,
    )


@pytest.mark.django_db
def test_signed_intake_is_audited_and_idempotent(api_client, credential):
    data = payload()
    request_id = str(uuid.uuid4())
    first = signed_post(api_client, data, request_id=request_id)
    repeated = signed_post(api_client, data, request_id=request_id)

    assert first.status_code == 201, first.data
    assert repeated.status_code == 200, repeated.data
    assert ExternalEnquirySubmission.objects.count() == 1
    submission = ExternalEnquirySubmission.objects.get()
    assert submission.email == "purchase@abc.example"
    assert submission.normalized_phone == "9000000000"
    assert AuditEvent.objects.filter(
        entity_type="external_enquiry_submission",
        entity_id=str(submission.pk),
        event_type="external_enquiry.received",
    ).exists()
    assert submission.source_history.get().original_message == data["message"]


@pytest.mark.django_db
def test_manual_tradeindia_capture_preserves_source_and_supports_ownership(
    api_client, user, employee
):
    user.is_superuser = True
    user.is_staff = True
    user.save(update_fields=["is_superuser", "is_staff"])
    api_client.force_authenticate(user)

    created = api_client.post(
        "/api/v1/external-enquiries/manual-capture/",
        {
            "channel": "TRADEINDIA",
            "source_reference": "TI-RFQ-2026-104",
            "person_name": "Priya Shah",
            "company_name": "Shah Automation",
            "phone": "+91 98888 77665",
            "subject": "APFC panel requirement",
            "message": "Need an APFC panel quotation for our new plant.",
            "priority": "HIGH",
        },
        format="json",
    )

    assert created.status_code == 201, created.data
    submission = ExternalEnquirySubmission.objects.get(pk=created.data["id"])
    assert submission.channel == ExternalEnquirySubmission.Channel.TRADEINDIA
    assert submission.source_type == ExternalEnquirySubmission.SourceType.MARKETPLACE
    assert submission.assigned_to is None
    assert submission.source_history.get().source_reference == "TI-RFQ-2026-104"

    claimed = api_client.post(f"/api/v1/external-enquiries/{submission.pk}/take-ownership/")
    mine = api_client.get("/api/v1/external-enquiries/?queue=mine")
    unassigned = api_client.get("/api/v1/external-enquiries/?queue=unassigned")

    assert claimed.status_code == 200, claimed.data
    assert str(claimed.data["assigned_to"]) == str(employee.pk)
    assert mine.data["pagination"]["count"] == 1
    assert unassigned.data["pagination"]["count"] == 0
    assert IncomingEnquirySourceEvent.objects.filter(submission=submission).count() == 1


@pytest.mark.django_db
def test_intake_rejects_bad_signature_expired_timestamp_and_conflicting_retry(api_client, credential):
    bad = signed_post(api_client, payload(), signature="0" * 64)
    expired = signed_post(api_client, payload(), timestamp=int(time.time()) - 601)
    accepted = signed_post(api_client, payload())
    conflict = signed_post(api_client, payload(message="Different content"))

    assert bad.status_code == 403
    assert expired.status_code == 403
    assert accepted.status_code == 201
    assert conflict.status_code == 409
    assert ExternalEnquirySubmission.objects.count() == 1


@pytest.mark.django_db
def test_intake_rate_limit_is_enforced(api_client, credential, settings):
    settings.WEBSITE_INTAKE_RATE_LIMIT_PER_MINUTE = 1
    first = signed_post(api_client, payload(submission_id="rate-1"))
    second = signed_post(api_client, payload(submission_id="rate-2"))

    assert first.status_code == 201
    assert second.status_code == 429


@pytest.mark.django_db
def test_public_attachment_is_validated_and_quarantined(api_client, credential, settings, tmp_path):
    settings.LOCAL_PRIVATE_STORAGE_ROOT = tmp_path
    document = base64.b64encode(b"%PDF-1.4\nwebsite rfq").decode()
    accepted = signed_post(
        api_client,
        payload(
            submission_id="attachment-1",
            attachments=[{"filename": "customer-rfq.pdf", "content_base64": document}],
        ),
    )
    rejected = signed_post(
        api_client,
        payload(
            submission_id="attachment-2",
            attachments=[{"filename": "unsafe.exe", "content_base64": document}],
        ),
    )

    assert accepted.status_code == 201, accepted.data
    assert rejected.status_code == 400
    attachment = ExternalEnquiryAttachment.objects.get()
    assert attachment.scan_status == ExternalEnquiryAttachment.ScanStatus.NOT_SCANNED
    assert attachment.validation_status == ExternalEnquiryAttachment.ValidationStatus.ACCEPTED


@pytest.mark.django_db
def test_duplicate_candidates_explain_customer_and_contact_matches(api_client, credential, admin, currency):
    customer = Customer.objects.create(
        company=credential.company,
        customer_code="CUST-ABC",
        legal_name="ABC Industries Private Limited",
        primary_email="purchase@abc.example",
        default_currency=currency,
        status=Customer.Status.ACTIVE,
        created_by=admin,
        updated_by=admin,
    )
    CustomerContact.objects.create(
        customer=customer,
        first_name="Asha",
        last_name="Rao",
        email="purchase@abc.example",
        phone="9000000000",
    )
    response = signed_post(api_client, payload())
    submission = ExternalEnquirySubmission.objects.get()
    api_client.force_authenticate(admin)
    matches = api_client.get(f"/api/v1/external-enquiries/{submission.pk}/candidates/")

    assert response.status_code == 201
    assert submission.review_status == ExternalEnquirySubmission.ReviewStatus.POSSIBLE_DUPLICATE
    assert matches.status_code == 200
    assert matches.data["customers"][0]["id"] == str(customer.pk)
    assert "Email matches" in matches.data["customers"][0]["reasons"]
    assert matches.data["contacts"][0]["reasons"] == ["Email matches", "Phone matches"]


@pytest.mark.django_db
def test_duplicate_candidates_include_phone_match_when_email_differs(
    api_client, credential, admin, currency
):
    customer = Customer.objects.create(
        company=credential.company,
        customer_code="CUST-PHONE",
        legal_name="Phone Match Industries",
        default_currency=currency,
        status=Customer.Status.ACTIVE,
        created_by=admin,
        updated_by=admin,
    )
    contact = CustomerContact.objects.create(
        customer=customer,
        first_name="Asha",
        email="old-address@example.test",
        phone="9000000000",
    )
    signed_post(api_client, payload(company="Unrelated company", email="new-address@example.test"))
    submission = ExternalEnquirySubmission.objects.get()
    api_client.force_authenticate(admin)

    matches = api_client.get(f"/api/v1/external-enquiries/{submission.pk}/candidates/")

    assert matches.status_code == 200
    assert matches.data["contacts"] == [
        {
            "id": str(contact.pk),
            "display_name": contact.display_name,
            "customer_id": str(customer.pk),
            "customer_code": customer.customer_code,
            "customer_name": customer.legal_name,
            "reasons": ["Phone matches"],
        }
    ]


def create_submission(credential, **overrides):
    values = {
        "company": credential.company,
        "credential": credential,
        "channel": ExternalEnquirySubmission.Channel.WEBSITE,
        "source_type": ExternalEnquirySubmission.SourceType.CONTACT_FORM,
        "external_submission_id": f"web-{uuid.uuid4()}",
        "idempotency_key": str(uuid.uuid4()),
        "request_id": str(uuid.uuid4()),
        "payload_checksum": "a" * 64,
        "person_name": "Asha Rao",
        "company_name": "ABC Industries Pvt. Ltd.",
        "email": "purchase@abc.example",
        "normalized_phone": "9000000000",
        "subject": "PLC panel enquiry",
        "message": "Please quote a PLC control panel.",
    }
    values.update(overrides)
    return ExternalEnquirySubmission.objects.create(**values)


@pytest.mark.django_db(transaction=True)
def test_conversion_uses_existing_customer_contact_and_enquiry_numbering(
    api_client,
    credential,
    admin,
    currency,
    employee,
    sequences,
    django_capture_on_commit_callbacks,
):
    customer = Customer.objects.create(
        company=credential.company,
        customer_code="CUST-EXISTING",
        legal_name="ABC Industries Pvt. Ltd.",
        default_currency=currency,
        status=Customer.Status.ACTIVE,
        created_by=admin,
        updated_by=admin,
    )
    contact = CustomerContact.objects.create(
        customer=customer,
        first_name="Asha",
        last_name="Rao",
        email="purchase@abc.example",
    )
    submission = create_submission(credential)
    api_client.force_authenticate(admin)
    with django_capture_on_commit_callbacks(execute=True):
        response = api_client.post(
            f"/api/v1/external-enquiries/{submission.pk}/convert/",
            {
                "customer_id": str(customer.pk),
                "contact_id": str(contact.pk),
                "responsible_salesperson_id": str(employee.pk),
                "priority": "HIGH",
            },
            format="json",
        )

    assert response.status_code == 200, response.data
    submission.refresh_from_db()
    assert submission.converted_enquiry.enquiry_number == "ENQ-2026-0001"
    assert submission.converted_enquiry.source == "Website"
    assert submission.converted_enquiry.customer == customer
    assert Notification.objects.filter(
        recipient_user=employee.user, notification_type="ENQUIRY_ASSIGNED"
    ).exists()
    repeated = api_client.post(
        f"/api/v1/external-enquiries/{submission.pk}/convert/",
        {
            "customer_id": str(customer.pk),
            "contact_id": str(contact.pk),
            "responsible_salesperson_id": str(employee.pk),
        },
        format="json",
    )
    assert repeated.status_code == 400
    assert customer.enquiries.count() == 1


@pytest.mark.django_db
def test_conversion_can_create_reviewed_customer_and_contact(
    api_client, credential, admin, currency, employee, sequences
):
    submission = create_submission(
        credential,
        company_name="New Controls Pvt. Ltd.",
        email="buyer@newcontrols.example",
    )
    api_client.force_authenticate(admin)
    response = api_client.post(
        f"/api/v1/external-enquiries/{submission.pk}/convert/",
        {
            "new_customer": {
                "legal_name": "New Controls Pvt. Ltd.",
                "primary_email": "buyer@newcontrols.example",
                "default_currency": str(currency.pk),
            },
            "new_contact": {
                "first_name": "New",
                "last_name": "Buyer",
                "email": "buyer@newcontrols.example",
                "is_primary": True,
            },
            "responsible_salesperson_id": str(employee.pk),
        },
        format="json",
    )

    assert response.status_code == 200, response.data
    submission.refresh_from_db()
    assert submission.converted_customer.customer_code == "CUST-0001"
    assert submission.converted_contact.customer == submission.converted_customer
    assert submission.converted_enquiry.customer == submission.converted_customer


@pytest.mark.django_db(transaction=True)
def test_concurrent_conversion_creates_exactly_one_enquiry(
    credential, admin, currency, employee, sequences
):
    customer = Customer.objects.create(
        company=credential.company,
        customer_code="CUST-CONCURRENT",
        legal_name="Concurrent Controls Pvt. Ltd.",
        default_currency=currency,
        status=Customer.Status.ACTIVE,
        created_by=admin,
        updated_by=admin,
    )
    contact = CustomerContact.objects.create(
        customer=customer,
        first_name="Asha",
        email="concurrent@example.test",
    )
    submission = create_submission(credential, email="concurrent@example.test")
    barrier = Barrier(2)

    def attempt_conversion():
        close_old_connections()
        try:
            actor = User.objects.get(pk=admin.pk)
            barrier.wait(timeout=5)
            converted = convert_submission(
                submission_id=submission.pk,
                actor=actor,
                data={
                    "customer_id": customer.pk,
                    "contact_id": contact.pk,
                    "responsible_salesperson_id": employee.pk,
                    "priority": "NORMAL",
                },
            )
            return "converted", str(converted.converted_enquiry_id)
        except Exception as exc:  # The losing transaction must fail cleanly.
            return "blocked", type(exc).__name__
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _index: attempt_conversion(), range(2)))

    submission.refresh_from_db()
    assert [result[0] for result in results].count("converted") == 1
    assert [result[0] for result in results].count("blocked") == 1
    assert customer.enquiries.count() == 1
    assert submission.review_status == ExternalEnquirySubmission.ReviewStatus.CONVERTED


@pytest.mark.django_db
def test_rejected_submission_requires_restore_before_conversion(
    api_client, credential, admin, currency, employee, sequences
):
    submission = create_submission(credential)
    customer = Customer.objects.create(
        company=credential.company,
        customer_code="CUST-RESTORE",
        legal_name="Restore Test",
        default_currency=currency,
        status=Customer.Status.ACTIVE,
        created_by=admin,
        updated_by=admin,
    )
    contact = CustomerContact.objects.create(customer=customer, first_name="Asha", email="asha@test.example")
    api_client.force_authenticate(admin)
    rejected = api_client.post(
        f"/api/v1/external-enquiries/{submission.pk}/reject/",
        {"reason": "Insufficient details"},
        format="json",
    )
    conversion = api_client.post(
        f"/api/v1/external-enquiries/{submission.pk}/convert/",
        {
            "customer_id": str(customer.pk),
            "contact_id": str(contact.pk),
            "responsible_salesperson_id": str(employee.pk),
        },
        format="json",
    )

    assert rejected.status_code == 200
    assert conversion.status_code == 400


@pytest.mark.django_db
def test_external_enquiry_list_is_company_scoped(api_client, user, employee, company):
    permission = Permission.objects.get(code="crm.external_enquiry.view")
    role = Role.objects.create(company=company, code="WEB-VIEW", name="Website enquiry viewer")
    RolePermission.objects.create(role=role, permission=permission)
    RoleAssignment.objects.create(
        user=user,
        role=role,
        scope_type=ScopeType.COMPANY,
        company=company,
    )
    own_credential = IntegrationCredential.objects.create(
        company=company,
        name="Own",
        integration_type="WEBSITE",
        key_id="own-site",
        secret_hash="a" * 64,
    )
    create_submission(own_credential)
    other_company = Company.objects.create(name="Other company", code="OTHER-WEB")
    other_credential = IntegrationCredential.objects.create(
        company=other_company,
        name="Other",
        integration_type="WEBSITE",
        key_id="other-site",
        secret_hash="b" * 64,
    )
    create_submission(other_credential, email="other@example.test")
    api_client.force_authenticate(user)

    response = api_client.get("/api/v1/external-enquiries/")

    assert response.status_code == 200
    results = response.data["results"] if isinstance(response.data, dict) else response.data
    assert len(results) == 1
    assert results[0]["company"] == company.pk
