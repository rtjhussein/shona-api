import pytest
from django.core.cache import caches
from django.core.management import call_command
from django.urls import path
from redis.exceptions import ConnectionError as RedisConnectionError
from rest_framework.response import Response
from rest_framework.views import APIView

from shona_api.api_auth.models import APIKey
from shona_api.api_auth.throttles import APIKeyRateThrottle


class ProtectedEchoView(APIView):
    def get(self, request):
        return Response(
            {
                "client": request.auth.name,
                "plan": request.auth.plan,
            }
        )


urlpatterns = [
    path("v1/protected", ProtectedEchoView.as_view(), name="protected-echo"),
]


@pytest.fixture(autouse=True)
def api_auth_settings(settings):
    settings.ROOT_URLCONF = __name__
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "api-auth-tests",
        }
    }
    caches["default"].clear()


@pytest.mark.django_db
def test_api_key_manager_returns_raw_key_once_and_stores_only_hash():
    api_key, raw_key = APIKey.objects.create_key(
        name="Docs app",
        plan=APIKey.Plan.DEVELOPER,
        rate_limit_per_minute=5,
    )

    api_key.refresh_from_db()

    assert raw_key.startswith("shona_sk_")
    assert api_key.prefix in raw_key
    assert raw_key not in api_key.key_hash
    assert api_key.verify(raw_key) is True


@pytest.mark.django_db
def test_valid_api_key_authenticates_protected_drf_endpoint(client):
    api_key, raw_key = APIKey.objects.create_key(
        name="Dictionary client",
        plan=APIKey.Plan.DEVELOPER,
        rate_limit_per_minute=5,
    )

    response = client.get(
        "/v1/protected",
        HTTP_AUTHORIZATION=f"Api-Key {raw_key}",
    )

    assert response.status_code == 200
    assert response.json() == {
        "client": "Dictionary client",
        "plan": APIKey.Plan.DEVELOPER,
    }
    assert response.headers["X-RateLimit-Limit"] == "5"
    assert response.headers["X-RateLimit-Remaining"] == "4"
    assert response.headers["X-RateLimit-Plan"] == APIKey.Plan.DEVELOPER

    api_key.refresh_from_db()
    assert api_key.last_used_at is not None


@pytest.mark.django_db
def test_invalid_api_key_is_rejected(client):
    response = client.get(
        "/v1/protected",
        HTTP_AUTHORIZATION="Api-Key shona_sk_invalid_missing_key",
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid API key."
    assert "X-RateLimit-Limit" not in response.headers


@pytest.mark.django_db
def test_api_key_rate_limit_blocks_requests_after_plan_limit(client):
    _, raw_key = APIKey.objects.create_key(
        name="Burst client",
        plan=APIKey.Plan.DEVELOPER,
        rate_limit_per_minute=2,
    )

    first = client.get("/v1/protected", HTTP_X_API_KEY=raw_key)
    second = client.get("/v1/protected", HTTP_X_API_KEY=raw_key)
    throttled = client.get("/v1/protected", HTTP_X_API_KEY=raw_key)

    assert first.status_code == 200
    assert first.headers["X-RateLimit-Remaining"] == "1"
    assert second.status_code == 200
    assert second.headers["X-RateLimit-Remaining"] == "0"
    assert throttled.status_code == 429
    assert throttled.headers["X-RateLimit-Limit"] == "2"
    assert throttled.headers["X-RateLimit-Remaining"] == "0"
    assert int(throttled.headers["X-RateLimit-Reset"]) > 0
    assert int(throttled.headers["Retry-After"]) > 0


def test_api_key_rate_throttle_falls_back_when_cache_is_unavailable(monkeypatch):
    class BrokenCache:
        def add(self, *args, **kwargs):
            raise RedisConnectionError("redis unavailable")

    monkeypatch.setattr("shona_api.api_auth.throttles.caches", {"default": BrokenCache()})

    throttle = APIKeyRateThrottle()

    assert throttle._cache() is throttle.fallback_cache


@pytest.mark.django_db
def test_create_api_key_command_prints_raw_key_without_storing_it(capsys):
    call_command(
        "create_api_key",
        "CLI client",
        "--plan",
        APIKey.Plan.STANDARD,
        "--rate-limit-per-minute",
        "7",
    )

    output = capsys.readouterr().out
    api_key = APIKey.objects.get(name="CLI client")
    raw_key = output.split("Raw key: ", 1)[1].splitlines()[0]

    assert api_key.plan == APIKey.Plan.STANDARD
    assert api_key.rate_limit_per_minute == 7
    assert api_key.verify(raw_key) is True
    assert raw_key not in api_key.key_hash
