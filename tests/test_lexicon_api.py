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


def publish_canonical_bundle(canonical_lemma):
    for record in canonical_lemma:
        record.review_state = ReviewState.PUBLISHED
        record.save(update_fields=("review_state",))


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
            "entry_quality": {
                "sense_count": 1,
                "example_count": 0,
                "form_count": 1,
                "derived_form_count": 1,
                "tone_record_count": 1,
                "cross_reference_count": 0,
                "resolved_cross_reference_count": 0,
                "unresolved_cross_reference_count": 0,
            },
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
                "dialects": [],
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
    publish_canonical_bundle(canonical_lemma)

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
    publish_canonical_bundle(canonical_lemma)

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
def test_search_endpoint_applies_bounded_filters(
    client, api_key, current_release, canonical_lemma
):
    lemma, *_ = canonical_lemma
    other = Lemma.objects.create(
        headword="buda",
        headword_kind=Lemma.HeadwordKind.NOUN,
        part_of_speech_code="n",
        part_of_speech_label="noun",
        dialects=["M"],
        review_state=ReviewState.PUBLISHED,
    )
    Sense.objects.create(
        lemma=other,
        number=1,
        definition="Filtered noun duplicate.",
        review_state=ReviewState.PUBLISHED,
    )
    publish_canonical_bundle(canonical_lemma)

    response = client.get(
        "/v1/search",
        {
            "q": "buda",
            "headword_kind": "verb_stem",
            "pos": "vi",
            "dialect": "K",
            "limit": "1",
        },
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["count"] == 1
    assert body["data"]["query"]["filters"] == {
        "headword_kind": "verb_stem",
        "pos": "vi",
        "dialect": "K",
        "limit": 1,
    }
    assert body["data"]["results"][0]["lemma"]["public_id"] == lemma.public_id


@pytest.mark.django_db
def test_search_endpoint_rejects_invalid_filters(client, api_key, current_release):
    response = client.get(
        "/v1/search",
        {"q": "buda", "dialect": "bad"},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert response.status_code == 400
    assert response.json() == {
        "api_version": "v1",
        "error": {
            "code": "SEARCH_FILTER_INVALID",
            "message": "Invalid search filter 'dialect'.",
            "detail": {
                "field": "dialect",
                "value": "bad",
                "allowed_values": ["K", "Ko", "M", "Z"],
            },
        },
    }


@pytest.mark.django_db
def test_lemma_and_search_payloads_expose_derived_form_evidence(
    client, api_key, current_release, canonical_lemma
):
    lemma, _, _, form = canonical_lemma
    evidence = {
        "marker": ">",
        "relation": "headword_to_derived_form",
        "source_note": "> mbudo; rubudiko.",
        "source_path": "derived_forms[0]",
    }
    form.provenance = {
        **form.provenance,
        "derived_form_evidence": evidence,
    }
    form.save(update_fields=("provenance",))
    publish_canonical_bundle(canonical_lemma)

    lemma_response = client.get(
        f"/v1/lemmas/{lemma.public_id}",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    search_response = client.get(
        "/v1/search",
        {"q": "mbudo"},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert lemma_response.status_code == 200
    assert search_response.status_code == 200
    assert lemma_response.json()["data"]["forms"][0]["derived_form_evidence"] == evidence
    search_result = search_response.json()["data"]["results"][0]
    assert search_result["form"]["derived_form_evidence"] == evidence
    assert search_result["lemma"]["forms"][0]["derived_form_evidence"] == evidence


@pytest.mark.django_db
def test_lemma_and_search_payloads_use_shared_example_shape(
    client, api_key, current_release, canonical_lemma
):
    lemma, sense, *_ = canonical_lemma
    sense.examples = [
        {
            "text": "Ndinobuda muhotwe",
            "translation": "my nose is bleeding",
            "source_note": "Ndinobuda muhotwe: my nose is bleeding.",
            "dialects": ["K"],
        },
        "Ndabuda basa: I have left my employment.",
    ]
    sense.save(update_fields=("examples",))
    publish_canonical_bundle(canonical_lemma)

    lemma_response = client.get(
        f"/v1/lemmas/{lemma.public_id}",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    search_response = client.get(
        "/v1/search",
        {"q": "buda"},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    expected_examples = [
        {
            "shona": "Ndinobuda muhotwe",
            "english": "my nose is bleeding",
            "source_note": "Ndinobuda muhotwe: my nose is bleeding.",
            "dialects": ["K"],
        },
        {
            "shona": "Ndabuda basa",
            "english": "I have left my employment.",
        },
    ]
    assert lemma_response.status_code == 200
    assert search_response.status_code == 200
    assert lemma_response.json()["data"]["senses"][0]["examples"] == expected_examples
    assert (
        search_response.json()["data"]["results"][0]["lemma"]["senses"][0]["examples"]
        == expected_examples
    )


@pytest.mark.django_db
def test_lemma_and_search_payloads_resolve_cross_reference_targets(
    client, api_key, current_release, canonical_lemma
):
    lemma, sense, *_ = canonical_lemma
    target = Lemma.objects.create(
        headword="-simba",
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        part_of_speech_code="vi",
        review_state=ReviewState.PUBLISHED,
    )
    sense.cross_references = [
        {
            "type": "cp",
            "target": "-simba",
            "dialects": ["K"],
            "source_note": "cp -simba K.",
        },
        {
            "type": "see",
            "target": "chisipo",
            "source_note": "see chisipo.",
        },
    ]
    sense.save(update_fields=("cross_references",))
    publish_canonical_bundle(canonical_lemma)

    lemma_response = client.get(
        f"/v1/lemmas/{lemma.public_id}",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    search_response = client.get(
        "/v1/search",
        {"q": "buda"},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    expected_cross_references = [
        {
            "type": "cp",
            "target": "-simba",
            "dialects": ["K"],
            "source_note": "cp -simba K.",
            "resolved": True,
            "target_public_id": target.public_id,
            "target_headword": "-simba",
        },
        {
            "type": "see",
            "target": "chisipo",
            "dialects": [],
            "source_note": "see chisipo.",
            "resolved": False,
        },
    ]
    assert lemma_response.status_code == 200
    assert search_response.status_code == 200
    assert (
        lemma_response.json()["data"]["senses"][0]["cross_references"]
        == expected_cross_references
    )
    assert (
        search_response.json()["data"]["results"][0]["lemma"]["senses"][0][
            "cross_references"
        ]
        == expected_cross_references
    )


@pytest.mark.django_db
def test_lemma_and_search_payloads_share_entry_quality_summary(
    client, api_key, current_release, canonical_lemma
):
    lemma, sense, _, _ = canonical_lemma
    target = Lemma.objects.create(
        headword="-simba",
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        review_state=ReviewState.PUBLISHED,
    )
    sense.examples = [{"shona": "Ndinobuda muhotwe", "english": "my nose is bleeding"}]
    sense.cross_references = [
        {"type": "cp", "target": "-simba", "dialects": []},
        {"type": "see", "target": "chisipo", "dialects": []},
    ]
    sense.save(update_fields=("examples", "cross_references"))
    publish_canonical_bundle(canonical_lemma)

    lemma_response = client.get(
        f"/v1/lemmas/{lemma.public_id}",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    search_response = client.get(
        "/v1/search",
        {"q": "buda"},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    expected_quality = {
        "sense_count": 1,
        "example_count": 1,
        "form_count": 1,
        "derived_form_count": 1,
        "tone_record_count": 1,
        "cross_reference_count": 2,
        "resolved_cross_reference_count": 1,
        "unresolved_cross_reference_count": 1,
    }
    assert target.public_id
    assert lemma_response.status_code == 200
    assert search_response.status_code == 200
    assert lemma_response.json()["data"]["lemma"]["entry_quality"] == expected_quality
    assert (
        search_response.json()["data"]["results"][0]["lemma"]["entry_quality"]
        == expected_quality
    )


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
        "morphology_enrichment": {
            "status": "unsupported",
            "code": "ANALYSIS_UNSUPPORTED",
            "message": (
                "No supported v1 analysis matched the input. Supported v1 forms "
                "are ku- infinitive forms (ku + reviewed verb stem), positive "
                "present verb forms (subject concord + 'no' + [object_concord] "
                "+ verb_stem), and negative present verb forms (ha- + subject "
                "concord + [object_concord] + verb_stem ending in -e)."
            ),
        },
    }


@pytest.mark.django_db
def test_search_endpoint_hides_approved_unpublished_records(
    client, api_key, current_release, canonical_lemma
):
    response = client.get(
        "/v1/search",
        {"q": "-buda"},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert response.status_code == 200
    assert response.json()["data"]["count"] == 0


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


@pytest.mark.django_db
def test_search_endpoint_returns_morphology_analysis_on_verb_forms(
    client, api_key, current_release, canonical_lemma
):
    lemma, *_ = canonical_lemma
    publish_canonical_bundle(canonical_lemma)

    response = client.get(
        "/v1/search",
        {"q": "ndinobuda"},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["count"] == 0
    assert "zero_result" not in body["data"]
    assert body["data"]["morphology_enrichment"] == {
        "status": "matched",
        "count": 1,
    }
    assert "morphology" in body["data"]
    morph = body["data"]["morphology"]
    assert morph["count"] > 0
    analysis = morph["analyses"][0]
    assert analysis["analysis_type"] == "verb_form"
    assert analysis["lemma"]["public_id"] == lemma.public_id
    assert "lemma_details" in analysis
    assert analysis["lemma_details"]["public_id"] == lemma.public_id
    assert len(analysis["lemma_details"]["senses"]) == 1
    assert analysis["lemma_details"]["senses"][0]["definition"] == "Come out."


@pytest.mark.django_db
def test_search_endpoint_returns_morphology_analysis_on_ku_infinitives(
    client, api_key, current_release, canonical_lemma
):
    lemma, *_ = canonical_lemma
    publish_canonical_bundle(canonical_lemma)

    response = client.get(
        "/v1/search",
        {"q": "kubuda"},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["count"] == 0
    assert "zero_result" not in body["data"]
    assert body["data"]["morphology_enrichment"] == {
        "status": "matched",
        "count": 1,
    }
    analysis = body["data"]["morphology"]["analyses"][0]
    assert analysis["analysis_type"] == "infinitive"
    assert analysis["rule_id"] == "fortune.verbal.infinitive.001"
    assert analysis["slots"]["infinitive_prefix"]["surface"] == "ku"
    assert analysis["lemma"]["public_id"] == lemma.public_id
    assert analysis["lemma_details"]["public_id"] == lemma.public_id
    assert analysis["lemma_details"]["senses"][0]["definition"] == "Come out."


@pytest.mark.django_db
def test_search_zero_result_exposes_unsupported_shape_future_lane(
    client, api_key, current_release
):
    response = client.get(
        "/v1/search",
        {"q": "badanudzwa"},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert response.status_code == 200
    enrichment = response.json()["data"]["zero_result"]["morphology_enrichment"]
    assert enrichment["status"] == "unsupported"
    assert enrichment["detail"]["future_lanes"] == [
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
def test_search_endpoint_records_morphology_enrichment_failures(
    client, api_key, current_release, monkeypatch
):
    metrics = []

    def fail_analysis(raw_text, *, rule_set_version):
        raise RuntimeError("synthetic analyzer failure")

    def capture_metric(name, value=1, tags=None):
        metrics.append({"name": name, "value": value, "tags": tags or {}})

    monkeypatch.setattr(
        "shona_api.morphology.services.analyze_text",
        fail_analysis,
    )
    monkeypatch.setattr("shona_api.lexicon.views.record_metric", capture_metric)

    response = client.get(
        "/v1/search",
        {"q": "ndinobuda"},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert response.status_code == 200
    body = response.json()
    assert "morphology" not in body["data"]
    assert body["data"]["zero_result"] == {
        "code": "NO_MATCH",
        "message": "No reviewed lemma or form matched the query.",
        "morphology_enrichment": {
            "status": "failed",
            "code": "MORPHOLOGY_ENRICHMENT_FAILED",
            "message": (
                "Morphology enrichment failed; exact lexical search results "
                "are still returned."
            ),
        },
    }
    assert metrics == [
        {
            "name": "search.morphology_enrichment.failed",
            "value": 1,
            "tags": {"error_type": "RuntimeError"},
        }
    ]

