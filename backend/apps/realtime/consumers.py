from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core.exceptions import ValidationError

from apps.core.entity_registry import entity_company_id, resolve_entity
from apps.organization.models import Employee
from apps.rbac.services import has_permission

from .groups import company_group, entity_group, user_group
from .presence import list_presence, remove_presence, touch_presence

ENTITY_VIEW_PERMISSIONS = {
    "customer": "crm.customer.view",
    "enquiry": "crm.enquiry.view",
    "engineering_feasibility_review": "crm.engineering_review.view",
    "commercial_estimate": "crm.estimate.view",
    "external_enquiry_submission": "crm.external_enquiry.view",
    "quotation": "crm.quotation.view",
    "quotation_revision": "crm.quotation.view",
}


class WorkspaceConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        employee = await self._employee(user)
        if not employee:
            await self.close(code=4401)
            return
        self.company_id = str(employee.company_id)
        self.user_id = str(user.pk)
        self.entity_subscriptions = set()
        await self.channel_layer.group_add(company_group(self.company_id), self.channel_name)
        await self.channel_layer.group_add(user_group(self.user_id), self.channel_name)
        await self.accept()
        await self.send_json({"type": "connection.ready"})

    async def disconnect(self, _code):
        if not hasattr(self, "company_id"):
            return
        for entity_type, entity_id in tuple(self.entity_subscriptions):
            await self._remove_presence(entity_type, entity_id)
            await self.channel_layer.group_discard(
                entity_group(entity_type, entity_id), self.channel_name
            )
        await self.channel_layer.group_discard(company_group(self.company_id), self.channel_name)
        await self.channel_layer.group_discard(user_group(self.user_id), self.channel_name)

    async def receive_json(self, content, **_kwargs):
        message_type = content.get("type")
        if message_type == "subscribe":
            await self._subscribe(content)
        elif message_type == "unsubscribe":
            await self._unsubscribe(content)
        elif message_type == "presence.heartbeat":
            await self._heartbeat(content)
        else:
            await self.send_json({"type": "error", "code": "unsupported_message"})

    async def _subscribe(self, content):
        entity_type = content.get("entity_type")
        entity_id = str(content.get("entity_id", ""))
        if not await self._can_view(entity_type, entity_id):
            await self.send_json({"type": "error", "code": "subscription_denied"})
            return
        subscription = (entity_type, entity_id)
        if subscription not in self.entity_subscriptions:
            self.entity_subscriptions.add(subscription)
            await self.channel_layer.group_add(
                entity_group(entity_type, entity_id), self.channel_name
            )
        await self._broadcast_presence(entity_type, entity_id, touch=True)

    async def _unsubscribe(self, content):
        entity_type = content.get("entity_type")
        entity_id = str(content.get("entity_id", ""))
        subscription = (entity_type, entity_id)
        if subscription in self.entity_subscriptions:
            self.entity_subscriptions.remove(subscription)
            await self._remove_presence(entity_type, entity_id)
            await self.channel_layer.group_discard(
                entity_group(entity_type, entity_id), self.channel_name
            )

    async def _heartbeat(self, content):
        entity_type = content.get("entity_type")
        entity_id = str(content.get("entity_id", ""))
        if (entity_type, entity_id) in self.entity_subscriptions:
            await self._broadcast_presence(entity_type, entity_id, touch=True)

    async def _broadcast_presence(self, entity_type, entity_id, *, touch=False):
        if touch:
            users = await database_sync_to_async(touch_presence)(
                self.company_id, entity_type, entity_id, self.scope["user"]
            )
        else:
            users = await database_sync_to_async(list_presence)(
                self.company_id, entity_type, entity_id
            )
        await self.channel_layer.group_send(
            entity_group(entity_type, entity_id),
            {
                "type": "presence.changed",
                "payload": {
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "users": users,
                },
            },
        )

    async def _remove_presence(self, entity_type, entity_id):
        users = await database_sync_to_async(remove_presence)(
            self.company_id, entity_type, entity_id, self.user_id
        )
        await self.channel_layer.group_send(
            entity_group(entity_type, entity_id),
            {
                "type": "presence.changed",
                "payload": {
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "users": users,
                },
            },
        )

    async def domain_event(self, event):
        await self.send_json({"type": "domain.event", **event["payload"]})

    async def presence_changed(self, event):
        await self.send_json({"type": "presence.changed", **event["payload"]})

    @database_sync_to_async
    def _employee(self, user):
        if not user or not user.is_authenticated or not user.is_active:
            return None
        return Employee.objects.filter(user=user, user__is_active=True).first()

    @database_sync_to_async
    def _can_view(self, entity_type, entity_id):
        permission = ENTITY_VIEW_PERMISSIONS.get(entity_type)
        if not permission or not entity_id:
            return False
        try:
            entity = resolve_entity(entity_type, entity_id)
        except ValidationError:
            return False
        return str(entity_company_id(entity)) == self.company_id and has_permission(
            self.scope["user"], permission, entity
        )
