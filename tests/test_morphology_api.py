import pytest
import json
from django.core.cache import caches
from pathlib import Path

from shona_api.api_auth.models import APIKey
from shona_api.editorial.models import ReviewState
from shona_api.lexicon.models import Lemma, NounClass
from shona_api.morphology.services import MORPHOLOGY_RULES_VERSION
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
        rule_set_version=MORPHOLOGY_RULES_VERSION,
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
        "negative_third_person_object": {
            "generation_type": "verb_form",
            "subject": {"type": "person", "person": "first", "number": "singular"},
            "object": {"type": "person", "person": "third", "number": "singular"},
            "tense_aspect": "present",
            "polarity": "negative",
        },
        "positive_class_subject": {
            "generation_type": "verb_form",
            "subject": {"type": "noun_class", "class_number": "2"},
            "tense_aspect": "present",
            "polarity": "positive",
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
        "positive_infinitive": {
            "generation_type": "infinitive",
        },
        "positive_imperative_singular": {
            "generation_type": "imperative",
            "number": "singular",
            "polarity": "positive",
        },
        "positive_imperative_plural": {
            "generation_type": "imperative",
            "number": "plural",
            "polarity": "positive",
        },
        "negative_imperative_singular": {
            "generation_type": "imperative",
            "number": "singular",
            "polarity": "negative",
        },
        "negative_imperative_plural": {
            "generation_type": "imperative",
            "number": "plural",
            "polarity": "negative",
        },
        "positive_imperative_class_object": {
            "generation_type": "imperative",
            "number": "singular",
            "polarity": "positive",
            "object": {"type": "noun_class", "class_number": "2"},
        },
        "negative_imperative_class_object": {
            "generation_type": "imperative",
            "number": "singular",
            "polarity": "negative",
            "object": {"type": "noun_class", "class_number": "2"},
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
    assert {"form": "kusaambura", "reason": "negative infinitive across deferred sa-/a-stem boundary"} in unsupported_forms


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
        "normalizer": "shona-orthography-normalizer-v2",
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
        "polarity": {
            "surface": "",
            "value": "positive",
            "label": "No negative marker in the supported infinitive pattern.",
        },
        "object": None,
        "reflexive": None,
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
    assert "optionally negative" in analysis["limitations"][0]


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
        "supported_shape": "ku + [sa] + [object_concord | zvi-reflexive] + reviewed verb_stem / subject_concord + no + [object_concord] + verb_stem / ha + subject_concord + [object_concord] + verb_stem_ending_in_i / imperative: bare_stem [+ plural -i] or usa-/musa- + [object_concord] + stem_ending_in_e_or_a",
        "supported_rule_ids": [
            "fortune.verbal.infinitive.001",
            "fortune.verbal.imperative.001",
            "fortune.verbal.imperative.negative.001",
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
    # The lane message changed under morphology-rules-v3: extensions are analyzed
    # in v1 now, so an unmatched extension-like surface reports a harmony/lexical
    # miss instead of a "future review lane".
    assert body["error"]["detail"]["future_lanes"] == [
        {
            "code": "passive_or_extension_like",
            "message": (
                "This surface contains extension-like material but no supported "
                "v1 construction matched it. Check vowel harmony and the lexical "
                "stem; the supported extension boundary is documented in the "
                "verbal extension rule cards."
            ),
            "support_status": "not_supported",
            "rule_card_ids": [
                "fortune.verbal.extensions.001",
                "fortune.verbal.reversive.001",
                "fortune.verbal.repetitive.001",
                "fortune.verbal.extensions.retained.001",
            ],
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
        "supported_shape": "subject_concord + no + [object_concord] + verb_stem / ha + subject_concord + [object_concord] + verb_stem_ending_in_i",
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
    # 1. Regular person subject (Standard Shona terminal -i)
    response = client.post(
        "/v1/analyze",
        {"text": "handibudi"},
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
        "surface": "budi",
        "lemma_public_id": verb_lemma.public_id,
    }
    assert analysis["slots"]["final_vowel"] == {
        "surface": "i",
        "value": "i",
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
        {"text": "havabudi"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    analysis = response.json()["data"]["analyses"][0]
    assert analysis["slots"]["subject"]["surface"] == "va"
    assert analysis["slots"]["verb_stem"]["surface"] == "budi"

    # 3. Class 2 subject with vowel stem: the a-final subject concord
    # immediately before the a-initial stem is deferred pending evidence
    # (morphology-rules-v5). The surface is not blacklisted; the coalesced
    # va + ambura reading is simply not inferred.
    response = client.post(
        "/v1/analyze",
        {"text": "havambure"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "ANALYSIS_UNSUPPORTED"
    matching = [
        lane
        for lane in body["error"]["detail"]["future_lanes"]
        if lane["code"] == "deferred_finite_boundary"
        and lane["boundary"] == "subject_before_a_initial_stem"
    ]
    assert matching, body["error"]["detail"]["future_lanes"]
    assert matching[0]["support_status"] == "deferred_pending_evidence"
    assert matching[0]["rule_card_ids"] == ["fortune.verbal.slots.001"]

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
        {"text": "haabudi"},
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
    # 1. 1st person singular -> handibudi (Standard Shona terminal -i)
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
    assert generated["form"] == "handibudi"
    assert generated["rule_id"] == "fortune.verbal.negation.001"
    assert generated["slots"]["subject"]["surface"] == "ndi"
    assert generated["slots"]["polarity"]["value"] == "negative"
    assert generated["slots"]["tense_aspect"] is None

    # 2. Class 2 -> havabudi
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
    assert response.json()["data"]["generated"]["form"] == "havabudi"

    # 3. Class 2 + a-initial stem: deferred pending evidence under
    # morphology-rules-v5; no coalesced or hiatus spelling is generated.
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
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "GENERATION_UNSUPPORTED"
    assert error["detail"]["field"] == "finite_boundary"
    assert error["detail"]["boundary"] == "subject_before_a_initial_stem"
    assert error["detail"]["reason"] == "deferred_pending_evidence"

    # 4. Class 1 -> haabudi
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
    assert response.json()["data"]["generated"]["form"] == "haabudi"


@pytest.mark.django_db
def test_negative_terminal_vowel_i_with_attested_dialect_variants(
    client, api_key, current_release, verb_lemma
):
    """Negated -no- present terminal vowel, morphology-rules-v5.

    Generation emits -i (FSI Unit 12 Handízíví/Handítaúrí; Hannan front
    matter "Handidyi St. Sh." and the -ziva entry "Handimuzivi"). The Zezuru
    -e spelling (Fortune TC VII ha-ndí-zív-é; Hannan "Handidye Z") remains an
    analyzed dialect variant of the same construction, never blacklisted.
    """
    ziva = Lemma.objects.create(
        headword="-ziva",
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        part_of_speech_code="vt",
        part_of_speech_label="transitive verb",
        provenance={"source_key": "source_hannan"},
        review_state=ReviewState.PUBLISHED,
    )
    noun_class_2 = NounClass.objects.create(
        class_number="2",
        display_order=2,
        label="Class 2",
        nominal_prefix="va",
        subject_concord="va",
        object_concord="va",
        review_state=ReviewState.PUBLISHED,
    )
    noun_class_6 = NounClass.objects.create(
        class_number="6",
        display_order=6,
        label="Class 6",
        nominal_prefix="ma",
        subject_concord="a",
        object_concord="a",
        review_state=ReviewState.PUBLISHED,
    )

    # FSI p. 171 "Havaazivi: they don't know them" (ha-va-a-ziv-i)
    response = client.post(
        "/v1/generate",
        {
            "lemma_public_id": ziva.public_id,
            "features": {
                "generation_type": "verb_form",
                "subject": {"type": "noun_class", "class_number": "2"},
                "object": {"type": "noun_class", "class_number": "6"},
                "tense_aspect": "present",
                "polarity": "negative",
            },
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    generated = response.json()["data"]["generated"]
    assert generated["form"] == "havaazivi"
    assert generated["slots"]["final_vowel"] == {"surface": "i", "value": "i"}

    # The attested -i spelling analyzes with the class 6 object reading.
    response = client.post(
        "/v1/analyze",
        {"text": "havaazivi"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["count"] == 1
    analysis = body["data"]["analyses"][0]
    assert analysis["lemma"]["public_id"] == ziva.public_id
    assert analysis["slots"]["object"]["surface"] == "a"
    assert analysis["slots"]["verb_stem"]["surface"] == "zivi"
    assert analysis["slots"]["final_vowel"] == {"surface": "i", "value": "i"}

    # The Zezuru -e spellings of the same construction still analyze.
    response = client.post(
        "/v1/analyze",
        {"text": "havaazive"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    analysis = response.json()["data"]["analyses"][0]
    assert analysis["lemma"]["public_id"] == ziva.public_id
    assert analysis["slots"]["verb_stem"]["surface"] == "zive"
    assert analysis["slots"]["final_vowel"] == {"surface": "e", "value": "e"}

    response = client.post(
        "/v1/analyze",
        {"text": "handibude"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    analysis = response.json()["data"]["analyses"][0]
    assert analysis["lemma"]["public_id"] == verb_lemma.public_id
    assert analysis["slots"]["verb_stem"]["surface"] == "bude"

    noun_class_2.delete()
    noun_class_6.delete()


@pytest.mark.django_db
def test_negative_divergent_and_pro_verb_stems(
    client, api_key, current_release
):
    """Divergent stems keep their non-a terminal; the defective pro-verb -na
    is refused instead of inventing a terminal."""
    # Divergent stems without terminal -a (Fortune 3.3.18: -ti, -nzi) are
    # taken as-is; no terminal is appended.
    ti = Lemma.objects.create(
        headword="-ti",
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        part_of_speech_code="vt",
        part_of_speech_label="transitive verb",
        provenance={"source_key": "source_hannan"},
        review_state=ReviewState.PUBLISHED,
    )
    response = client.post(
        "/v1/generate",
        {
            "lemma_public_id": ti.public_id,
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
    assert response.json()["data"]["generated"]["form"] == "handiti"
    response = client.post(
        "/v1/analyze",
        {"text": "handiti"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    analysis = response.json()["data"]["analyses"][0]
    assert analysis["lemma"]["public_id"] == ti.public_id
    assert analysis["slots"]["verb_stem"]["surface"] == "ti"

    # The defective pro-verb -na carries its own -ne/-na paradigm (Hannan
    # front matter; FSI Unit 12: pro-verb stems keep their final vowels), so
    # its negated -no- present is refused instead of inventing a terminal.
    na = Lemma.objects.create(
        headword="-na",
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        part_of_speech_code="vt",
        part_of_speech_label="defective verb",
        provenance={"source_key": "source_hannan"},
        review_state=ReviewState.PUBLISHED,
    )
    response = client.post(
        "/v1/generate",
        {
            "lemma_public_id": na.public_id,
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
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "GENERATION_UNSUPPORTED"
    assert error["detail"]["field"] == "lemma_stem"
    assert error["detail"]["reason"] == "defective_pro_verb_stem"
    # Analysis of the attested past-negative surface stays unsupported here:
    # ha+SP+na+ku-infinitive is a different construction from the negated
    # -no- present and has no supported shape.
    response = client.post(
        "/v1/analyze",
        {"text": "handina"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ANALYSIS_UNSUPPORTED"


@pytest.mark.django_db
def test_negative_pro_verb_readings_excluded_from_analysis(
    client, api_key, current_release
):
    """The ordinary terminal rule must not infer ni/ne readings from -na.

    Generation refuses the defective pro-verb (defective_pro_verb_stem), so
    analysis excludes the same derivation across the plain, object-marked and
    extension-decomposed paths, reporting an identifiable lane instead of
    claiming the spelling is ungrammatical.
    """
    Lemma.objects.create(
        headword="-na",
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        part_of_speech_code="vt",
        part_of_speech_label="defective verb",
        provenance={"source_key": "source_hannan"},
        review_state=ReviewState.PUBLISHED,
    )

    for text in ("handini", "handine", "handimuni", "handinisi"):
        response = client.post(
            "/v1/analyze",
            {"text": text},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Api-Key {api_key}",
        )
        assert response.status_code == 422, text
        error = response.json()["error"]
        assert error["code"] == "ANALYSIS_UNSUPPORTED", text
        lanes = error["detail"]["future_lanes"]
        lane = next(
            lane
            for lane in lanes
            if lane["code"] == "excluded_defective_pro_verb_stem"
        )
        assert lane["support_status"] == "not_supported"
        assert lane["excluded_stem_headwords"] == ["-na"]
        assert "not claimed to be ungrammatical" in lane["message"]


@pytest.mark.django_db
def test_independent_lemma_survives_pro_verb_restriction(
    client, api_key, current_release
):
    """An independently reviewed stem keeps its reading; the excluded -na
    derivation stays out of analysis and search enrichment."""
    Lemma.objects.create(
        headword="-na",
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        part_of_speech_code="vt",
        part_of_speech_label="defective verb",
        provenance={"source_key": "source_hannan"},
        review_state=ReviewState.PUBLISHED,
    )
    ni = Lemma.objects.create(
        headword="-ni",
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        part_of_speech_code="vt",
        part_of_speech_label="transitive verb",
        provenance={"source_key": "source_hannan"},
        review_state=ReviewState.PUBLISHED,
    )

    # handini resolves through the reviewed -ni stem, not through -na.
    response = client.post(
        "/v1/analyze",
        {"text": "handini"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["count"] == 1
    analysis = body["data"]["analyses"][0]
    assert analysis["lemma"]["public_id"] == ni.public_id
    assert analysis["slots"]["verb_stem"]["surface"] == "ni"
    assert analysis["slots"]["final_vowel"] == {"surface": "i", "value": "i"}

    # The object-marked surface resolves the same independent stem.
    response = client.post(
        "/v1/analyze",
        {"text": "handimuni"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    analysis = response.json()["data"]["analyses"][0]
    assert analysis["lemma"]["public_id"] == ni.public_id
    assert analysis["slots"]["object"]["surface"] == "mu"

    # Search enrichment follows the corrected analyzer: the surviving
    # reading is reported as matched even with no lexical records, while the
    # excluded -ne derivation is not exposed as matched morphology.
    response = client.get(
        "/v1/search",
        {"q": "handini"},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["count"] == 0
    assert data["morphology_enrichment"]["status"] == "matched"
    assert data["morphology"]["count"] == 1
    assert data["morphology"]["analyses"][0]["lemma"]["public_id"] == ni.public_id
    assert "zero_result" not in data

    response = client.get(
        "/v1/search",
        {"q": "handine"},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["count"] == 0
    zero = data["zero_result"]
    assert zero["code"] == "NO_MATCH"
    assert zero["morphology_enrichment"]["status"] == "unsupported"
    lanes = zero["morphology_enrichment"]["detail"]["future_lanes"]
    assert any(
        lane["code"] == "excluded_defective_pro_verb_stem" for lane in lanes
    )


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

    # 2. Negative present with person subject and person object (handikudi)
    response = client.post(
        "/v1/analyze",
        {"text": "handikudi"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    analysis = response.json()["data"]["analyses"][0]
    assert analysis["rule_id"] == "fortune.concord.object.001"
    assert analysis["slots"]["polarity"]["value"] == "negative"
    assert analysis["slots"]["object"]["surface"] == "ku"
    assert analysis["slots"]["verb_stem"]["surface"] == "di"

    # 3. Class 2 subject, Class 2 object, a-initial stem: the object
    # concord|stem contact is deferred pending evidence (morphology-rules-v5);
    # neither the contracted spelling nor the hiatus spelling is inferred.
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

    def assert_deferred_object_lane(text):
        response = client.post(
            "/v1/analyze",
            {"text": text},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Api-Key {api_key}",
        )
        assert response.status_code == 422, text
        matching = [
            lane
            for lane in response.json()["error"]["detail"]["future_lanes"]
            if lane["code"] == "deferred_finite_boundary"
            and lane["boundary"] == "object_before_a_initial_stem"
        ]
        assert matching, response.json()["error"]["detail"]["future_lanes"]
        assert matching[0]["support_status"] == "deferred_pending_evidence"
        assert matching[0]["rule_card_ids"] == ["fortune.verbal.slots.001"]

    for text in ("vanovambura", "vanovaambura"):
        assert_deferred_object_lane(text)

    # 4. Negative present, class 2 object across the same deferred boundary
    assert_deferred_object_lane("havavambure")


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

    # 2. Generate Negative Present with person object (handikudi)
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
    assert generated["form"] == "handikudi"
    assert generated["rule_id"] == "fortune.concord.object.001"
    assert generated["slots"]["object"]["surface"] == "ku"

    # 3. Generate Positive Present class 2 subject + class 2 object on an
    # a-initial stem: deferred pending evidence (morphology-rules-v5).
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
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "GENERATION_UNSUPPORTED"
    assert error["detail"]["field"] == "finite_boundary"
    assert error["detail"]["boundary"] == "object_before_a_initial_stem"

    # 4. Generate Negative Present across the same deferred boundary
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
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["detail"]["boundary"] == "object_before_a_initial_stem"


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
    # Finding 2: both "mu" object concords (3rd-singular and 2nd-plural)
    # prefix the stem, so both feature readings are returned, 3rd singular
    # first (PERSON_OBJECT_CONCORDS order); the exact -ambura reading is kept.
    assert body["data"]["count"] == 2
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
    second = body["data"]["analyses"][1]
    assert second["slots"]["object"]["person"] == "second"
    assert second["slots"]["object"]["number"] == "plural"
    assert second["lemma"]["public_id"] == vowel_verb_lemma.public_id


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

    # 3. Generation with the 3rd-person plural object on the a-initial stem:
    # the a-final object concord + a-initial stem contact is deferred pending
    # evidence (morphology-rules-v5); the mu-object form above stays supported.
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
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["detail"]["field"] == "finite_boundary"
    assert error["detail"]["boundary"] == "object_before_a_initial_stem"


@pytest.fixture
def vowel_boundary_classes(current_release):
    for class_number, subject_concord, object_concord in (
        ("1", "u", "mu"),
        ("2", "va", "va"),
        ("6", "a", "a"),
    ):
        NounClass.objects.get_or_create(
            class_number=class_number,
            defaults=dict(
                display_order=int(class_number),
                label=f"Class {class_number}",
                nominal_prefix=object_concord if class_number != "1" else "mu",
                subject_concord=subject_concord,
                object_concord=object_concord,
                review_state=ReviewState.APPROVED,
            ),
        )


@pytest.fixture
def badanudza_lemma(current_release):
    return Lemma.objects.create(
        headword="-badanudza",
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        part_of_speech_code="vt",
        part_of_speech_label="transitive verb",
        provenance={
            "source_key": "source_hannan",
            "entry_locator": "hannan:page_004:entry_004:badanudza",
        },
        review_state=ReviewState.APPROVED,
    )


@pytest.mark.django_db
def test_deferred_finite_vowel_boundaries_are_structured_generation_422s(
    client, corpus_api_key, current_release, vowel_verb_lemma, badanudza_lemma,
    vowel_boundary_classes,
):
    """morphology-rules-v5: no source witnesses an a-final subject/object
    concord immediately before an a-initial stem (Fortune 3.3.9 coalescence is
    nominal; the attested verbal witnesses retain double `aa`). Generation
    refuses those combinations with a stable boundary instead of contracting
    (the prior-v1 joining rule) or inventing unattested hiatus."""

    def features(polarity, subject, object_feature=None, extensions=None):
        payload = {
            "generation_type": "verb_form",
            "subject": subject,
            "tense_aspect": "present",
            "polarity": polarity,
        }
        if object_feature is not None:
            payload["object"] = object_feature
        if extensions is not None:
            payload["extensions"] = extensions
        return payload

    class2 = {"type": "noun_class", "class_number": "2"}
    class6 = {"type": "noun_class", "class_number": "6"}
    person_3pl = {"type": "person", "person": "third", "number": "plural"}

    cases = [
        # (lemma, features, expected boundary)
        (vowel_verb_lemma, features("positive", class2, class2), "object_before_a_initial_stem"),
        (vowel_verb_lemma, features("positive", class2, person_3pl), "object_before_a_initial_stem"),
        (vowel_verb_lemma, features("positive", class6, class6), "object_before_a_initial_stem"),
        (vowel_verb_lemma, features("negative", class2), "subject_before_a_initial_stem"),
        (vowel_verb_lemma, features("negative", class2, class2), "object_before_a_initial_stem"),
        (vowel_verb_lemma, features("negative", class2, class6), "object_before_a_initial_stem"),
        # the resulting stem after extensions still starts with the a-initial radical
        (vowel_verb_lemma, features("positive", class2, person_3pl, ["causative"]), "object_before_a_initial_stem"),
        (vowel_verb_lemma, features("negative", class2, None, ["causative"]), "subject_before_a_initial_stem"),
    ]
    for lemma, request_features, boundary in cases:
        response = client.post(
            "/v1/generate",
            {"lemma_public_id": lemma.public_id, "features": request_features},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Api-Key {corpus_api_key}",
        )
        assert response.status_code == 422, (request_features, response.json())
        error = response.json()["error"]
        assert error["code"] == "GENERATION_UNSUPPORTED"
        assert error["detail"]["field"] == "finite_boundary"
        assert error["detail"]["boundary"] == boundary
        assert error["detail"]["reason"] == "deferred_pending_evidence"
        assert error["detail"]["supported_rule_ids"] == [
            "fortune.verbal.slots.001",
            "fortune.verbal.negation.001",
            "fortune.concord.object.001",
        ]


@pytest.mark.django_db
def test_deferred_finite_vowel_boundaries_are_excluded_from_analysis(
    client, corpus_api_key, current_release, vowel_verb_lemma, vowel_boundary_classes
):
    """Analysis excludes only the unsupported inferred construction: contracted
    and hiatus spellings of the deferred boundary get no reading, while the
    surface itself is never blacklisted (supported readings elsewhere remain)."""

    deferred_lane = {
        "code": "deferred_finite_boundary",
        "support_status": "deferred_pending_evidence",
        "rule_card_ids": ["fortune.verbal.slots.001"],
    }
    cases = [
        ("vanovambura", "object_before_a_initial_stem"),
        ("vanovaambura", "object_before_a_initial_stem"),
        ("ndinovambura", "object_before_a_initial_stem"),
        ("ndinoaambura", "object_before_a_initial_stem"),
        ("havambure", "subject_before_a_initial_stem"),
        ("haambure", "subject_before_a_initial_stem"),
        ("havavambure", "object_before_a_initial_stem"),
        ("ndinovamburisa", "object_before_a_initial_stem"),
    ]
    for text, boundary in cases:
        response = client.post(
            "/v1/analyze",
            {"text": text},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Api-Key {corpus_api_key}",
        )
        assert response.status_code == 422, (text, response.json())
        error = response.json()["error"]
        assert error["code"] == "ANALYSIS_UNSUPPORTED"
        matching = [
            lane
            for lane in error["detail"]["future_lanes"]
            if lane["code"] == "deferred_finite_boundary"
            and lane["boundary"] == boundary
        ]
        assert matching, (text, error["detail"]["future_lanes"])
        assert matching[0]["support_status"] == deferred_lane["support_status"]
        assert matching[0]["rule_card_ids"] == deferred_lane["rule_card_ids"]


@pytest.mark.django_db
def test_attested_a_vowel_contacts_still_concatenate(
    client, corpus_api_key, current_release, verb_lemma, badanudza_lemma,
    vowel_boundary_classes,
):
    """Retention at attested contacts is unchanged: negative prefix + subject
    concord, subject concord + a-initial object concord, tense marker + object
    concord, and non-identical object|stem contacts keep both vowels."""

    class2 = {"type": "noun_class", "class_number": "2"}
    class6 = {"type": "noun_class", "class_number": "6"}

    # Positive generation: class 6 object before a consonant-initial stem
    response = client.post(
        "/v1/generate",
        {
            "lemma_public_id": badanudza_lemma.public_id,
            "features": {
                "generation_type": "verb_form",
                "subject": {"type": "person", "person": "first", "number": "singular"},
                "object": class6,
                "tense_aspect": "present",
                "polarity": "positive",
            },
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {corpus_api_key}",
    )
    assert response.status_code == 200
    assert response.json()["data"]["generated"]["form"] == "ndinoabadanudza"

    # Negative generation: subject|object a-a contact retained (Havaazivi-type)
    response = client.post(
        "/v1/generate",
        {
            "lemma_public_id": badanudza_lemma.public_id,
            "features": {
                "generation_type": "verb_form",
                "subject": class2,
                "object": class6,
                "tense_aspect": "present",
                "polarity": "negative",
            },
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {corpus_api_key}",
    )
    assert response.status_code == 200
    assert response.json()["data"]["generated"]["form"] == "havaabadanudzi"

    # Negative generation: negative prefix + class 1 subject a-a retained
    response = client.post(
        "/v1/generate",
        {
            "lemma_public_id": badanudza_lemma.public_id,
            "features": {
                "generation_type": "verb_form",
                "subject": {"type": "noun_class", "class_number": "1"},
                "tense_aspect": "present",
                "polarity": "negative",
            },
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {corpus_api_key}",
    )
    assert response.status_code == 200
    assert response.json()["data"]["generated"]["form"] == "haabadanudzi"

    # Analysis recovers the class 6 object reading across the retained aa
    response = client.post(
        "/v1/analyze",
        {"text": "havaabadanudzi"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {corpus_api_key}",
    )
    assert response.status_code == 200
    analyses = response.json()["data"]["analyses"]
    object_readings = [
        analysis
        for analysis in analyses
        if analysis["slots"]["object"]
        and analysis["slots"]["object"]["surface"] == "a"
        and analysis["lemma"]["public_id"] == badanudza_lemma.public_id
    ]
    assert object_readings, analyses

    # Positive class 2 subject with object before a consonant-initial stem
    response = client.post(
        "/v1/analyze",
        {"text": "vanovabadanudza"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {corpus_api_key}",
    )
    assert response.status_code == 200
    analyses = response.json()["data"]["analyses"]
    assert any(
        analysis["slots"]["object"]
        and analysis["slots"]["object"]["surface"] == "va"
        and analysis["lemma"]["public_id"] == badanudza_lemma.public_id
        for analysis in analyses
    )


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

    # 4. Generate negative present causative of buda -> handibudisi
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
    assert data["generated"]["form"] == "handibudisi"


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

    # 3. Compound stack outside the documented sequence convention
    # (neuter applied before reciprocal): the shared analyzer/generator
    # policy rejects the sequence, so the surface is unsupported.
    response = client.post(
        "/v1/analyze",
        {"text": "munobudikana"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "ANALYSIS_UNSUPPORTED"



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
def test_analyze_endpoint_excludes_unverified_secondary_causative_derivations(
    client, api_key, current_release, verb_lemma
):
    """Supervisor blocker: publishing -buda or -chema does not authorize the
    -idz-/-its- derivations. The analyzer excludes those readings; the
    structured 422 explains the evidence gate."""
    Lemma.objects.create(
        headword="-chema",
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        part_of_speech_code="vi",
        part_of_speech_label="intransitive verb",
        provenance={"source_key": "source_hannan", "entry_locator": "fixture:chema"},
        review_state=ReviewState.PUBLISHED,
    )

    for text in ("kuchemedza", "kubuditsa", "kubudidza"):
        response = client.post(
            "/v1/analyze",
            {"text": text},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Api-Key {api_key}",
        )
        assert response.status_code == 422, text
        error = response.json()["error"]
        assert error["code"] == "ANALYSIS_UNSUPPORTED", text
        lane_codes = [
            lane["code"] for lane in error["detail"]["future_lanes"]
        ]
        assert "unverified_extension_derivation" in lane_codes, text


@pytest.mark.django_db
def test_analyze_endpoint_returns_long_reversive_with_vowel_copy(
    client, api_key, current_release
):
    # Reversive analysis with vowel copy: kupetenura.
    # Corrected under morphology-rules-v3: Fortune Vol. 1 section 2.10.2.3.3(c)
    # gives -pfek- -> -pfekenur-, so an e-radical like -peta- takes -enur-, not
    # the old u/o-only -unur-. The previous kupetunura expectation encoded the
    # implementation bug and is now an unsupported surface (422, below).
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
        {"text": "kupetenura"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    body = response.json()
    analysis = body["data"]["analyses"][0]
    assert analysis["lemma"]["public_id"] == peta_lemma.public_id
    assert analysis["slots"]["extensions"] == [
        {"surface": "enur", "type": "reversive", "style": "long", "label": "reversive extension (-anur- / -enur- / -inur- / -onor- / -unur-)"}
    ]

    # The old u/o-only surface violates vowel copy and no longer analyzes.
    response = client.post(
        "/v1/analyze",
        {"text": "kupetunura"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 422


@pytest.mark.django_db
def test_generate_endpoint_refuses_unverified_secondary_causatives(
    client, api_key, current_release, verb_lemma
):
    """Finding 4: dz/ts causative allomorphs are evidence-gated on both sides:
    generation refuses them with a structured EXTENSION_UNVERIFIED error
    instead of a warning."""
    for style in ("dz", "ts"):
        response = client.post(
            "/v1/generate",
            {
                "lemma_public_id": verb_lemma.public_id,
                "features": {
                    "generation_type": "verb_form",
                    "subject": {"type": "person", "person": "first", "number": "singular"},
                    "tense_aspect": "present",
                    "polarity": "positive",
                    "extensions": [{"type": "causative", "style": style}]
                },
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Api-Key {api_key}",
        )
        assert response.status_code == 422, style
        body = response.json()
        assert body["error"]["code"] == "EXTENSION_UNVERIFIED", style
        assert body["error"]["detail"]["extension_type"] == "causative", style
        assert body["error"]["detail"]["style"] == style, style


@pytest.mark.django_db
def test_generate_endpoint_reversive_long_round_trips(
    client, api_key, current_release, verb_lemma
):
    # Reversive generation (long with vowel copy): kora -> ndinokoronora.
    # Corrected under morphology-rules-v3: Fortune Vol. 1 section 2.10.2.3.3(c)
    # gives -roy- -> -royonor-, so an o-radical takes -onor-. The previous
    # ndinokororora expectation mislabeled the repetitive extension (-oror-,
    # section (b)) as reversive; ndinokororora is now generated via
    # {"type": "repetitive"} instead.
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
    assert body["data"]["generated"]["form"] == "ndinokoronora"
    assert body["data"]["generated"]["slots"]["extensions"] == [
        {"surface": "onor", "type": "reversive", "style": "long", "label": "reversive extension (-anur- / -enur- / -inur- / -onor- / -unur-)"}
    ]


