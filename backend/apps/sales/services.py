from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.approvals.conditions import conditions_match
from apps.approvals.models import ApprovalRequest, ApprovalWorkflow, ApprovalWorkflowVersion
from apps.approvals.services import create_approval_request
from apps.core.conflicts import VersionConflict
from apps.core.domain_events import DomainEvent, publish
from apps.crm.models import Customer, CustomerContact, CustomerSite
from apps.documents.models import Document
from apps.enquiries.models import Enquiry
from apps.masters.models import Currency
from apps.numbering.services import allocate_company_number, financial_year_label
from apps.organization.models import Employee
from apps.quotations.models import Quotation
from apps.rbac.services import has_permission

from .models import (
    CustomerPurchaseOrder,
    CustomerPurchaseOrderRevision,
    SalesOrder,
    SalesOrderLine,
    SalesOrderRevision,
)

EDITABLE_REVISION_FIELDS = {
    "customer_reference",
    "order_date",
    "requested_delivery",
    "promised_delivery",
    "payment_terms",
    "delivery_terms",
    "warranty_terms",
    "freight_terms",
    "installation_terms",
    "scope",
    "exclusions",
    "customer_notes",
    "internal_notes",
}


def _employee(user):
    return Employee.objects.filter(user=user, user__is_active=True).first()


def _require(user, permission, context, message="sales action"):
    if not has_permission(user, permission, context):
        raise PermissionDenied(f"You do not have permission to complete this {message}.")


def _event(name, entity, actor, action, summary, *, metadata=None, changes=None):
    employee = _employee(actor)
    entity_type = "customer_purchase_order" if isinstance(entity, CustomerPurchaseOrder) else "sales_order"
    reference = entity.po_number if isinstance(entity, CustomerPurchaseOrder) else entity.sales_order_number
    return DomainEvent(
        event_name=name,
        entity_type=entity_type,
        entity_id=entity.pk,
        company_id=entity.company_id,
        actor_user_id=actor.pk,
        actor_employee_id=employee.pk if employee else None,
        action=action,
        module="sales",
        summary=summary,
        metadata={"entity_reference": reference, "customer_id": str(entity.customer_id), **(metadata or {})},
        changes=changes or {},
    )


def _document(document_id, company_id):
    if not document_id:
        return None
    document = Document.objects.filter(pk=document_id, company_id=company_id).first()
    if not document:
        raise ValidationError({"supporting_document_id": ["Choose a document from this company."]})
    return document


def _po_revision_values(data, *, fallback=None):
    source = fallback
    return {
        "customer_revision_reference": data.get(
            "customer_revision_reference", getattr(source, "customer_revision_reference", "")
        ),
        "po_date": data.get("po_date", getattr(source, "po_date", timezone.localdate())),
        "received_date": data.get("received_date", getattr(source, "received_date", timezone.localdate())),
        "currency": data.get("currency", getattr(source, "currency", None)),
        "stated_total": data.get("stated_total", getattr(source, "stated_total", None)),
        "tax_information": data.get("tax_information", getattr(source, "tax_information", {})),
        "line_snapshot": data.get("line_snapshot", getattr(source, "line_snapshot", [])),
        "delivery_information": data.get("delivery_information", getattr(source, "delivery_information", "")),
        "payment_terms": data.get("payment_terms", getattr(source, "payment_terms", "")),
        "warranty_terms": data.get("warranty_terms", getattr(source, "warranty_terms", "")),
        "customer_reference": data.get("customer_reference", getattr(source, "customer_reference", "")),
        "notes": data.get("notes", getattr(source, "notes", "")),
        "supporting_document": data.get("supporting_document", getattr(source, "supporting_document", None)),
    }


def compare_po_to_quotation(po_revision):
    po = po_revision.customer_purchase_order
    quotation = po.quotation
    differences = []
    if not quotation or not quotation.current_revision_id:
        return differences
    quote_revision = quotation.current_revision

    def add(field, label, quotation_value, po_value):
        left = "" if quotation_value is None else str(quotation_value).strip()
        right = "" if po_value is None else str(po_value).strip()
        if right and left != right:
            differences.append({"field": field, "label": label, "quotation": left, "customer_po": right})

    add("customer", "Customer", quotation.customer.legal_name, po.customer.legal_name)
    add("currency", "Currency", quote_revision.currency.code, po_revision.currency.code)
    add("order_value", "Order Value", quote_revision.grand_total, po_revision.stated_total)
    add("delivery", "Delivery", quote_revision.delivery_terms, po_revision.delivery_information)
    add("payment_terms", "Payment Terms", quote_revision.payment_terms, po_revision.payment_terms)
    add("warranty", "Warranty", quote_revision.warranty_terms, po_revision.warranty_terms)
    if po_revision.line_snapshot:
        quoted_lines = [
            {
                "description": line.description,
                "quantity": str(line.quantity),
                "unit_price": str(line.unit_price),
            }
            for line in quote_revision.lines.all()
        ]
        if quoted_lines != po_revision.line_snapshot:
            differences.append(
                {
                    "field": "items",
                    "label": "Ordered Items",
                    "quotation": quoted_lines,
                    "customer_po": po_revision.line_snapshot,
                }
            )
    return differences


