from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from apps.core.domain_events import publish
from apps.numbering.services import allocate_company_number
from apps.rbac.services import has_permission

from .models import CrmActivity, Customer, CustomerContact, CustomerSite
from .services import _activity_event, find_customer_duplicates


class CleanModelSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        for field in ("gstin", "pan", "cin"):
            if field in attrs:
                attrs[field] = attrs[field].strip().upper()
        instance = self.instance or self.Meta.model()
        for field, value in attrs.items():
            setattr(instance, field, value)
        if not self.instance and hasattr(instance, "created_by_id"):
            actor = self.context["request"].user
            instance.created_by = actor
        if isinstance(instance, Customer) and not self.instance:
            instance.updated_by = actor
        instance.full_clean(exclude=["customer_code"] if isinstance(instance, Customer) else None)
        return attrs


class CustomerContactSerializer(CleanModelSerializer):
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = CustomerContact
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        customer = attrs.get("customer", getattr(self.instance, "customer", None))
        if self.instance and "customer" in attrs and customer.pk != self.instance.customer_id:
            raise serializers.ValidationError({"customer": "Contact customer cannot be changed."})
        permission = "crm.contact.edit" if self.instance else "crm.contact.create"
        if not has_permission(self.context["request"].user, permission, customer):
            raise PermissionDenied("You cannot manage contacts for this customer.")
        return attrs


class CustomerSiteSerializer(CleanModelSerializer):
    class Meta:
        model = CustomerSite
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        customer = attrs.get("customer", getattr(self.instance, "customer", None))
        if self.instance and "customer" in attrs and customer.pk != self.instance.customer_id:
            raise serializers.ValidationError({"customer": "Site customer cannot be changed."})
        if not has_permission(self.context["request"].user, "crm.customer.edit", customer):
            raise PermissionDenied("You cannot manage sites for this customer.")
        return attrs


class CustomerSerializer(CleanModelSerializer):
    duplicate_override_reason = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        max_length=500,
    )
    company_name = serializers.CharField(source="company.name", read_only=True)
    account_manager_name = serializers.CharField(source="account_manager.display_name", read_only=True)
    primary_contact = serializers.SerializerMethodField()
    contacts = CustomerContactSerializer(many=True, read_only=True)
    sites = CustomerSiteSerializer(many=True, read_only=True)

    class Meta:
        model = Customer
        fields = "__all__"
        validators = []
        read_only_fields = [
            "id",
            "customer_code",
            "status",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def get_primary_contact(self, obj):
        contact = next((item for item in obj.contacts.all() if item.is_primary and item.is_active), None)
        return CustomerContactSerializer(contact).data if contact else None

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if "status" in self.initial_data:
            raise serializers.ValidationError({"status": "Use a customer status action."})
        if self.instance and "company" in attrs and attrs["company"].pk != self.instance.company_id:
            raise serializers.ValidationError({"company": "Customer company cannot be changed."})
        company = attrs.get("company", self.instance.company if self.instance else None)
        permission = "crm.customer.edit" if self.instance else "crm.customer.create"
        if not has_permission(self.context["request"].user, permission, company):
            raise PermissionDenied("You cannot manage customers for this company.")
        return attrs

    def create(self, validated_data):
        override_reason = validated_data.pop("duplicate_override_reason", "").strip()
        duplicates = find_customer_duplicates(
            company=validated_data["company"],
            legal_name=validated_data.get("legal_name", ""),
            gstin=validated_data.get("gstin", ""),
            pan=validated_data.get("pan", ""),
            email=validated_data.get("primary_email", ""),
            phone=validated_data.get("primary_phone", ""),
        )
        if duplicates and not override_reason:
            raise serializers.ValidationError(
                {
                    "possible_matches": duplicates,
                    "message": "Possible matching customer found. Review it before continuing.",
                }
            )
        actor = self.context["request"].user
        customer = Customer.objects.create(
            **validated_data,
            customer_code=allocate_company_number(
                company=validated_data["company"],
                code="CUSTOMER",
            ),
            created_by=actor,
            updated_by=actor,
        )
        if override_reason:
            from apps.audit.services import record_event

            record_event(
                actor=actor,
                company=customer.company,
                action="UPDATE",
                entity=customer,
                event_type="crm.customer.duplicate_override",
                module="crm",
                summary=f"Possible duplicate warning overridden for {customer.customer_code}",
                metadata={"reason": override_reason, "possible_matches": duplicates},
            )
        return customer

    def update(self, instance, validated_data):
        validated_data.pop("duplicate_override_reason", None)
        validated_data["updated_by"] = self.context["request"].user
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if request and not has_permission(request.user, "crm.contact.view", instance):
            data.pop("contacts", None)
            data.pop("primary_contact", None)
        if request and not has_permission(request.user, "crm.customer.view_sensitive", instance):
            for field in ("gstin", "pan", "cin", "credit_limit", "payment_term", "default_tax"):
                data.pop(field, None)
        return data


class CustomerDuplicateCheckSerializer(serializers.Serializer):
    company = serializers.UUIDField()
    legal_name = serializers.CharField(required=False, allow_blank=True)
    gstin = serializers.CharField(required=False, allow_blank=True)
    pan = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)


class CustomerStatusCommandSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)


class CrmActivitySerializer(CleanModelSerializer):
    customer_code = serializers.CharField(source="customer.customer_code", read_only=True)
    customer_name = serializers.CharField(source="customer.legal_name", read_only=True)
    contact_name = serializers.CharField(source="contact.display_name", read_only=True)
    follow_up_owner_name = serializers.CharField(source="follow_up_owner.display_name", read_only=True)
    created_by_name = serializers.SerializerMethodField()
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = CrmActivity
        fields = "__all__"
        read_only_fields = [
            "id",
            "company",
            "created_by",
            "status",
            "completed_at",
            "completed_by",
            "created_at",
            "updated_at",
        ]

    def get_created_by_name(self, obj):
        employee = getattr(obj.created_by, "employee", None)
        return employee.display_name if employee else getattr(obj.created_by, "email", "")

    def validate(self, attrs):
        customer = attrs.get("customer", getattr(self.instance, "customer", None))
        permission = "crm.activity.edit" if self.instance else "crm.activity.create"
        if not has_permission(self.context["request"].user, permission, customer):
            raise PermissionDenied("You cannot manage activities for this customer.")
        if self.instance and "customer" in attrs and customer.pk != self.instance.customer_id:
            raise serializers.ValidationError({"customer": "Activity customer cannot be changed."})
        activity_type = attrs.get("activity_type", getattr(self.instance, "activity_type", None))
        if not self.instance:
            attrs["company"] = customer.company
            attrs["status"] = (
                CrmActivity.Status.OPEN
                if activity_type == CrmActivity.ActivityType.FOLLOW_UP
                else CrmActivity.Status.COMPLETED
            )
        return super().validate(attrs)

    def create(self, validated_data):
        actor = self.context["request"].user
        activity = CrmActivity.objects.create(**validated_data, created_by=actor)
        if activity.activity_type == CrmActivity.ActivityType.FOLLOW_UP:
            publish(
                _activity_event(
                    activity,
                    actor,
                    "crm.follow_up.assigned",
                    "ASSIGN",
                    f"Follow-up assigned: {activity.subject}",
                )
            )
        return activity
