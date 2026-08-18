from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.configuration.models import FeatureFlag
from apps.organization.models import Branch, Company, Department, Employee


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def company(db):
    company = Company.objects.create(name="Monika Engineers Test", code="METEST")
    FeatureFlag.objects.create(company=company, key="quick_quotation", is_enabled=True)
    FeatureFlag.objects.create(company=company, key="website_enquiries", is_enabled=True)
    return company


@pytest.fixture
def branch(company):
    return Branch.objects.create(company=company, name="Pune", code="PUN")


@pytest.fixture
def department(company, branch):
    return Department.objects.create(company=company, branch=branch, name="Engineering", code="ENG")


@pytest.fixture
def user(db):
    return User.objects.create_user(email="engineer@example.test", password="SafePassword-2741")


@pytest.fixture
def employee(user, company, branch, department):
    return Employee.objects.create(
        user=user,
        company=company,
        branch=branch,
        department=department,
        employee_code="ME-TEST-001",
        first_name="Test",
        last_name="Engineer",
        joining_date=date(2026, 1, 1),
        employment_type=Employee.EmploymentType.PERMANENT,
    )
