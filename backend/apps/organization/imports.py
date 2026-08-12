from django.db import transaction
from rest_framework import serializers

from apps.core.tabular_imports import parse_tabular_upload

from .models import Branch, Company, Department, Designation, Employee, Warehouse


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


def _company_payload(row):
    data = _present(row, "code", "name", "legal_name", "gstin", "pan", "timezone", "is_active")
    for field in ("code", "gstin", "pan"):
        if field in data:
            data[field] = data[field].upper()
    return data


def _branch_payload(row):
    company = _company(row)
    return {
        **_present(row, "code", "name", "address", "is_active"),
        "company": company.pk,
        "code": row["code"].upper(),
    }


def _department_payload(row):
    company = _company(row)
    branch = _related(
        Branch,
        field="branch_code",
        code=row.get("branch_code"),
        company=company,
    )
    parent = _related(
        Department,
        field="parent_department_code",
        code=row.get("parent_department_code"),
        company=company,
    )
    return {
        **_present(row, "code", "name", "is_active"),
        "company": company.pk,
        "branch": branch.pk if branch else None,
        "parent": parent.pk if parent else None,
        "code": row["code"].upper(),
    }


def _designation_payload(row):
    company = _company(row)
    return {
        **_present(row, "code", "name", "is_active"),
        "company": company.pk,
        "code": row["code"].upper(),
    }


def _warehouse_payload(row):
    company = _company(row)
    branch = _related(
        Branch,
        field="branch_code",
        code=row.get("branch_code"),
        company=company,
        required=True,
    )
    return {
        **_present(row, "code", "name", "address", "is_active"),
        "company": company.pk,
        "branch": branch.pk,
        "code": row["code"].upper(),
    }


def _employee_payload(row):
    company = _company(row)
    branch = _related(Branch, field="branch_code", code=row.get("branch_code"), company=company)
    department = _related(
        Department,
        field="department_code",
        code=row.get("department_code"),
        company=company,
    )
    designation = _related(
        Designation,
        field="designation_code",
        code=row.get("designation_code"),
        company=company,
    )
    manager = _related(
        Employee,
        field="reporting_manager_code",
        code=row.get("reporting_manager_code"),
        lookup_field="employee_code",
        company=company,
    )
    data = _present(
        row,
        "employee_code",
        "first_name",
        "last_name",
        "company_email",
        "phone",
        "joining_date",
        "employment_type",
        "employment_status",
    )
    data.update(
        company=company.pk,
        branch=branch.pk if branch else None,
        department=department.pk if department else None,
        designation=designation.pk if designation else None,
        reporting_manager=manager.pk if manager else None,
    )
    data["employee_code"] = data["employee_code"].upper()
    data["employment_type"] = data["employment_type"].upper().replace(" ", "_")
    if "employment_status" in data:
        data["employment_status"] = data["employment_status"].upper().replace(" ", "_")
    if "company_email" in data:
        data["company_email"] = data["company_email"].lower()
    return data


IMPORT_SPECS = {
    Company: {
        "required": {"code", "name"},
        "allowed": {"code", "name", "legal_name", "gstin", "pan", "timezone", "is_active"},
        "label": "companies",
        "prepare": _company_payload,
    },
    Branch: {
        "required": {"company_code", "code", "name"},
        "allowed": {"company_code", "code", "name", "address", "is_active"},
        "label": "branches",
        "prepare": _branch_payload,
    },
    Department: {
        "required": {"company_code", "code", "name"},
        "allowed": {"company_code", "branch_code", "parent_department_code", "code", "name", "is_active"},
        "label": "departments",
        "prepare": _department_payload,
    },
    Designation: {
        "required": {"company_code", "code", "name"},
        "allowed": {"company_code", "code", "name", "is_active"},
        "label": "designations",
        "prepare": _designation_payload,
    },
    Warehouse: {
        "required": {"company_code", "branch_code", "code", "name"},
        "allowed": {"company_code", "branch_code", "code", "name", "address", "is_active"},
        "label": "warehouses",
        "prepare": _warehouse_payload,
    },
    Employee: {
        "required": {"company_code", "employee_code", "first_name", "joining_date", "employment_type"},
        "allowed": {
            "company_code",
            "branch_code",
            "department_code",
            "designation_code",
            "reporting_manager_code",
            "employee_code",
            "first_name",
            "last_name",
            "company_email",
            "phone",
            "joining_date",
            "employment_type",
            "employment_status",
        },
        "label": "employees",
        "prepare": _employee_payload,
    },
}


def import_organization_records(view, upload):
    spec = IMPORT_SPECS[view.get_queryset().model]
    rows = parse_tabular_upload(
        upload,
        required_headers=spec["required"],
        allowed_headers=spec["allowed"],
        label=spec["label"],
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
