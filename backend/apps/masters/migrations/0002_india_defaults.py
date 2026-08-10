from django.db import migrations


def seed_india_defaults(apps, schema_editor):
    currency = apps.get_model("masters", "Currency")
    currency.objects.update_or_create(
        code="INR",
        defaults={"name": "Indian Rupee", "symbol": "₹", "decimal_places": 2, "is_active": True},
    )


def remove_india_defaults(apps, schema_editor):
    apps.get_model("masters", "Currency").objects.filter(code="INR").delete()


class Migration(migrations.Migration):
    dependencies = [("masters", "0001_initial")]
    operations = [migrations.RunPython(seed_india_defaults, remove_india_defaults)]
