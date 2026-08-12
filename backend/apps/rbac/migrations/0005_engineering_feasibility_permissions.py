from django.db import migrations


PERMISSIONS = {
    "engineering.feasibility.start": "Start engineering feasibility reviews",
    "engineering.feasibility.edit": "Edit engineering feasibility assessments",
    "engineering.feasibility.request_clarification": "Request engineering clarifications",
    "engineering.feasibility.respond_clarification": "Respond to engineering clarifications",
    "engineering.feasibility.mark_not_feasible": "Mark engineering reviews not feasible",
    "engineering.feasibility.reassess": "Create engineering reassessment revisions",
    "engineering.feasibility.view_sensitive": "View sensitive engineering review data",
}


def seed_permissions(apps, schema_editor):
    Permission = apps.get_model("rbac", "Permission")
    for code, name in PERMISSIONS.items():
        Permission.objects.update_or_create(
            code=code,
            defaults={"name": name, "description": "Phase 2 engineering feasibility", "is_active": True},
        )


def remove_permissions(apps, schema_editor):
    apps.get_model("rbac", "Permission").objects.filter(code__in=PERMISSIONS).delete()


class Migration(migrations.Migration):
    dependencies = [("rbac", "0004_commercial_crm_permissions")]
    operations = [migrations.RunPython(seed_permissions, remove_permissions)]
