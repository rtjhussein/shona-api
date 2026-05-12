# Shona API

Foundation Django REST API for the Shona language platform.

## Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
python manage.py migrate
python manage.py runserver
```

The health endpoint is available at `GET /health`.

Developer quickstart and endpoint documentation are available in
`docs/developer_quickstart.md`. The OpenAPI spec is published at
`GET /openapi.json` and committed at `docs/openapi.json`.

Local development expects Postgres and Redis to be available. Redis is used as
the configured Django cache backend and Celery broker/result backend.

## Configuration

Runtime configuration is read from environment variables, with `.env` supported for local development.

- `DJANGO_SETTINGS_MODULE`: settings module, usually `config.settings.dev`
- `SECRET_KEY`: Django secret key
- `DEBUG`: enables debug mode in local development
- `ALLOWED_HOSTS`: comma-separated host allowlist
- `DATABASE_URL`: database URL, expected to be Postgres outside test defaults
- `REDIS_URL`: shared Redis URL used by default cache and Celery settings
- `CELERY_BROKER_URL`: Celery broker URL, defaults to `REDIS_URL`
- `CELERY_RESULT_BACKEND`: Celery result backend URL, defaults to `REDIS_URL`
- `CELERY_TASK_ALWAYS_EAGER`: executes Celery tasks inline, enabled in tests
- `CELERY_TASK_EAGER_PROPAGATES`: propagates eager task exceptions
- `LOG_LEVEL`: log level for `shona_api` loggers
- `APP_VERSION`: version string returned by `/health`

## Infrastructure

Postgres search extensions are installed through the `shona_api.infra`
migration path:

```powershell
python manage.py migrate infra
```

The migration enables `pg_trgm` and `unaccent` when the active database vendor
is Postgres. Non-Postgres test databases skip that SQL.

Celery initializes from `config.celery` and discovers Django app tasks. Start a
worker once Redis is running:

```powershell
celery -A config worker --loglevel=INFO
```

Observability starts with structured console logging for `shona_api` loggers and
a small `record_metric` hook in `shona_api.observability.metrics`.

## Tests

```powershell
pytest
```
