import importlib

from django.conf import settings


def test_redis_cache_and_celery_broker_are_configured_from_shared_url():
    # Assert on the base wiring itself: test settings intentionally swap
    # CACHES for LocMemCache, so the effective settings object is the wrong
    # lens for this contract.
    base = importlib.import_module("config.settings.base")

    assert base.REDIS_URL == "redis://localhost:6379/0"
    assert base.CACHES["default"]["BACKEND"] == "django_redis.cache.RedisCache"
    assert base.CACHES["default"]["LOCATION"] == base.REDIS_URL
    assert base.CACHES["default"]["OPTIONS"]["CLIENT_CLASS"] == (
        "django_redis.client.DefaultClient"
    )
    assert base.CELERY_BROKER_URL == base.REDIS_URL
    assert base.CELERY_RESULT_BACKEND == base.REDIS_URL


def test_celery_app_initializes_from_django_settings():
    from config.celery import app

    assert app.main == "shona_api"
    assert app.conf.broker_url == settings.CELERY_BROKER_URL
    assert app.conf.result_backend == settings.CELERY_RESULT_BACKEND
    assert app.conf.task_always_eager is settings.CELERY_TASK_ALWAYS_EAGER


def test_observability_logging_and_metrics_hook_are_available():
    assert "json" in settings.LOGGING["formatters"]
    assert "shona_api" in settings.LOGGING["loggers"]

    from shona_api.observability.metrics import record_metric

    metric = record_metric(
        "infra.scaffold.ready",
        value=1,
        tags={"component": "test"},
    )

    assert metric == {
        "name": "infra.scaffold.ready",
        "value": 1,
        "tags": {"component": "test"},
    }


def test_postgres_search_extension_migration_declares_required_extensions():
    migration = importlib.import_module(
        "shona_api.infra.migrations.0001_enable_postgres_search_extensions"
    )

    assert migration.POSTGRES_SEARCH_EXTENSIONS == ("pg_trgm", "unaccent")
