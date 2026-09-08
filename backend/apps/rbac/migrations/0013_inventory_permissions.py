from django.db import migrations

PERMISSIONS = {
    "inventory.product.view": "View products and categories",
    "inventory.product.manage": "Manage products and categories",
    "inventory.supplier.view": "View suppliers",
    "inventory.supplier.manage": "Manage suppliers",
    "inventory.stock.view": "View stock balances and movements",
    "inventory.stock.manage": "Record stock movements and adjustments",
    "inventory.stock.reserve": "Reserve or release stock against Sales Orders",
}


def seed_permissions(apps, schema_editor):
    Permission = apps.get_model("rbac", "Permission")
    for code, name in PERMISSIONS.items():
        Permission.objects.update_or_create(
            code=code,
            defaults={"name": name, "description": "Inventory", "is_active": True},
        )


def remove_permissions(apps, schema_editor):
    apps.get_model("rbac", "Permission").objects.filter(code__in=PERMISSIONS).delete()


class Migration(migrations.Migration):
    dependencies = [("rbac", "0012_owner_control_permissions")]
    operations = [migrations.RunPython(seed_permissions, remove_permissions)]
