from datetime import date

import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.organization.models import Branch, Company, Employee


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
