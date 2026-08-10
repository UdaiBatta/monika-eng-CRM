from django.db import migrations


PERMISSIONS = {
    "documents.document.view": "View documents",
    "documents.document.upload": "Upload documents",
    "documents.document.version_add": "Add document versions",
    "documents.document.download": "Download documents",
    "documents.document.archive": "Archive documents",
    "documents.document.restore": "Restore documents",
    "documents.category.view": "View document categories",
    "documents.category.manage": "Manage document categories",
    "audit.event.view": "View activity history",
    "audit.event.export": "Export activity history",
    "approvals.workflow.view": "View approval workflows",
    "approvals.workflow.manage": "Manage approval workflows",
    "approvals.request.view": "View approval requests",
    "approvals.request.submit": "Submit approval requests",
    "approvals.request.approve": "Approve assigned requests",
    "approvals.request.reject": "Reject assigned requests",
    "approvals.request.return": "Return assigned requests for changes",
    "approvals.request.cancel": "Cancel approval requests",
    "notifications.notification.view": "View own notifications",
    "notifications.notification.manage_preferences": "Manage notification preferences",
}


def seed_permissions(apps, schema_editor):
    permission = apps.get_model("rbac", "Permission")
    for code, name in PERMISSIONS.items():
        permission.objects.update_or_create(code=code, defaults={"name": name, "is_active": True})


def remove_permissions(apps, schema_editor):
    apps.get_model("rbac", "Permission").objects.filter(code__in=PERMISSIONS).delete()


class Migration(migrations.Migration):
    dependencies = [("rbac", "0002_foundation_permissions")]
    operations = [migrations.RunPython(seed_permissions, remove_permissions)]
