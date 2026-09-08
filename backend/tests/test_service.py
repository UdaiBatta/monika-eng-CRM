from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.crm.models import Customer
from apps.inventory.models import Product, ProductCategory, StockItem, StockLocation, StockMovement, Supplier
from apps.inventory.services import record_movement
from apps.masters.models import Currency, UnitOfMeasure
from apps.numbering.models import DocumentSequence
from apps.numbering.services import financial_year_label
from apps.organization.models import Warehouse
from apps.rbac.models import Permission, Role, RoleAssignment, RolePermission, ScopeType
from apps.service.models import Equipment, ServiceJobLine, ServiceTicket
from apps.service.services import (
    add_job_line,
    assign_technician,
    change_status,
    close_ticket,
    consume_part,
    create_service_ticket,
    dispatch_ticket,
    link_quotation,
    record_diagnosis,
)


def _grant(user, company, codes):
    role = Role.objects.create(company=company, code=f"ROLE-{'-'.join(codes)}"[:40], name="Test role")
    for code in codes:
        permission, _ = Permission.objects.get_or_create(code=code, defaults={"name": code})
        RolePermission.objects.create(role=role, permission=permission)
    RoleAssignment.objects.create(user=user, role=role, scope_type=ScopeType.COMPANY, company=company)


@pytest.fixture
def admin(db):
    return User.objects.create_superuser(email="service-admin@example.test", password="SafePassword-2741")


@pytest.fixture(autouse=True)
def sequences(company):
    financial_year = financial_year_label(company)
    for code, template in (("SVC", "SVC-{number}"), ("STK", "STK-{number}")):
        DocumentSequence.objects.create(
            company=company, code=code, financial_year=financial_year, template=template, padding=5
        )


@pytest.fixture
def currency(company):
    return Currency.objects.get(code="INR")


@pytest.fixture
def customer(company, currency, admin):
    return Customer.objects.create(
        company=company,
        customer_code="CUST-SVC-001",
        legal_name="Service Test Industries",
        default_currency=currency,
        created_by=admin,
        updated_by=admin,
    )


@pytest.fixture
def uom(db):
    return UnitOfMeasure.objects.create(code="NOS", name="Numbers")


@pytest.fixture
def warehouse(company, branch):
    return Warehouse.objects.create(company=company, branch=branch, name="Service Store", code="SVCST")


@pytest.fixture
def location(warehouse):
    return StockLocation.objects.create(warehouse=warehouse, bin_code="")


@pytest.fixture
def product(company, uom):
    category = ProductCategory.objects.create(company=company, code="SPARE", name="Spares")
    supplier = Supplier.objects.create(company=company, code="SUPSVC", name="Spares Distributor")
    return Product.objects.create(
        company=company,
        category=category,
        default_supplier=supplier,
        unit_of_measure=uom,
        internal_code="SPARE-001",
        description="VFD Cooling Fan",
    )


@pytest.fixture
def equipment(company, customer):
    return Equipment.objects.create(
        company=company,
        customer=customer,
        equipment_name="ABB ACS550 VFD",
        serial_number="SN-12345",
    )


@pytest.mark.django_db
def test_create_service_ticket(company, customer, equipment, admin):
    ticket = create_service_ticket(
        company=company,
        actor=admin,
        data={
            "customer": customer,
            "equipment": equipment,
            "source": ServiceTicket.Source.CALL,
            "complaint": "VFD fan not spinning",
            "priority": ServiceTicket.Priority.HIGH,
        },
    )
    assert ticket.ticket_number.startswith("SVC-")
    assert ticket.status == ServiceTicket.Status.NEW
    assert ticket.stage_events.count() == 1


@pytest.mark.django_db
def test_assign_technician_moves_to_assigned(company, customer, employee, admin):
    ticket = create_service_ticket(
        company=company,
        actor=admin,
        data={
            "customer": customer,
            "complaint": "No display on HMI",
            "priority": ServiceTicket.Priority.NORMAL,
        },
    )
    updated = assign_technician(ticket_id=ticket.pk, actor=admin, technician_id=employee.pk)
    assert updated.status == ServiceTicket.Status.ASSIGNED
    assert updated.technician_id == employee.pk


@pytest.mark.django_db
def test_invalid_status_transition_rejected(company, customer, admin):
    ticket = create_service_ticket(
        company=company,
        actor=admin,
        data={"customer": customer, "complaint": "Overheating", "priority": ServiceTicket.Priority.NORMAL},
    )
    with pytest.raises(ValidationError):
        change_status(ticket_id=ticket.pk, actor=admin, to_status=ServiceTicket.Status.READY_FOR_DISPATCH)


