from django.db import migrations

PERMISSIONS = {
    "crm.customer.view": "View customers",
    "crm.customer.create": "Create customers",
    "crm.customer.edit": "Edit customers",
    "crm.customer.deactivate": "Deactivate customers",
    "crm.customer.block": "Block customers",
    "crm.customer.view_sensitive": "View sensitive customer data",
    "crm.contact.view": "View customer contacts",
    "crm.contact.create": "Create customer contacts",
    "crm.contact.edit": "Edit customer contacts",
    "crm.activity.view": "View CRM activities",
    "crm.activity.create": "Create CRM activities",
    "crm.activity.edit": "Edit CRM activities",
    "crm.activity.complete": "Complete CRM activities",
    "enquiry.enquiry.view": "View enquiries",
    "enquiry.enquiry.create": "Create enquiries",
    "enquiry.enquiry.edit": "Edit enquiries",
    "enquiry.enquiry.assign": "Assign enquiries",
    "enquiry.enquiry.submit_engineering": "Submit enquiries to engineering",
    "enquiry.enquiry.mark_won": "Mark enquiries won",
    "enquiry.enquiry.mark_lost": "Mark enquiries lost",
    "enquiry.enquiry.cancel": "Cancel enquiries",
    "engineering.feasibility.view": "View engineering feasibility reviews",
    "engineering.feasibility.assign": "Assign engineering feasibility reviews",
    "engineering.feasibility.review": "Review engineering feasibility",
    "engineering.feasibility.complete": "Complete engineering feasibility reviews",
    "engineering.feasibility.reopen": "Reopen engineering feasibility reviews",
    "estimation.estimate.view": "View estimates",
    "estimation.estimate.create": "Create estimates",
    "estimation.estimate.edit": "Edit estimates",
    "estimation.estimate.view_cost": "View estimate costs",
    "estimation.estimate.view_margin": "View estimate margins",
    "estimation.estimate.submit": "Submit estimates",
    "estimation.estimate.approve": "Approve estimates",
    "estimation.estimate.create_revision": "Create estimate revisions",
    "quotation.quotation.view": "View quotations",
    "quotation.quotation.create": "Create quotations",
    "quotation.quotation.edit": "Edit quotations",
    "quotation.quotation.submit": "Submit quotations",
    "quotation.quotation.approve": "Approve quotations",
    "quotation.quotation.send": "Send quotations",
    "quotation.quotation.create_revision": "Create quotation revisions",
    "quotation.quotation.accept": "Accept quotations",
    "quotation.quotation.reject": "Reject quotations",
    "quotation.quotation.cancel": "Cancel quotations",
    "quotation.quotation.view_internal": "View internal quotation information",
}


def seed_permissions(apps, schema_editor):
    Permission = apps.get_model("rbac", "Permission")
    for code, name in PERMISSIONS.items():
        Permission.objects.update_or_create(
            code=code,
            defaults={"name": name, "description": "Phase 2 Commercial CRM", "is_active": True},
        )


def remove_permissions(apps, schema_editor):
    apps.get_model("rbac", "Permission").objects.filter(code__in=PERMISSIONS).delete()


class Migration(migrations.Migration):
    dependencies = [("rbac", "0003_shared_service_permissions")]
    operations = [migrations.RunPython(seed_permissions, remove_permissions)]
