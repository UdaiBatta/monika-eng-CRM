from rest_framework import serializers


class WorkReferenceSerializer(serializers.Serializer):
    work_type = serializers.CharField(max_length=60)
    id = serializers.UUIDField()


class WorkReassignSerializer(serializers.Serializer):
    work_type = serializers.CharField(max_length=60, required=False)
    record_id = serializers.UUIDField(required=False)
    items = WorkReferenceSerializer(many=True, required=False)
    employee_id = serializers.UUIDField()
    reason = serializers.CharField(min_length=3, max_length=500)

    def validate(self, attrs):
        if bool(attrs.get("items")) == bool(attrs.get("work_type") and attrs.get("record_id")):
            raise serializers.ValidationError("Choose one work item or a list of work items.")
        return attrs


class FeatureChangeSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=100)
    is_enabled = serializers.BooleanField()
    reason = serializers.CharField(min_length=3, max_length=500)
    record_version = serializers.IntegerField(min_value=1, required=False, allow_null=True)

