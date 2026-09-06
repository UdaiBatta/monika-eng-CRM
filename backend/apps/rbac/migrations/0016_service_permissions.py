from django.db import migrations

PERMISSIONS = {
    "service.equipment.view": "View customer equipment",
    "service.equipment.manage": "Manage customer equipment",
    "service.ticket.view": "View Service Tickets",
    "service.ticket.create": "Create Service Tickets",
    "service.ticket.assign": "Assign a technician to a Service Ticket",
    "service.ticket.diagnose": "Record Service Ticket diagnosis",
    "service.ticket.record_parts_labour": "Record Service Ticket parts and labour",
    "service.ticket.link_quotation": "Link a quotation to a Service Ticket",
    "service.ticket.repair": "Change Service Ticket repair status",
    "service.ticket.dispatch": "Dispatch a Service Ticket",
    "service.ticket.close": "Close a Service Ticket",
    "service.ticket.cancel": "Cancel a Service Ticket",
}


def seed_permissions(apps, schema_editor):
    Permission = apps.get_model("rbac", "Permission")
    for code, name in PERMISSIONS.items():
        Permission.objects.update_or_create(
            code=code,
            defaults={"name": name, "description": "Service and repair", "is_active": True},
        )


def remove_permissions(apps, schema_editor):
    apps.get_model("rbac", "Permission").objects.filter(code__in=PERMISSIONS).delete()


class Migration(migrations.Migration):
    dependencies = [("rbac", "0015_workshop_panel_job_permissions")]
    operations = [migrations.RunPython(seed_permissions, remove_permissions)]
