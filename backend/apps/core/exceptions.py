from rest_framework.views import exception_handler


def _first_value(value):
    if isinstance(value, dict):
        for item in value.values():
            resolved = _first_value(item)
            if resolved is not None:
                return resolved
        return None
    if isinstance(value, (list, tuple)):
        for item in value:
            resolved = _first_value(item)
            if resolved is not None:
                return resolved
        return None
    return value


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    detail = response.data
    message = _first_value(detail)
    codes = exc.get_codes() if hasattr(exc, "get_codes") else None
    code = _first_value(codes) or getattr(exc, "default_code", "api_error")
    response.data = {
        "error": {
            "status": response.status_code,
            "code": str(code),
            "message": str(message or "The request could not be completed."),
            "details": detail,
        }
    }
    return response