def _review_po_locked(po, actor):
    revision = po.current_revision
    if not revision:
        raise ValidationError("This Customer PO does not have a current revision.")
    differences = compare_po_to_quotation(revision)
    revision.variance_snapshot = differences
    revision.match_status = (
        CustomerPurchaseOrderRevision.MatchStatus.DIFFERENCES
        if differences
        else CustomerPurchaseOrderRevision.MatchStatus.MATCHES
    )
    revision.record_version += 1
    revision.save(update_fields=["variance_snapshot", "match_status", "record_version", "updated_at"])
    po.status = (
        CustomerPurchaseOrder.Status.DIFFERENCE_REVIEW if differences else CustomerPurchaseOrder.Status.ACTIVE
    )
    po.save(update_fields=["status", "updated_at"])
    publish(
        _event(
            "customer_po.variance_detected" if differences else "customer_po.reviewed",
            po,
            actor,
            "REVIEW",
            f"Customer PO compared with quotation: {revision.get_match_status_display()}",
            metadata={"status": po.status},
        )
    )
    return revision


def record_customer_po(*, actor, data):
    employee = _employee(actor)
    if not employee:
        raise PermissionDenied("Your account is not linked to an active employee.")
    _require(actor, "sales.customer_po.create", {"company": employee.company_id}, "Customer PO action")
    customer = Customer.objects.filter(pk=data["customer_id"], company_id=employee.company_id).first()
    if not customer:
        raise ValidationError({"customer_id": ["Choose a customer from your company."]})
    po_number = data["po_number"].strip()
    quotation = None
    if data.get("quotation_id"):
        quotation = Quotation.objects.filter(
            pk=data["quotation_id"], company_id=employee.company_id, customer=customer
        ).first()
        if not quotation:
            raise ValidationError({"quotation_id": ["Choose a quotation for this customer."]})
    confirmation = getattr(quotation, "commercial_confirmation", None) if quotation else None
    allowed_currency_ids = {customer.default_currency_id}
    if quotation and quotation.current_revision_id:
        allowed_currency_ids.add(quotation.current_revision.currency_id)
    currency = Currency.objects.filter(
        pk=data.get("currency_id") or customer.default_currency_id,
        pk__in=allowed_currency_ids,
        is_active=True,
    ).first()
    if not currency:
        raise ValidationError({"currency_id": ["Choose a currency from this company."]})
    document = _document(data.get("supporting_document_id"), employee.company_id)
    with transaction.atomic():
        existing = (
            CustomerPurchaseOrder.objects.select_for_update(of=("self",))
            .filter(company_id=employee.company_id, customer=customer, po_number__iexact=po_number)
            .first()
        )
        if existing:
            raise ValidationError(
                {
                    "po_number": [
                        f"A Customer PO with this number already exists for {customer.legal_name}."
                    ],
                    "existing_id": str(existing.pk),
                },
                code="CUSTOMER_PO_DUPLICATE",
            )
        po = CustomerPurchaseOrder.objects.create(
            company_id=employee.company_id,
            customer=customer,
            po_number=po_number,
            quotation=quotation,
            confirmation=confirmation,
            responsible_employee_id=data.get("responsible_employee_id") or employee.pk,
            created_by=actor,
        )
        revision = CustomerPurchaseOrderRevision.objects.create(
            customer_purchase_order=po,
            revision_number=1,
            customer_revision_reference=data.get("customer_revision_reference", ""),
            po_date=data["po_date"],
            received_date=data.get("received_date") or timezone.localdate(),
            currency=currency,
            stated_total=data.get("stated_total"),
            tax_information=data.get("tax_information", {}),
            line_snapshot=data.get("line_snapshot", []),
            delivery_information=data.get("delivery_information", ""),
            payment_terms=data.get("payment_terms", ""),
            warranty_terms=data.get("warranty_terms", ""),
            customer_reference=data.get("customer_reference", ""),
            notes=data.get("notes", ""),
            supporting_document=document,
            created_by=actor,
        )
        po.current_revision = revision
        po.save(update_fields=["current_revision", "updated_at"])
        publish(
            _event(
                "customer_po.created",
                po,
                actor,
                "CREATE",
                f"Customer PO {po.po_number} recorded",
                metadata={"status": po.status, "quotation_id": str(po.quotation_id or "")},
            )
        )
        if quotation:
            _review_po_locked(po, actor)
        return po


