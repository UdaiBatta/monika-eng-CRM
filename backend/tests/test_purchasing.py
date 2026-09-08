from datetime import date
from decimal import Decimal

import pytest
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.approvals.models import ApprovalStepDefinition
from apps.approvals.services import activate_workflow_version, approve_request, create_workflow
from apps.audit.models import AuditEvent
from apps.inventory.models import Product, ProductCategory, StockItem, StockLocation, Supplier
from apps.masters.models import Currency, UnitOfMeasure
from apps.numbering.models import DocumentSequence
from apps.numbering.services import financial_year_label
from apps.organization.models import Employee, Warehouse
from apps.purchasing.models import PurchaseOrder, PurchaseRequisition
from apps.purchasing.services import (
    cancel_purchase_order,
    confirm_goods_receipt,
    create_goods_receipt,
    create_purchase_order,
    create_purchase_requisition,
    record_purchase_order_payment,
    submit_purchase_order,
    submit_purchase_requisition,
)
from apps.rbac.models import Permission, Role, RoleAssignment, RolePermission, ScopeType


def _grant(user, company, codes):
    role = Role.objects.create(company=company, code=f"ROLE-{'-'.join(codes)}"[:40], name="Test role")
    for code in codes:
        permission, _ = Permission.objects.get_or_create(code=code, defaults={"name": code})
        RolePermission.objects.create(role=role, permission=permission)
    RoleAssignment.objects.create(user=user, role=role, scope_type=ScopeType.COMPANY, company=company)


@pytest.fixture
def admin(db):
    return User.objects.create_superuser(email="purchasing-admin@example.test", password="SafePassword-2741")


@pytest.fixture(autouse=True)
def sequences(company):
    financial_year = financial_year_label(company)
    for code, template in (
        ("PR", "PR-{number}"),
        ("PO", "PO-{number}"),
        ("GRN", "GRN-{number}"),
        ("STK", "STK-{number}"),
    ):
        DocumentSequence.objects.create(
            company=company, code=code, financial_year=financial_year, template=template, padding=5
        )


@pytest.fixture
def uom(db):
    return UnitOfMeasure.objects.create(code="NOS", name="Numbers")


@pytest.fixture
def warehouse(company, branch):
    return Warehouse.objects.create(company=company, branch=branch, name="Main Store", code="MAIN")


@pytest.fixture
def supplier(company):
    return Supplier.objects.create(company=company, code="SUP1", name="ABB Distributor")


@pytest.fixture
def product(company, uom):
    category = ProductCategory.objects.create(company=company, code="VFD", name="VFDs")
    return Product.objects.create(
        company=company,
        category=category,
        unit_of_measure=uom,
        internal_code="PROD-001",
        description="ABB ACS550 5.5kW VFD",
    )


@pytest.fixture
def currency(db):
    currency, _ = Currency.objects.get_or_create(code="INR", defaults={"name": "Indian Rupee", "symbol": "₹"})
    return currency


@pytest.fixture
def po_header(warehouse, employee, supplier, currency):
    return {
        "supplier": supplier,
        "warehouse": warehouse,
        "responsible_employee": employee,
        "currency": currency,
    }


@pytest.mark.django_db
def test_requisition_create_and_auto_approve_without_workflow(company, warehouse, employee, product, admin):
    requisition = create_purchase_requisition(
        company=company,
        actor=admin,
        data={"warehouse": warehouse, "requested_by": employee, "justification": "Low stock"},
        lines=[{"product": product, "quantity": Decimal("10")}],
    )
    assert requisition.status == PurchaseRequisition.Status.DRAFT
    assert requisition.requisition_number.startswith("PR-")

    submitted = submit_purchase_requisition(requisition_id=requisition.pk, actor=admin)
    assert submitted.status == PurchaseRequisition.Status.APPROVED
    assert submitted.approved_by_id == admin.pk


@pytest.mark.django_db
def test_requisition_submit_requires_at_least_one_line(company, warehouse, employee, admin):
    with pytest.raises(ValidationError):
        create_purchase_requisition(
            company=company,
            actor=admin,
            data={"warehouse": warehouse, "requested_by": employee},
            lines=[],
        )


