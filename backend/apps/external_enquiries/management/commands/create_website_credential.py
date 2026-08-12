import secrets

from django.core.management.base import BaseCommand, CommandError

from apps.organization.models import Company

from ...models import IntegrationCredential


class Command(BaseCommand):
    help = "Create or rotate a website integration credential and print its secret once."

    def add_arguments(self, parser):
        parser.add_argument("--company-code", required=True)
        parser.add_argument("--key-id", required=True)
        parser.add_argument("--name", default="Monika Engineers website")
        parser.add_argument("--allowed-source", default="www.monikaengineers.co.in")

    def handle(self, *args, **options):
        try:
            company = Company.objects.get(code=options["company_code"])
        except Company.DoesNotExist as exc:
            raise CommandError("Company not found.") from exc
        secret = secrets.token_urlsafe(32)
        credential, created = IntegrationCredential.objects.update_or_create(
            key_id=options["key_id"],
            defaults={
                "company": company,
                "name": options["name"],
                "integration_type": IntegrationCredential.IntegrationType.WEBSITE,
                "secret_hash": IntegrationCredential.hash_secret(secret),
                "allowed_source": options["allowed_source"],
                "is_active": True,
            },
        )
        action = "Created" if created else "Rotated"
        self.stdout.write(self.style.SUCCESS(f"{action} {credential.key_id}"))
        self.stdout.write("Copy this secret now; it will not be shown again:")
        self.stdout.write(secret)
        self.stdout.write(f'Add it to INTEGRATION_SECRETS_JSON as {{"{credential.key_id}": "<secret>"}}.')
