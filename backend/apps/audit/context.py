import uuid
from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class AuditContext:
    request_id: str = ""
    ip_address: str | None = None
    user_agent: str = ""


_current_context = ContextVar("audit_context", default=None)


def set_audit_context(context):
    return _current_context.set(context)


def reset_audit_context(token):
    _current_context.reset(token)


def get_audit_context():
    return _current_context.get() or AuditContext()


def request_context(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
    request_id = request.META.get("HTTP_X_REQUEST_ID", "")[:64] or str(uuid.uuid4())
    return AuditContext(
        request_id=request_id,
        ip_address=forwarded or request.META.get("REMOTE_ADDR"),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
    )