def create_customer_po_revision(*, po_id, actor, data):
    with transaction.atomic():
        po = (
            CustomerPurchaseOrder.objects.select_for_update(of=("self",))
            .select_related("current_revision__currency", "current_revision__supporting_document")
            .get(pk=po_id)
        )
        _require(actor, "sales.customer_po.revise", po, "Customer PO revision")
        previous = po.current_revision
        if not previous:
            raise ValidationError("This Customer PO does not have a current revision.")
        document = (
            _document(data.get("supporting_document_id"), po.company_id)
            if "supporting_document_id" in data
            else previous.supporting_document
        )
        currency = (
            Currency.objects.filter(
                pk=data["currency_id"],
                pk__in={
                    po.customer.default_currency_id,
                    po.quotation.current_revision.currency_id
                    if po.quotation_id and po.quotation.current_revision_id
                    else None,
                },
                is_active=True,
            ).first()
            if data.get("currency_id")
            else previous.currency
        )
        if not currency:
            raise ValidationError({"currency_id": ["Choose a currency from this company."]})
        values = _po_revision_values(
            {**data, "currency": currency, "supporting_document": document}, fallback=previous
        )
        revision = CustomerPurchaseOrderRevision.objects.create(
            customer_purchase_order=po,
            revision_number=previous.revision_number + 1,
            supersedes=previous,
            created_by=actor,
            **values,
        )
        po.current_revision = revision
        po.status = CustomerPurchaseOrder.Status.ACTIVE
        po.save(update_fields=["current_revision", "status", "updated_at"])
        publish(
            _event(
                "customer_po.updated",
                po,
                actor,
                "VERSION_CREATE",
                f"Customer PO revision {revision.revision_number} recorded",
            )
        )
        if po.quotation_id:
            _review_po_locked(po, actor)
        return revision


def review_po_variance(*, po_id, actor):
    with transaction.atomic():
        po = (
            CustomerPurchaseOrder.objects.select_for_update(of=("self",))
            .select_related(
                "customer",
                "current_revision__currency",
                "quotation__customer",
                "quotation__current_revision__currency",
            )
            .prefetch_related("quotation__current_revision__lines")
            .get(pk=po_id)
        )
        _require(actor, "sales.customer_po.review_variance", po, "PO variance review")
        if not po.quotation_id:
            raise ValidationError("Link an accepted quotation before comparing this Customer PO.")
        return _review_po_locked(po, actor)


def accept_po_variance(*, po_id, actor, reason):
    if not reason.strip():
        raise ValidationError({"reason": ["Explain why the differences are acceptable."]})
    with transaction.atomic():
        po = (
            CustomerPurchaseOrder.objects.select_for_update(of=("self",))
            .select_related("current_revision")
            .get(pk=po_id)
        )
        _require(actor, "sales.customer_po.accept_variance", po, "PO variance acceptance")
        revision = po.current_revision
        if not revision or revision.match_status != CustomerPurchaseOrderRevision.MatchStatus.DIFFERENCES:
            raise ValidationError("This Customer PO does not have unresolved differences.")
        revision.match_status = CustomerPurchaseOrderRevision.MatchStatus.ACCEPTED_DIFFERENCES
        revision.notes = f"{revision.notes}\nVariance accepted: {reason.strip()}".strip()
        revision.record_version += 1
        revision.save(update_fields=["match_status", "notes", "record_version", "updated_at"])
        po.status = CustomerPurchaseOrder.Status.ACCEPTED_WITH_DIFFERENCES
        po.save(update_fields=["status", "updated_at"])
        publish(
            _event(
                "customer_po.variance_accepted",
                po,
                actor,
                "APPROVE",
                f"Customer PO differences accepted: {reason.strip()}",
                metadata={"status": po.status},
            )
        )
        return revision


def _line_values(line, number):
    return {
        "line_number": number,
        "quotation_line_id": line.get("quotation_line_id"),
        "customer_po_line_reference": line.get("customer_po_line_reference", ""),
        "description": line["description"],
        "long_description": line.get("long_description", ""),
        "customer_item_reference": line.get("customer_item_reference", ""),
        "quantity": Decimal(str(line["quantity"])),
        "unit_of_measure": line.get("unit_of_measure", "NOS"),
        "unit_price": Decimal(str(line["unit_price"])),
        "discount_percent": Decimal(str(line.get("discount_percent", "0"))),
        "tax_percent": Decimal(str(line.get("tax_percent", "0"))),
        "requested_delivery_date": line.get("requested_delivery_date"),
        "promised_delivery_date": line.get("promised_delivery_date"),
        "delivery_text": line.get("delivery_text", ""),
        "customer_visible_note": line.get("customer_visible_note", ""),
        "internal_note": line.get("internal_note", ""),
        "project_scope_category": line.get("project_scope_category", ""),
    }


def _replace_lines(revision, lines):
    if not lines:
        raise ValidationError({"lines": ["Add at least one ordered item."]})
    revision.lines.all().delete()
    for number, line in enumerate(lines, 1):
        SalesOrderLine.objects.create(revision=revision, **_line_values(line, number))
    _recalculate(revision)