@pytest.mark.django_db
def test_diagnosis_and_parts_labour_and_consumption(
    company, customer, employee, product, location, admin
):
    record_movement(
        company=company,
        movement_type=StockMovement.MovementType.INWARD,
        product=product,
        quantity=Decimal("5"),
        to_location=location,
        to_condition=StockItem.Condition.AVAILABLE,
        actor=admin,
    )
    ticket = create_service_ticket(
        company=company,
        actor=admin,
        data={"customer": customer, "complaint": "Fan noise", "priority": ServiceTicket.Priority.NORMAL},
    )
    assign_technician(ticket_id=ticket.pk, actor=admin, technician_id=employee.pk)
    record_diagnosis(ticket_id=ticket.pk, actor=admin, diagnosis="Cooling fan bearing worn out")

    part_line = add_job_line(
        ticket_id=ticket.pk,
        actor=admin,
        line_type=ServiceJobLine.LineType.PART,
        description="Replacement cooling fan",
        quantity=Decimal("1"),
        unit_price=Decimal("1500"),
        product=product,
    )
    labour_line = add_job_line(
        ticket_id=ticket.pk,
        actor=admin,
        line_type=ServiceJobLine.LineType.LABOUR,
        description="Technician labour",
        quantity=Decimal("2"),
        unit_price=Decimal("500"),
    )
    assert part_line.total_amount == Decimal("1500.00")
    assert labour_line.total_amount == Decimal("1000.00")

    change_status(ticket_id=ticket.pk, actor=admin, to_status=ServiceTicket.Status.UNDER_REPAIR)
    consumed = consume_part(ticket_id=ticket.pk, actor=admin, job_line_id=part_line.pk, location=location)
    assert consumed.consumed_quantity == Decimal("1")

    balance = StockItem.objects.get(product=product, location=location, condition="AVAILABLE")
    assert balance.quantity == Decimal("4")


@pytest.mark.django_db
def test_consume_part_without_stock_fails(company, customer, employee, product, location, admin):
    ticket = create_service_ticket(
        company=company,
        actor=admin,
        data={"customer": customer, "complaint": "Fan noise", "priority": ServiceTicket.Priority.NORMAL},
    )
    assign_technician(ticket_id=ticket.pk, actor=admin, technician_id=employee.pk)
    change_status(ticket_id=ticket.pk, actor=admin, to_status=ServiceTicket.Status.UNDER_REPAIR)
    part_line = add_job_line(
        ticket_id=ticket.pk,
        actor=admin,
        line_type=ServiceJobLine.LineType.PART,
        description="Replacement cooling fan",
        quantity=Decimal("1"),
        unit_price=Decimal("1500"),
        product=product,
    )
    with pytest.raises(DjangoValidationError):
        consume_part(ticket_id=ticket.pk, actor=admin, job_line_id=part_line.pk, location=location)


@pytest.mark.django_db
def test_full_ticket_lifecycle_to_dispatch_and_close(company, customer, employee, admin):
    ticket = create_service_ticket(
        company=company,
        actor=admin,
        data={
            "customer": customer,
            "complaint": "Servo motor fault",
            "priority": ServiceTicket.Priority.URGENT,
        },
    )
    assign_technician(ticket_id=ticket.pk, actor=admin, technician_id=employee.pk)
    change_status(ticket_id=ticket.pk, actor=admin, to_status=ServiceTicket.Status.UNDER_REPAIR)
    change_status(ticket_id=ticket.pk, actor=admin, to_status=ServiceTicket.Status.READY_FOR_DISPATCH)
    dispatched = dispatch_ticket(
        ticket_id=ticket.pk, actor=admin, dispatch_reference="COURIER-9981", warranty_claim=True
    )
    assert dispatched.dispatched_at is not None
    assert dispatched.warranty_claim is True

    closed = close_ticket(ticket_id=ticket.pk, actor=admin, notes="Customer confirmed working")
    assert closed.status == ServiceTicket.Status.CLOSED
    assert closed.closed_at is not None
    assert closed.stage_events.count() >= 4


@pytest.mark.django_db
def test_link_quotation_moves_to_awaiting_customer_approval(
    company, customer, employee, currency, admin
):
    from apps.quotations.models import Quotation, QuotationRevision

    ticket = create_service_ticket(
        company=company,
        actor=admin,
        data={
            "customer": customer,
            "complaint": "PLC module failure",
            "priority": ServiceTicket.Priority.HIGH,
        },
    )
    assign_technician(ticket_id=ticket.pk, actor=admin, technician_id=employee.pk)
    change_status(ticket_id=ticket.pk, actor=admin, to_status=ServiceTicket.Status.UNDER_REPAIR)

    quotation = Quotation.objects.create(
        company=company,
        quotation_number="QUO-SVC-0001",
        customer=customer,
        path=Quotation.Path.QUICK,
        quick_reason="Service repair quotation",
        owner=employee,
        created_by=admin,
    )
    revision = QuotationRevision.objects.create(quotation=quotation, revision_number=1, currency=currency)
    quotation.current_revision = revision
    quotation.save(update_fields=["current_revision"])

    updated = link_quotation(ticket_id=ticket.pk, actor=admin, quotation_id=quotation.pk)
    assert updated.status == ServiceTicket.Status.AWAITING_CUSTOMER_APPROVAL
    assert updated.quotation_id == quotation.pk


@pytest.mark.django_db
def test_user_without_service_permission_forbidden_from_ticket_view(api_client, user, employee, company):
    _grant(user, company, ["purchasing.requisition.view"])
    api_client.force_authenticate(user)
    response = api_client.get("/api/v1/service/tickets/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_service_ticket_api_create_and_assign(api_client, user, employee, company, customer):
    _grant(
        user,
        company,
        ["service.ticket.view", "service.ticket.create", "service.ticket.assign"],
    )
    api_client.force_authenticate(user)
    create_response = api_client.post(
        "/api/v1/service/tickets/",
        {
            "customer": str(customer.pk),
            "complaint": "Sensor giving false readings",
            "priority": "NORMAL",
            "source": "CALL",
        },
        format="json",
    )
    assert create_response.status_code == 201
    ticket_id = create_response.data["id"]

    assign_response = api_client.post(
        f"/api/v1/service/tickets/{ticket_id}/assign/",
        {"technician_id": str(employee.pk)},
        format="json",
    )
    assert assign_response.status_code == 200
    assert assign_response.data["status"] == ServiceTicket.Status.ASSIGNED
