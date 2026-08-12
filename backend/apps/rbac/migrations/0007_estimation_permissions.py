from django.db import migrations

PERMISSIONS = {
    "estimation.estimate.view": "View commercial estimates",
    "estimation.estimate.view_cost": "View estimate cost details",
    "estimation.estimate.view_margin": "View estimate price and margin",
    "estimation.estimate.create": "Create commercial estimates",
    "estimation.estimate.edit": "Edit commercial estimates",
    "estimation.estimate.submit": "Submit estimates for approval",
    "estimation.estimate.revise": "Revise commercial estimates",
    "estimation.estimate.cancel": "Cancel commercial estimates",
    "estimation.estimate.export": "Export commercial estimates",
}


def seed_permissions(apps, schema_editor):
    Permission = apps.get_model("rbac", "Permission")
    for code, name in PERMISSIONS.items():
        Permission.objects.update_or_create(
            code=code,
            defaults={"name": name, "description": "Phase 2 commercial estimation", "is_active": True},
        )


def remove_permissions(apps, schema_editor):
    apps.get_model("rbac", "Permission").objects.filter(code__in=PERMISSIONS).delete()


class Migration(migrations.Migration):
    dependencies = [("rbac", "0006_external_enquiry_permissions")]
    operations = [migrations.RunPython(seed_permissions, remove_permissions)]
