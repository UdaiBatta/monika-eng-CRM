from django.db import migrations

PERMISSIONS = {
    "workshop.panel_job.view": "View Panel Jobs",
    "workshop.panel_job.create": "Create Panel Jobs from an accepted Project",
    "workshop.panel_job.plan_material": "Plan Panel Job material requirements",
    "workshop.panel_job.reserve_stock": "Reserve stock for a Panel Job",
    "workshop.panel_job.record_material": "Record Panel Job material issue, consumption and return",
    "workshop.panel_job.advance": "Advance a Panel Job to its next stage",
    "workshop.panel_job.assemble": "Move a Panel Job into Assembly",
    "workshop.panel_job.wire": "Move a Panel Job into Wiring",
    "workshop.panel_job.test": "Move a Panel Job into Testing",
    "workshop.panel_job.quality_check": "Record a Panel Job Quality Check",
    "workshop.panel_job.handover": "Hand over a completed Panel Job",
    "workshop.panel_job.hold": "Put a Panel Job on hold or resume it",
    "workshop.panel_job.cancel": "Cancel a Panel Job",
}


def seed_permissions(apps, schema_editor):
    Permission = apps.get_model("rbac", "Permission")
    for code, name in PERMISSIONS.items():
        Permission.objects.update_or_create(
            code=code,
            defaults={"name": name, "description": "Panel workshop", "is_active": True},
        )


def remove_permissions(apps, schema_editor):
    apps.get_model("rbac", "Permission").objects.filter(code__in=PERMISSIONS).delete()


class Migration(migrations.Migration):
    dependencies = [("rbac", "0014_purchasing_permissions")]
    operations = [migrations.RunPython(seed_permissions, remove_permissions)]
