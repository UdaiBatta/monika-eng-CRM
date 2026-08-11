from .base import *  # noqa: F403

DEBUG = True
CSRF_TRUSTED_ORIGINS = ["http://127.0.0.1:5173", "http://localhost:5173"]

# Local development is intentionally Docker-free. PostgreSQL runs as the
# native Windows service; cache and background jobs stay in-process.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "monika-erp-development",
    }
}
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
