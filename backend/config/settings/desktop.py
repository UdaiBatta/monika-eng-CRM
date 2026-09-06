from .base import *  # noqa: F403
from .base import BASE_DIR

# Packaged Windows desktop build: single user, single process, no separate
# services to install or start. SQLite replaces Postgres (see
# apps.core.sqlite_compat for the one behavioral gap this opens: FOR UPDATE
# OF isn't supported, harmless with no concurrent writers). Cache/channels
# reuse the same in-process backends the Docker-free dev setup already
# proves out in development.py, and Celery runs its one periodic task
# in-process instead of needing a broker and worker.
DEBUG = False
IS_DESKTOP_BUILD = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

DATA_DIR = Path(os.getenv("MONIKA_DESKTOP_DATA_DIR", BASE_DIR / "desktop-data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(DATA_DIR / "monika-erp.sqlite3"),
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "monika-erp-desktop",
    }
}
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

LOCAL_PRIVATE_STORAGE_ROOT = str(DATA_DIR / "private_storage")
