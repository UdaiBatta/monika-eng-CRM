from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    detail = response.data
    message = detail.get("detail") if isinstance(detail, dict) else None
    response.data = {
        "error": {
            "status": response.status_code,
            "code": getattr(exc, "default_code", "api_error"),
            "message": str(message or "The request could not be completed."),
            "details": detail,
        }
    }
    return response
