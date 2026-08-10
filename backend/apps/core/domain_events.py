import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DomainEvent:
    event_name: str
    entity_type: str
    entity_id: object
    company_id: object = None
    actor_user_id: object = None
    actor_employee_id: object = None
    action: str = "UPDATE"
    module: str = "core"
    summary: str = ""
    metadata: dict = field(default_factory=dict)
    changes: dict = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=timezone.now)
    correlation_id: uuid.UUID = field(default_factory=uuid.uuid4)


_subscribers: dict[str, Callable[[DomainEvent], None]] = {}
_after_commit_subscribers: dict[str, Callable[[DomainEvent], None]] = {}


def subscribe(name, callback, *, after_commit=False):
    target = _after_commit_subscribers if after_commit else _subscribers
    target[name] = callback


def _dispatch_after_commit(event):
    for name, callback in tuple(_after_commit_subscribers.items()):
        try:
            callback(event)
        except Exception:  # notification failure must not invalidate a committed business action
            logger.exception("Post-commit domain-event subscriber failed", extra={"subscriber": name})


def publish(event):
    for callback in tuple(_subscribers.values()):
        callback(event)
    transaction.on_commit(lambda: _dispatch_after_commit(event))
    return event
