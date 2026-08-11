import base64

from rest_framework import serializers

from apps.crm.models import Customer

from .models import (
    ExternalEnquiryAttachment,
    ExternalEnquirySubmission,
    IncomingEnquirySourceEvent,
)


class IntakeAttachmentSerializer(serializers.Serializer):
    filename = serializers.CharField(max_length=255)
    content_base64 = serializers.CharField(write_only=True)

    def validate_content_base64(self, value):
        try:
            base64.b64decode(value, validate=True)
        except (ValueError, TypeError) as exc:
            raise serializers.ValidationError("Attachment content is not valid base64 data.") from exc
        return value


class WebsiteIntakeSerializer(serializers.Serializer):
    submission_id = serializers.CharField(max_length=160)
    idempotency_key = serializers.CharField(max_length=160, required=False)
    source_type = serializers.ChoiceField(choices=ExternalEnquirySubmission.SourceType.choices)
    name = serializers.CharField(max_length=200)
    company = serializers.CharField(max_length=250, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=40, required=False, allow_blank=True)
    subject = serializers.CharField(max_length=250)
    message = serializers.CharField(max_length=10000)
    product_reference = serializers.CharField(max_length=160, required=False, allow_blank=True)
    product_name = serializers.CharField(max_length=250, required=False, allow_blank=True)
    product_url = serializers.URLField(required=False, allow_blank=True)
    page_url = serializers.URLField(required=False, allow_blank=True)
    referrer_url = serializers.URLField(required=False, allow_blank=True)
    utm_source = serializers.CharField(max_length=160, required=False, allow_blank=True)
    utm_medium = serializers.CharField(max_length=160, required=False, allow_blank=True)
    utm_campaign = serializers.CharField(max_length=160, required=False, allow_blank=True)
    utm_term = serializers.CharField(max_length=160, required=False, allow_blank=True)
    utm_content = serializers.CharField(max_length=160, required=False, allow_blank=True)
    submitted_at = serializers.DateTimeField(required=False)
    captcha_verified = serializers.BooleanField(required=False)
    honeypot = serializers.CharField(required=False, allow_blank=True, write_only=True)
    attachments = IntakeAttachmentSerializer(many=True, required=False, max_length=3)

    def validate(self, attrs):
        attrs["email"] = attrs.get("email", "").strip().lower()
        attrs["phone"] = attrs.get("phone", "").strip()
        if not attrs["email"] and not attrs["phone"]:
            raise serializers.ValidationError("Provide an email address or phone number.")
        attrs["idempotency_key"] = attrs.get("idempotency_key") or attrs["submission_id"]
        return attrs


class ExternalAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalEnquiryAttachment
        exclude = ["storage_key"]
        read_only_fields = [field.name for field in ExternalEnquiryAttachment._meta.fields]


class IncomingSourceEventSerializer(serializers.ModelSerializer):
    channel_label = serializers.CharField(source="get_channel_display", read_only=True)

    class Meta:
        model = IncomingEnquirySourceEvent
        exclude = ["updated_at"]
        read_only_fields = [field.name for field in IncomingEnquirySourceEvent._meta.fields]


class ExternalSubmissionSerializer(serializers.ModelSerializer):
    attachments = ExternalAttachmentSerializer(many=True, read_only=True)
    source_history = IncomingSourceEventSerializer(many=True, read_only=True)
    channel_label = serializers.CharField(source="get_channel_display", read_only=True)
    assigned_to_name = serializers.CharField(source="assigned_to.display_name", read_only=True)
    matched_customer_name = serializers.CharField(source="matched_customer.legal_name", read_only=True)
    matched_contact_name = serializers.CharField(source="matched_contact.display_name", read_only=True)
    converted_customer_name = serializers.CharField(source="converted_customer.legal_name", read_only=True)
    converted_contact_name = serializers.CharField(source="converted_contact.display_name", read_only=True)
    converted_enquiry_number = serializers.CharField(
        source="converted_enquiry.enquiry_number", read_only=True
    )

    class Meta:
        model = ExternalEnquirySubmission
        fields = "__all__"
        read_only_fields = [field.name for field in ExternalEnquirySubmission._meta.fields]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if request and not request.user.is_superuser:
            from apps.rbac.services import has_permission

            if not has_permission(request.user, "crm.external_enquiry.view_source_metadata", instance):
                for field in ("remote_ip_hash", "user_agent", "referrer_url", "utm_term", "utm_content"):
                    data.pop(field, None)
        return data


