import uuid
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache
from django.db import connection, models, transaction
from django.db.models.functions import Lower
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.approvals.models import ApprovalRequest
from apps.audit.models import AuditEvent
from apps.configuration.features import feature_controls, set_feature
from apps.core.domain_events import DomainEvent, publish
from apps.crm.models import Customer
from apps.documents.storage import get_storage
from apps.engineering_reviews.models import EngineeringFeasibilityReview
from apps.enquiries.models import Enquiry
from apps.external_enquiries.models import ExternalEnquirySubmission, IntegrationCredential
from apps.organization.models import Company, Employee
from apps.projects.models import Project, ProjectEngineeringHandoff
from apps.purchasing.models import PurchaseOrder
from apps.quotations.models import Quotation
from apps.rbac.models import Role
from apps.sales.models import CustomerPurchaseOrder, SalesOrder
from apps.service.models import ServiceTicket
from apps.workshop.models import PanelJob


@dataclass(frozen=True)
class WorkSpec:
    key: str
    label: str
    model: type[models.Model]
    owner_field: str
    reference_field: str
    title_field: str
    status_field: str
    closed_statuses: tuple[str, ...]
    action_url: str

    def open(self, company):
        return self.model.objects.filter(company=company).exclude(
            **{f"{self.status_field}__in": self.closed_statuses}
        )


WORK_SPECS = (
    WorkSpec(
        "incoming_enquiry",
        "Incoming enquiry",
        ExternalEnquirySubmission,
        "assigned_to",
        "external_submission_id",
        "subject",
        "review_status",
        ("CONVERTED", "REJECTED", "SPAM"),
        "/app/crm/incoming-enquiries",
    ),
    WorkSpec(
        "enquiry",
        "Enquiry",
        Enquiry,
        "responsible_salesperson",
        "enquiry_number",
        "subject",
        "status",
        ("WON", "LOST", "CANCELLED"),
        "/app/crm/enquiries",
    ),
    WorkSpec(
        "engineering_review",
        "Workshop Review",
        EngineeringFeasibilityReview,
        "assigned_engineer",
        "id",
        "enquiry__subject",
        "status",
        ("FEASIBLE", "NOT_FEASIBLE", "CANCELLED", "SUPERSEDED"),
        "/app/crm/engineering",
    ),
    WorkSpec(
        "quotation",
        "Quotation",
        Quotation,
        "owner",
        "quotation_number",
        "customer__legal_name",
        "status",
        ("REJECTED", "EXPIRED", "CANCELLED", "READY_FOR_SALES_ORDER"),
        "/app/crm/quotations",
    ),
    WorkSpec(
        "customer_po",
        "Customer PO",
        CustomerPurchaseOrder,
        "responsible_employee",
        "po_number",
        "customer__legal_name",
        "status",
        ("SUPERSEDED", "CANCELLED"),
        "/app/sales/customer-pos",
    ),
    WorkSpec(
        "sales_order",
        "Sales order",
        SalesOrder,
        "responsible_sales_employee",
        "sales_order_number",
        "customer__legal_name",
        "status",
        ("CANCELLED", "SUPERSEDED"),
        "/app/sales/orders",
    ),
    WorkSpec(
        "project_engineering",
        "Project Workshop work",
        Project,
        "engineering_owner",
        "project_number",
        "project_name",
        "status",
        ("ENGINEERING_ACCEPTED", "CANCELLED"),
        "/app/projects",
    ),
    WorkSpec(
        "panel_job",
        "Panel Job",
        PanelJob,
        "workshop_owner",
        "panel_job_number",
        "panel_name",
        "status",
        ("CLOSED", "CANCELLED"),
        "/app/projects",
    ),
    WorkSpec(
        "service_ticket",
        "Service Ticket",
        ServiceTicket,
        "technician",
        "ticket_number",
        "complaint",
        "status",
        ("CLOSED", "CANCELLED"),
        "/app/service/tickets",
    ),
)

WORK_BY_KEY = {spec.key: spec for spec in WORK_SPECS}


def resolve_owner_company(user, requested_id=None):
    employee = getattr(user, "employee", None)
    if employee:
        if requested_id and str(employee.company_id) != str(requested_id) and not user.is_superuser:
            raise ValidationError("You can only administer your own company.")
        return employee.company
    if not user.is_superuser:
        raise ValidationError("Your account is not linked to a company employee record.")
    queryset = Company.objects.filter(is_active=True)
    if requested_id:
        queryset = queryset.filter(pk=requested_id)
    company = queryset.order_by("name").first()
    if not company:
        raise ValidationError("Choose an active company.")
    return company