def _recalculate(revision):
    totals = revision.lines.aggregate(
        subtotal=Sum("line_subtotal"),
        discount=Sum("discount_amount"),
        taxable=Sum("taxable_amount"),
        tax=Sum("tax_amount"),
        total=Sum("total_amount"),
    )
    revision.subtotal = totals["subtotal"] or Decimal("0")
    revision.discount_amount = totals["discount"] or Decimal("0")
    revision.taxable_amount = totals["taxable"] or Decimal("0")
    revision.tax_amount = totals["tax"] or Decimal("0")
    revision.grand_total = totals["total"] or Decimal("0")
    revision.save(
        update_fields=[
            "subtotal",
            "discount_amount",
            "taxable_amount",
            "tax_amount",
            "grand_total",
            "updated_at",
        ]
    )


def _quotation_snapshot(quotation, revision, confirmation):
    return {
        "quotation_id": str(quotation.pk),
        "quotation_number": quotation.quotation_number,
        "quotation_revision_id": str(revision.pk),
        "quotation_revision": revision.revision_number,
        "customer_confirmation": {
            "method": confirmation.method,
            "confirmed_at": confirmation.confirmed_at.isoformat(),
            "reference": confirmation.confirmation_reference,
            "po_pending": confirmation.po_pending,
        },
    }


def _po_snapshot(po):
    if not po or not po.current_revision_id:
        return {}
    revision = po.current_revision
    return {
        "customer_po_id": str(po.pk),
        "po_number": po.po_number,
        "revision_id": str(revision.pk),
        "revision": revision.revision_number,
        "po_date": revision.po_date.isoformat(),
        "stated_total": str(revision.stated_total) if revision.stated_total is not None else None,
        "match_status": revision.match_status,
    }


def _find_customer_po(quotation):
    return (
        quotation.customer_purchase_orders.select_related("current_revision").order_by("-updated_at").first()
    )


def create_sales_order_from_quotation(*, quotation_id, actor, data):
    employee = _employee(actor)
    if not employee:
        raise PermissionDenied("Your account is not linked to an active employee.")
    with transaction.atomic():
        quotation = (
            Quotation.objects.select_for_update(of=("self",))
            .select_related(
                "company",
                "customer",
                "customer_contact",
                "enquiry",
                "current_revision__currency",
                "commercial_confirmation",
            )
            .prefetch_related("current_revision__lines", "customer_purchase_orders__current_revision")
            .get(pk=quotation_id)
        )
        _require(actor, "sales.sales_order.create", quotation, "Sales Order creation")
        existing = SalesOrder.objects.filter(accepted_quotation=quotation).first()
        if existing:
            return existing
        if quotation.status != Quotation.Status.READY_FOR_SALES_ORDER:
            raise ValidationError("Mark the accepted quotation Ready for Sales Order first.")
        confirmation = quotation.commercial_confirmation
        if confirmation.revision_id != quotation.current_revision_id:
            raise ValidationError("Customer confirmation must refer to the current quotation revision.")
        quote_revision = quotation.current_revision
        po = _find_customer_po(quotation)
        number = allocate_company_number(company=quotation.company, code="SO")
        order = SalesOrder.objects.create(
            company=quotation.company,
            financial_year=financial_year_label(quotation.company),
            sales_order_number=number,
            customer=quotation.customer,
            contact=quotation.customer_contact,
            site_id=data.get("site_id"),
            enquiry=quotation.enquiry,
            accepted_quotation=quotation,
            customer_confirmation=confirmation,
            customer_purchase_order=po,
            order_mode=SalesOrder.Mode.QUOTATION_BASED,
            responsible_sales_employee_id=data.get("responsible_sales_employee_id") or quotation.owner_id,
            project_required=data.get("project_required", True),
            po_pending=not bool(po) or confirmation.po_pending,
            status=SalesOrder.Status.DRAFT,
            created_by=actor,
        )
        revision = SalesOrderRevision.objects.create(
            sales_order=order,
            revision_number=0,
            source_quotation_revision=quote_revision,
            source_customer_po_revision=po.current_revision if po else None,
            customer_reference=confirmation.confirmation_reference,
            currency=quote_revision.currency,
            requested_delivery=data.get("requested_delivery"),
            promised_delivery=data.get("promised_delivery"),
            payment_terms=quote_revision.payment_terms,
            delivery_terms=quote_revision.delivery_terms,
            warranty_terms=quote_revision.warranty_terms,
            freight_terms=quote_revision.freight_terms,
            scope=quote_revision.scope,
            exclusions=quote_revision.exclusions,
            customer_notes=quote_revision.customer_notes,
            internal_notes=data.get("internal_notes", ""),
            commercial_snapshot=_quotation_snapshot(quotation, quote_revision, confirmation),
            po_snapshot=_po_snapshot(po),
            prepared_by=actor,
        )
        _replace_lines(
            revision,
            [
                {
                    "quotation_line_id": line.pk,
                    "description": line.description,
                    "quantity": line.quantity,
                    "unit_of_measure": line.unit_of_measure,
                    "unit_price": line.unit_price,
                    "discount_percent": line.discount_percent,
                    "tax_percent": line.tax_percent,
                    "customer_visible_note": line.notes,
                }
                for line in quote_revision.lines.all()
                if not line.is_optional
            ],
        )
        order.current_revision = revision
        order.save(update_fields=["current_revision", "updated_at"])
        publish(
            _event(
                "sales_order.created",
                order,
                actor,
                "CREATE",
                f"Sales Order {order.sales_order_number} created from {quotation.quotation_number}",
                metadata={"status": order.status, "quotation_id": str(quotation.pk)},
            )
        )
        return order


