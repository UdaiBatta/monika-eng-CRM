from django.db import migrations


LEGACY_CODES = [
    "quotation.quotation.view",
    "quotation.quotation.create",
    "quotation.quotation.edit",
    "quotation.quotation.submit",
    "quotation.quotation.approve",
    "quotation.quotation.send",
    "quotation.quotation.create_revision",
    "quotation.quotation.accept",
    "quotation.quotation.reject",
    "quotation.quotation.cancel",
    "quotation.quotation.view_internal",
]


def deactivate_legacy_permissions(apps, _schema_editor):
    apps.get_model("rbac", "Permission").objects.filter(code__in=LEGACY_CODES).update(
        is_active=False
    )


def reactivate_legacy_permissions(apps, _schema_editor):
    apps.get_model("rbac", "Permission").objects.filter(code__in=LEGACY_CODES).update(
        is_active=True
    )


class Migration(migrations.Migration):
    dependencies = [("rbac", "0008_quotation_permissions")]
    operations = [migrations.RunPython(deactivate_legacy_permissions, reactivate_legacy_permissions)]
