import pytest
import json
from django.core.cache import caches
from pathlib import Path

from shona_api.api_auth.models import APIKey
from shona_api.editorial.models import ReviewState
from shona_api.lexicon.models import Lemma, NounClass
from shona_api.releases.models import DataRelease


REAL_DATA_CORPUS_PATH = (
    Path(__file__).parent / "fixtures" / "morphology" / "real_data_present_verbs.json"
)


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
def corpus_api_key():
    _, raw_key = APIKey.objects.create_key(
        name="Morphology real-data corpus client",
        plan=APIKey.Plan.DEVELOPER,
        rate_limit_per_minute=60,
    )
    return raw_key


@pytest.fixture
def real_data_present_verb_corpus(current_release):
    records = json.loads(REAL_DATA_CORPUS_PATH.read_text(encoding="utf-8"))
    lemmas = {}
    for record in records:
        lemma = Lemma.objects.create(
            headword=record["headword"],
            headword_kind=Lemma.HeadwordKind.VERB_STEM,
            part_of_speech_code=record["part_of_speech_code"],
            part_of_speech_label=record["part_of_speech_label"],
            provenance={
                "source_key": "source_hannan",
                "source_location_reference": record["source_locator"],
                "regression_corpus": "real_data_present_verbs",
            },
            review_state=ReviewState.PUBLISHED,
        )
        lemmas[record["id"]] = lemma
    return records, lemmas


@pytest.fixture
def class_2_for_real_data_corpus(current_release):
    return NounClass.objects.create(
        class_number="2",
        display_order=2,
        label="Class 2",
        nominal_prefix="va",
        subject_concord="va",
        object_concord="va",
        review_state=ReviewState.PUBLISHED,
    )


@pytest.mark.django_db
def test_real_data_present_verb_corpus_analyzes_supported_forms(
    client,
    corpus_api_key,
    current_release,
    real_data_present_verb_corpus,
    class_2_for_real_data_corpus,
):
    records, lemmas = real_data_present_verb_corpus

    for record in records:
        lemma = lemmas[record["id"]]
        for case in record["supported_cases"]:
            response = client.post(
                "/v1/analyze",
                {"text": case["text"]},
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Api-Key {corpus_api_key}",
            )

            assert response.status_code == 200, case
            body = response.json()
            assert body["data"]["rule_set_version"] == current_release.rule_set_version
            assert body["data"]["count"] >= 1
            analysis = body["data"]["analyses"][0]
            assert analysis["rule_id"] == case["rule_id"]
            assert analysis["lemma"]["public_id"] == lemma.public_id
            assert analysis["slots"]["verb_stem"]["lemma_public_id"] == lemma.public_id
            if "object_surface" in case:
                assert analysis["slots"]["object"]["surface"] == case["object_surface"]
            if "subject_surface" in case:
                assert analysis["slots"]["subject"]["surface"] == case["subject_surface"]
            if "verb_stem_surface" in case:
                assert (
                    analysis["slots"]["verb_stem"]["surface"]
                    == case["verb_stem_surface"]
                )


@pytest.mark.django_db
def test_real_data_present_verb_corpus_generates_supported_forms(
    client,
    corpus_api_key,
    current_release,
    real_data_present_verb_corpus,
    class_2_for_real_data_corpus,
):
    records, lemmas = real_data_present_verb_corpus
    feature_by_case = {
        "positive_person_subject": {
            "generation_type": "verb_form",
            "subject": {"type": "person", "person": "first", "number": "singular"},
            "tense_aspect": "present",
            "polarity": "positive",
        },
        "negative_person_subject": {
            "generation_type": "verb_form",
            "subject": {"type": "person", "person": "first", "number": "singular"},
            "tense_aspect": "present",
            "polarity": "negative",
        },
        "positive_person_object": {
            "generation_type": "verb_form",
            "subject": {"type": "person", "person": "first", "number": "singular"},
            "object": {"type": "person", "person": "second", "number": "singular"},
            "tense_aspect": "present",
            "polarity": "positive",
        },
        "negative_person_object": {
            "generation_type": "verb_form",
            "subject": {"type": "person", "person": "first", "number": "singular"},
            "object": {"type": "person", "person": "second", "number": "singular"},
            "tense_aspect": "present",
            "polarity": "negative",
        },
        "positive_class_object_coalescence": {
            "generation_type": "verb_form",
            "subject": {"type": "noun_class", "class_number": "2"},
            "object": {"type": "noun_class", "class_number": "2"},
            "tense_aspect": "present",
            "polarity": "positive",
        },
        "negative_class_object_coalescence": {
            "generation_type": "verb_form",
            "subject": {"type": "noun_class", "class_number": "2"},
            "object": {"type": "noun_class", "class_number": "2"},
            "tense_aspect": "present",
            "polarity": "negative",
        },
        "positive_third_person_object": {
            "generation_type": "verb_form",
            "subject": {"type": "person", "person": "first", "number": "singular"},
            "object": {"type": "person", "person": "third", "number": "singular"},
            "tense_aspect": "present",
            "polarity": "positive",
        },
    }

    for record in records:
        lemma = lemmas[record["id"]]
        for case in record["supported_cases"]:
            response = client.post(
                "/v1/generate",
                {
                    "lemma_public_id": lemma.public_id,
                    "features": feature_by_case[case["name"]],
                },
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Api-Key {corpus_api_key}",
            )

            assert response.status_code == 200, case
            body = response.json()
            generated = body["data"]["generated"]
            assert body["data"]["rule_set_version"] == current_release.rule_set_version
            assert generated["form"] == case["text"]
            assert generated["rule_id"] == case["rule_id"]
            assert generated["lemma"]["public_id"] == lemma.public_id
            if "object_surface" in case:
                assert generated["slots"]["object"]["surface"] == case["object_surface"]


