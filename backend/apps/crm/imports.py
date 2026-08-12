from django.db import transaction
from rest_framework import serializers

from apps.core.tabular_imports import parse_tabular_upload
from apps.masters.models import Currency
from apps.organization.models import Company, Employee

CUSTOMER_IMPORT_HEADERS = {
    "company_code",
    "legal_name",
    "trade_name",
    "customer_type",
    "gstin",
    "pan",
    "cin",
    "industry",
    "website",
    "primary_email",
    "primary_phone",
    "account_manager_code",
    "default_currency_code",
    "source",
    "notes",
}


def _related(model, *, field, code, lookup_field="code", required=False, **filters):
    if not code:
        if required:
            raise serializers.ValidationError({field: ["This field is required."]})
        return None
    try:
        return model.objects.get(**{f"{lookup_field}__iexact": code}, **filters)
    except model.DoesNotExist as exc:
        raise serializers.ValidationError(
            {field: [f'No matching {model._meta.verbose_name} with code "{code}".']}
        ) from exc
    except model.MultipleObjectsReturned as exc:
        raise serializers.ValidationError(
            {field: [f'More than one {model._meta.verbose_name} uses code "{code}".']}
        ) from exc


def _customer_payload(row):
    company = _related(
        Company,
        field="company_code",
        code=row.get("company_code"),
        required=True,
    )
    currency = _related(
        Currency,
        field="default_currency_code",
        code=row.get("default_currency_code"),
        required=True,
    )
    manager = _related(
        Employee,
        field="account_manager_code",
        code=row.get("account_manager_code"),
        lookup_field="employee_code",
        company=company,
    )
    data = {
        key: row[key]
        for key in (
            "legal_name",
            "trade_name",
            "customer_type",
            "gstin",
            "pan",
            "cin",
            "industry",
            "website",
            "primary_email",
            "primary_phone",
            "source",
            "notes",
        )
        if row.get(key, "") != ""
    }
    data.update(
        company=company.pk,
        account_manager=manager.pk if manager else None,
        default_currency=currency.pk,
    )
    if "customer_type" in data:
        data["customer_type"] = data["customer_type"].upper().replace(" ", "_")
    for field in ("gstin", "pan", "cin"):
        if field in data:
            data[field] = data[field].upper()
    return data


def import_customers(view, upload):
    rows = parse_tabular_upload(
        upload,
        required_headers={"company_code", "legal_name", "default_currency_code"},
        allowed_headers=CUSTOMER_IMPORT_HEADERS,
        label="customers",
    )
    created = []
    errors = []
    with transaction.atomic():
        for row_number, row in enumerate(rows, start=2):
            try:
                data = _customer_payload(row)
            except serializers.ValidationError as exc:
                errors.append({"row": row_number, "errors": exc.detail})
                continue
            serializer = view.get_serializer(data=data)
            if not serializer.is_valid():
                errors.append({"row": row_number, "errors": serializer.errors})
                continue
            try:
                view.perform_create(serializer)
            except serializers.ValidationError as exc:
                errors.append({"row": row_number, "errors": exc.detail})
                continue
            created.append(serializer.instance)
        if errors:
            raise serializers.ValidationError({"rows": errors})
    return created