def _related_fields(spec):
    fields = [spec.owner_field]
    if "__" in spec.title_field:
        fields.append(spec.title_field.rsplit("__", 1)[0])
    return fields


def _work_item(spec, record):
    owner = getattr(record, spec.owner_field)
    title = record
    for part in spec.title_field.split("__"):
        title = getattr(title, part)
    reference = getattr(record, spec.reference_field)
    if spec.key == "engineering_review":
        reference = record.enquiry.enquiry_number
    status = getattr(record, spec.status_field)
    status_display = getattr(record, f"get_{spec.status_field}_display")()
    return {
        "work_type": spec.key,
        "work_type_label": spec.label,
        "id": str(record.pk),
        "reference": str(reference),
        "title": str(title),
        "status": status_display,
        "status_code": status,
        "assigned_to": str(owner.pk) if owner else None,
        "assigned_to_name": owner.display_name if owner else "Unassigned",
        "updated_at": record.updated_at,
        "action_url": (
            spec.action_url
            if spec.key == "customer_po"
            else f"{spec.action_url}/{record.pk}"
        ),
    }


def work_items(company, *, work_type="", employee_id=None, queue=""):
    specs = [WORK_BY_KEY[work_type]] if work_type in WORK_BY_KEY else WORK_SPECS
    results = []
    for spec in specs:
        queryset = spec.open(company).select_related(*_related_fields(spec))
        if employee_id:
            queryset = queryset.filter(**{f"{spec.owner_field}_id": employee_id})
        if queue == "unassigned":
            queryset = queryset.filter(**{f"{spec.owner_field}__isnull": True})
        if queue == "inactive":
            queryset = queryset.exclude(
                **{
                    f"{spec.owner_field}__employment_status": Employee.EmploymentStatus.ACTIVE,
                    f"{spec.owner_field}__user__is_active": True,
                }
            ).exclude(**{f"{spec.owner_field}__isnull": True})
        for record in queryset.order_by("-updated_at")[:100]:
            results.append(_work_item(spec, record))
    return sorted(results, key=lambda item: item["updated_at"], reverse=True)


def work_counts(company, employee_id=None):
    counts = []
    for spec in WORK_SPECS:
        queryset = spec.open(company)
        if employee_id:
            queryset = queryset.filter(**{f"{spec.owner_field}_id": employee_id})
        counts.append(
            {
                "work_type": spec.key,
                "label": spec.label,
                "open": queryset.count(),
                "unassigned": queryset.filter(**{f"{spec.owner_field}__isnull": True}).count(),
            }
        )
    return counts


def _active_employee(company, employee_id):
    try:
        return Employee.objects.select_related("user").get(
            pk=employee_id,
            company=company,
            employment_status=Employee.EmploymentStatus.ACTIVE,
            user__is_active=True,
        )
    except Employee.DoesNotExist as exc:
        raise ValidationError("Choose an active employee account from this company.") from exc


@transaction.atomic
def reassign_work(*, company, work_type, record_id, employee_id, reason, actor):
    spec = WORK_BY_KEY.get(work_type)
    if not spec:
        raise ValidationError("Choose a supported work type.")
    if len(reason.strip()) < 3:
        raise ValidationError({"reason": ["Explain why this work is being reassigned."]})
    employee = _active_employee(company, employee_id)
    try:
        record = spec.open(company).select_for_update().get(pk=record_id)
    except (spec.model.DoesNotExist, ValueError) as exc:
        raise ValidationError("This open work item no longer exists.") from exc
    previous = getattr(record, spec.owner_field)
    if previous and previous.pk == employee.pk:
        return _work_item(spec, record), False

    setattr(record, spec.owner_field, employee)
    update_fields = [spec.owner_field, "updated_at"]
    if hasattr(record, "updated_by"):
        record.updated_by = actor
        update_fields.append("updated_by")
    if hasattr(record, "record_version"):
        record.record_version += 1
        update_fields.append("record_version")
    record.save(update_fields=update_fields)
    if spec.key == "project_engineering":
        handoff = ProjectEngineeringHandoff.objects.select_for_update().filter(project=record).first()
        if handoff:
            handoff.assigned_engineer = employee
            handoff.record_version += 1
            handoff.save(update_fields=["assigned_engineer", "record_version", "updated_at"])

    event = DomainEvent(
        event_name="work.reassigned",
        entity_type=record._meta.model_name,
        entity_id=record.pk,
        company_id=company.pk,
        actor_user_id=actor.pk,
        actor_employee_id=getattr(getattr(actor, "employee", None), "pk", None),
        action="ASSIGN",
        module=record._meta.app_label,
        summary=f"{spec.label} {getattr(record, spec.reference_field)} assigned to {employee.display_name}",
        metadata={
            "recipient_user_id": str(employee.user_id),
            "status": getattr(record, spec.status_field),
            "reason": reason.strip(),
            "entity_reference": str(getattr(record, spec.reference_field)),
        },
        changes={
            spec.owner_field: {
                "old": str(getattr(previous, "pk", "")),
                "new": str(employee.pk),
            }
        },
    )
    publish(event)
    return _work_item(spec, record), True