@pytest.mark.django_db(transaction=True)
def test_requisition_goes_through_approval_workflow(
    company, branch, department, warehouse, employee, product, admin
):
    approver_user = User.objects.create_user(email="pr-approver@example.test", password="SafePassword-2741")
    Employee.objects.create(
        user=approver_user,
        company=company,
        branch=branch,
        department=department,
        employee_code="ME-PR-APP-1",
        first_name="Approver",
        joining_date=date(2026, 1, 1),
        employment_type=Employee.EmploymentType.PERMANENT,
    )
    _grant(approver_user, company, ["approvals.request.approve"])
    workflow = create_workflow(
        company=company, code="PR-REVIEW", name="PR Review", entity_type="purchase_requisition", actor=admin
    )
    version = workflow.versions.get(version_number=1)
    step = ApprovalStepDefinition.objects.create(
        workflow_version=version,
        sequence=1,
        name="Purchase manager approval",
        approval_mode="SINGLE",
        resolver_type=ApprovalStepDefinition.ResolverType.SPECIFIC_USERS,
        minimum_approvals=1,
    )
    step.specific_users.set([approver_user])
    activate_workflow_version(version_id=version.pk, actor=admin)

    requisition = create_purchase_requisition(
        company=company,
        actor=admin,
        data={"warehouse": warehouse, "requested_by": employee},
        lines=[{"product": product, "quantity": Decimal("5")}],
    )
    submitted = submit_purchase_requisition(requisition_id=requisition.pk, actor=admin)
    assert submitted.status == PurchaseRequisition.Status.PENDING_APPROVAL
    assert submitted.approval_request_id is not None

    approve_request(request_id=submitted.approval_request_id, actor=approver_user)
    submitted.refresh_from_db()
    assert submitted.status == PurchaseRequisition.Status.APPROVED


@pytest.mark.django_db
def test_purchase_order_create_from_approved_requisition(company, po_header, employee, product, admin):
    requisition = create_purchase_requisition(
        company=company,
        actor=admin,
        data={"warehouse": po_header["warehouse"], "requested_by": employee},
        lines=[{"product": product, "quantity": Decimal("10")}],
    )
    submit_purchase_requisition(requisition_id=requisition.pk, actor=admin)
    requisition.refresh_from_db()
    assert requisition.status == PurchaseRequisition.Status.APPROVED

    line = {
        "product": product,
        "quantity": Decimal("10"),
        "unit_price": Decimal("5000"),
        "tax_percent": Decimal("18"),
    }
    order = create_purchase_order(
        company=company, actor=admin, data=po_header, lines=[line], requisition_id=requisition.pk
    )
    assert order.po_number.startswith("PO-")
    assert order.grand_total == Decimal("59000.00")
    requisition.refresh_from_db()
    assert requisition.status == PurchaseRequisition.Status.CONVERTED


@pytest.mark.django_db
def test_purchase_order_submit_without_workflow_moves_to_ordered(company, po_header, product, admin):
    order = create_purchase_order(
        company=company,
        actor=admin,
        data=po_header,
        lines=[{"product": product, "quantity": Decimal("10"), "unit_price": Decimal("5000")}],
    )
    submitted = submit_purchase_order(order_id=order.pk, actor=admin)
    assert submitted.status == PurchaseOrder.Status.ORDERED


@pytest.mark.django_db
def test_purchase_order_cannot_cancel_once_fully_received(company, po_header, employee, product, admin):
    order = create_purchase_order(
        company=company,
        actor=admin,
        data=po_header,
        lines=[{"product": product, "quantity": Decimal("5"), "unit_price": Decimal("1000")}],
    )
    submit_purchase_order(order_id=order.pk, actor=admin)
    order.refresh_from_db()
    line = order.lines.get()

    receipt = create_goods_receipt(
        company=company,
        actor=admin,
        purchase_order_id=order.pk,
        data={"received_by": employee},
        lines=[{"order_line": line.pk, "quantity_received": Decimal("5")}],
    )
    confirm_goods_receipt(receipt_id=receipt.pk, actor=admin)
    order.refresh_from_db()
    assert order.status == PurchaseOrder.Status.FULLY_RECEIVED

    with pytest.raises(ValidationError):
        cancel_purchase_order(order_id=order.pk, actor=admin, reason="Changed my mind")


