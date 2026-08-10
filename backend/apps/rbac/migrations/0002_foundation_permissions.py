from django.db import migrations


PERMISSIONS = {
    "accounts.user.view": "View user accounts",
    "accounts.user.manage": "Manage user accounts",
    "organization.company.view": "View companies",
    "organization.company.manage": "Manage companies",
    "organization.branch.view": "View branches",
    "organization.branch.manage": "Manage branches",
    "organization.department.view": "View departments",
    "organization.department.manage": "Manage departments",
    "organization.designation.view": "View designations",
    "organization.designation.manage": "Manage designations",
    "organization.warehouse.view": "View warehouses",
    "organization.warehouse.manage": "Manage warehouses",
    "organization.employee.view": "View employees",
    "organization.employee.manage": "Manage employees",
    "rbac.permission.view": "View permission catalogue",
    "rbac.permission.manage": "Manage permission catalogue",
    "rbac.role.view": "View roles",
    "rbac.role.manage": "Manage roles",
    "rbac.assignment.view": "View role assignments",
    "rbac.assignment.manage": "Manage role assignments",
    "rbac.override.view": "View permission overrides",
    "rbac.override.manage": "Manage permission overrides",
    "configuration.settings.view": "View company settings",
    "configuration.settings.manage": "Manage company settings",
    "configuration.feature_flag.view": "View feature flags",
    "configuration.feature_flag.manage": "Manage feature flags",
    "masters.view": "View foundation masters",
    "masters.manage": "Manage foundation masters",
    "numbering.sequence.view": "View document sequences",
    "numbering.sequence.manage": "Manage document sequences",
}


def seed_permissions(apps, schema_editor):
    permission = apps.get_model("rbac", "Permission")
    for code, name in PERMISSIONS.items():
        permission.objects.update_or_create(code=code, defaults={"name": name, "is_active": True})


def remove_permissions(apps, schema_editor):
    apps.get_model("rbac", "Permission").objects.filter(code__in=PERMISSIONS).delete()


class Migration(migrations.Migration):
    dependencies = [("rbac", "0001_initial")]
    operations = [migrations.RunPython(seed_permissions, remove_permissions)]
