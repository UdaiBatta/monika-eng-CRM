from decimal import Decimal

from rest_framework import serializers

from .models import PanelJob, PanelJobMaterialLine, PanelJobStageEvent


class PanelJobMaterialLineSerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(source="product.internal_code", read_only=True)
    product_description = serializers.CharField(source="product.description", read_only=True)
    shortage_quantity = serializers.DecimalField(max_digits=18, decimal_places=4, read_only=True)

    class Meta:
        model = PanelJobMaterialLine
        fields = "__all__"
        read_only_fields = [field.name for field in PanelJobMaterialLine._meta.fields]


class PanelJobStageEventSerializer(serializers.ModelSerializer):
    from_status_label = serializers.SerializerMethodField()
    to_status_label = serializers.SerializerMethodField()
    actor_name = serializers.CharField(source="actor.get_full_name", read_only=True, default="")

    class Meta:
        model = PanelJobStageEvent
        fields = "__all__"
        read_only_fields = [field.name for field in PanelJobStageEvent._meta.fields]

    def get_from_status_label(self, obj):
        return dict(PanelJob.Status.choices).get(obj.from_status, obj.from_status)

    def get_to_status_label(self, obj):
        return dict(PanelJob.Status.choices).get(obj.to_status, obj.to_status)


class PanelJobSerializer(serializers.ModelSerializer):
    material_lines = PanelJobMaterialLineSerializer(many=True, read_only=True)
    stage_events = PanelJobStageEventSerializer(many=True, read_only=True)
    project_number = serializers.CharField(source="project.project_number", read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    workshop_owner_name = serializers.CharField(
        source="workshop_owner.display_name", read_only=True, default=""
    )
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = PanelJob
        fields = "__all__"
        read_only_fields = [field.name for field in PanelJob._meta.fields]


class PanelJobCreateSerializer(serializers.Serializer):
    panel_name = serializers.CharField(max_length=250)
    panel_reference = serializers.CharField(max_length=250, required=False, allow_blank=True, default="")
    warehouse = serializers.UUIDField()
    workshop_owner = serializers.UUIDField(required=False, allow_null=True)
    requirement_notes = serializers.CharField(required=False, allow_blank=True, default="")
    target_completion = serializers.DateField(required=False, allow_null=True)
    material_lines = serializers.ListField(child=serializers.DictField(), required=False, default=list)


class AddMaterialLineInputSerializer(serializers.Serializer):
    product = serializers.UUIDField()
    required_quantity = serializers.DecimalField(max_digits=18, decimal_places=4, min_value=Decimal("0.0001"))
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class ReserveMaterialsInputSerializer(serializers.Serializer):
    location = serializers.UUIDField()


class MaterialMovementInputSerializer(serializers.Serializer):
    material_line = serializers.UUIDField()
    movement_type = serializers.ChoiceField(choices=["ISSUE", "CONSUME", "RETURN"])
    quantity = serializers.DecimalField(max_digits=18, decimal_places=4, min_value=Decimal("0.0001"))
    location = serializers.UUIDField()


class QualityCheckInputSerializer(serializers.Serializer):
    passed = serializers.BooleanField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class ReasonInputSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=3, max_length=500)


class NotesInputSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True, default="")