@pytest.mark.django_db
def test_goods_receipt_confirmation_updates_stock_and_po_status(
    company, po_header, employee, product, admin
):
    order = create_purchase_order(
        company=company,
        actor=admin,
        data=po_header,
        lines=[{"product": product, "quantity": Decimal("10"), "unit_price": Decimal("1000")}],
    )
    submit_purchase_order(order_id=order.pk, actor=admin)
    line = order.lines.get()

    partial_receipt = create_goods_receipt(
        company=company,
        actor=admin,
        purchase_order_id=order.pk,
        data={"received_by": employee},
        lines=[{"order_line": line.pk, "quantity_received": Decimal("4")}],
    )
    confirm_goods_receipt(receipt_id=partial_receipt.pk, actor=admin)
    order.refresh_from_db()
    assert order.status == PurchaseOrder.Status.PART_RECEIVED

    location = StockLocation.objects.get(warehouse=po_header["warehouse"], bin_code="")
    balance = StockItem.objects.get(product=product, location=location, condition="AVAILABLE")
    assert balance.quantity == Decimal("4")

    final_receipt = create_goods_receipt(
        company=company,
        actor=admin,
        purchase_order_id=order.pk,
        data={"received_by": employee},
        lines=[{"order_line": line.pk, "quantity_received": Decimal("6")}],
    )
    confirm_goods_receipt(receipt_id=final_receipt.pk, actor=admin)
    order.refresh_from_db()
    assert order.status == PurchaseOrder.Status.FULLY_RECEIVED
    balance.refresh_from_db()
    assert balance.quantity == Decimal("10")


@pytest.mark.django_db
def test_goods_receipt_rejects_over_receipt(company, po_header, employee, product, admin):
    order = create_purchase_order(
        company=company,
        actor=admin,
        data=po_header,
        lines=[{"product": product, "quantity": Decimal("5"), "unit_price": Decimal("1000")}],
    )
    submit_purchase_order(order_id=order.pk, actor=admin)
    line = order.lines.get()

    with pytest.raises(ValidationError):
        create_goods_receipt(
            company=company,
            actor=admin,
            purchase_order_id=order.pk,
            data={"received_by": employee},
            lines=[{"order_line": line.pk, "quantity_received": Decimal("999")}],
        )


@pytest.mark.django_db
def test_record_payment_updates_balance_due_and_status(company, po_header, product, admin):
    order = create_purchase_order(
        company=company,
        actor=admin,
        data=po_header,
        lines=[{"product": product, "quantity": Decimal("2"), "unit_price": Decimal("10000")}],
    )
    assert order.grand_total == Decimal("20000.00")
    updated = record_purchase_order_payment(
        order_id=order.pk,
        actor=admin,
        amount=Decimal("8000"),
        payment_status=PurchaseOrder.PaymentStatus.PART_PAID,
    )
    assert updated.paid_amount == Decimal("8000.00")
    assert updated.balance_due == Decimal("12000.00")
    assert updated.payment_status == PurchaseOrder.PaymentStatus.PART_PAID
    assert AuditEvent.objects.filter(
        entity_id=str(order.pk), event_type="purchase_order.payment_recorded"
    ).exists()


@pytest.mark.django_db
def test_sales_only_user_forbidden_from_purchasing_create(api_client, user, employee, company, warehouse):
    _grant(user, company, ["purchasing.requisition.view"])
    api_client.force_authenticate(user)
    response = api_client.post(
        "/api/v1/purchasing/requisitions/",
        {
            "company": str(company.pk),
            "warehouse": str(warehouse.pk),
            "requested_by": str(employee.pk),
            "lines": [],
        },
        format="json",
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_purchase_order_api_create_and_submit(
    api_client, user, company, warehouse, employee, supplier, currency, product
):
    _grant(
        user,
        company,
        [
            "purchasing.purchase_order.view",
            "purchasing.purchase_order.create",
            "purchasing.purchase_order.submit",
        ],
    )
    api_client.force_authenticate(user)
    create_response = api_client.post(
        "/api/v1/purchasing/orders/",
        {
            "supplier": str(supplier.pk),
            "warehouse": str(warehouse.pk),
            "responsible_employee": str(employee.pk),
            "currency": str(currency.pk),
            "lines": [
                {"product": str(product.pk), "quantity": "3", "unit_price": "2000", "tax_percent": "0"}
            ],
        },
        format="json",
    )
    assert create_response.status_code == 201
    order_id = create_response.data["id"]

    submit_response = api_client.post(f"/api/v1/purchasing/orders/{order_id}/submit/", {}, format="json")
    assert submit_response.status_code == 200
    assert submit_response.data["status"] == PurchaseOrder.Status.ORDERED