class SubmissionAssignSerializer(serializers.Serializer):
    employee_id = serializers.UUIDField()
    priority = serializers.ChoiceField(choices=ExternalEnquirySubmission.Priority.choices, required=False)


class ManualIncomingEnquirySerializer(serializers.Serializer):
    channel = serializers.ChoiceField(choices=ExternalEnquirySubmission.Channel.choices)
    source_reference = serializers.CharField(max_length=160, required=False, allow_blank=True)
    person_name = serializers.CharField(max_length=200)
    company_name = serializers.CharField(max_length=250, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=40, required=False, allow_blank=True)
    subject = serializers.CharField(max_length=250)
    message = serializers.CharField(max_length=10000)
    assigned_to_id = serializers.UUIDField(required=False, allow_null=True)
    priority = serializers.ChoiceField(
        choices=ExternalEnquirySubmission.Priority.choices,
        default=ExternalEnquirySubmission.Priority.NORMAL,
    )

    def validate(self, attrs):
        if attrs["channel"] == ExternalEnquirySubmission.Channel.WEBSITE:
            raise serializers.ValidationError(
                "Website enquiries must use the signed website integration endpoint."
            )
        attrs["email"] = attrs.get("email", "").strip().lower()
        attrs["phone"] = attrs.get("phone", "").strip()
        if attrs["channel"] in {
            ExternalEnquirySubmission.Channel.TRADEINDIA,
            ExternalEnquirySubmission.Channel.WHATSAPP,
            ExternalEnquirySubmission.Channel.PHONE,
            ExternalEnquirySubmission.Channel.EMAIL,
        } and not (attrs["email"] or attrs["phone"]):
            raise serializers.ValidationError("Add the available email address or phone number.")
        return attrs


class HistoricalIncomingEnquiryRowSerializer(ManualIncomingEnquirySerializer):
    received_at = serializers.DateTimeField()


class HistoricalIncomingEnquiryImportSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("The import file must be 5 MB or smaller.")
        if not value.name.lower().endswith((".csv", ".xlsx")):
            raise serializers.ValidationError("Upload a .csv or .xlsx file.")
        return value


class SubmissionDecisionSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)


class NewCustomerSerializer(serializers.Serializer):
    legal_name = serializers.CharField(max_length=250)
    trade_name = serializers.CharField(max_length=250, required=False, allow_blank=True)
    customer_type = serializers.ChoiceField(
        choices=Customer.CustomerType.choices, default=Customer.CustomerType.ORGANIZATION
    )
    primary_email = serializers.EmailField(required=False, allow_blank=True)
    primary_phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    default_currency = serializers.UUIDField()
    account_manager = serializers.UUIDField(required=False, allow_null=True)
    duplicate_override_reason = serializers.CharField(max_length=500, required=False, allow_blank=True)


class NewContactSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    title = serializers.CharField(max_length=120, required=False, allow_blank=True)
    department = serializers.CharField(max_length=120, required=False, allow_blank=True)
    is_primary = serializers.BooleanField(default=False)

    def validate(self, attrs):
        if not attrs.get("email") and not attrs.get("phone"):
            raise serializers.ValidationError("Provide an email address or phone number for the contact.")
        return attrs


class SubmissionConversionSerializer(serializers.Serializer):
    customer_id = serializers.UUIDField(required=False)
    new_customer = NewCustomerSerializer(required=False)
    contact_id = serializers.UUIDField(required=False)
    new_contact = NewContactSerializer(required=False)
    responsible_salesperson_id = serializers.UUIDField()
    priority = serializers.ChoiceField(
        choices=ExternalEnquirySubmission.Priority.choices, default=ExternalEnquirySubmission.Priority.NORMAL
    )
    follow_up_at = serializers.DateTimeField(required=False)
    document_category_id = serializers.UUIDField(required=False)

    def validate(self, attrs):
        if bool(attrs.get("customer_id")) == bool(attrs.get("new_customer")):
            raise serializers.ValidationError("Choose an existing customer or enter a new customer.")
        if bool(attrs.get("contact_id")) == bool(attrs.get("new_contact")):
            raise serializers.ValidationError("Choose an existing contact or enter a new contact.")
        return attrs
