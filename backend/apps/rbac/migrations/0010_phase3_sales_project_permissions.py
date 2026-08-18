from django.db import migrations

PERMISSIONS = {
    "sales.customer_po.view": "View Customer POs",
    "sales.customer_po.create": "Record Customer POs",
    "sales.customer_po.edit_draft": "Edit draft Customer POs",
    "sales.customer_po.revise": "Create Customer PO revisions",
    "sales.customer_po.link_to_order": "Link Customer POs to Sales Orders",
    "sales.customer_po.review_variance": "Review Customer PO differences",
    "sales.customer_po.accept_variance": "Accept Customer PO differences",
    "sales.sales_order.view": "View Sales Orders",
    "sales.sales_order.view_internal_notes": "View confidential Sales Order notes",
    "sales.sales_order.create": "Create Sales Orders from quotations",
    "sales.sales_order.direct_create": "Create Direct Sales Orders",
    "sales.sales_order.edit": "Edit draft Sales Orders",
    "sales.sales_order.submit": "Submit Sales Orders",
    "sales.sales_order.approve": "Approve Sales Orders",
    "sales.sales_order.return": "Return Sales Orders for changes",
    "sales.sales_order.release": "Release Sales Orders",
    "sales.sales_order.revise": "Create Sales Order amendments",
    "sales.sales_order.hold": "Put Sales Orders on hold",
    "sales.sales_order.resume": "Resume Sales Orders",
    "sales.sales_order.cancel": "Cancel Sales Orders",
    "projects.project.view": "View Projects",
    "projects.project.create": "Create Projects",
    "projects.project.edit": "Edit Project details",
    "projects.project.assign": "Assign Project ownership",
    "projects.project.hold": "Put Projects on hold",
    "projects.project.cancel": "Cancel Projects",
    "projects.handoff.view": "View Engineering handoffs",
    "projects.handoff.prepare": "Prepare Engineering handoffs",
    "projects.handoff.submit": "Send Projects to Engineering",
    "projects.handoff.take_ownership": "Take Engineering handoff ownership",
    "projects.handoff.assign": "Assign Engineering handoffs",
    "projects.handoff.request_clarification": "Request Project clarification",
    "projects.handoff.respond_clarification": "Respond to Project clarification",
    "projects.handoff.accept": "Accept Engineering handoffs",
    "projects.handoff.acknowledge_commercial_change": "Acknowledge Project commercial changes",
}


def seed_permissions(apps, schema_editor):
    permission = apps.get_model("rbac", "Permission")
    for code, name in PERMISSIONS.items():
        permission.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "description": "Phase 3 Sales Order and Project control",
                "is_active": True,
            },
        )


def remove_permissions(apps, schema_editor):
    apps.get_model("rbac", "Permission").objects.filter(code__in=PERMISSIONS).delete()


class Migration(migrations.Migration):
    dependencies = [("rbac", "0009_deactivate_legacy_quotation_permissions")]
    operations = [migrations.RunPython(seed_permissions, remove_permissions)]
