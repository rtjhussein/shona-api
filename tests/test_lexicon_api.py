import pytest
from django.core.cache import caches
from rest_framework.test import APIClient

from shona_api.api_auth.models import APIKey
from shona_api.editorial.models import ReviewState
from shona_api.lexicon.models import Form, Lemma, Sense, ToneRecord
from shona_api.releases.models import DataRelease


@pytest.fixture(autouse=True)
def lexical_api_settings(settings):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "lexical-api-tests",
        }
    }
    caches["default"].clear()


@pytest.fixture
def current_release():
    return DataRelease.objects.create(
        version="2026.05.0",
        label="May 2026 release",
        rule_set_version="morphology-rules-v2",
        is_current=True,
    )


@pytest.fixture
def api_key():
    _, raw_key = APIKey.objects.create_key(
        name="Lexical client",
        plan=APIKey.Plan.DEVELOPER,
        rate_limit_per_minute=5,
    )
    return raw_key


@pytest.fixture
def canonical_lemma(current_release):
    provenance = {
        "source_key": "source_hannan",
        "entry_locator": "fixture:buda",
    }
    lemma = Lemma.objects.create(
        headword="-buda",
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        part_of_speech_code="vi",
        part_of_speech_label="intransitive verb",
        dialects=["K", "Ko", "M", "Z"],
        provenance=provenance,
        review_state=ReviewState.APPROVED,
    )
    sense = Sense.objects.create(
        lemma=lemma,
        number=1,
        definition="Come out.",
        grammar=["vi"],
        provenance=provenance,
        review_state=ReviewState.APPROVED,
    )
    tone = ToneRecord.objects.create(
        lemma=lemma,
        form=None,
        pattern="H-L",
        notation_system=ToneRecord.NotationSystem.HANNAN_BRACKET,
        provenance=provenance,
        review_state=ReviewState.APPROVED,
    )
    form = Form.objects.create(
        lemma=lemma,
        sense=sense,
        form_text="mbudo",
        form_kind=Form.FormKind.DERIVED,
        grammar=["nominalized"],
        provenance=provenance,
        review_state=ReviewState.APPROVED,
    )
    tone.form = form
    tone.save(update_fields=("form",))
    return lemma, sense, tone, form


