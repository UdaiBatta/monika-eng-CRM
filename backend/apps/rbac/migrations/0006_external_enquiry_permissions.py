from django.db import migrations


PERMISSIONS = {
    "crm.external_enquiry.view": "View website enquiries",
    "crm.external_enquiry.review": "Review website enquiries",
    "crm.external_enquiry.assign": "Assign website enquiries",
    "crm.external_enquiry.convert": "Convert website enquiries",
    "crm.external_enquiry.reject": "Reject website enquiries",
    "crm.external_enquiry.mark_spam": "Mark website enquiries as spam",
    "crm.external_enquiry.view_source_metadata": "View website enquiry source metadata",
}


def seed_permissions(apps, schema_editor):
    Permission = apps.get_model("rbac", "Permission")
    for code, name in PERMISSIONS.items():
        Permission.objects.update_or_create(
            code=code,
            defaults={"name": name, "description": "Phase 2 website enquiry intake", "is_active": True},
        )


def remove_permissions(apps, schema_editor):
    apps.get_model("rbac", "Permission").objects.filter(code__in=PERMISSIONS).delete()


class Migration(migrations.Migration):
    dependencies = [("rbac", "0005_engineering_feasibility_permissions")]
    operations = [migrations.RunPython(seed_permissions, remove_permissions)]
