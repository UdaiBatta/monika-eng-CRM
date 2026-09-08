"""Standalone self-check for the SQLite select_for_update patch.

Not a pytest test: the project's test suite runs against Postgres
(pytest.ini), and this patch only matters for the desktop SQLite build.
Run directly against desktop settings instead:

    DJANGO_SETTINGS_MODULE=config.settings.desktop python apps/core/sqlite_compat_check.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.desktop")

import django  # noqa: E402


def main():
    django.setup()
    from django.db import connection, transaction
    from django.db.utils import NotSupportedError

    assert connection.vendor == "sqlite", "this check only makes sense against the desktop SQLite settings"

    from apps.accounts.models import User

    with transaction.atomic():
        try:
            list(User.objects.select_for_update(of=("self",)).filter(pk__isnull=False))
        except NotSupportedError:
            raise AssertionError(
                "select_for_update(of=...) raised NotSupportedError on SQLite — "
                "apps.core.sqlite_compat patch is not active or was not applied before this query"
            )

    print("OK: select_for_update(of=...) is silently downgraded on SQLite as expected")


if __name__ == "__main__":
    main()
