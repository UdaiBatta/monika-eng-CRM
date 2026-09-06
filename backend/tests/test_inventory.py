from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.crm.models import Customer
from apps.inventory.models import (
    Product,
    ProductCategory,
    StockItem,
    StockLocation,
    StockMovement,
    Supplier,
)
from apps.inventory.services import record_movement
from apps.masters.models import Currency, UnitOfMeasure
from apps.numbering.models import DocumentSequence
from apps.numbering.services import financial_year_label
from apps.organization.models import Warehouse
from apps.rbac.models import Permission, Role, RoleAssignment, RolePermission, ScopeType
from apps.sales.models import SalesOrder, SalesOrderLine, SalesOrderRevision


def _csv_upload(name, contents):
    return SimpleUploadedFile(name, contents.encode(), content_type="text/csv")


@pytest.fixture
def admin(db):
    return User.objects.create_superuser(email="inventory-admin@example.test", password="SafePassword-2741")


@pytest.fixture(autouse=True)
def stk_sequence(company):
    return DocumentSequence.objects.create(
        company=company,
        code="STK",
        financial_year=financial_year_label(company),
        template="STK-{number}",
        padding=5,
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
def category(company):
    return ProductCategory.objects.create(company=company, code="VFD", name="Variable Frequency Drives")


@pytest.fixture
def supplier(company):
    return Supplier.objects.create(company=company, code="SUP1", name="ABB Distributor")


@pytest.fixture
def product(company, category, supplier, uom):
    return Product.objects.create(
        company=company,
        category=category,
        default_supplier=supplier,
        unit_of_measure=uom,
        internal_code="PROD-001",
        brand="ABB",
        part_number="ACS550-01",
        description="ABB ACS550 5.5kW VFD",
        reorder_level=Decimal("5"),
        reorder_quantity=Decimal("10"),
    )


def _grant(user, company, codes):
    role = Role.objects.create(company=company, code=f"ROLE-{'-'.join(codes)}"[:40], name="Test role")
    for code in codes:
        permission = Permission.objects.get(code=code)
        RolePermission.objects.create(role=role, permission=permission)
    RoleAssignment.objects.create(user=user, role=role, scope_type=ScopeType.COMPANY, company=company)


@pytest.mark.django_db
def test_inward_movement_increases_available_balance(company, product, location, admin):
    movement = record_movement(
        company=company,
        movement_type=StockMovement.MovementType.INWARD,
        product=product,
        quantity=Decimal("20"),
        to_location=location,
        to_condition=StockItem.Condition.AVAILABLE,
        actor=admin,
    )
    item = StockItem.objects.get(product=product, location=location, condition=StockItem.Condition.AVAILABLE)
    assert item.quantity == Decimal("20")
    assert movement.movement_number
    assert AuditEvent.objects.filter(entity_id=str(movement.pk)).exists()


@pytest.mark.django_db
def test_outward_movement_cannot_go_negative(company, product, location, admin):
    with pytest.raises(DjangoValidationError):
        record_movement(
            company=company,
            movement_type=StockMovement.MovementType.OUTWARD,
            product=product,
            quantity=Decimal("5"),
            from_location=location,
            from_condition=StockItem.Condition.AVAILABLE,
            actor=admin,
        )


@pytest.mark.django_db
def test_reserve_then_second_reserve_of_same_stock_fails(company, product, location, admin):
    record_movement(
        company=company,
        movement_type=StockMovement.MovementType.INWARD,
        product=product,
        quantity=Decimal("10"),
        to_location=location,
        to_condition=StockItem.Condition.AVAILABLE,
        actor=admin,
    )
    record_movement(
        company=company,
        movement_type=StockMovement.MovementType.RESERVE,
        product=product,
        quantity=Decimal("10"),
        from_location=location,
        from_condition=StockItem.Condition.AVAILABLE,
        to_location=location,
        to_condition=StockItem.Condition.RESERVED,
        reference_type="test",
        actor=admin,
    )
    available = StockItem.objects.get(
        product=product, location=location, condition=StockItem.Condition.AVAILABLE
    )
    reserved = StockItem.objects.get(
        product=product, location=location, condition=StockItem.Condition.RESERVED
    )
    assert available.quantity == Decimal("0")
    assert reserved.quantity == Decimal("10")

    with pytest.raises(DjangoValidationError):
        record_movement(
            company=company,
            movement_type=StockMovement.MovementType.RESERVE,
            product=product,
            quantity=Decimal("10"),
            from_location=location,
            from_condition=StockItem.Condition.AVAILABLE,
            to_location=location,
            to_condition=StockItem.Condition.RESERVED,
            reference_type="test",
            actor=admin,
        )


@pytest.mark.django_db
def test_transfer_moves_quantity_between_locations_preserving_total(company, product, warehouse, admin):
    location_a = StockLocation.objects.create(warehouse=warehouse, bin_code="A1")
    location_b = StockLocation.objects.create(warehouse=warehouse, bin_code="B1")
    record_movement(
        company=company,
        movement_type=StockMovement.MovementType.INWARD,
        product=product,
        quantity=Decimal("15"),
        to_location=location_a,
        to_condition=StockItem.Condition.AVAILABLE,
        actor=admin,
    )
    record_movement(
        company=company,
        movement_type=StockMovement.MovementType.TRANSFER,
        product=product,
        quantity=Decimal("6"),
        from_location=location_a,
        from_condition=StockItem.Condition.AVAILABLE,
        to_location=location_b,
        to_condition=StockItem.Condition.AVAILABLE,
        actor=admin,
    )
    qty_a = StockItem.objects.get(product=product, location=location_a).quantity
    qty_b = StockItem.objects.get(product=product, location=location_b).quantity
    assert qty_a == Decimal("9")
    assert qty_b == Decimal("6")
    assert qty_a + qty_b == Decimal("15")


@pytest.mark.django_db
def test_adjustment_requires_reason(company, product, location, admin):
    with pytest.raises(DjangoValidationError):
        record_movement(
            company=company,
            movement_type=StockMovement.MovementType.ADJUSTMENT,
            product=product,
            quantity=Decimal("1"),
            to_location=location,
            to_condition=StockItem.Condition.DAMAGED,
            reason="",
            actor=admin,
        )
    record_movement(
        company=company,
        movement_type=StockMovement.MovementType.ADJUSTMENT,
        product=product,
        quantity=Decimal("1"),
        to_location=location,
        to_condition=StockItem.Condition.DAMAGED,
        reason="Found damaged unit during cycle count",
        actor=admin,
    )
    damaged = StockItem.objects.get(product=product, location=location, condition="DAMAGED")
    assert damaged.quantity == Decimal("1")


@pytest.mark.django_db
def test_stock_items_list_endpoint_supports_ordering(api_client, company, product, location, admin):
    record_movement(
        company=company,
        movement_type=StockMovement.MovementType.INWARD,
        product=product,
        quantity=Decimal("5"),
        to_location=location,
        to_condition=StockItem.Condition.AVAILABLE,
        actor=admin,
    )
    api_client.force_authenticate(admin)
    response = api_client.get("/api/v1/inventory/stock-items/?page_size=200&ordering=product__description")
    assert response.status_code == 200
    assert response.data["results"][0]["product_code"] == "PROD-001"


@pytest.mark.django_db
def test_low_stock_endpoint_flags_products_under_reorder_level(api_client, company, product, location, admin):
    record_movement(
        company=company,
        movement_type=StockMovement.MovementType.INWARD,
        product=product,
        quantity=Decimal("2"),
        to_location=location,
        to_condition=StockItem.Condition.AVAILABLE,
        actor=admin,
    )
    api_client.force_authenticate(admin)
    response = api_client.get("/api/v1/inventory/products/low-stock/")
    assert response.status_code == 200
    codes = [row["internal_code"] for row in response.data]
    assert "PROD-001" in codes


@pytest.mark.django_db
def test_low_stock_endpoint_excludes_products_above_reorder_level(
    api_client, company, product, location, admin
):
    record_movement(
        company=company,
        movement_type=StockMovement.MovementType.INWARD,
        product=product,
        quantity=Decimal("50"),
        to_location=location,
        to_condition=StockItem.Condition.AVAILABLE,
        actor=admin,
    )
    api_client.force_authenticate(admin)
    response = api_client.get("/api/v1/inventory/products/low-stock/")
    assert response.status_code == 200
    codes = [row["internal_code"] for row in response.data]
    assert "PROD-001" not in codes


@pytest.mark.django_db
def test_sales_only_user_forbidden_from_inventory_manage_endpoints(api_client, user, employee, company):
    _grant(user, company, ["inventory.product.view"])
    api_client.force_authenticate(user)
    response = api_client.post(
        "/api/v1/inventory/products/",
        {
            "company": str(company.pk),
            "internal_code": "SHOULD-FAIL",
            "description": "Should be forbidden",
            "unit_of_measure": str(UnitOfMeasure.objects.create(code="EA", name="Each").pk),
        },
        format="json",
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_stock_manage_user_can_record_movement_via_api(
    api_client, user, employee, company, product, location
):
    _grant(user, company, ["inventory.stock.view", "inventory.stock.manage"])
    api_client.force_authenticate(user)
    response = api_client.post(
        "/api/v1/inventory/stock-movements/record/",
        {
            "movement_type": "INWARD",
            "product": str(product.pk),
            "quantity": "3.0000",
            "to_location": str(location.pk),
            "to_condition": "AVAILABLE",
        },
        format="json",
    )
    assert response.status_code == 201
    assert StockItem.objects.get(product=product, location=location).quantity == Decimal("3")


@pytest.mark.django_db
def test_product_and_supplier_csv_import_reports_row_errors(api_client, admin, company):
    api_client.force_authenticate(admin)
    response = api_client.post(
        "/api/v1/inventory/suppliers/import-history/",
        {"file": _csv_upload("suppliers.csv", "company_code,code,name\nBADCODE,SUP2,Bad Supplier\n")},
        format="multipart",
    )
    assert response.status_code == 400
    assert "rows" in response.data["error"]["details"]

    good_csv = f"company_code,code,name\n{company.code},SUP2,Good Supplier\n"
    good = api_client.post(
        "/api/v1/inventory/suppliers/import-history/",
        {"file": _csv_upload("suppliers.csv", good_csv)},
        format="multipart",
    )
    assert good.status_code == 201
    assert good.data["imported"] == 1
    assert Supplier.objects.filter(code="SUP2").exists()


@pytest.mark.django_db
def test_reserve_sales_order_line_blocks_double_promise(
    api_client, company, branch, employee, product, location, admin, uom
):
    currency, _ = Currency.objects.get_or_create(
        code="INR", defaults={"name": "Indian Rupee", "symbol": "₹"}
    )
    customer = Customer.objects.create(
        company=company,
        customer_code="CUST-INV-TEST",
        legal_name="Test Customer",
        default_currency=currency,
        created_by=admin,
        updated_by=admin,
    )
    record_movement(
        company=company,
        movement_type=StockMovement.MovementType.INWARD,
        product=product,
        quantity=Decimal("4"),
        to_location=location,
        to_condition=StockItem.Condition.AVAILABLE,
        actor=admin,
    )
    order = SalesOrder.objects.create(
        company=company,
        financial_year=financial_year_label(company),
        sales_order_number="SO-TEST-0001",
        customer=customer,
        order_mode=SalesOrder.Mode.DIRECT,
        direct_reason="Walk-in",
        responsible_sales_employee=employee,
        po_pending=True,
        created_by=admin,
    )
    revision = SalesOrderRevision.objects.create(
        sales_order=order,
        revision_number=1,
        currency=currency,
    )
    order.current_revision = revision
    order.save(update_fields=["current_revision"])
    line = SalesOrderLine.objects.create(
        revision=revision,
        line_number=1,
        product=product,
        description=product.description,
        quantity=Decimal("4"),
        unit_of_measure="NOS",
        unit_price=Decimal("1000"),
    )

    _grant(admin, company, [])  # superuser already bypasses permission checks
    api_client.force_authenticate(admin)

    first = api_client.post(
        f"/api/v1/inventory/sales-order-lines/{line.pk}/reserve/",
        {"location": str(location.pk)},
        format="json",
    )
    assert first.status_code == 201
    reserved = StockItem.objects.get(product=product, location=location, condition="RESERVED")
    available = StockItem.objects.get(product=product, location=location, condition="AVAILABLE")
    assert reserved.quantity == Decimal("4")
    assert available.quantity == Decimal("0")

    other_order = SalesOrder.objects.create(
        company=company,
        financial_year=financial_year_label(company),
        sales_order_number="SO-TEST-0002",
        customer=customer,
        order_mode=SalesOrder.Mode.DIRECT,
        direct_reason="Walk-in",
        responsible_sales_employee=employee,
        po_pending=True,
        created_by=admin,
    )
    other_revision = SalesOrderRevision.objects.create(
        sales_order=other_order,
        revision_number=1,
        currency=currency,
    )
    other_order.current_revision = other_revision
    other_order.save(update_fields=["current_revision"])
    other_line = SalesOrderLine.objects.create(
        revision=other_revision,
        line_number=1,
        product=product,
        description=product.description,
        quantity=Decimal("4"),
        unit_of_measure="NOS",
        unit_price=Decimal("1000"),
    )

    second = api_client.post(
        f"/api/v1/inventory/sales-order-lines/{other_line.pk}/reserve/",
        {"location": str(location.pk)},
        format="json",
    )
    assert second.status_code == 400

    released = api_client.post(
        f"/api/v1/inventory/sales-order-lines/{line.pk}/release/",
        {"location": str(location.pk)},
        format="json",
    )
    assert released.status_code == 201
    available_after_release = StockItem.objects.get(product=product, location=location, condition="AVAILABLE")
    assert available_after_release.quantity == Decimal("4")
