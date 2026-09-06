"""Entrypoint for the bundled desktop build.

Runs migrations (a no-op after the first launch), creates the initial
admin account on a fresh database only, then starts the server the
Tauri sidecar talks to. Everything Django-specific lives here so the
Rust side only ever spawns one process and doesn't need to know about
management commands.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.desktop")

import django  # noqa: E402
from django.core.management import call_command  # noqa: E402

FIRST_RUN_ADMIN_EMAIL = "admin@monika.local"
FIRST_RUN_ADMIN_PASSWORD = "ChangeMe-First-Login"


def main():
    django.setup()
    from django.conf import settings
    from django.db import connection

    is_first_run = not os.path.exists(settings.DATABASES["default"]["NAME"])

    call_command("migrate", verbosity=0, interactive=False)

    if is_first_run:
        os.environ["DEV_ADMIN_EMAIL"] = FIRST_RUN_ADMIN_EMAIL
        os.environ["DEV_ADMIN_PASSWORD"] = FIRST_RUN_ADMIN_PASSWORD
        call_command("seed_development")
        print(f"First run: created admin account {FIRST_RUN_ADMIN_EMAIL}", flush=True)

    connection.close()

    host = os.getenv("MONIKA_DESKTOP_HOST", "127.0.0.1")
    port = os.getenv("MONIKA_DESKTOP_PORT", "8010")
    print(f"READY {host}:{port}", flush=True)
    call_command("runserver", f"{host}:{port}", use_reloader=False)


if __name__ == "__main__":
    sys.exit(main())
