from decimal import Decimal

from rest_framework import serializers

from .models import Equipment, ServiceJobLine, ServiceTicket, ServiceTicketStageEvent


class EquipmentSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.legal_name", read_only=True)
    site_label = serializers.CharField(source="site.label", read_only=True, default="")
    product_code = serializers.CharField(source="product.internal_code", read_only=True, default="")
    under_warranty = serializers.BooleanField(read_only=True)

    class Meta:
        model = Equipment
        fields = "__all__"
        read_only_fields = [field.name for field in Equipment._meta.fields]


class ServiceJobLineSerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(source="product.internal_code", read_only=True, default="")
    line_type_label = serializers.CharField(source="get_line_type_display", read_only=True)

    class Meta:
        model = ServiceJobLine
        fields = "__all__"
        read_only_fields = [field.name for field in ServiceJobLine._meta.fields]


class ServiceJobLineInputSerializer(serializers.Serializer):
    line_type = serializers.ChoiceField(choices=ServiceJobLine.LineType.choices)
    product = serializers.UUIDField(required=False, allow_null=True)
    description = serializers.CharField(max_length=500)
    quantity = serializers.DecimalField(max_digits=18, decimal_places=4, min_value=Decimal("0.0001"))
    unit_price = serializers.DecimalField(max_digits=18, decimal_places=4, min_value=Decimal("0"))


class ServiceTicketStageEventSerializer(serializers.ModelSerializer):
    from_status_label = serializers.SerializerMethodField()
    to_status_label = serializers.SerializerMethodField()
    actor_name = serializers.CharField(source="actor.get_full_name", read_only=True, default="")

    class Meta:
        model = ServiceTicketStageEvent
        fields = "__all__"
        read_only_fields = [field.name for field in ServiceTicketStageEvent._meta.fields]

    def get_from_status_label(self, obj):
        return dict(ServiceTicket.Status.choices).get(obj.from_status, obj.from_status)

    def get_to_status_label(self, obj):
        return dict(ServiceTicket.Status.choices).get(obj.to_status, obj.to_status)


class ServiceTicketSerializer(serializers.ModelSerializer):
    job_lines = ServiceJobLineSerializer(many=True, read_only=True)
    stage_events = ServiceTicketStageEventSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source="customer.legal_name", read_only=True)
    contact_name = serializers.CharField(source="contact.display_name", read_only=True, default="")
    equipment_name = serializers.CharField(source="equipment.equipment_name", read_only=True, default="")
    technician_name = serializers.CharField(source="technician.display_name", read_only=True, default="")
    quotation_number = serializers.CharField(source="quotation.quotation_number", read_only=True, default="")
    source_label = serializers.CharField(source="get_source_display", read_only=True)
    priority_label = serializers.CharField(source="get_priority_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ServiceTicket
        fields = "__all__"
        read_only_fields = [field.name for field in ServiceTicket._meta.fields]


class ServiceTicketCreateSerializer(serializers.Serializer):
    customer = serializers.UUIDField()
    contact = serializers.UUIDField(required=False, allow_null=True)
    equipment = serializers.UUIDField(required=False, allow_null=True)
    source = serializers.ChoiceField(
        choices=ServiceTicket.Source.choices, default=ServiceTicket.Source.MANUAL
    )
    complaint = serializers.CharField()
    priority = serializers.ChoiceField(
        choices=ServiceTicket.Priority.choices, default=ServiceTicket.Priority.NORMAL
    )


class AssignTechnicianInputSerializer(serializers.Serializer):
    technician_id = serializers.UUIDField()
    scheduled_visit_at = serializers.DateTimeField(required=False, allow_null=True)


class DiagnosisInputSerializer(serializers.Serializer):
    diagnosis = serializers.CharField()


class LinkQuotationInputSerializer(serializers.Serializer):
    quotation_id = serializers.UUIDField()


class StatusChangeInputSerializer(serializers.Serializer):
    to_status = serializers.ChoiceField(
        choices=[
            ServiceTicket.Status.AWAITING_PARTS,
            ServiceTicket.Status.UNDER_REPAIR,
            ServiceTicket.Status.READY_FOR_DISPATCH,
            ServiceTicket.Status.CANCELLED,
        ]
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class DispatchInputSerializer(serializers.Serializer):
    dispatch_reference = serializers.CharField(max_length=250)
    warranty_claim = serializers.BooleanField(default=False)


class NotesInputSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class ConsumePartInputSerializer(serializers.Serializer):
    job_line_id = serializers.UUIDField()
    location = serializers.UUIDField()