@transaction.atomic
def bulk_reassign(*, company, items, employee_id, reason, actor):
    if not items or len(items) > 100:
        raise ValidationError("Choose between 1 and 100 open work items.")
    ordered = sorted(items, key=lambda item: (item["work_type"], str(item["id"])))
    results = [
        reassign_work(
            company=company,
            work_type=item["work_type"],
            record_id=item["id"],
            employee_id=employee_id,
            reason=reason,
            actor=actor,
        )[0]
        for item in ordered
    ]
    return results


def data_quality_issues(company):
    issues = []

    def add(issue_type, severity, count, message, action_url):
        if count:
            issues.append(
                {
                    "type": issue_type,
                    "severity": severity,
                    "count": count,
                    "message": message,
                    "recommended_action": "Review the affected records; no data was changed automatically.",
                    "action_url": action_url,
                }
            )

    add(
        "employee_missing_department",
        "attention",
        Employee.objects.filter(
            company=company,
            employment_status=Employee.EmploymentStatus.ACTIVE,
            department__isnull=True,
        ).count(),
        "Active employees have no department.",
        "/app/employees",
    )
    add(
        "active_employee_without_login",
        "attention",
        Employee.objects.filter(
            company=company,
            employment_status=Employee.EmploymentStatus.ACTIVE,
        )
        .filter(models.Q(user__isnull=True) | models.Q(user__is_active=False))
        .count(),
        "Active employees do not have an active login.",
        "/app/employees",
    )
    add(
        "login_without_employee",
        "attention",
        User.objects.filter(
            is_active=True,
            employee__isnull=True,
            is_superuser=False,
            role_assignments__company=company,
        )
        .distinct()
        .count(),
        "Active login accounts are not linked to an employee.",
        "/app/owner/people",
    )
    duplicate_names = (
        Customer.objects.filter(company=company)
        .annotate(normalized_name=Lower("legal_name"))
        .values("normalized_name")
        .annotate(total=models.Count("id"))
        .filter(total__gt=1)
        .count()
    )
    add(
        "exact_customer_name_duplicate",
        "review",
        duplicate_names,
        "Exact Customer-name duplicate groups need review.",
        "/app/crm/customers",
    )
    add(
        "project_without_engineering_owner",
        "attention",
        Project.objects.filter(company=company, engineering_owner__isnull=True)
        .exclude(status__in=[Project.Status.ENGINEERING_ACCEPTED, Project.Status.CANCELLED])
        .count(),
        "Open projects have no Workshop owner.",
        "/app/owner/work?queue=unassigned&work_type=project_engineering",
    )
    inactive_work = sum(
        spec.open(company)
        .exclude(**{f"{spec.owner_field}__isnull": True})
        .exclude(
            **{
                f"{spec.owner_field}__employment_status": Employee.EmploymentStatus.ACTIVE,
                f"{spec.owner_field}__user__is_active": True,
            }
        )
        .count()
        for spec in WORK_SPECS
    )
    add(
        "open_work_inactive_employee",
        "problem",
        inactive_work,
        "Open work is assigned to an inactive employee account.",
        "/app/owner/work?queue=inactive",
    )
    return issues


def operations_overview(company):
    from apps.inventory.services import low_stock_products

    low_stock_count = len(low_stock_products(company=company))
    delayed_purchase_orders = PurchaseOrder.objects.filter(
        company=company,
        status__in=[
            PurchaseOrder.Status.ORDERED,
            PurchaseOrder.Status.PART_RECEIVED,
            PurchaseOrder.Status.DELAYED,
        ],
        expected_delivery_date__lt=timezone.localdate(),
    ).count()
    overdue_payables = PurchaseOrder.objects.filter(
        company=company,
        payment_status__in=[PurchaseOrder.PaymentStatus.NOT_DUE, PurchaseOrder.PaymentStatus.PART_PAID],
        payment_due_date__lt=timezone.localdate(),
    ).count()
    panel_jobs_in_progress = (
        PanelJob.objects.filter(company=company)
        .exclude(status__in=[PanelJob.Status.CLOSED, PanelJob.Status.CANCELLED, PanelJob.Status.ON_HOLD])
        .count()
    )
    open_service_tickets = (
        ServiceTicket.objects.filter(company=company)
        .exclude(status__in=[ServiceTicket.Status.CLOSED, ServiceTicket.Status.CANCELLED])
        .count()
    )
    return {
        "stock_shortages": low_stock_count,
        "delayed_purchase_orders": delayed_purchase_orders,
        "overdue_payables": overdue_payables,
        "panel_jobs_in_progress": panel_jobs_in_progress,
        "open_service_tickets": open_service_tickets,
        "receivables_tracked": False,
    }


