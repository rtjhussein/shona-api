from .dev import *


# Copy this file to config/settings/local.py for personal machine-only overrides.
# config/settings/local.py is gitignored and must not be used by CI or production.

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "shona-api-local",
    }
}

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