def _direct_enquiry(*, actor, employee, customer, contact, site, data):
    if data.get("enquiry_id"):
        enquiry = Enquiry.objects.filter(
            pk=data["enquiry_id"], company_id=employee.company_id, customer=customer
        ).first()
        if not enquiry:
            raise ValidationError({"enquiry_id": ["Choose an enquiry for this customer."]})
        return enquiry
    number = allocate_company_number(company=employee.company, code="ENQUIRY")
    return Enquiry.objects.create(
        company=employee.company,
        enquiry_number=number,
        customer=customer,
        customer_contact=contact,
        customer_site=site,
        source=data.get("confirmation_channel", "Direct Sales Order"),
        received_date=data.get("confirmation_date") or timezone.localdate(),
        subject=data.get("subject") or f"Direct order — {data['lines'][0]['description']}",
        description=data.get("requirement", ""),
        responsible_salesperson=employee,
        estimated_value=sum(
            Decimal(str(line["quantity"])) * Decimal(str(line["unit_price"])) for line in data["lines"]
        ),
        currency_id=data["currency_id"],
        status=Enquiry.Status.WON,
        closed_at=timezone.now(),
        closed_by=actor,
        created_by=actor,
        updated_by=actor,
    )


def create_direct_sales_order(*, actor, data):
    employee = _employee(actor)
    if not employee:
        raise PermissionDenied("Your account is not linked to an active employee.")
    _require(actor, "sales.sales_order.direct_create", {"company": employee.company_id}, "Direct Sales Order")
    if not data.get("direct_reason", "").strip():
        raise ValidationError({"direct_reason": ["Choose a business reason for this Direct Sales Order."]})
    if not data.get("confirmation_channel", "").strip():
        raise ValidationError({"confirmation_channel": ["Record how the customer confirmed the order."]})
    customer = Customer.objects.filter(pk=data["customer_id"], company_id=employee.company_id).first()
    if not customer:
        raise ValidationError({"customer_id": ["Choose a customer from your company."]})
    contact = CustomerContact.objects.filter(pk=data.get("contact_id"), customer=customer).first()
    site = CustomerSite.objects.filter(pk=data.get("site_id"), customer=customer).first()
    currency = Currency.objects.filter(pk=data["currency_id"], is_active=True).first()
    if currency and currency.pk != customer.default_currency_id:
        currency = None
    if not currency:
        raise ValidationError({"currency_id": ["Choose a currency from this company."]})
    with transaction.atomic():
        enquiry = _direct_enquiry(
            actor=actor, employee=employee, customer=customer, contact=contact, site=site, data=data
        )
        order = SalesOrder.objects.create(
            company=employee.company,
            financial_year=financial_year_label(employee.company),
            sales_order_number=allocate_company_number(company=employee.company, code="SO"),
            customer=customer,
            contact=contact,
            site=site,
            enquiry=enquiry,
            order_mode=SalesOrder.Mode.DIRECT,
            responsible_sales_employee=employee,
            project_required=data.get("project_required", True),
            po_pending=data.get("po_pending", True),
            direct_reason=data["direct_reason"].strip(),
            direct_reason_notes=data.get("direct_reason_notes", "").strip(),
            confirmation_channel=data["confirmation_channel"].strip(),
            confirmation_reference=data.get("confirmation_reference", "").strip(),
            confirmation_date=data.get("confirmation_date") or timezone.localdate(),
            created_by=actor,
        )
        revision = SalesOrderRevision.objects.create(
            sales_order=order,
            revision_number=0,
            currency=currency,
            requested_delivery=data.get("requested_delivery"),
            promised_delivery=data.get("promised_delivery"),
            payment_terms=data.get("payment_terms", ""),
            delivery_terms=data.get("delivery_terms", ""),
            warranty_terms=data.get("warranty_terms", ""),
            freight_terms=data.get("freight_terms", ""),
            installation_terms=data.get("installation_terms", ""),
            scope=data.get("scope", data.get("requirement", "")),
            exclusions=data.get("exclusions", ""),
            customer_notes=data.get("customer_notes", ""),
            internal_notes=data.get("internal_notes", ""),
            commercial_snapshot={
                "direct_reason": order.direct_reason,
                "direct_reason_notes": order.direct_reason_notes,
                "confirmation_channel": order.confirmation_channel,
                "confirmation_reference": order.confirmation_reference,
                "confirmation_date": order.confirmation_date.isoformat(),
                "enquiry_id": str(enquiry.pk),
            },
            prepared_by=actor,
        )
        _replace_lines(revision, data["lines"])
        order.current_revision = revision
        order.save(update_fields=["current_revision", "updated_at"])
        publish(
            _event(
                "sales_order.created",
                order,
                actor,
                "CREATE",
                f"Direct Sales Order {order.sales_order_number} created",
                metadata={"status": order.status, "order_mode": order.order_mode},
            )
        )
        return order