@pytest.mark.django_db
def test_lemma_read_endpoint_returns_envelope_with_core_lexical_records(
    client, api_key, current_release, canonical_lemma
):
    lemma, sense, tone, form = canonical_lemma

    response = client.get(
        f"/v1/lemmas/{lemma.public_id}",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["api_version"] == "v1"
    assert body["data_release"] == current_release.version
    assert body["rule_set_version"] == current_release.rule_set_version
    assert body["generated_at"].endswith("Z")
    assert body["data"] == {
        "lemma": {
            "public_id": lemma.public_id,
            "headword": "-buda",
            "normalized_headword": "buda",
            "headword_kind": Lemma.HeadwordKind.VERB_STEM,
            "part_of_speech_code": "vi",
            "part_of_speech_label": "intransitive verb",
            "noun_class": None,
            "dialects": ["K", "Ko", "M", "Z"],
            "comparative_bantu_marker": False,
            "learner_level": Lemma.LearnerLevel.UNKNOWN,
            "curriculum_stage": Lemma.CurriculumStage.UNKNOWN,
            "curriculum_domains": [],
            "learning_functions": [],
            "communication_contexts": [],
            "register_tags": [],
            "learner_source_links": [],
            "first_appearance_source_key": "",
            "first_appearance_locator": "",
            "first_appearance_unit": "",
            "first_appearance_lesson": None,
            "first_appearance_page": "",
            "frequency_tier": Lemma.FrequencyTier.UNKNOWN,
            "frequency_score": 0.0,
            "phonology_inventory_version": "shona-core-v1",
            "graphemes": ["b", "u", "d", "a"],
            "grapheme_count": 4,
            "syllables": ["bu", "da"],
            "syllable_count": 2,
            "provenance": {
                "source_key": "source_hannan",
                "entry_locator": "fixture:buda",
            },
            "revision": 1,
            "review_state": ReviewState.APPROVED,
        },
        "senses": [
            {
                "public_id": sense.public_id,
                "number": 1,
                "definition": "Come out.",
                "dialects": [],
                "grammar": ["vi"],
                "examples": [],
                "cross_references": [],
                "provenance": {
                    "source_key": "source_hannan",
                    "entry_locator": "fixture:buda",
                },
                "revision": 1,
                "review_state": ReviewState.APPROVED,
            }
        ],
        "tone_records": [
            {
                "public_id": tone.public_id,
                "pattern": "H-L",
                "notation_system": ToneRecord.NotationSystem.HANNAN_BRACKET,
                "note": "",
                "form_public_id": form.public_id,
                "provenance": {
                    "source_key": "source_hannan",
                    "entry_locator": "fixture:buda",
                },
                "revision": 1,
                "review_state": ReviewState.APPROVED,
            }
        ],
        "forms": [
            {
                "public_id": form.public_id,
                "form_text": "mbudo",
                "normalized_form": "mbudo",
                "form_kind": Form.FormKind.DERIVED,
                "dialects": [],
                "grammar": ["nominalized"],
                "sense_public_id": sense.public_id,
                "phonology_inventory_version": "shona-core-v1",
                "graphemes": ["mb", "u", "d", "o"],
                "grapheme_count": 4,
                "syllables": ["mbu", "do"],
                "syllable_count": 2,
                "provenance": {
                    "source_key": "source_hannan",
                    "entry_locator": "fixture:buda",
                },
                "revision": 1,
                "review_state": ReviewState.APPROVED,
            }
        ],
    }


@pytest.mark.django_db
def test_lemma_read_endpoint_returns_stable_not_found_error(client, api_key, current_release):
    response = client.get(
        "/v1/lemmas/lemma_missing",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert response.status_code == 404
    assert response.json() == {
        "api_version": "v1",
        "error": {
            "code": "LEMMA_NOT_FOUND",
            "message": "No lemma found for public_id 'lemma_missing'",
            "detail": None,
        },
    }


@pytest.mark.django_db
def test_lemma_read_endpoint_uses_existing_api_key_auth(client, current_release, canonical_lemma):
    lemma, *_ = canonical_lemma

    response = client.get(f"/v1/lemmas/{lemma.public_id}")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication credentials were not provided."


@pytest.mark.django_db
def test_lemma_read_endpoint_rejects_invalid_api_key(client, current_release, canonical_lemma):
    lemma, *_ = canonical_lemma

    response = client.get(
        f"/v1/lemmas/{lemma.public_id}",
        HTTP_AUTHORIZATION="Api-Key shona_sk_invalid_missing_key",
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid API key."


@pytest.mark.django_db
def test_search_endpoint_returns_exact_lemma_match(
    client, api_key, current_release, canonical_lemma
):
    lemma, *_ = canonical_lemma

    response = client.get(
        "/v1/search",
        {"q": " -BUDA "},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["api_version"] == "v1"
    assert body["data_release"] == current_release.version
    assert body["rule_set_version"] == current_release.rule_set_version
    assert body["data"]["query"] == {
        "raw": " -BUDA ",
        "normalized": "buda",
        "normalizer": "shona-orthography-normalizer-v1",
    }
    assert body["data"]["count"] == 1
    assert body["data"]["results"][0]["result_type"] == "lemma"
    assert body["data"]["results"][0]["match_type"] == "exact_lemma"
    assert body["data"]["results"][0]["lemma"]["public_id"] == lemma.public_id


@pytest.mark.django_db
def test_search_endpoint_returns_exact_form_match(
    client, api_key, current_release, canonical_lemma
):
    lemma, _, _, form = canonical_lemma

    response = client.get(
        "/v1/search",
        {"q": "mbudo"},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["count"] == 1
    assert body["data"]["results"][0]["result_type"] == "form"
    assert body["data"]["results"][0]["match_type"] == "exact_form"
    assert body["data"]["results"][0]["lemma"]["public_id"] == lemma.public_id
    assert body["data"]["results"][0]["form"]["public_id"] == form.public_id


@pytest.mark.django_db
def test_search_endpoint_returns_structured_zero_result(client, api_key, current_release):
    response = client.get(
        "/v1/search",
        {"q": "zvisipo"},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["count"] == 0
    assert body["data"]["results"] == []
    assert body["data"]["zero_result"] == {
        "code": "NO_MATCH",
        "message": "No reviewed lemma or form matched the query.",
    }


@pytest.mark.django_db
def test_search_endpoint_requires_non_empty_query(client, api_key, current_release):
    response = client.get(
        "/v1/search",
        {"q": "   "},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert response.status_code == 400
    assert response.json() == {
        "api_version": "v1",
        "error": {
            "code": "SEARCH_QUERY_REQUIRED",
            "message": "Search requires a non-empty 'q' query parameter.",
            "detail": None,
        },
    }
