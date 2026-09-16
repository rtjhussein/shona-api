"""Explicit evaluation settings: isolated SQLite chosen before any DB access.

Unlike the dev/test settings, this module never consults ``DATABASE_URL`` (the
project ``.env`` is authoritative there via ``overwrite=True`` and would win).
The standalone runner exports ``EVAL_DB_PATH`` (an empty temporary directory
file it owns) before ``django.setup()``; a missing variable fails fast here,
before any connection exists.
"""

import os

from .test import *  # noqa: F401,F403

ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "source-backed-eval-standalone",
    }
}

_EVAL_DB_PATH = os.environ.get("EVAL_DB_PATH")
if not _EVAL_DB_PATH:
    raise RuntimeError(
        "EVAL_DB_PATH is required by config.settings.eval and was not set. "
        "Use tools/evaluate_source_backed.py, which creates an isolated "
        "temporary database and exports EVAL_DB_PATH before django.setup()."
    )

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": _EVAL_DB_PATH,
    }
}
