from django.db import transaction
from django.db.models import Max
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from apps.core.domain_events import publish
from apps.crm.models import Customer
from apps.numbering.services import allocate_company_number
from apps.rbac.services import has_permission

from .models import Enquiry, EnquiryItem, EnquiryRequirement
from .services import enquiry_event


class CleanModelSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        instance = self.instance or self.Meta.model()
        for field, value in attrs.items():
            setattr(instance, field, value)
        if not self.instance and hasattr(instance, "created_by_id"):
            actor = self.context["request"].user
            instance.created_by = actor
            instance.updated_by = actor
        exclude = []
        if isinstance(instance, Enquiry):
            exclude.append("enquiry_number")
        if isinstance(instance, EnquiryItem) and not self.instance:
            exclude.append("line_number")
        instance.full_clean(exclude=exclude)
        return attrs


class EnquiryRequirementSerializer(CleanModelSerializer):
    class Meta:
        model = EnquiryRequirement
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        enquiry = attrs.get("enquiry", getattr(self.instance, "enquiry", None))
        if not has_permission(self.context["request"].user, "enquiry.enquiry.edit", enquiry):
            raise PermissionDenied("You cannot manage requirements for this enquiry.")
        if self.instance and "enquiry" in attrs and enquiry.pk != self.instance.enquiry_id:
            raise serializers.ValidationError({"enquiry": "Requirement enquiry cannot be changed."})
        if enquiry.status in {Enquiry.Status.WON, Enquiry.Status.LOST, Enquiry.Status.CANCELLED}:
            raise serializers.ValidationError("Closed enquiry requirements cannot be changed.")
        return super().validate(attrs)


class EnquiryItemSerializer(CleanModelSerializer):
    uom_code = serializers.CharField(source="uom.code", read_only=True)

    class Meta:
        model = EnquiryItem
        fields = "__all__"
        read_only_fields = ["id", "line_number", "created_at", "updated_at"]
        validators = []

    def validate(self, attrs):
        enquiry = attrs.get("enquiry", getattr(self.instance, "enquiry", None))
        if not has_permission(self.context["request"].user, "enquiry.enquiry.edit", enquiry):
            raise PermissionDenied("You cannot manage items for this enquiry.")
        if self.instance and "enquiry" in attrs and enquiry.pk != self.instance.enquiry_id:
            raise serializers.ValidationError({"enquiry": "Item enquiry cannot be changed."})
        if enquiry.status in {Enquiry.Status.WON, Enquiry.Status.LOST, Enquiry.Status.CANCELLED}:
            raise serializers.ValidationError("Closed enquiry items cannot be changed.")
        return super().validate(attrs)

    def create(self, validated_data):
        with transaction.atomic():
            enquiry = Enquiry.objects.select_for_update().get(pk=validated_data["enquiry"].pk)
            next_line = (
                enquiry.items.aggregate(number=Max("line_number"))["number"] or 0
            ) + 1
            validated_data["enquiry"] = enquiry
            return EnquiryItem.objects.create(
                **validated_data,
                line_number=next_line,
            )


class EnquirySerializer(CleanModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    customer_code = serializers.CharField(source="customer.customer_code", read_only=True)
    customer_name = serializers.CharField(source="customer.legal_name", read_only=True)
    customer_contact_name = serializers.CharField(
        source="customer_contact.display_name",
        read_only=True,
    )
    customer_site_name = serializers.CharField(source="customer_site.label", read_only=True)
    responsible_salesperson_name = serializers.CharField(
        source="responsible_salesperson.display_name",
        read_only=True,
    )
    currency_code = serializers.CharField(source="currency.code", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    requirements = EnquiryRequirementSerializer(many=True, read_only=True)
    items = EnquiryItemSerializer(many=True, read_only=True)

    class Meta:
        model = Enquiry
        fields = "__all__"
        validators = []
        read_only_fields = [
            "id",
            "company",
            "enquiry_number",
            "status",
            "lost_reason",
            "cancellation_reason",
            "competitor",
            "customer_feedback",
            "closed_at",
            "closed_by",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        if "status" in self.initial_data:
            raise serializers.ValidationError({"status": "Use an enquiry stage action."})
        customer = attrs.get("customer", getattr(self.instance, "customer", None))
        permission = "enquiry.enquiry.edit" if self.instance else "enquiry.enquiry.create"
        if not has_permission(self.context["request"].user, permission, customer):
            raise PermissionDenied("You cannot manage enquiries for this company.")
        if self.instance:
            if "customer" in attrs and customer.pk != self.instance.customer_id:
                raise serializers.ValidationError({"customer": "Enquiry customer cannot be changed."})
            if "responsible_salesperson" in self.initial_data:
                raise serializers.ValidationError(
                    {"responsible_salesperson": "Use the assign action to change the owner."}
                )
            if self.instance.status in {
                Enquiry.Status.WON,
                Enquiry.Status.LOST,
                Enquiry.Status.CANCELLED,
            }:
                raise serializers.ValidationError("A closed enquiry cannot be edited.")
        elif customer.status in {Customer.Status.INACTIVE, Customer.Status.BLOCKED}:
            raise serializers.ValidationError(
                {"customer": "New enquiries cannot be created for an inactive or blocked customer."}
            )
        if attrs.get("estimated_value") is not None and not attrs.get(
            "currency", getattr(self.instance, "currency", None)
        ):
            attrs["currency"] = customer.default_currency
        attrs["company"] = customer.company
        return super().validate(attrs)

    def create(self, validated_data):
        actor = self.context["request"].user
        enquiry = Enquiry.objects.create(
            **validated_data,
            enquiry_number=allocate_company_number(
                company=validated_data["company"],
                code="ENQUIRY",
            ),
            created_by=actor,
            updated_by=actor,
        )
        publish(
            enquiry_event(
                enquiry,
                actor,
                "enquiry.assigned",
                "ASSIGN",
                (
                    f"{enquiry.enquiry_number} assigned to "
                    f"{enquiry.responsible_salesperson.display_name}"
                ),
                metadata={
                    "recipient_user_id": str(enquiry.responsible_salesperson.user_id),
                },
            )
        )
        return enquiry

    def update(self, instance, validated_data):
        validated_data["updated_by"] = self.context["request"].user
        return super().update(instance, validated_data)


class EnquiryCloseSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)
    competitor = serializers.CharField(required=False, allow_blank=True, max_length=250)
    customer_feedback = serializers.CharField(required=False, allow_blank=True)


class EnquiryAssignSerializer(serializers.Serializer):
    salesperson_id = serializers.UUIDField()
