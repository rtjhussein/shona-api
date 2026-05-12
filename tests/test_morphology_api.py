import pytest
from django.core.cache import caches

from shona_api.api_auth.models import APIKey
from shona_api.editorial.models import ReviewState
from shona_api.lexicon.models import Lemma, NounClass
from shona_api.releases.models import DataRelease


@pytest.fixture(autouse=True)
def morphology_api_settings(settings):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "morphology-api-tests",
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
        name="Morphology client",
        plan=APIKey.Plan.DEVELOPER,
        rate_limit_per_minute=5,
    )
    return raw_key


@pytest.fixture
def verb_lemma(current_release):
    return Lemma.objects.create(
        headword="-buda",
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        part_of_speech_code="vi",
        part_of_speech_label="intransitive verb",
        provenance={
            "source_key": "source_hannan",
            "entry_locator": "fixture:buda",
        },
        review_state=ReviewState.APPROVED,
    )


@pytest.mark.django_db
def test_analyze_endpoint_returns_bounded_positive_present_verb_analysis(
    client, api_key, current_release, verb_lemma
):
    response = client.post(
        "/v1/analyze",
        {"text": "NdINobuda"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["api_version"] == "v1"
    assert body["data_release"] == current_release.version
    assert body["rule_set_version"] == current_release.rule_set_version
    assert body["data"]["rule_set_version"] == current_release.rule_set_version
    assert body["data"]["query"] == {
        "raw": "NdINobuda",
        "normalized": "ndinobuda",
        "normalizer": "shona-orthography-normalizer-v1",
    }
    assert body["data"]["count"] == 1
    analysis = body["data"]["analyses"][0]
    assert analysis["analysis_type"] == "verb_form"
    assert analysis["confidence"] == 0.86
    assert analysis["rule_id"] == "fortune.verbal.slots.001"
    assert analysis["lemma"] == {
        "public_id": verb_lemma.public_id,
        "headword": "-buda",
        "normalized_headword": "buda",
        "part_of_speech_code": "vi",
    }
    assert analysis["slots"] == {
        "subject": {
            "surface": "ndi",
            "type": "person",
            "label": "1st person singular subject concord",
            "person": "first",
            "number": "singular",
        },
        "tense_aspect": {
            "surface": "no",
            "value": "present",
            "label": "positive present marker",
        },
        "polarity": {
            "surface": "",
            "value": "positive",
            "label": "No negative marker detected in supported v1 pattern.",
        },
        "object": None,
        "verb_stem": {
            "surface": "buda",
            "lemma_public_id": verb_lemma.public_id,
        },
        "final_vowel": {
            "surface": "a",
            "value": "a",
        },
    }
    assert analysis["phonology"]["phonology_inventory_version"] == "shona-core-v1"
    assert analysis["phonology"]["syllables"] == ["ndi", "no", "bu", "da"]
    assert "tone" in analysis["limitations"][1]


@pytest.mark.django_db
def test_analyze_endpoint_can_use_reviewed_noun_class_subject_concord(
    client, api_key, current_release, verb_lemma
):
    noun_class = NounClass.objects.create(
        class_number="2",
        display_order=2,
        label="Class 2",
        nominal_prefix="va",
        subject_concord="va",
        review_state=ReviewState.APPROVED,
    )

    response = client.post(
        "/v1/analyze",
        {"text": "vanobuda"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert response.status_code == 200
    analysis = response.json()["data"]["analyses"][0]
    assert analysis["confidence"] == 0.78
    assert analysis["slots"]["subject"] == {
        "surface": "va",
        "type": "noun_class",
        "label": "Class 2",
        "class_number": "2",
        "noun_class_public_id": noun_class.public_id,
    }


@pytest.mark.django_db
def test_analyze_endpoint_requires_text_string(client, api_key, current_release):
    response = client.post(
        "/v1/analyze",
        {"form": "ndinobuda"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert response.status_code == 400
    assert response.json() == {
        "api_version": "v1",
        "error": {
            "code": "ANALYSIS_TEXT_REQUIRED",
            "message": "Analysis requires a non-empty 'text' string.",
            "detail": {"field": "text", "expected_type": "string"},
        },
    }


@pytest.mark.django_db
def test_analyze_endpoint_returns_structured_unsupported_failure(
    client, api_key, current_release, verb_lemma
):
    response = client.post(
        "/v1/analyze",
        {"text": "handibude"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert response.status_code == 422
    body = response.json()
    assert body["api_version"] == "v1"
    assert body["error"]["code"] == "ANALYSIS_UNSUPPORTED"
    assert body["error"]["detail"] == {
        "normalized": "handibude",
        "supported_shape": "subject_concord + no + verb_stem",
        "supported_rule_ids": ["fortune.verbal.slots.001"],
    }