def update_sales_order_draft(*, revision_id, actor, submitted_version, data):
    with transaction.atomic():
        revision = (
            SalesOrderRevision.objects.select_for_update().select_related("sales_order").get(pk=revision_id)
        )
        order = revision.sales_order
        _require(actor, "sales.sales_order.edit", order, "Sales Order edit")
        if order.current_revision_id != revision.pk or revision.status not in {
            SalesOrderRevision.Status.DRAFT,
            SalesOrderRevision.Status.RETURNED,
        }:
            raise ValidationError("Only the current draft Sales Order revision can be edited.")
        if revision.record_version != submitted_version:
            raise VersionConflict(revision.record_version)
        for field in EDITABLE_REVISION_FIELDS:
            if field in data:
                setattr(revision, field, data[field])
        if data.get("currency_id"):
            currency = Currency.objects.filter(
                pk=data["currency_id"],
                pk__in={
                    order.customer.default_currency_id,
                    revision.source_quotation_revision.currency_id
                    if revision.source_quotation_revision_id
                    else None,
                    revision.source_customer_po_revision.currency_id
                    if revision.source_customer_po_revision_id
                    else None,
                },
                is_active=True,
            ).first()
            if not currency:
                raise ValidationError({"currency_id": ["Choose a currency from this company."]})
            revision.currency = currency
        revision.record_version += 1
        revision.save()
        if "lines" in data:
            _replace_lines(revision, data["lines"])
        publish(
            _event(
                "sales_order.updated",
                order,
                actor,
                "UPDATE",
                f"Draft {revision} updated",
                metadata={"status": order.status},
            )
        )
        return revision


def _matching_workflows(revision):
    workflows = ApprovalWorkflow.objects.select_related("current_version").filter(
        company=revision.sales_order.company,
        entity_type="sales_order_revision",
        is_active=True,
        current_version__status=ApprovalWorkflowVersion.Status.ACTIVE,
    )
    return [workflow for workflow in workflows if conditions_match(workflow.current_version, revision)]


def submit_sales_order(*, order_id, actor, comment=""):
    with transaction.atomic():
        order = (
            SalesOrder.objects.select_for_update(of=("self",))
            .select_related("current_revision")
            .get(pk=order_id)
        )
        _require(actor, "sales.sales_order.submit", order, "Sales Order submission")
        revision = order.current_revision
        if not revision or revision.status not in {
            SalesOrderRevision.Status.DRAFT,
            SalesOrderRevision.Status.RETURNED,
        }:
            raise ValidationError("Only the current draft Sales Order can be submitted.")
        _recalculate(revision)
        if not revision.lines.exists() or revision.grand_total < 0:
            raise ValidationError("Add at least one valid ordered item.")
        matches = _matching_workflows(revision)
        if len(matches) > 1:
            raise ValidationError("More than one approval workflow matches this Sales Order.")
        if matches:
            request = create_approval_request(
                workflow_id=matches[0].pk,
                entity_type="sales_order_revision",
                entity_id=revision.pk,
                actor=actor,
                submission_comment=comment,
                snapshot_metadata={
                    "sales_order_number": order.sales_order_number,
                    "revision": revision.revision_number,
                    "currency": revision.currency.code,
                    "grand_total": str(revision.grand_total),
                    "order_mode": order.order_mode,
                    "po_pending": order.po_pending,
                },
            )
            revision.approval_request = request
            revision.status = SalesOrderRevision.Status.PENDING_APPROVAL
            order.status = SalesOrder.Status.PENDING_APPROVAL
        else:
            revision.status = SalesOrderRevision.Status.APPROVED
            revision.approved_by = actor
            revision.approved_at = timezone.now()
            order.status = SalesOrder.Status.APPROVED
        revision.save()
        order.save(update_fields=["status", "updated_at"])
        publish(
            _event(
                "sales_order.submitted",
                order,
                actor,
                "SUBMIT",
                f"{order.sales_order_number} submitted",
                metadata={"status": order.status},
            )
        )
        return order


def release_sales_order(*, order_id, actor):
    with transaction.atomic():
        order = (
            SalesOrder.objects.select_for_update(of=("self",))
            .select_related("current_revision", "customer_purchase_order__current_revision")
            .get(pk=order_id)
        )
        _require(actor, "sales.sales_order.release", order, "Sales Order release")
        revision = order.current_revision
        if not revision or revision.status != SalesOrderRevision.Status.APPROVED:
            raise ValidationError("Approve the current Sales Order revision before release.")
        if order.customer_purchase_order_id:
            match_status = order.customer_purchase_order.current_revision.match_status
            if match_status == CustomerPurchaseOrderRevision.MatchStatus.DIFFERENCES:
                raise ValidationError("Resolve or accept the Customer PO differences before release.")
        elif not order.po_pending:
            raise ValidationError("Link the Customer PO or mark it pending before release.")
        if not revision.lines.exists():
            raise ValidationError("Add at least one ordered item before release.")
        now = timezone.now()
        revision.status = SalesOrderRevision.Status.RELEASED
        revision.released_by = actor
        revision.released_at = now
        revision.save(update_fields=["status", "released_by", "released_at", "updated_at"])
        order.status = SalesOrder.Status.RELEASED
        order.save(update_fields=["status", "updated_at"])
        publish(
            _event(
                "sales_order.released",
                order,
                actor,
                "RELEASE",
                f"{order.sales_order_number} released for execution",
                metadata={"status": order.status},
            )
        )
        if order.project_required:
            from apps.projects.services import create_project_from_sales_order

            create_project_from_sales_order(order_id=order.pk, actor=actor)
        return order


