from .context import request_context, reset_audit_context, set_audit_context


class AuditContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        context = request_context(request)
        token = set_audit_context(context)
        try:
            response = self.get_response(request)
            response["X-Request-ID"] = context.request_id
            return response
        finally:
            reset_audit_context(token)
