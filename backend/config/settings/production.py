import os

from .base import *  # noqa: F403

if SECRET_KEY == "unsafe-development-only-key":  # noqa: F405
    raise RuntimeError("DJANGO_SECRET_KEY must be set in production")

SECURE_SSL_REDIRECT = os.getenv("DJANGO_SECURE_SSL_REDIRECT", "true").lower() == "true"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
