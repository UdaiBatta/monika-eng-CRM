import io
from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from openpyxl import Workbook

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.organization.models import Branch, Company, Department, Designation, Employee, Warehouse


def _csv_upload(name, contents):
    return SimpleUploadedFile(name, contents.encode(), content_type="text/csv")


@pytest.mark.django_db
def test_user_and_employee_are_separate_records(user, employee):
    assert isinstance(user, User)
    assert employee.user == user
    assert employee.pk != user.pk
    assert employee.display_name == "Test Engineer"


@pytest.mark.django_db
def test_employee_rejects_cross_company_branch(user):
    first = Company.objects.create(name="First Company", code="FIRST")
    second = Company.objects.create(name="Second Company", code="SECOND")
    other_branch = Branch.objects.create(company=second, name="Other", code="OTHER")
    candidate = Employee(
        user=user,
        company=first,
        branch=other_branch,
        employee_code="FIRST-001",
        first_name="Boundary",
        joining_date=date(2026, 1, 1),
        employment_type=Employee.EmploymentType.PERMANENT,
    )
    with pytest.raises(ValidationError, match="selected company"):
        candidate.save()


@pytest.mark.django_db
def test_company_creation_applies_india_defaults(company):
    assert company.settings.timezone == "Asia/Kolkata"
    assert company.settings.country_code == "IN"
    assert company.settings.financial_year_start_month == 4
    assert company.settings.default_currency.code == "INR"


@pytest.mark.django_db
def test_existing_organization_registers_import_from_csv(api_client):
    admin = User.objects.create_superuser(email="import-admin@example.test", password="SafePassword-2741")
    api_client.force_authenticate(admin)
    imports = [
        (
            "/api/v1/companies/import-history/",
            "companies.csv",
            "code,name,legal_name,is_active\nIMP,Imported Industries,Imported Industries Pvt Ltd,true\n",
        ),
        (
            "/api/v1/branches/import-history/",
            "branches.csv",
            "company_code,code,name,address,is_active\nIMP,PUN,Pune Works,Pune,true\n",
        ),
        (
            "/api/v1/departments/import-history/",
            "departments.csv",
            "company_code,branch_code,parent_department_code,code,name,is_active\nIMP,PUN,,ENG,Engineering,true\n",
        ),
        (
            "/api/v1/designations/import-history/",
            "designations.csv",
            "company_code,code,name,is_active\nIMP,DES-ENG,Engineer,true\n",
        ),
        (
            "/api/v1/warehouses/import-history/",
            "warehouses.csv",
            "company_code,branch_code,code,name,address,is_active\nIMP,PUN,MAIN,Main Stores,Pune,true\n",
        ),
        (
            "/api/v1/employees/import-history/",
            "employees.csv",
            "company_code,branch_code,department_code,designation_code,reporting_manager_code,employee_code,first_name,last_name,company_email,phone,joining_date,employment_type,employment_status\n"
            "IMP,PUN,ENG,DES-ENG,,IMP-001,Asha,Rao,asha@imported.example,9000000000,2025-04-01,permanent,active\n",
        ),
    ]

    for endpoint, filename, contents in imports:
        response = api_client.post(
            endpoint,
            {"file": _csv_upload(filename, contents)},
            format="multipart",
        )
        assert response.status_code == 201, response.data
        assert response.data == {"imported": 1}

    company = Company.objects.get(code="IMP")
    assert Branch.objects.filter(company=company, code="PUN").exists()
    assert Department.objects.filter(company=company, code="ENG").exists()
    assert Designation.objects.filter(company=company, code="DES-ENG").exists()
    assert Warehouse.objects.filter(company=company, code="MAIN").exists()
    imported_employee = Employee.objects.get(company=company, employee_code="IMP-001")
    assert imported_employee.company_email == "asha@imported.example"
    assert AuditEvent.objects.filter(action="CREATE").count() >= 6


@pytest.mark.django_db
def test_organization_import_is_atomic_and_reports_bad_row(api_client, company):
    admin = User.objects.create_superuser(email="atomic-admin@example.test", password="SafePassword-2741")
    api_client.force_authenticate(admin)
    contents = (
        "company_code,code,name,address,is_active\n"
        f"{company.code},GOOD,Good Branch,Pune,true\n"
        "MISSING,BAD,Bad Branch,Nowhere,true\n"
    )

    response = api_client.post(
        "/api/v1/branches/import-history/",
        {"file": _csv_upload("branches.csv", contents)},
        format="multipart",
    )

    assert response.status_code == 400
    assert not Branch.objects.filter(code__in=["GOOD", "BAD"]).exists()
    assert int(response.data["error"]["details"]["rows"][0]["row"]) == 3


@pytest.mark.django_db
def test_department_import_accepts_xlsx_and_parent_codes(api_client, company, branch):
    admin = User.objects.create_superuser(email="xlsx-admin@example.test", password="SafePassword-2741")
    api_client.force_authenticate(admin)
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["company_code", "branch_code", "parent_department_code", "code", "name", "is_active"])
    sheet.append([company.code, branch.code, "", "OPS", "Operations", True])
    sheet.append([company.code, branch.code, "OPS", "QA", "Quality", True])
    stream = io.BytesIO()
    workbook.save(stream)

    response = api_client.post(
        "/api/v1/departments/import-history/",
        {
            "file": SimpleUploadedFile(
                "departments.xlsx",
                stream.getvalue(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        format="multipart",
    )

    assert response.status_code == 201, response.data
    assert Department.objects.get(company=company, code="QA").parent.code == "OPS"
