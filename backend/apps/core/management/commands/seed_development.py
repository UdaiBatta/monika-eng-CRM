import os
from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User
from apps.numbering.models import DocumentSequence
from apps.numbering.services import financial_year_label
from apps.organization.models import Branch, Company, Department, Designation, Employee


class Command(BaseCommand):
    help = "Create an explicit local-only administrator and linked employee for UI QA."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_development is disabled unless DEBUG=True")
        email = os.getenv("DEV_ADMIN_EMAIL")
        password = os.getenv("DEV_ADMIN_PASSWORD")
        if not email or not password:
            raise CommandError("Set DEV_ADMIN_EMAIL and DEV_ADMIN_PASSWORD before running this command")

        company, _ = Company.objects.get_or_create(
            code="MEDEV",
            defaults={"name": "Monika Engineers Development", "legal_name": "Local development data"},
        )
        branch, _ = Branch.objects.get_or_create(
            company=company, code="DEV", defaults={"name": "Development Branch"}
        )
        department, _ = Department.objects.get_or_create(
            company=company, code="DEV-ENG", defaults={"name": "Development Engineering", "branch": branch}
        )
        designation, _ = Designation.objects.get_or_create(
            company=company, code="DEV-ADMIN", defaults={"name": "Development Administrator"}
        )
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "first_name": "Development",
                "last_name": "Administrator",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()
        Employee.objects.update_or_create(
            user=user,
            defaults={
                "company": company,
                "branch": branch,
                "department": department,
                "designation": designation,
                "employee_code": "ME-DEV-001",
                "first_name": "Development",
                "last_name": "Administrator",
                "company_email": email,
                "joining_date": date(2026, 1, 1),
                "employment_type": Employee.EmploymentType.PERMANENT,
                "employment_status": Employee.EmploymentStatus.ACTIVE,
            },
        )
        financial_year = financial_year_label(company)
        for code, template, padding in (
            ("CUSTOMER", "CUST-{number}", 5),
            ("ENQUIRY", "ENQ-{year}-{number}", 4),
        ):
            DocumentSequence.objects.get_or_create(
                company=company,
                branch=None,
                code=code,
                financial_year=financial_year,
                defaults={"template": template, "padding": padding},
            )
        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} local development administrator {email}"))
