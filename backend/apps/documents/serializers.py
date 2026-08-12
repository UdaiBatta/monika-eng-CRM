from rest_framework import serializers

from .models import Document, DocumentCategory, DocumentLink, DocumentVersion
from .services import create_document


class DocumentCategorySerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = DocumentCategory
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        instance = self.instance or DocumentCategory()
        for field, value in attrs.items():
            setattr(instance, field, value)
        instance.full_clean()
        return attrs


class DocumentVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentVersion
        exclude = ["storage_key"]
        read_only_fields = [
            field.name for field in DocumentVersion._meta.fields if field.name != "storage_key"
        ]


class DocumentLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentLink
        fields = "__all__"
        read_only_fields = [field.name for field in DocumentLink._meta.fields]


class DocumentSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    current_version = DocumentVersionSerializer(read_only=True)
    versions = DocumentVersionSerializer(many=True, read_only=True)
    links = DocumentLinkSerializer(many=True, read_only=True)

    class Meta:
        model = Document
        fields = [
            "id",
            "company",
            "company_name",
            "document_number",
            "title",
            "description",
            "category",
            "category_name",
            "status",
            "created_by",
            "created_by_name",
            "is_confidential",
            "current_version",
            "versions",
            "links",
            "archived_at",
            "archived_by",
            "archive_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class DocumentUploadSerializer(serializers.Serializer):
    category = serializers.PrimaryKeyRelatedField(queryset=DocumentCategory.objects.all())
    title = serializers.CharField(max_length=250)
    description = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    is_confidential = serializers.BooleanField(required=False, allow_null=True)
    file = serializers.FileField()

    def create(self, validated_data):
        file_object = validated_data.pop("file")
        return create_document(
            file_object=file_object,
            actor=self.context["request"].user,
            **validated_data,
        )


class DocumentVersionUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    notes = serializers.CharField(required=False, allow_blank=True)


class DocumentArchiveSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)


class DocumentLinkCommandSerializer(serializers.Serializer):
    entity_type = serializers.CharField(max_length=80)
    entity_id = serializers.CharField(max_length=100)
    relationship_type = serializers.CharField(max_length=80, default="RELATED")
