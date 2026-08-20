from django.db import migrations


PERMISSIONS = {
    "system.owner_control.view": (
        "Open Owner Control",
        "Open the business Owner Control Centre and its administrative summaries.",
    ),
    "system.owner_control.manage": (
        "Manage Owner Control",
        "Perform protected business-owner administration. Assignment of this permission is guarded.",
    ),
    "system.access_explanation.view": (
        "Explain employee access",
        "See why an employee can or cannot perform a business action.",
    ),
    "system.work.reassign": (
        "Reassign work",
        "Move open work between active employees within the permitted company scope.",
    ),
    "system.data_quality.view": (
        "View data quality",
        "Review missing relationships, inactive assignees, and exact duplicate candidates.",
    ),
    "system.system_health.view": (
        "View system health",
        "See safe operational status for database, realtime, jobs, storage, and integrations.",
    ),
    "system.override.perform": (
        "Perform controlled override",
        "Perform a supported business override with a mandatory reason and Audit history.",
    ),
}


def seed_permissions(apps, schema_editor):
    permission = apps.get_model("rbac", "Permission")
    for code, (name, description) in PERMISSIONS.items():
        permission.objects.update_or_create(
            code=code,
            defaults={"name": name, "description": description, "is_active": True},
        )


def remove_permissions(apps, schema_editor):
    apps.get_model("rbac", "Permission").objects.filter(code__in=PERMISSIONS).delete()


class Migration(migrations.Migration):
    dependencies = [("rbac", "0011_permission_record_version_and_more")]
    operations = [migrations.RunPython(seed_permissions, remove_permissions)]