def create_sales_order_amendment(*, order_id, actor, reason):
    if not reason.strip():
        raise ValidationError({"reason": ["Explain why this order amendment is needed."]})
    with transaction.atomic():
        order = (
            SalesOrder.objects.select_for_update(of=("self",))
            .select_related("current_revision__currency")
            .prefetch_related("current_revision__lines")
            .get(pk=order_id)
        )
        _require(actor, "sales.sales_order.revise", order, "Sales Order amendment")
        previous = order.current_revision
        if not previous or previous.status != SalesOrderRevision.Status.RELEASED:
            raise ValidationError("Only the current released Sales Order can be amended.")
        revision = SalesOrderRevision.objects.create(
            sales_order=order,
            revision_number=previous.revision_number + 1,
            source_quotation_revision=previous.source_quotation_revision,
            source_customer_po_revision=(
                order.customer_purchase_order.current_revision
                if order.customer_purchase_order_id
                else previous.source_customer_po_revision
            ),
            customer_reference=previous.customer_reference,
            currency=previous.currency,
            order_date=previous.order_date,
            requested_delivery=previous.requested_delivery,
            promised_delivery=previous.promised_delivery,
            payment_terms=previous.payment_terms,
            delivery_terms=previous.delivery_terms,
            warranty_terms=previous.warranty_terms,
            freight_terms=previous.freight_terms,
            installation_terms=previous.installation_terms,
            scope=previous.scope,
            exclusions=previous.exclusions,
            customer_notes=previous.customer_notes,
            internal_notes=previous.internal_notes,
            commercial_snapshot=previous.commercial_snapshot,
            po_snapshot=_po_snapshot(order.customer_purchase_order),
            prepared_by=actor,
            revision_reason=reason.strip(),
            supersedes=previous,
        )
        for line in previous.lines.all():
            SalesOrderLine.objects.create(
                revision=revision,
                **{
                    field: getattr(line, field)
                    for field in (
                        "line_number",
                        "quotation_line_id",
                        "customer_po_line_reference",
                        "description",
                        "long_description",
                        "customer_item_reference",
                        "quantity",
                        "unit_of_measure",
                        "unit_price",
                        "discount_percent",
                        "tax_percent",
                        "requested_delivery_date",
                        "promised_delivery_date",
                        "delivery_text",
                        "customer_visible_note",
                        "internal_note",
                        "project_scope_category",
                    )
                },
            )
        _recalculate(revision)
        previous.status = SalesOrderRevision.Status.SUPERSEDED
        previous.save(update_fields=["status", "updated_at"])
        order.current_revision = revision
        order.status = SalesOrder.Status.DRAFT
        order.save(update_fields=["current_revision", "status", "updated_at"])
        publish(
            _event(
                "sales_order.revised",
                order,
                actor,
                "VERSION_CREATE",
                f"Amendment R{revision.revision_number} created: {reason.strip()}",
                metadata={"status": order.status},
            )
        )
        return revision


def compare_sales_order_revisions(order):
    revisions = list(order.revisions.prefetch_related("lines").order_by("revision_number"))
    comparisons = []
    for previous, current in zip(revisions, revisions[1:], strict=False):
        changes = []
        for field in EDITABLE_REVISION_FIELDS | {"grand_total"}:
            old, new = getattr(previous, field), getattr(current, field)
            if old != new:
                changes.append({"field": field, "from": str(old or ""), "to": str(new or "")})
        old_lines = {line.line_number: line for line in previous.lines.all()}
        new_lines = {line.line_number: line for line in current.lines.all()}
        for number in sorted(set(old_lines) | set(new_lines)):
            old, new = old_lines.get(number), new_lines.get(number)
            if (
                not old
                or not new
                or (old.description, old.quantity, old.unit_price)
                != (
                    new.description,
                    new.quantity,
                    new.unit_price,
                )
            ):
                changes.append(
                    {
                        "field": f"line_{number}",
                        "from": "" if not old else f"{old.description} · {old.quantity} × {old.unit_price}",
                        "to": "" if not new else f"{new.description} · {new.quantity} × {new.unit_price}",
                    }
                )
        comparisons.append(
            {
                "from_revision": previous.revision_number,
                "to_revision": current.revision_number,
                "changes": changes,
            }
        )
    return comparisons


