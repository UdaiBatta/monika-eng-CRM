from django.db import migrations

PERMISSIONS = {
    "crm.quotation.view": "View quotations",
    "crm.quotation.create": "Create standard quotations",
    "crm.quotation.quick_create": "Create quick quotations",
    "crm.quotation.change": "Edit and revise quotations",
    "crm.quotation.finalize": "Finalize quotations",
    "crm.quotation.send": "Record quotation communication",
    "crm.quotation.negotiate": "Record quotation negotiations",
    "crm.quotation.confirm": "Record customer commercial confirmation",
    "crm.quotation.ready_for_sales_order": "Mark quotation Ready for Sales Order",
    "crm.quotation.generate_document": "Generate quotation Word and PDF documents",
    "crm.quotation.template_manage": "Manage quotation templates",
}


def seed_permissions(apps, _schema_editor):
    Permission = apps.get_model("rbac", "Permission")
    for code, name in PERMISSIONS.items():
        Permission.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "description": "Phase 2 quotation and negotiation",
                "is_active": True,
            },
        )
    incoming_names = {
        "crm.external_enquiry.view": "View incoming enquiries",
        "crm.external_enquiry.review": "Review incoming enquiries",
        "crm.external_enquiry.assign": "Assign incoming enquiries",
        "crm.external_enquiry.convert": "Convert incoming enquiries",
        "crm.external_enquiry.reject": "Reject incoming enquiries",
        "crm.external_enquiry.mark_spam": "Mark incoming enquiries as spam",
        "crm.external_enquiry.view_source_metadata": "View incoming enquiry source metadata",
    }
    for code, name in incoming_names.items():
        Permission.objects.filter(code=code).update(name=name)


def remove_permissions(apps, _schema_editor):
    apps.get_model("rbac", "Permission").objects.filter(code__in=PERMISSIONS).delete()


class Migration(migrations.Migration):
    dependencies = [("rbac", "0007_estimation_permissions")]
    operations = [migrations.RunPython(seed_permissions, remove_permissions)]