def test_real_data_present_verb_corpus_documents_future_unsupported_forms():
    records = json.loads(REAL_DATA_CORPUS_PATH.read_text(encoding="utf-8"))

    unsupported_forms = [
        item
        for record in records
        for item in record["unsupported_observed_forms"]
    ]

    assert unsupported_forms
    assert {"form": "badanudzwa", "reason": "passive or extension-like surface outside present v1 support"} in unsupported_forms
    assert {"form": "kuambura", "reason": "infinitive/nominal form outside analyze/generate v1"} in unsupported_forms


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
        "extensions": [],
        "final_vowel": {
            "surface": "a",
            "value": "a",
        },
    }
    assert analysis["phonology"]["phonology_inventory_version"] == "shona-core-v1"
    assert analysis["phonology"]["syllables"] == ["ndi", "no", "bu", "da"]
    assert "tone" in analysis["limitations"][1]


@pytest.mark.django_db
def test_analyze_endpoint_returns_ku_infinitive_analysis(
    client, api_key, current_release, verb_lemma
):
    response = client.post(
        "/v1/analyze",
        {"text": "Kubuda"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["query"]["normalized"] == "kubuda"
    assert body["data"]["count"] == 1
    analysis = body["data"]["analyses"][0]
    assert analysis["analysis_type"] == "infinitive"
    assert analysis["rule_id"] == "fortune.verbal.infinitive.001"
    assert analysis["lemma"]["public_id"] == verb_lemma.public_id
    assert analysis["source"] == {
        "rule_card_id": "fortune.verbal.infinitive.001",
        "source_key": "source_fortune",
        "source_locator": (
            "Fortune Grammatical Constructions, section 3.3.18 Noun Class 15, "
            "PDF pages 90-91 (printed pp. 78-79)"
        ),
    }
    assert analysis["slots"] == {
        "infinitive_prefix": {
            "surface": "ku",
            "type": "class_15_infinitive_prefix",
            "label": "class 15 infinitive prefix",
        },
        "subject": None,
        "tense_aspect": None,
        "polarity": None,
        "object": None,
        "verb_stem": {
            "surface": "buda",
            "lemma_public_id": verb_lemma.public_id,
        },
        "extensions": [],
        "final_vowel": {
            "surface": "a",
            "value": "a",
        },
    }
    assert "generation is not supported" in analysis["limitations"][2]


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
        {"text": "handibuda"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert response.status_code == 422
    body = response.json()
    assert body["api_version"] == "v1"
    assert body["error"]["code"] == "ANALYSIS_UNSUPPORTED"
    assert body["error"]["detail"] == {
        "normalized": "handibuda",
        "supported_shape": "ku + reviewed verb_stem / subject_concord + no + [object_concord] + verb_stem / ha + subject_concord + [object_concord] + verb_stem_ending_in_e",
        "supported_rule_ids": [
            "fortune.verbal.infinitive.001",
            "fortune.verbal.slots.001",
            "fortune.verbal.negation.001",
            "fortune.concord.object.001",
        ],
    }


@pytest.mark.django_db
def test_analyze_endpoint_explains_passive_extension_like_future_lane(
    client, api_key, current_release
):
    response = client.post(
        "/v1/analyze",
        {"text": "badanudzwa"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "ANALYSIS_UNSUPPORTED"
    assert body["error"]["detail"]["future_lanes"] == [
        {
            "code": "passive_or_extension_like",
            "message": (
                "This looks like a passive or extension-like verb surface. "
                "Those forms are a future review lane and are not analyzed in v1."
            ),
            "support_status": "not_supported",
            "rule_card_ids": ["fortune.verbal.extensions.001"],
        }
    ]


@pytest.mark.django_db
def test_generate_endpoint_returns_bounded_positive_present_verb_form(
    client, api_key, current_release, verb_lemma
):
    response = client.post(
        "/v1/generate",
        {
            "lemma_public_id": verb_lemma.public_id,
            "features": {
                "generation_type": "verb_form",
                "subject": {
                    "type": "person",
                    "person": "first",
                    "number": "singular",
                },
                "tense_aspect": "present",
                "polarity": "positive",
            },
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["api_version"] == "v1"
    assert body["data_release"] == current_release.version
    assert body["rule_set_version"] == current_release.rule_set_version
    assert body["data"]["rule_set_version"] == current_release.rule_set_version
    assert body["data"]["generator_version"] == "shona-morphology-generator-v1"
    assert body["data"]["confidence"] == 0.86
    assert body["data"]["generated"]["form"] == "ndinobuda"
    assert body["data"]["generated"]["normalized"] == "ndinobuda"
    assert body["data"]["generated"]["rule_id"] == "fortune.verbal.slots.001"
    assert body["data"]["generated"]["lemma"] == {
        "public_id": verb_lemma.public_id,
        "headword": "-buda",
        "normalized_headword": "buda",
        "part_of_speech_code": "vi",
    }
    assert body["data"]["generated"]["slots"]["subject"] == {
        "surface": "ndi",
        "type": "person",
        "label": "1st person singular subject concord",
        "person": "first",
        "number": "singular",
    }
    assert body["data"]["generated"]["phonology"]["syllables"] == [
        "ndi",
        "no",
        "bu",
        "da",
    ]
    assert body["data"]["warnings"] == [
        {
            "code": "GENERATION_PARTIAL_RULE_SET",
            "message": (
                "v1 generation supports only single-token positive present verb forms."
            ),
        },
        {
            "code": "TONE_NOT_GENERATED",
            "message": (
                "Tone, object markers, negative forms, and extensions are not generated."
            ),
        },
    ]


@pytest.mark.django_db
def test_generate_endpoint_can_use_reviewed_noun_class_subject_concord(
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
        "/v1/generate",
        {
            "lemma_public_id": verb_lemma.public_id,
            "features": {
                "generation_type": "verb_form",
                "subject": {
                    "type": "noun_class",
                    "class_number": "2",
                },
                "tense_aspect": "present",
                "polarity": "positive",
            },
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert response.status_code == 200
    generated = response.json()["data"]["generated"]
    assert generated["form"] == "vanobuda"
    assert generated["slots"]["subject"] == {
        "surface": "va",
        "type": "noun_class",
        "label": "Class 2",
        "class_number": "2",
        "noun_class_public_id": noun_class.public_id,
    }


@pytest.mark.django_db
def test_generate_endpoint_requires_structured_features(client, api_key, current_release):
    response = client.post(
        "/v1/generate",
        {
            "lemma_public_id": "lemma_test",
            "features": "present positive",
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert response.status_code == 400
    assert response.json() == {
        "api_version": "v1",
        "error": {
            "code": "GENERATION_FEATURES_REQUIRED",
            "message": "Generation requires a structured 'features' object.",
            "detail": {"field": "features", "expected_type": "object"},
        },
    }


@pytest.mark.django_db
def test_generate_endpoint_returns_structured_unsupported_failure(
    client, api_key, current_release, verb_lemma
):
    response = client.post(
        "/v1/generate",
        {
            "lemma_public_id": verb_lemma.public_id,
            "features": {
                "generation_type": "verb_form",
                "subject": {
                    "type": "person",
                    "person": "first",
                    "number": "singular",
                },
                "tense_aspect": "past",
                "polarity": "positive",
            },
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert response.status_code == 422
    body = response.json()
    assert body["api_version"] == "v1"
    assert body["error"]["code"] == "GENERATION_UNSUPPORTED"
    assert body["error"]["detail"] == {
        "field": "tense_aspect",
        "received": "past",
        "supported": ["present"],
        "supported_shape": "subject_concord + no + [object_concord] + verb_stem / ha + subject_concord + [object_concord] + verb_stem_ending_in_e",
        "supported_rule_ids": ["fortune.verbal.slots.001", "fortune.verbal.negation.001", "fortune.concord.object.001"],
    }


@pytest.fixture
def vowel_verb_lemma(current_release):
    return Lemma.objects.create(
        headword="-ambura",
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        part_of_speech_code="vt",
        part_of_speech_label="transitive verb",
        provenance={
            "source_key": "source_hannan",
            "entry_locator": "fixture:ambura",
        },
        review_state=ReviewState.APPROVED,
    )


@pytest.mark.django_db
def test_analyze_endpoint_returns_bounded_negative_present_verb_analysis(
    client, api_key, current_release, verb_lemma, vowel_verb_lemma
):
    # 1. Regular person subject
    response = client.post(
        "/v1/analyze",
        {"text": "handibude"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["count"] == 1
    analysis = body["data"]["analyses"][0]
    assert analysis["analysis_type"] == "verb_form"
    assert analysis["rule_id"] == "fortune.verbal.negation.001"
    assert analysis["lemma"]["public_id"] == verb_lemma.public_id
    assert analysis["slots"]["subject"] == {
        "surface": "ndi",
        "type": "person",
        "label": "1st person singular subject concord",
        "person": "first",
        "number": "singular",
    }
    assert analysis["slots"]["polarity"] == {
        "surface": "ha",
        "value": "negative",
        "label": "present negative marker",
    }
    assert analysis["slots"]["tense_aspect"] is None
    assert analysis["slots"]["verb_stem"] == {
        "surface": "bude",
        "lemma_public_id": verb_lemma.public_id,
    }
    assert analysis["slots"]["final_vowel"] == {
        "surface": "e",
        "value": "e",
    }

    # 2. Class 2 subject (regular consonant)
    noun_class_2 = NounClass.objects.create(
        class_number="2",
        display_order=2,
        label="Class 2",
        nominal_prefix="va",
        subject_concord="va",
        review_state=ReviewState.APPROVED,
    )
    response = client.post(
        "/v1/analyze",
        {"text": "havabude"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    analysis = response.json()["data"]["analyses"][0]
    assert analysis["slots"]["subject"]["surface"] == "va"
    assert analysis["slots"]["verb_stem"]["surface"] == "bude"

    # 3. Class 2 subject with vowel stem (coalescence)
    response = client.post(
        "/v1/analyze",
        {"text": "havambure"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    analysis = response.json()["data"]["analyses"][0]
    assert analysis["slots"]["subject"]["surface"] == "va"
    assert analysis["slots"]["verb_stem"]["surface"] == "ambure"
    assert analysis["lemma"]["public_id"] == vowel_verb_lemma.public_id

    # 4. Class 1 override
    noun_class_1 = NounClass.objects.create(
        class_number="1",
        display_order=1,
        label="Class 1",
        nominal_prefix="mu",
        subject_concord="u",
        review_state=ReviewState.APPROVED,
    )
    response = client.post(
        "/v1/analyze",
        {"text": "haabude"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    analysis = response.json()["data"]["analyses"][0]
    assert analysis["slots"]["subject"]["surface"] == "a"
    assert analysis["slots"]["subject"]["class_number"] == "1"


@pytest.mark.django_db
def test_generate_endpoint_returns_bounded_negative_present_verb_form(
    client, api_key, current_release, verb_lemma, vowel_verb_lemma
):
    # 1. 1st person singular -> handibude
    response = client.post(
        "/v1/generate",
        {
            "lemma_public_id": verb_lemma.public_id,
            "features": {
                "generation_type": "verb_form",
                "subject": {
                    "type": "person",
                    "person": "first",
                    "number": "singular",
                },
                "tense_aspect": "present",
                "polarity": "negative",
            },
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    body = response.json()
    generated = body["data"]["generated"]
    assert generated["form"] == "handibude"
    assert generated["rule_id"] == "fortune.verbal.negation.001"
    assert generated["slots"]["subject"]["surface"] == "ndi"
    assert generated["slots"]["polarity"]["value"] == "negative"
    assert generated["slots"]["tense_aspect"] is None

    # 2. Class 2 -> havabude
    noun_class_2 = NounClass.objects.create(
        class_number="2",
        display_order=2,
        label="Class 2",
        nominal_prefix="va",
        subject_concord="va",
        review_state=ReviewState.APPROVED,
    )
    response = client.post(
        "/v1/generate",
        {
            "lemma_public_id": verb_lemma.public_id,
            "features": {
                "generation_type": "verb_form",
                "subject": {
                    "type": "noun_class",
                    "class_number": "2",
                },
                "tense_aspect": "present",
                "polarity": "negative",
            },
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    assert response.json()["data"]["generated"]["form"] == "havabude"

    # 3. Class 2 + vowel stem -> havambure
    response = client.post(
        "/v1/generate",
        {
            "lemma_public_id": vowel_verb_lemma.public_id,
            "features": {
                "generation_type": "verb_form",
                "subject": {
                    "type": "noun_class",
                    "class_number": "2",
                },
                "tense_aspect": "present",
                "polarity": "negative",
            },
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    assert response.json()["data"]["generated"]["form"] == "havambure"

    # 4. Class 1 -> haabude
    noun_class_1 = NounClass.objects.create(
        class_number="1",
        display_order=1,
        label="Class 1",
        nominal_prefix="mu",
        subject_concord="u",
        review_state=ReviewState.APPROVED,
    )
    response = client.post(
        "/v1/generate",
        {
            "lemma_public_id": verb_lemma.public_id,
            "features": {
                "generation_type": "verb_form",
                "subject": {
                    "type": "noun_class",
                    "class_number": "1",
                },
                "tense_aspect": "present",
                "polarity": "negative",
            },
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    assert response.json()["data"]["generated"]["form"] == "haabude"


@pytest.mark.django_db
def test_analyze_endpoint_returns_present_verb_form_with_object_concord(
    client, api_key, current_release, verb_lemma, vowel_verb_lemma
):
    # 1. Positive present with person subject and person object (ndinokuda)
    da_lemma = Lemma.objects.create(
        headword="-da",
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        part_of_speech_code="vt",
        part_of_speech_label="transitive verb",
        provenance={"source_key": "source_hannan", "entry_locator": "fixture:da"},
        review_state=ReviewState.APPROVED,
    )

    response = client.post(
        "/v1/analyze",
        {"text": "ndinokuda"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["count"] == 1
    analysis = body["data"]["analyses"][0]
    assert analysis["rule_id"] == "fortune.concord.object.001"
    assert analysis["lemma"]["public_id"] == da_lemma.public_id
    assert analysis["slots"]["subject"]["surface"] == "ndi"
    assert analysis["slots"]["object"] == {
        "surface": "ku",
        "type": "person",
        "label": "2nd person singular object concord",
        "person": "second",
        "number": "singular",
    }
    assert analysis["slots"]["verb_stem"]["surface"] == "da"

    # 2. Negative present with person subject and person object (handikude)
    response = client.post(
        "/v1/analyze",
        {"text": "handikude"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    analysis = response.json()["data"]["analyses"][0]
    assert analysis["rule_id"] == "fortune.concord.object.001"
    assert analysis["slots"]["polarity"]["value"] == "negative"
    assert analysis["slots"]["object"]["surface"] == "ku"
    assert analysis["slots"]["verb_stem"]["surface"] == "de"

    # 3. Class 2 subject, Class 2 object, vowel stem with coalescence (vanovambura)
    noun_class_2 = NounClass.objects.filter(class_number="2").first()
    if not noun_class_2:
        noun_class_2 = NounClass.objects.create(
            class_number="2",
            display_order=2,
            label="Class 2",
            nominal_prefix="va",
            subject_concord="va",
            object_concord="va",
            review_state=ReviewState.APPROVED,
        )
    else:
        noun_class_2.object_concord = "va"
        noun_class_2.save()

    response = client.post(
        "/v1/analyze",
        {"text": "vanovambura"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    analysis = response.json()["data"]["analyses"][0]
    assert analysis["slots"]["subject"]["surface"] == "va"
    assert analysis["slots"]["object"]["surface"] == "va"
    assert analysis["slots"]["verb_stem"]["surface"] == "ambura"

    # 4. Negative present with coalescence (havavambure)
    response = client.post(
        "/v1/analyze",
        {"text": "havavambure"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    analysis = response.json()["data"]["analyses"][0]
    assert analysis["slots"]["subject"]["surface"] == "va"
    assert analysis["slots"]["object"]["surface"] == "va"
    assert analysis["slots"]["verb_stem"]["surface"] == "ambure"


@pytest.mark.django_db
def test_generate_endpoint_returns_present_verb_form_with_object_concord(
    client, api_key, current_release, vowel_verb_lemma
):
    da_lemma = Lemma.objects.create(
        headword="-da",
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        part_of_speech_code="vt",
        part_of_speech_label="transitive verb",
        provenance={"source_key": "source_hannan", "entry_locator": "fixture:da"},
        review_state=ReviewState.APPROVED,
    )

    # 1. Generate Positive Present with person object (ndinokuda)
    response = client.post(
        "/v1/generate",
        {
            "lemma_public_id": da_lemma.public_id,
            "features": {
                "generation_type": "verb_form",
                "subject": {
                    "type": "person",
                    "person": "first",
                    "number": "singular",
                },
                "object": {
                    "type": "person",
                    "person": "second",
                    "number": "singular",
                },
                "tense_aspect": "present",
                "polarity": "positive",
            },
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    body = response.json()
    generated = body["data"]["generated"]
    assert generated["form"] == "ndinokuda"
    assert generated["rule_id"] == "fortune.concord.object.001"
    assert generated["slots"]["object"]["surface"] == "ku"

    # 2. Generate Negative Present with person object (handikude)
    response = client.post(
        "/v1/generate",
        {
            "lemma_public_id": da_lemma.public_id,
            "features": {
                "generation_type": "verb_form",
                "subject": {
                    "type": "person",
                    "person": "first",
                    "number": "singular",
                },
                "object": {
                    "type": "person",
                    "person": "second",
                    "number": "singular",
                },
                "tense_aspect": "present",
                "polarity": "negative",
            },
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    generated = response.json()["data"]["generated"]
    assert generated["form"] == "handikude"
    assert generated["rule_id"] == "fortune.concord.object.001"
    assert generated["slots"]["object"]["surface"] == "ku"

    # 3. Generate Positive Present Class 2 subject, Class 2 object, vowel stem with coalescence (vanovambura)
    noun_class_2 = NounClass.objects.filter(class_number="2").first()
    if not noun_class_2:
        NounClass.objects.create(
            class_number="2",
            display_order=2,
            label="Class 2",
            nominal_prefix="va",
            subject_concord="va",
            object_concord="va",
            review_state=ReviewState.APPROVED,
        )
    else:
        noun_class_2.object_concord = "va"
        noun_class_2.save()

    response = client.post(
        "/v1/generate",
        {
            "lemma_public_id": vowel_verb_lemma.public_id,
            "features": {
                "generation_type": "verb_form",
                "subject": {
                    "type": "noun_class",
                    "class_number": "2",
                },
                "object": {
                    "type": "noun_class",
                    "class_number": "2",
                },
                "tense_aspect": "present",
                "polarity": "positive",
            },
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    assert response.json()["data"]["generated"]["form"] == "vanovambura"

    # 4. Generate Negative Present Class 2 subject, Class 2 object, vowel stem with coalescence (havavambure)
    response = client.post(
        "/v1/generate",
        {
            "lemma_public_id": vowel_verb_lemma.public_id,
            "features": {
                "generation_type": "verb_form",
                "subject": {
                    "type": "noun_class",
                    "class_number": "2",
                },
                "object": {
                    "type": "noun_class",
                    "class_number": "2",
                },
                "tense_aspect": "present",
                "polarity": "negative",
            },
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    assert response.json()["data"]["generated"]["form"] == "havavambure"


@pytest.mark.django_db
def test_extension_3_primary_object_concords_analysis_and_generation(
    client, api_key, current_release, vowel_verb_lemma
):
    # 1. Analysis of ndinomuambura
    response = client.post(
        "/v1/analyze",
        {"text": "ndinomuambura"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["count"] == 1
    analysis = body["data"]["analyses"][0]
    assert analysis["rule_id"] == "fortune.concord.object.001"
    assert analysis["lemma"]["public_id"] == vowel_verb_lemma.public_id
    assert analysis["slots"]["subject"]["surface"] == "ndi"
    assert analysis["slots"]["object"] == {
        "surface": "mu",
        "type": "person",
        "label": "3rd person singular object concord",
        "person": "third",
        "number": "singular",
    }
    assert analysis["slots"]["verb_stem"]["surface"] == "ambura"

    # 2. Generation of ndinomuambura
    response = client.post(
        "/v1/generate",
        {
            "lemma_public_id": vowel_verb_lemma.public_id,
            "features": {
                "generation_type": "verb_form",
                "subject": {
                    "type": "person",
                    "person": "first",
                    "number": "singular",
                },
                "object": {
                    "type": "person",
                    "person": "third",
                    "number": "singular",
                },
                "tense_aspect": "present",
                "polarity": "positive",
            },
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    generated = response.json()["data"]["generated"]
    assert generated["form"] == "ndinomuambura"
    assert generated["slots"]["object"]["surface"] == "mu"

    # 3. Generation of ndinovaambura
    response = client.post(
        "/v1/generate",
        {
            "lemma_public_id": vowel_verb_lemma.public_id,
            "features": {
                "generation_type": "verb_form",
                "subject": {
                    "type": "person",
                    "person": "first",
                    "number": "singular",
                },
                "object": {
                    "type": "person",
                    "person": "third",
                    "number": "plural",
                },
                "tense_aspect": "present",
                "polarity": "positive",
            },
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    generated = response.json()["data"]["generated"]
    assert generated["form"] == "ndinovambura"
    assert generated["slots"]["object"]["surface"] == "va"


@pytest.fixture
def transitive_mid_verb_lemma(current_release):
    return Lemma.objects.create(
        headword="-tenga",
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        part_of_speech_code="vt",
        part_of_speech_label="transitive verb",
        provenance={
            "source_key": "source_hannan",
            "entry_locator": "fixture:tenga",
        },
        review_state=ReviewState.APPROVED,
    )


@pytest.fixture
def monosyllabic_verb_lemma(current_release):
    return Lemma.objects.create(
        headword="-pa",
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        part_of_speech_code="vt",
        part_of_speech_label="transitive verb",
        provenance={
            "source_key": "source_hannan",
            "entry_locator": "fixture:pa",
        },
        review_state=ReviewState.APPROVED,
    )


@pytest.mark.django_db
def test_analyze_endpoint_verbal_extensions_passive_causative_applicative(
    client, corpus_api_key, current_release, verb_lemma, transitive_mid_verb_lemma, monosyllabic_verb_lemma
):
    # 1. Passive of buda -> budwa
    response = client.post(
        "/v1/analyze",
        {"text": "ndinobudwa"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {corpus_api_key}",
    )
    assert response.status_code == 200
    analysis = response.json()["data"]["analyses"][0]
    assert analysis["lemma"]["public_id"] == verb_lemma.public_id
    assert analysis["slots"]["extensions"] == [
        {"surface": "w", "type": "passive", "label": "passive extension (-w-)"}
    ]

    # 2. Causative of buda -> budisa
    response = client.post(
        "/v1/analyze",
        {"text": "ndinobudisa"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {corpus_api_key}",
    )
    assert response.status_code == 200
    analysis = response.json()["data"]["analyses"][0]
    assert analysis["lemma"]["public_id"] == verb_lemma.public_id
    assert analysis["slots"]["extensions"] == [
        {"surface": "is", "type": "causative", "label": "causative extension (-is- / -es-)"}
    ]

    # 3. Applicative of buda -> budira
    response = client.post(
        "/v1/analyze",
        {"text": "ndinobudira"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {corpus_api_key}",
    )
    assert response.status_code == 200
    analysis = response.json()["data"]["analyses"][0]
    assert analysis["lemma"]["public_id"] == verb_lemma.public_id
    assert analysis["slots"]["extensions"] == [
        {"surface": "ir", "type": "applicative", "label": "applicative extension (-ir- / -er-)"}
    ]

    # 4. Mid vowel harmony causative of tenga -> tengesa (valid)
    response = client.post(
        "/v1/analyze",
        {"text": "ndinotengesa"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {corpus_api_key}",
    )
    assert response.status_code == 200
    analysis = response.json()["data"]["analyses"][0]
    assert analysis["lemma"]["public_id"] == transitive_mid_verb_lemma.public_id
    assert analysis["slots"]["extensions"] == [
        {"surface": "es", "type": "causative", "label": "causative extension (-is- / -es-)"}
    ]

    # 5. Mid vowel harmony violation: tengisa instead of tengesa (invalid -> 422)
    response = client.post(
        "/v1/analyze",
        {"text": "ndinotengisa"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {corpus_api_key}",
    )
    assert response.status_code == 422

    # 6. High vowel harmony violation: budesa instead of budisa (invalid -> 422)
    response = client.post(
        "/v1/analyze",
        {"text": "ndinobudesa"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {corpus_api_key}",
    )
    assert response.status_code == 422

    # 7. Stacked suffixes: causative + passive of buda -> budiswa
    response = client.post(
        "/v1/analyze",
        {"text": "ndinobudiswa"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {corpus_api_key}",
    )
    assert response.status_code == 200
    analysis = response.json()["data"]["analyses"][0]
    assert analysis["lemma"]["public_id"] == verb_lemma.public_id
    assert analysis["slots"]["extensions"] == [
        {"surface": "is", "type": "causative", "label": "causative extension (-is- / -es-)"},
        {"surface": "w", "type": "passive", "label": "passive extension (-w-)"}
    ]

    # 8. Monosyllabic passive: pa -> piwa
    response = client.post(
        "/v1/analyze",
        {"text": "ndinopiwa"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {corpus_api_key}",
    )
    assert response.status_code == 200
    analysis = response.json()["data"]["analyses"][0]
    assert analysis["lemma"]["public_id"] == monosyllabic_verb_lemma.public_id
    assert analysis["slots"]["extensions"] == [
        {"surface": "iw", "type": "passive", "label": "passive extension (-iw-)"}
    ]


@pytest.mark.django_db
def test_generate_endpoint_verbal_extensions(
    client, corpus_api_key, current_release, verb_lemma, transitive_mid_verb_lemma, monosyllabic_verb_lemma
):
    # 1. Generate causative (high vowel harmony) of buda -> ndinobudisa
    response = client.post(
        "/v1/generate",
        {
            "lemma_public_id": verb_lemma.public_id,
            "features": {
                "generation_type": "verb_form",
                "subject": {"type": "person", "person": "first", "number": "singular"},
                "tense_aspect": "present",
                "polarity": "positive",
                "extensions": ["causative"]
            },
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {corpus_api_key}",
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["generated"]["form"] == "ndinobudisa"
    assert data["generated"]["slots"]["extensions"] == [
        {"surface": "is", "type": "causative", "label": "causative extension (-is- / -es-)"}
    ]

    # 2. Generate causative (mid vowel harmony) of tenga -> ndinotengesa
    response = client.post(
        "/v1/generate",
        {
            "lemma_public_id": transitive_mid_verb_lemma.public_id,
            "features": {
                "generation_type": "verb_form",
                "subject": {"type": "person", "person": "first", "number": "singular"},
                "tense_aspect": "present",
                "polarity": "positive",
                "extensions": [{"type": "causative"}]
            },
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {corpus_api_key}",
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["generated"]["form"] == "ndinotengesa"
    assert data["generated"]["slots"]["extensions"] == [
        {"surface": "es", "type": "causative", "label": "causative extension (-is- / -es-)"}
    ]

    # 3. Generate monosyllabic passive of pa -> ndinopiwa
    response = client.post(
        "/v1/generate",
        {
            "lemma_public_id": monosyllabic_verb_lemma.public_id,
            "features": {
                "generation_type": "verb_form",
                "subject": {"type": "person", "person": "first", "number": "singular"},
                "tense_aspect": "present",
                "polarity": "positive",
                "extensions": ["passive"]
            },
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {corpus_api_key}",
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["generated"]["form"] == "ndinopiwa"
    assert data["generated"]["slots"]["extensions"] == [
        {"surface": "iw", "type": "passive", "label": "passive extension (-iw-)"}
    ]

    # 4. Generate negative present causative of buda -> handibudise
    response = client.post(
        "/v1/generate",
        {
            "lemma_public_id": verb_lemma.public_id,
            "features": {
                "generation_type": "verb_form",
                "subject": {"type": "person", "person": "first", "number": "singular"},
                "tense_aspect": "present",
                "polarity": "negative",
                "extensions": ["causative"]
            },
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {corpus_api_key}",
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["generated"]["form"] == "handibudise"


@pytest.mark.django_db
def test_analyze_endpoint_returns_neuter_and_reciprocal_extensions(
    client, api_key, current_release, verb_lemma
):
    # 1. Neuter analysis: munobudika
    response = client.post(
        "/v1/analyze",
        {"text": "munobudika"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["count"] == 1  # mu- person (Class 18 mu- is not seeded in this test)
    analysis = body["data"]["analyses"][0]
    assert analysis["lemma"]["public_id"] == verb_lemma.public_id
    assert analysis["slots"]["extensions"] == [
        {"surface": "ik", "type": "neuter", "label": "neuter extension (-ik- / -ek-)"}
    ]

    # 2. Reciprocal analysis: vanobudana
    noun_class_2 = NounClass.objects.create(
        class_number="2",
        display_order=2,
        label="Class 2",
        nominal_prefix="va",
        subject_concord="va",
        review_state=ReviewState.APPROVED,
    )
    response = client.post(
        "/v1/analyze",
        {"text": "vanobudana"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    body = response.json()
    analysis = body["data"]["analyses"][0]
    assert analysis["lemma"]["public_id"] == verb_lemma.public_id
    assert analysis["slots"]["extensions"] == [
        {"surface": "an", "type": "reciprocal", "label": "reciprocal extension (-an-)"}
    ]

    # 3. Compound extensions: munobudikana (neuter + reciprocal)
    response = client.post(
        "/v1/analyze",
        {"text": "munobudikana"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    body = response.json()
    analysis = body["data"]["analyses"][0]
    assert analysis["lemma"]["public_id"] == verb_lemma.public_id
    assert analysis["slots"]["extensions"] == [
        {"surface": "ik", "type": "neuter", "label": "neuter extension (-ik- / -ek-)"},
        {"surface": "an", "type": "reciprocal", "label": "reciprocal extension (-an-)"}
    ]


@pytest.mark.django_db
def test_generate_endpoint_supports_neuter_and_reciprocal_extensions(
    client, api_key, current_release, verb_lemma
):
    # 1. Neuter generation with high-vowel harmony (-ik-): buda -> ndinobudika
    response = client.post(
        "/v1/generate",
        {
            "lemma_public_id": verb_lemma.public_id,
            "features": {
                "generation_type": "verb_form",
                "subject": {"type": "person", "person": "first", "number": "singular"},
                "tense_aspect": "present",
                "polarity": "positive",
                "extensions": ["neuter"]
            },
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["generated"]["form"] == "ndinobudika"
    assert body["data"]["generated"]["slots"]["extensions"] == [
        {"surface": "ik", "type": "neuter", "label": "neuter extension (-ik- / -ek-)"}
    ]

    # 2. Neuter generation with mid-vowel harmony (-ek-): gova -> ndinogoveka
    gova_lemma = Lemma.objects.create(
        headword="-gova",
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        part_of_speech_code="vt",
        part_of_speech_label="transitive verb",
        provenance={"source_key": "source_hannan", "entry_locator": "fixture:gova"},
        review_state=ReviewState.APPROVED,
    )
    response = client.post(
        "/v1/generate",
        {
            "lemma_public_id": gova_lemma.public_id,
            "features": {
                "generation_type": "verb_form",
                "subject": {"type": "person", "person": "first", "number": "singular"},
                "tense_aspect": "present",
                "polarity": "positive",
                "extensions": ["neuter"]
            },
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["generated"]["form"] == "ndinogoveka"
    assert body["data"]["generated"]["slots"]["extensions"] == [
        {"surface": "ek", "type": "neuter", "label": "neuter extension (-ik- / -ek-)"}
    ]

    # 3. Reciprocal generation: buda -> ndinobudana
    response = client.post(
        "/v1/generate",
        {
            "lemma_public_id": verb_lemma.public_id,
            "features": {
                "generation_type": "verb_form",
                "subject": {"type": "person", "person": "first", "number": "singular"},
                "tense_aspect": "present",
                "polarity": "positive",
                "extensions": ["reciprocal"]
            },
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["generated"]["form"] == "ndinobudana"
    assert body["data"]["generated"]["slots"]["extensions"] == [
        {"surface": "an", "type": "reciprocal", "label": "reciprocal extension (-an-)"}
    ]


@pytest.mark.django_db
def test_analyze_endpoint_returns_secondary_causatives_and_reversives(
    client, api_key, current_release, verb_lemma
):
    # Seed the -chema lemma in the isolated test DB
    Lemma.objects.create(
        headword="-chema",
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        part_of_speech_code="vi",
        part_of_speech_label="intransitive verb",
        provenance={"source_key": "source_hannan", "entry_locator": "fixture:chema"},
        review_state=ReviewState.PUBLISHED,
    )

    # 1. Secondary causative analysis (style 'dz'): kuchemedza
    response = client.post(
        "/v1/analyze",
        {"text": "kuchemedza"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    body = response.json()
    analysis = body["data"]["analyses"][0]
    assert analysis["lemma"]["normalized_headword"] == "chema"
    assert analysis["slots"]["extensions"] == [
        {"surface": "edz", "type": "causative", "style": "dz", "label": "causative extension (-idz- / -edz-)"}
    ]

    # 2. Secondary causative analysis (style 'ts'): kubuditsa
    response = client.post(
        "/v1/analyze",
        {"text": "kubuditsa"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    body = response.json()
    analysis = body["data"]["analyses"][0]
    assert analysis["lemma"]["public_id"] == verb_lemma.public_id
    assert analysis["slots"]["extensions"] == [
        {"surface": "its", "type": "causative", "style": "ts", "label": "causative extension (-its- / -ets-)"}
    ]

    # 3. Reversive analysis (short & long): kupetunura
    peta_lemma = Lemma.objects.create(
        headword="-peta",
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        part_of_speech_code="vt",
        part_of_speech_label="transitive verb",
        provenance={"source_key": "source_hannan", "entry_locator": "fixture:peta"},
        review_state=ReviewState.PUBLISHED,
    )
    response = client.post(
        "/v1/analyze",
        {"text": "kupetunura"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    body = response.json()
    analysis = body["data"]["analyses"][0]
    assert analysis["lemma"]["public_id"] == peta_lemma.public_id
    assert analysis["slots"]["extensions"] == [
        {"surface": "unur", "type": "reversive", "style": "long", "label": "reversive extension (-unur- / -onor-)"}
    ]


@pytest.mark.django_db
def test_generate_endpoint_supports_secondary_causatives_and_reversives(
    client, api_key, current_release, verb_lemma
):
    # 1. Secondary causative generation (style 'dz'): buda -> ndinobudidza
    response = client.post(
        "/v1/generate",
        {
            "lemma_public_id": verb_lemma.public_id,
            "features": {
                "generation_type": "verb_form",
                "subject": {"type": "person", "person": "first", "number": "singular"},
                "tense_aspect": "present",
                "polarity": "positive",
                "extensions": [{"type": "causative", "style": "dz"}]
            },
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["generated"]["form"] == "ndinobudidza"
    assert body["data"]["generated"]["slots"]["extensions"] == [
        {"surface": "idz", "type": "causative", "style": "dz", "label": "causative extension (-idz- / -edz-)"}
    ]

    # 2. Secondary causative generation (style 'ts'): buda -> ndinobuditsa
    response = client.post(
        "/v1/generate",
        {
            "lemma_public_id": verb_lemma.public_id,
            "features": {
                "generation_type": "verb_form",
                "subject": {"type": "person", "person": "first", "number": "singular"},
                "tense_aspect": "present",
                "polarity": "positive",
                "extensions": [{"type": "causative", "style": "ts"}]
            },
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["generated"]["form"] == "ndinobuditsa"
    assert body["data"]["generated"]["slots"]["extensions"] == [
        {"surface": "its", "type": "causative", "style": "ts", "label": "causative extension (-its- / -ets-)"}
    ]

    # 3. Reversive generation (long with 'o' mid vowel trigger): kora -> ndinokorora
    kora_lemma = Lemma.objects.create(
        headword="-kora",
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        part_of_speech_code="vi",
        part_of_speech_label="intransitive verb",
        provenance={"source_key": "source_hannan", "entry_locator": "fixture:kora"},
        review_state=ReviewState.APPROVED,
    )
    response = client.post(
        "/v1/generate",
        {
            "lemma_public_id": kora_lemma.public_id,
            "features": {
                "generation_type": "verb_form",
                "subject": {"type": "person", "person": "first", "number": "singular"},
                "tense_aspect": "present",
                "polarity": "positive",
                "extensions": [{"type": "reversive", "style": "long"}]
            },
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["generated"]["form"] == "ndinokororora"
    assert body["data"]["generated"]["slots"]["extensions"] == [
        {"surface": "oror", "type": "reversive", "style": "long", "label": "reversive extension (-urur- / -oror-)"}
    ]


