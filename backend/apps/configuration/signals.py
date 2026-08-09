from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.masters.models import Currency
from apps.organization.models import Company

from .models import CompanySettings


@receiver(post_save, sender=Company)
def create_company_settings(sender, instance, created, **kwargs):
    if created:
        CompanySettings.objects.get_or_create(
            company=instance,
            defaults={"default_currency": Currency.objects.filter(code="INR", is_active=True).first()},
        )
