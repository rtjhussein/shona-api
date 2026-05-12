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

## Configuration

Runtime configuration is read from environment variables, with `.env` supported for local development.

- `DJANGO_SETTINGS_MODULE`: settings module, usually `config.settings.dev`
- `SECRET_KEY`: Django secret key
- `DEBUG`: enables debug mode in local development
- `ALLOWED_HOSTS`: comma-separated host allowlist
- `DATABASE_URL`: database URL, expected to be Postgres outside test defaults
- `APP_VERSION`: version string returned by `/health`

## Tests

```powershell
pytest
```
