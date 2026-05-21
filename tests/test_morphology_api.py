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
        "supported_shape": "subject_concord + no + [object_concord] + verb_stem / ha + subject_concord + [object_concord] + verb_stem_ending_in_e",
        "supported_rule_ids": ["fortune.verbal.slots.001", "fortune.verbal.negation.001", "fortune.concord.object.001"],
    }


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
