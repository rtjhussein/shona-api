import importlib

from django.conf import settings


def test_redis_cache_and_celery_broker_are_configured_from_shared_url():
    assert settings.REDIS_URL == "redis://localhost:6379/0"
    assert settings.CACHES["default"]["BACKEND"] == "django_redis.cache.RedisCache"
    assert settings.CACHES["default"]["LOCATION"] == settings.REDIS_URL
    assert settings.CACHES["default"]["OPTIONS"]["CLIENT_CLASS"] == (
        "django_redis.client.DefaultClient"
    )
    assert settings.CELERY_BROKER_URL == settings.REDIS_URL
    assert settings.CELERY_RESULT_BACKEND == settings.REDIS_URL


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
