import json

from django.core.management import call_command
from django.test import Client
from django.urls import reverse

from config.settings.base import BASE_DIR
from shona_api.api_docs.spec import build_openapi_spec


def test_openapi_spec_is_published_without_api_auth():
    response = Client().get(reverse("openapi-spec"))

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"
    body = response.json()
    assert body["openapi"] == "3.1.0"
    assert body["info"]["title"] == "Shona API"
    assert "/v1/search" in body["paths"]
    assert "/v1/lemmas/{public_id}" in body["paths"]
    assert "ApiKeyAuth" in body["components"]["securitySchemes"]


def test_committed_openapi_spec_matches_generator():
    spec_path = BASE_DIR / "docs" / "openapi.json"

    assert json.loads(spec_path.read_text(encoding="utf-8")) == build_openapi_spec()


def test_openapi_generator_command_can_write_spec(tmp_path):
    output_path = tmp_path / "openapi.json"

    call_command("generate_openapi_spec", "--output", str(output_path))

    assert json.loads(output_path.read_text(encoding="utf-8")) == build_openapi_spec()


def test_developer_quickstart_documents_current_public_api_examples():
    quickstart = (BASE_DIR / "docs" / "developer_quickstart.md").read_text(
        encoding="utf-8"
    )

    assert "Authorization: Api-Key" in quickstart
    assert "GET /v1/search?q=buda" in quickstart
    assert "GET /v1/lemmas/{public_id}" in quickstart
    assert "GET /v1/figurative-expressions/tsumo" in quickstart
    assert "GET /v1/figurative-expressions/madimikira" in quickstart
    assert "POST /v1/analyze" in quickstart
    assert "POST /v1/generate" in quickstart