def link_customer_po(*, order_id, po_id, actor):
    with transaction.atomic():
        order = (
            SalesOrder.objects.select_for_update(of=("self",))
            .select_related("current_revision")
            .get(pk=order_id)
        )
        _require(actor, "sales.customer_po.link_to_order", order, "Customer PO link")
        po = (
            CustomerPurchaseOrder.objects.select_related("current_revision")
            .filter(pk=po_id, company_id=order.company_id, customer_id=order.customer_id)
            .first()
        )
        if not po:
            raise ValidationError({"customer_po_id": ["Choose a Customer PO for this customer."]})
        order.customer_purchase_order = po
        order.po_pending = False
        order.save(update_fields=["customer_purchase_order", "po_pending", "updated_at"])
        revision = order.current_revision
        if revision and revision.status in {
            SalesOrderRevision.Status.DRAFT,
            SalesOrderRevision.Status.RETURNED,
        }:
            revision.source_customer_po_revision = po.current_revision
            revision.po_snapshot = _po_snapshot(po)
            revision.record_version += 1
            revision.save(
                update_fields=["source_customer_po_revision", "po_snapshot", "record_version", "updated_at"]
            )
        publish(
            _event(
                "sales_order.customer_po_linked",
                order,
                actor,
                "ASSIGN",
                f"Customer PO {po.po_number} linked to {order.sales_order_number}",
                metadata={"status": order.status},
            )
        )
        return order


def hold_sales_order(*, order_id, actor, reason):
    if not reason.strip():
        raise ValidationError({"reason": ["Explain why the Sales Order is being put on hold."]})
    with transaction.atomic():
        order = SalesOrder.objects.select_for_update().get(pk=order_id)
        _require(actor, "sales.sales_order.hold", order, "Sales Order hold")
        if order.status not in {SalesOrder.Status.APPROVED, SalesOrder.Status.RELEASED}:
            raise ValidationError("Only an approved or released Sales Order can be put on hold.")
        old = order.status
        order.status = SalesOrder.Status.ON_HOLD
        order.save(update_fields=["status", "updated_at"])
        publish(
            _event(
                "sales_order.held",
                order,
                actor,
                "HOLD",
                reason.strip(),
                changes={"status": {"old": old, "new": order.status}},
            )
        )
        return order


def resume_sales_order(*, order_id, actor):
    with transaction.atomic():
        order = (
            SalesOrder.objects.select_for_update(of=("self",))
            .select_related("current_revision")
            .get(pk=order_id)
        )
        _require(actor, "sales.sales_order.resume", order, "Sales Order resume")
        if order.status != SalesOrder.Status.ON_HOLD:
            raise ValidationError("This Sales Order is not on hold.")
        order.status = (
            SalesOrder.Status.RELEASED
            if order.current_revision.status == SalesOrderRevision.Status.RELEASED
            else SalesOrder.Status.APPROVED
        )
        order.save(update_fields=["status", "updated_at"])
        publish(_event("sales_order.resumed", order, actor, "RESUME", f"{order.sales_order_number} resumed"))
        return order


def cancel_sales_order(*, order_id, actor, reason):
    if not reason.strip():
        raise ValidationError({"reason": ["Explain why the Sales Order is being cancelled."]})
    with transaction.atomic():
        order = SalesOrder.objects.select_for_update().get(pk=order_id)
        _require(actor, "sales.sales_order.cancel", order, "Sales Order cancellation")
        if order.status == SalesOrder.Status.CANCELLED:
            return order
        order.status = SalesOrder.Status.CANCELLED
        order.save(update_fields=["status", "updated_at"])
        publish(_event("sales_order.cancelled", order, actor, "CANCEL", reason.strip()))
        return order


def sync_sales_order_approval(event):
    if event.entity_type != "approval_request" or event.event_name not in {
        "approval.request_approved",
        "approval.request_rejected",
        "approval.request_returned",
    }:
        return
    approval = ApprovalRequest.objects.filter(pk=event.entity_id, entity_type="sales_order_revision").first()
    if not approval:
        return
    revision = SalesOrderRevision.objects.select_related("sales_order").filter(pk=approval.entity_id).first()
    if not revision:
        return
    if approval.status == ApprovalRequest.Status.APPROVED:
        revision.status = SalesOrderRevision.Status.APPROVED
        revision.approved_by_id = event.actor_user_id
        revision.approved_at = timezone.now()
        revision.sales_order.status = SalesOrder.Status.APPROVED
    elif approval.status == ApprovalRequest.Status.RETURNED_FOR_CHANGES:
        revision.status = SalesOrderRevision.Status.RETURNED
        revision.sales_order.status = SalesOrder.Status.DRAFT
    elif approval.status == ApprovalRequest.Status.REJECTED:
        revision.status = SalesOrderRevision.Status.CANCELLED
        revision.sales_order.status = SalesOrder.Status.CANCELLED
    revision.save()
    revision.sales_order.save(update_fields=["status", "updated_at"])
