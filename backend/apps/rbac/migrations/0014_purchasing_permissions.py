from django.db import migrations

PERMISSIONS = {
    "purchasing.requisition.view": "View Purchase Requisitions",
    "purchasing.requisition.create": "Create Purchase Requisitions",
    "purchasing.requisition.submit": "Submit Purchase Requisitions for approval",
    "purchasing.purchase_order.view": "View Purchase Orders",
    "purchasing.purchase_order.create": "Create Purchase Orders",
    "purchasing.purchase_order.submit": "Submit Purchase Orders for approval",
    "purchasing.purchase_order.cancel": "Cancel Purchase Orders",
    "purchasing.purchase_order.record_payment": "Record supplier payments",
    "purchasing.goods_receipt.view": "View Goods Receipts (GRN)",
    "purchasing.goods_receipt.create": "Create Goods Receipts (GRN)",
    "purchasing.goods_receipt.confirm": "Confirm Goods Receipts and update stock",
}


def seed_permissions(apps, schema_editor):
    Permission = apps.get_model("rbac", "Permission")
    for code, name in PERMISSIONS.items():
        Permission.objects.update_or_create(
            code=code,
            defaults={"name": name, "description": "Purchasing", "is_active": True},
        )


def remove_permissions(apps, schema_editor):
    apps.get_model("rbac", "Permission").objects.filter(code__in=PERMISSIONS).delete()


class Migration(migrations.Migration):
    dependencies = [("rbac", "0013_inventory_permissions")]
    operations = [migrations.RunPython(seed_permissions, remove_permissions)]
