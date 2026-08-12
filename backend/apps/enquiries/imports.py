from django.db import transaction
from rest_framework import serializers

from apps.core.tabular_imports import parse_tabular_upload
from apps.crm.models import Customer
from apps.masters.models import Currency
from apps.organization.models import Company, Employee

ENQUIRY_IMPORT_HEADERS = {
    "company_code",
    "customer_code",
    "subject",
    "customer_reference",
    "received_date",
    "due_date",
    "priority",
    "responsible_salesperson_code",
    "estimated_value",
    "currency_code",
    "source",
    "description",
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


def _enquiry_payload(row):
    company = _related(
        Company,
        field="company_code",
        code=row.get("company_code"),
        required=True,
    )
    customer = _related(
        Customer,
        field="customer_code",
        code=row.get("customer_code"),
        lookup_field="customer_code",
        company=company,
        required=True,
    )
    salesperson = _related(
        Employee,
        field="responsible_salesperson_code",
        code=row.get("responsible_salesperson_code"),
        lookup_field="employee_code",
        company=company,
        required=True,
    )
    currency = _related(
        Currency,
        field="currency_code",
        code=row.get("currency_code"),
    )
    data = {
        key: row[key]
        for key in (
            "subject",
            "customer_reference",
            "received_date",
            "due_date",
            "priority",
            "estimated_value",
            "source",
            "description",
        )
        if row.get(key, "") != ""
    }
    data.update(
        customer=customer.pk,
        responsible_salesperson=salesperson.pk,
    )
    if currency:
        data["currency"] = currency.pk
    if "priority" in data:
        data["priority"] = data["priority"].upper().replace(" ", "_")
    return data


def import_enquiries(view, upload):
    rows = parse_tabular_upload(
        upload,
        required_headers={
            "company_code",
            "customer_code",
            "subject",
            "received_date",
            "responsible_salesperson_code",
        },
        allowed_headers=ENQUIRY_IMPORT_HEADERS,
        label="enquiries",
    )
    created = []
    errors = []
    with transaction.atomic():
        for row_number, row in enumerate(rows, start=2):
            try:
                data = _enquiry_payload(row)
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
