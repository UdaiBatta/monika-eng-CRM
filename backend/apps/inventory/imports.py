from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from apps.core.tabular_imports import parse_tabular_upload
from apps.masters.models import PaymentTerm, UnitOfMeasure
from apps.organization.models import Company, Warehouse

from .models import Product, ProductCategory, StockItem, StockLocation, Supplier
from .services import record_movement


def _present(row, *fields):
    return {field: row[field] for field in fields if row.get(field, "") != ""}


def _related(model, *, field, code, lookup_field="code", required=False, **filters):
    if not code:
        if required:
            raise serializers.ValidationError({field: ["This field is required."]})
        return None
    try:
        return model.objects.get(**{f"{lookup_field}__iexact": code}, **filters)
    except model.DoesNotExist as exc:
        message = f'No matching {model._meta.verbose_name} with code "{code}".'
        raise serializers.ValidationError({field: [message]}) from exc
    except model.MultipleObjectsReturned as exc:
        message = f'More than one {model._meta.verbose_name} uses code "{code}".'
        raise serializers.ValidationError({field: [message]}) from exc


def _company(row):
    return _related(Company, field="company_code", code=row.get("company_code"), required=True)


def _category_payload(row):
    company = _company(row)
    return {**_present(row, "code", "name", "is_active"), "company": company.pk, "code": row["code"].upper()}


def _supplier_payload(row):
    company = _company(row)
    payment_term = _related(
        PaymentTerm, field="payment_term_code", code=row.get("payment_term_code"), company=company
    )
    data = _present(row, "code", "name", "gstin", "contact_name", "phone", "email", "address", "is_active")
    data.update(
        company=company.pk,
        code=row["code"].upper(),
        payment_term=payment_term.pk if payment_term else None,
    )
    return data


def _product_payload(row):
    company = _company(row)
    category = _related(
        ProductCategory, field="category_code", code=row.get("category_code"), company=company
    )
    supplier = _related(
        Supplier, field="default_supplier_code", code=row.get("default_supplier_code"), company=company
    )
    uom = _related(
        UnitOfMeasure,
        field="unit_of_measure_code",
        code=row.get("unit_of_measure_code"),
        lookup_field="code",
        required=True,
    )
    data = _present(
        row,
        "internal_code",
        "brand",
        "part_number",
        "description",
        "specification",
        "warranty_months",
        "reorder_level",
        "reorder_quantity",
        "is_active",
    )
    data.update(
        company=company.pk,
        category=category.pk if category else None,
        default_supplier=supplier.pk if supplier else None,
        unit_of_measure=uom.pk,
    )
    return data


IMPORT_SPECS = {
    ProductCategory: {
        "required": {"company_code", "code", "name"},
        "allowed": {"company_code", "code", "name", "is_active"},
        "label": "product categories",
        "prepare": _category_payload,
    },
    Supplier: {
        "required": {"company_code", "code", "name"},
        "allowed": {
            "company_code",
            "code",
            "name",
            "gstin",
            "contact_name",
            "phone",
            "email",
            "address",
            "payment_term_code",
            "is_active",
        },
        "label": "suppliers",
        "prepare": _supplier_payload,
    },
    Product: {
        "required": {"company_code", "internal_code", "description", "unit_of_measure_code"},
        "allowed": {
            "company_code",
            "category_code",
            "default_supplier_code",
            "unit_of_measure_code",
            "internal_code",
            "brand",
            "part_number",
            "description",
            "specification",
            "warranty_months",
            "reorder_level",
            "reorder_quantity",
            "is_active",
        },
        "label": "products",
        "prepare": _product_payload,
    },
}


def import_inventory_records(view, upload):
    spec = IMPORT_SPECS[view.get_queryset().model]
    rows = parse_tabular_upload(
        upload, required_headers=spec["required"], allowed_headers=spec["allowed"], label=spec["label"]
    )
    created = []
    errors = []
    with transaction.atomic():
        for row_number, row in enumerate(rows, start=2):
            try:
                data = spec["prepare"](row)
            except serializers.ValidationError as exc:
                errors.append({"row": row_number, "errors": exc.detail})
                continue
            serializer = view.get_serializer(data=data)
            if not serializer.is_valid():
                errors.append({"row": row_number, "errors": serializer.errors})
                continue
            view.perform_create(serializer)
            created.append(serializer.instance)
        if errors:
            raise serializers.ValidationError({"rows": errors})
    return created


OPENING_BALANCE_REQUIRED = {"company_code", "product_code", "warehouse_code", "condition", "quantity"}
OPENING_BALANCE_ALLOWED = OPENING_BALANCE_REQUIRED | {"bin_code"}


def import_opening_balances(upload, *, actor):
    rows = parse_tabular_upload(
        upload,
        required_headers=OPENING_BALANCE_REQUIRED,
        allowed_headers=OPENING_BALANCE_ALLOWED,
        label="opening balances",
    )
    created = []
    errors = []
    with transaction.atomic():
        for row_number, row in enumerate(rows, start=2):
            try:
                company = _related(Company, field="company_code", code=row["company_code"], required=True)
                product = _related(
                    Product,
                    field="product_code",
                    code=row["product_code"],
                    lookup_field="internal_code",
                    company=company,
                    required=True,
                )
                warehouse = _related(
                    Warehouse,
                    field="warehouse_code",
                    code=row["warehouse_code"],
                    company=company,
                    required=True,
                )
                location, _ = StockLocation.objects.get_or_create(
                    warehouse=warehouse, bin_code=row.get("bin_code", "")
                )
                condition = row["condition"].strip().upper().replace(" ", "_")
                if condition not in StockItem.Condition.values:
                    raise serializers.ValidationError(
                        {"condition": [f'"{row["condition"]}" is not a valid stock condition.']}
                    )
                try:
                    quantity = Decimal(row["quantity"])
                except InvalidOperation as exc:
                    raise serializers.ValidationError({"quantity": ["Enter a valid quantity."]}) from exc
                if quantity <= 0:
                    raise serializers.ValidationError({"quantity": ["Quantity must be greater than zero."]})
            except serializers.ValidationError as exc:
                errors.append({"row": row_number, "errors": exc.detail})
                continue
            try:
                movement = record_movement(
                    company=company,
                    movement_type="INWARD",
                    product=product,
                    quantity=quantity,
                    to_location=location,
                    to_condition=condition,
                    reason="Opening balance import",
                    actor=actor,
                )
            except DjangoValidationError as exc:
                detail = exc.message_dict if hasattr(exc, "message_dict") else str(exc)
                errors.append({"row": row_number, "errors": detail})
                continue
            created.append(movement)
        if errors:
            raise serializers.ValidationError({"rows": errors})
    return created
