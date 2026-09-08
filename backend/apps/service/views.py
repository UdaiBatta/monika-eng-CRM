from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.core.permissions import HasFoundationPermission, ScopedQuerysetMixin
from apps.crm.models import Customer, CustomerContact
from apps.inventory.models import Product, StockLocation
from apps.organization.models import Employee

from .models import Equipment, ServiceTicket
from .serializers import (
    AssignTechnicianInputSerializer,
    ConsumePartInputSerializer,
    DiagnosisInputSerializer,
    DispatchInputSerializer,
    EquipmentSerializer,
    LinkQuotationInputSerializer,
    NotesInputSerializer,
    ServiceJobLineInputSerializer,
    ServiceJobLineSerializer,
    ServiceTicketCreateSerializer,
    ServiceTicketSerializer,
    StatusChangeInputSerializer,
)
from .services import (
    add_job_line,
    assign_technician,
    change_status,
    close_ticket,
    consume_part,
    create_service_ticket,
    dispatch_ticket,
    link_quotation,
    record_diagnosis,
)


def _raise_from_django_validation(exc):
    detail = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
    raise ValidationError(detail) from exc


def _actor_company(user):
    employee = Employee.objects.filter(user=user, user__is_active=True).select_related("company").first()
    if not employee:
        raise ValidationError("Your account is not linked to an active employee.")
    return employee.company


class EquipmentViewSet(ScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Equipment.objects.select_related("company", "customer", "site", "product")
    serializer_class = EquipmentSerializer
    permission_classes = [HasFoundationPermission]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    permission_map = {
        "list": "service.equipment.view",
        "retrieve": "service.equipment.view",
        "default": "service.equipment.manage",
    }
    search_fields = ["equipment_name", "serial_number", "make_model", "customer__legal_name"]
    filterset_fields = ["company", "customer", "is_active"]
    ordering_fields = ["created_at", "updated_at", "equipment_name"]


class ServiceTicketViewSet(ScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = ServiceTicket.objects.select_related(
        "company", "customer", "contact", "equipment", "technician", "quotation"
    ).prefetch_related("job_lines", "stage_events")
    serializer_class = ServiceTicketSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "list": "service.ticket.view",
        "retrieve": "service.ticket.view",
        "create": "service.ticket.create",
        "add_job_line": "service.ticket.record_parts_labour",
        "consume_part_action": "service.ticket.record_parts_labour",
        "assign": "service.ticket.assign",
        "diagnose": "service.ticket.diagnose",
        "link_quotation_action": "service.ticket.link_quotation",
        "change_status_action": "service.ticket.repair",
        "dispatch_ticket_action": "service.ticket.dispatch",
        "close": "service.ticket.close",
        "default": "service.ticket.view",
    }
    search_fields = ["ticket_number", "complaint", "customer__legal_name"]
    filterset_fields = ["company", "status", "priority", "technician", "customer"]
    ordering_fields = ["created_at", "updated_at", "ticket_number", "status", "priority"]

    def get_queryset(self):
        queryset = super().get_queryset()
        queue = self.request.query_params.get("queue")
        employee = getattr(self.request.user, "employee", None)
        if queue == "mine":
            return queryset.filter(technician=employee) if employee else queryset.none()
        if queue == "unassigned":
            return queryset.filter(technician__isnull=True)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = ServiceTicketCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = dict(serializer.validated_data)
        contact_id = validated.pop("contact", None)
        equipment_id = validated.pop("equipment", None)
        data = {
            "customer": Customer.objects.get(pk=validated.pop("customer")),
            "contact": CustomerContact.objects.get(pk=contact_id) if contact_id else None,
            "equipment": Equipment.objects.get(pk=equipment_id) if equipment_id else None,
            "source": validated["source"],
            "complaint": validated["complaint"],
            "priority": validated["priority"],
        }
        try:
            ticket = create_service_ticket(
                company=_actor_company(request.user), actor=request.user, data=data
            )
        except DjangoValidationError as exc:
            _raise_from_django_validation(exc)
        return Response(ServiceTicketSerializer(ticket).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="job-lines")
    def add_job_line(self, request, pk=None):
        serializer = ServiceJobLineInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = dict(serializer.validated_data)
        product = Product.objects.get(pk=validated.pop("product")) if validated.get("product") else None
        try:
            line = add_job_line(
                ticket_id=self.get_object().pk,
                actor=request.user,
                line_type=validated["line_type"],
                description=validated["description"],
                quantity=validated["quantity"],
                unit_price=validated["unit_price"],
                product=product,
            )
        except DjangoValidationError as exc:
            _raise_from_django_validation(exc)
        return Response(ServiceJobLineSerializer(line).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="job-lines/consume")
    def consume_part_action(self, request, pk=None):
        serializer = ConsumePartInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        location = StockLocation.objects.get(pk=serializer.validated_data["location"])
        try:
            line = consume_part(
                ticket_id=self.get_object().pk,
                actor=request.user,
                job_line_id=serializer.validated_data["job_line_id"],
                location=location,
            )
        except DjangoValidationError as exc:
            _raise_from_django_validation(exc)
        return Response(ServiceJobLineSerializer(line).data)

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        serializer = AssignTechnicianInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            ticket = assign_technician(
                ticket_id=self.get_object().pk, actor=request.user, **serializer.validated_data
            )
        except DjangoValidationError as exc:
            _raise_from_django_validation(exc)
        return Response(ServiceTicketSerializer(ticket).data)

    @action(detail=True, methods=["post"])
    def diagnose(self, request, pk=None):
        serializer = DiagnosisInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            ticket = record_diagnosis(
                ticket_id=self.get_object().pk,
                actor=request.user,
                diagnosis=serializer.validated_data["diagnosis"],
            )
        except DjangoValidationError as exc:
            _raise_from_django_validation(exc)
        return Response(ServiceTicketSerializer(ticket).data)

    @action(detail=True, methods=["post"], url_path="link-quotation")
    def link_quotation_action(self, request, pk=None):
        serializer = LinkQuotationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            ticket = link_quotation(
                ticket_id=self.get_object().pk,
                actor=request.user,
                quotation_id=serializer.validated_data["quotation_id"],
            )
        except DjangoValidationError as exc:
            _raise_from_django_validation(exc)
        return Response(ServiceTicketSerializer(ticket).data)

    @action(detail=True, methods=["post"], url_path="change-status")
    def change_status_action(self, request, pk=None):
        serializer = StatusChangeInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            ticket = change_status(
                ticket_id=self.get_object().pk, actor=request.user, **serializer.validated_data
            )
        except DjangoValidationError as exc:
            _raise_from_django_validation(exc)
        return Response(ServiceTicketSerializer(ticket).data)

    @action(detail=True, methods=["post"], url_path="dispatch")
    def dispatch_ticket_action(self, request, pk=None):
        serializer = DispatchInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            ticket = dispatch_ticket(
                ticket_id=self.get_object().pk, actor=request.user, **serializer.validated_data
            )
        except DjangoValidationError as exc:
            _raise_from_django_validation(exc)
        return Response(ServiceTicketSerializer(ticket).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        serializer = NotesInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            ticket = close_ticket(
                ticket_id=self.get_object().pk,
                actor=request.user,
                notes=serializer.validated_data.get("notes", ""),
            )
        except DjangoValidationError as exc:
            _raise_from_django_validation(exc)
        return Response(ServiceTicketSerializer(ticket).data)
