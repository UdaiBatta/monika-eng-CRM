from django.db import transaction
from rest_framework.exceptions import ValidationError

from .conflicts import VersionConflict


class VersionedUpdateMixin:
    """Row-lock and version-check ordinary editable records before saving."""

    @transaction.atomic
    def perform_update(self, serializer):
        submitted = self.request.data.get("record_version")
        if submitted is None:
            raise ValidationError(
                {"record_version": ["This record may have changed. Refresh it before saving."]}
            )
        try:
            submitted = int(submitted)
        except (TypeError, ValueError) as exc:
            raise ValidationError({"record_version": ["Enter a valid record version."]}) from exc

        model = type(serializer.instance)
        current = model.objects.select_for_update().get(pk=serializer.instance.pk)
        if current.record_version != submitted:
            raise VersionConflict(current.record_version)
        serializer.instance = current
        super().perform_update(serializer)
        current.record_version += 1
        update_fields = ["record_version"]
        if hasattr(current, "updated_at"):
            update_fields.append("updated_at")
        current.save(update_fields=update_fields)
