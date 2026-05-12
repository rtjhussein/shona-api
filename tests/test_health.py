from rest_framework.test import APIClient


def test_health_endpoint_returns_status_and_version(settings):
    settings.APP_VERSION = "test-version"
    client = APIClient()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": "test-version",
    }
