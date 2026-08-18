from rest_framework import serializers

from .models import DocumentSequence
from .services import preview_number


class DocumentSequenceSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    preview = serializers.SerializerMethodField()

    class Meta:
        model = DocumentSequence
        fields = "__all__"
        read_only_fields = ["id", "record_version", "created_at", "updated_at", "preview"]

    def get_preview(self, obj):
        return preview_number(obj)

    def validate(self, attrs):
        instance = self.instance or DocumentSequence()
        for field, value in attrs.items():
            setattr(instance, field, value)
        instance.full_clean()
        return attrs