def owner_overview(company):
    counts = work_counts(company)
    issues = data_quality_issues(company)
    return {
        "company": {"id": str(company.pk), "name": company.name, "code": company.code},
        "people": {
            "active_employees": Employee.objects.filter(
                company=company, employment_status=Employee.EmploymentStatus.ACTIVE
            ).count(),
            "active_accounts": User.objects.filter(employee__company=company, is_active=True).count(),
            "roles": Role.objects.filter(company=company, is_active=True).count(),
        },
        "work": {
            "open": sum(item["open"] for item in counts),
            "unassigned": sum(item["unassigned"] for item in counts),
            "by_type": counts,
        },
        "operations": operations_overview(company),
        "attention": {
            "data_quality": sum(item["count"] for item in issues),
            "pending_approvals": ApprovalRequest.objects.filter(
                company=company,
                status__in=[ApprovalRequest.Status.PENDING, ApprovalRequest.Status.IN_PROGRESS],
            ).count(),
        },
        "recent_admin_activity": [
            {
                "id": str(event.pk),
                "summary": event.summary,
                "actor": event.actor_employee.display_name
                if event.actor_employee
                else event.actor_user.email
                if event.actor_user
                else "System",
                "occurred_at": event.occurred_at,
            }
            for event in AuditEvent.objects.select_related("actor_employee", "actor_user")
            .filter(company=company)
            .exclude(action=AuditEvent.Action.LOGIN)[:8]
        ],
    }


def _health_check(label, check, healthy_detail):
    try:
        check()
        return {"name": label, "status": "Available", "detail": healthy_detail}
    except Exception:
        return {
            "name": label,
            "status": "Unavailable",
            "detail": f"{label} could not be reached. No secret or technical error detail is exposed here.",
        }


def system_health(company):
    token = str(uuid.uuid4())

    def database_check():
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

    def cache_check():
        cache.set(f"owner-health:{token}", token, timeout=10)
        if cache.get(f"owner-health:{token}") != token:
            raise RuntimeError("Cache round-trip failed")

    storage = _health_check(
        "Document storage",
        get_storage,
        "Configured document storage can be initialized.",
    )
    integration = IntegrationCredential.objects.filter(
        company=company,
        integration_type=IntegrationCredential.IntegrationType.WEBSITE,
    ).order_by("-last_used_at").first()
    return {
        "checked_at": timezone.now(),
        "services": [
            _health_check("Database", database_check, "The system of record is responding."),
            _health_check("Cache", cache_check, "Cache round-trip succeeded."),
            {
                "name": "Realtime updates",
                "status": "Configured",
                "detail": (
                    "In-process realtime is configured for local development."
                    if "InMemory" in settings.CHANNEL_LAYERS["default"]["BACKEND"]
                    else (
                        "The production realtime channel layer is configured; employee screens "
                        "report live connection state."
                    )
                ),
            },
            {
                "name": "Background jobs",
                "status": "Available"
                if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False)
                else "Unknown",
                "detail": "Jobs run in-process in local development."
                if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False)
                else "A worker heartbeat is not configured for this screen yet.",
            },
            storage,
            {
                "name": "Website enquiry connection",
                "status": "Available"
                if integration and integration.is_active
                else "Not configured",
                "detail": (
                    f"{integration.name}; last used "
                    f"{integration.last_used_at.isoformat() if integration.last_used_at else 'never'}."
                    if integration and integration.is_active
                    else "No active website credential is configured for this company."
                ),
            },
            {
                "name": "Backup visibility",
                "status": "Not configured",
                "detail": "Backup execution and restore verification remain deployment operations.",
            },
        ],
    }


def owner_feature_controls(company):
    return feature_controls(company)


def change_owner_feature(*, company, actor, data):
    return set_feature(
        company=company,
        key=data["key"],
        enabled=data["is_enabled"],
        reason=data["reason"],
        submitted_version=data.get("record_version"),
        actor=actor,
    )
