"""SQLite doesn't support SELECT ... FOR UPDATE OF, which every
select_for_update(of=(...)) call site in this codebase relies on. That
locking granularity only matters under concurrent writers; the bundled
desktop build is single-user and single-process, so on SQLite it's safe
to silently drop the `of` argument rather than touch every call site.
"""

from django.db import connections
from django.db.models.query import QuerySet

_original_select_for_update = QuerySet.select_for_update


def _select_for_update_sqlite_safe(self, nowait=False, skip_locked=False, of=(), no_key=False):
    db_alias = self.db or "default"
    if connections[db_alias].vendor == "sqlite":
        of = ()
    return _original_select_for_update(self, nowait=nowait, skip_locked=skip_locked, of=of, no_key=no_key)


def patch_select_for_update_for_sqlite():
    QuerySet.select_for_update = _select_for_update_sqlite_safe
