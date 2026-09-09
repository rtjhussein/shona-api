"""Rule-version identity tests (correction pass, Finding 5).

Policy: the rule_set_version reported to API consumers must identify the rules
actually executed. Public endpoints validate the serving release's declared
version against ``MORPHOLOGY_RULES_VERSION`` and refuse mismatches with a
structured configuration error instead of silently serving different rules
under the old label. ``data_release`` identity stays separate.
"""

import pytest
from django.core.cache import caches

from shona_api.api_auth.models import APIKey
from shona_api.editorial.models import ReviewState
from shona_api.lexicon.models import Lemma
from shona_api.morphology.services import MORPHOLOGY_RULES_VERSION
from shona_api.releases.models import DataRelease


@pytest.fixture(autouse=True)
def version_gate_settings(settings):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "morphology-rules-version-tests",
        }
    }
    caches["default"].clear()


@pytest.fixture
def stale_release():
    return DataRelease.objects.create(
        version="2026.08.0",
        label="Stale rules label release",
        rule_set_version="morphology-rules-v2",
        is_current=True,
    )


@pytest.fixture
def api_key():
    _, raw_key = APIKey.objects.create_key(
        name="Rules version client",
        plan=APIKey.Plan.DEVELOPER,
        rate_limit_per_minute=60,
    )
    return raw_key


def make_verb(headword):
    return Lemma.objects.create(
        headword=headword,
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        part_of_speech_code="vt",
        part_of_speech_label="transitive verb",
        provenance={"source_key": "source_hannan", "entry_locator": "fixture:version"},
        review_state=ReviewState.PUBLISHED,
    )


def auth(client, api_key):
    client.defaults["HTTP_AUTHORIZATION"] = f"Api-Key {api_key}"
    return client


@pytest.mark.django_db
def test_analyze_refuses_stale_rules_version(client, api_key, stale_release):
    make_verb("-buda")
    response = auth(client, api_key).post(
        "/v1/analyze", {"text": "ndinobuda"}, content_type="application/json"
    )
    assert response.status_code == 503
    error = response.json()["error"]
    assert error["code"] == "MORPHOLOGY_RULES_VERSION_UNSUPPORTED"
    assert error["detail"]["received"] == "morphology-rules-v2"
    assert error["detail"]["implemented"] == MORPHOLOGY_RULES_VERSION
    assert "ensure_current_release" in error["detail"]["setup_command"]
    # The response must not silently rewrite or echo the stale label.
    assert "rule_set_version" not in response.json()


@pytest.mark.django_db
def test_generate_refuses_stale_rules_version(client, api_key, stale_release):
    lemma = make_verb("-kora")
    response = auth(client, api_key).post(
        "/v1/generate",
        {
            "lemma_public_id": lemma.public_id,
            "features": {
                "generation_type": "verb_form",
                "subject": {"type": "person", "person": "first", "number": "singular"},
                "tense_aspect": "present",
                "polarity": "positive",
                "extensions": [{"type": "reversive", "style": "long"}],
            },
        },
        content_type="application/json",
    )
    assert response.status_code == 503
    error = response.json()["error"]
    assert error["code"] == "MORPHOLOGY_RULES_VERSION_UNSUPPORTED"
    assert error["detail"]["received"] == "morphology-rules-v2"


@pytest.mark.django_db
def test_search_reports_unavailable_enrichment_on_stale_rules_version(
    client, api_key, stale_release
):
    make_verb("-buda")
    response = auth(client, api_key).get("/v1/search", {"q": "ndinobudisa"})
    # Search itself stays available; the enrichment state is explicit.
    assert response.status_code == 200
    body = response.json()["data"]
    enrichment = body["morphology_enrichment"]
    assert enrichment["status"] == "unavailable"
    assert enrichment["code"] == "MORPHOLOGY_RULES_VERSION_UNSUPPORTED"
    assert enrichment["detail"]["implemented"] == MORPHOLOGY_RULES_VERSION
    assert "morphology" not in body


@pytest.mark.django_db
def test_current_rules_version_serves_and_reports_itself(client, api_key):
    DataRelease.objects.create(
        version="2026.09.0",
        label="Implemented rules release",
        rule_set_version=MORPHOLOGY_RULES_VERSION,
        is_current=True,
    )
    lemma = make_verb("-kora")
    response = auth(client, api_key).post(
        "/v1/generate",
        {
            "lemma_public_id": lemma.public_id,
            "features": {
                "generation_type": "verb_form",
                "subject": {"type": "person", "person": "first", "number": "singular"},
                "tense_aspect": "present",
                "polarity": "positive",
                "extensions": [{"type": "reversive", "style": "long"}],
            },
        },
        content_type="application/json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["generated"]["form"] == "ndinokoronora"
    # The reported version identifies the executed rules, and the envelope
    # keeps data-release identity separate.
    assert body["data"]["rule_set_version"] == MORPHOLOGY_RULES_VERSION
    assert body["rule_set_version"] == MORPHOLOGY_RULES_VERSION
    assert body["data_release"] == "2026.09.0"
