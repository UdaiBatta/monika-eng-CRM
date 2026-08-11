import time

from django.conf import settings
from django.core.cache import cache


def _cache_key(company_id, entity_type, entity_id):
    return f"realtime:presence:{company_id}:{entity_type}:{entity_id}"


def _fresh(records):
    cutoff = time.time() - settings.REALTIME_PRESENCE_TTL_SECONDS
    return {key: value for key, value in records.items() if value["seen_at"] >= cutoff}


def list_presence(company_id, entity_type, entity_id):
    key = _cache_key(company_id, entity_type, entity_id)
    records = _fresh(cache.get(key, {}))
    cache.set(key, records, settings.REALTIME_PRESENCE_TTL_SECONDS)
    return [records[user_id] for user_id in sorted(records)]


def touch_presence(company_id, entity_type, entity_id, user):
    key = _cache_key(company_id, entity_type, entity_id)
    records = _fresh(cache.get(key, {}))
    employee = getattr(user, "employee", None)
    records[str(user.pk)] = {
        "user_id": str(user.pk),
        "display_name": getattr(employee, "display_name", None) or user.email,
        "seen_at": time.time(),
    }
    cache.set(key, records, settings.REALTIME_PRESENCE_TTL_SECONDS)
    return list(records.values())


def remove_presence(company_id, entity_type, entity_id, user_id):
    key = _cache_key(company_id, entity_type, entity_id)
    records = _fresh(cache.get(key, {}))
    records.pop(str(user_id), None)
    cache.set(key, records, settings.REALTIME_PRESENCE_TTL_SECONDS)
    return list(records.values())
