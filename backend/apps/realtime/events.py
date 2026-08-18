from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .groups import company_group, entity_group, user_group

SAFE_METADATA_KEYS = {
    "channel",
    "customer_id",
    "enquiry_id",
    "estimate_id",
    "quotation_id",
    "sales_order_id",
    "project_id",
    "order_mode",
    "recipient_user_id",
    "review_status",
    "source_type",
    "status",
}


def event_payload(event):
    return {
        "event_id": str(event.correlation_id),
        "event_name": event.event_name,
        "entity_type": event.entity_type,
        "entity_id": str(event.entity_id),
        "action": event.action,
        "module": event.module,
        "occurred_at": event.occurred_at.isoformat(),
        "metadata": {
            key: str(value)
            for key, value in event.metadata.items()
            if key in SAFE_METADATA_KEYS and value is not None
        },
    }


def broadcast_domain_event(event):
    if not event.company_id:
        return
    layer = get_channel_layer()
    if layer is None:
        return
    message = {"type": "domain.event", "payload": event_payload(event)}
    groups = {
        company_group(event.company_id),
        entity_group(event.entity_type, event.entity_id),
    }
    recipient = event.metadata.get("recipient_user_id")
    if recipient:
        groups.add(user_group(recipient))
    for group in groups:
        async_to_sync(layer.group_send)(group, message)
