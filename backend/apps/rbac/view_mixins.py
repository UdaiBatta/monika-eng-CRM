from apps.core.concurrency import VersionedUpdateMixin

from .safety import active_business_owners, ensure_owner_continuity


def _company(instance):
    return getattr(instance, "company", None) or getattr(getattr(instance, "role", None), "company", None)


class OwnerContinuityMixin(VersionedUpdateMixin):
    def perform_update(self, serializer):
        company = _company(serializer.instance)
        previously_had_owner = bool(company and active_business_owners(company))
        super().perform_update(serializer)
        if company:
            ensure_owner_continuity(company, previously_had_owner=previously_had_owner)

