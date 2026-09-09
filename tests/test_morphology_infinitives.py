"""Bounded infinitive analysis/generation (morphology-rules-v4).

Source locator for the construction expectations below:
Fortune, Shona Grammatical Constructions Vol. 1 (1985), section 3.3.18
"Noun Class 15", PDF pp. 90-91 (printed pp. 78-79).

Source-attested surfaces (verbatim in the source):
- kuzvitora "to take them" (object prefix)
- kuzviziva "to know oneself" (reflexive prefix)
- kusaziva "not to know" (negative prefix /-sa-/)
- ku-sa-zvi-ziv-a "not to know this" (negative + object combination)

Constructed combinations (documented as such, not verbatim source forms):
- negative + reflexive sharing the kusazviziva surface
- extension-bearing infinitives (e.g. -ziva + applicative -> kuzivira)
- hiatus at vowel boundaries (e.g. class-2 va + -ambura -> kuvaambura)
- finite-style person-object infinitives (e.g. kukutora)

The fixture radicals -ziva and -tora are the source's own example radicals
(-ziv-, -tor-); -buda/-ambura reuse the established morphology fixtures.
"""

import pytest
from django.core.cache import caches

from shona_api.api_auth.models import APIKey
from shona_api.editorial.models import ReviewState
from shona_api.lexicon.models import Lemma, NounClass
from shona_api.morphology.services import MORPHOLOGY_RULES_VERSION
from shona_api.releases.models import DataRelease


@pytest.fixture(autouse=True)
def infinitive_api_settings(settings):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "infinitive-tests",
        }
    }
    caches["default"].clear()


@pytest.fixture
def current_release():
    return DataRelease.objects.create(
        version="2026.09.0",
        label="Infinitive release",
        rule_set_version=MORPHOLOGY_RULES_VERSION,
        is_current=True,
    )


@pytest.fixture
def api_key():
    _, raw_key = APIKey.objects.create_key(
        name="Infinitive client",
        plan=APIKey.Plan.DEVELOPER,
        rate_limit_per_minute=60,
    )
    return raw_key


def make_verb(headword, review_state=ReviewState.APPROVED):
    return Lemma.objects.create(
        headword=headword,
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        part_of_speech_code="vt",
        part_of_speech_label="transitive verb",
        provenance={
            "source_key": "source_hannan",
            "entry_locator": "fixture:infinitive",
        },
        review_state=review_state,
    )


def make_class_8():
    return NounClass.objects.create(
        class_number="8",
        display_order=8,
        label="Class 8",
        nominal_prefix="zvi",
        subject_concord="zvi",
        object_concord="zvi",
        review_state=ReviewState.APPROVED,
    )


def make_class_2():
    return NounClass.objects.create(
        class_number="2",
        display_order=2,
        label="Class 2",
        nominal_prefix="va",
        subject_concord="va",
        object_concord="va",
        review_state=ReviewState.APPROVED,
    )


def generate(client, api_key, lemma, features):
    return client.post(
        "/v1/generate",
        {"lemma_public_id": lemma.public_id, "features": features},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )


def analyze(client, api_key, text):
    return client.post(
        "/v1/analyze",
        {"text": text},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )


def infinitive_features(**overrides):
    features = {"generation_type": "infinitive"}
    features.update(overrides)
    return features


# --- Source-attested generation ------------------------------------------------


@pytest.mark.django_db
def test_generate_positive_infinitive(client, api_key, current_release):
    lemma = make_verb("-ziva")
    response = generate(client, api_key, lemma, infinitive_features())

    assert response.status_code == 200, response.content
    generated = response.json()["data"]["generated"]
    assert generated["generation_type"] == "infinitive"
    assert generated["form"] == "kuziva"
    assert generated["rule_id"] == "fortune.verbal.infinitive.001"
    assert generated["slots"]["infinitive_prefix"]["surface"] == "ku"
    assert generated["slots"]["polarity"] == {
        "surface": "",
        "value": "positive",
        "label": "No negative marker in the supported infinitive pattern.",
    }
    assert generated["slots"]["object"] is None
    assert generated["slots"]["reflexive"] is None
    assert generated["slots"]["verb_stem"] == {
        "surface": "ziva",
        "lemma_public_id": lemma.public_id,
    }
    assert generated["slots"]["final_vowel"] == {"surface": "a", "value": "a"}


@pytest.mark.django_db
def test_generate_positive_infinitive_vowel_initial_stem(
    client, api_key, current_release
):
    lemma = make_verb("-ambura")
    response = generate(client, api_key, lemma, infinitive_features())

    assert response.status_code == 200, response.content
    assert response.json()["data"]["generated"]["form"] == "kuambura"


@pytest.mark.django_db
def test_generate_negative_infinitive_is_source_attested_kusaziva(
    client, api_key, current_release
):
    lemma = make_verb("-ziva")
    response = generate(
        client, api_key, lemma, infinitive_features(polarity="negative")
    )

    assert response.status_code == 200, response.content
    generated = response.json()["data"]["generated"]
    assert generated["form"] == "kusaziva"
    assert generated["slots"]["polarity"] == {
        "surface": "sa",
        "value": "negative",
        "label": "infinitive negative marker",
    }
    # Unlike finite negatives, the infinitive keeps terminal -a (kusaziva).
    assert generated["slots"]["final_vowel"] == {"surface": "a", "value": "a"}


@pytest.mark.django_db
def test_generate_object_infinitive_is_source_attested_kuzvitora(
    client, api_key, current_release
):
    make_class_8()
    lemma = make_verb("-tora")
    response = generate(
        client,
        api_key,
        lemma,
        infinitive_features(object={"type": "noun_class", "class_number": "8"}),
    )

    assert response.status_code == 200, response.content
    generated = response.json()["data"]["generated"]
    assert generated["form"] == "kuzvitora"
    assert generated["slots"]["object"]["surface"] == "zvi"
    assert generated["slots"]["object"]["class_number"] == "8"
    assert generated["slots"]["reflexive"] is None


@pytest.mark.django_db
def test_generate_reflexive_infinitive_is_source_attested_kuzviziva(
    client, api_key, current_release
):
    lemma = make_verb("-ziva")
    response = generate(client, api_key, lemma, infinitive_features(reflexive=True))

    assert response.status_code == 200, response.content
    generated = response.json()["data"]["generated"]
    assert generated["form"] == "kuzviziva"
    assert generated["slots"]["reflexive"] == {
        "surface": "zvi",
        "value": True,
        "label": "reflexive prefix",
    }
    assert generated["slots"]["object"] is None


@pytest.mark.django_db
def test_generate_negative_object_infinitive_is_source_attested_kusazviziva(
    client, api_key, current_release
):
    make_class_8()
    lemma = make_verb("-ziva")
    response = generate(
        client,
        api_key,
        lemma,
        infinitive_features(
            polarity="negative",
            object={"type": "noun_class", "class_number": "8"},
        ),
    )

    assert response.status_code == 200, response.content
    generated = response.json()["data"]["generated"]
    assert generated["form"] == "kusazviziva"
    assert generated["slots"]["polarity"]["value"] == "negative"
    assert generated["slots"]["object"]["surface"] == "zvi"
    assert generated["slots"]["reflexive"] is None


# --- Analysis keeps object and reflexive readings distinct ----------------------


@pytest.mark.django_db
def test_analyze_positive_infinitive_single_reading(
    client, api_key, current_release
):
    make_verb("-ziva")
    make_class_8()
    response = analyze(client, api_key, "kuziva")

    assert response.status_code == 200, response.content
    body = response.json()["data"]
    assert body["count"] == 1
    analysis = body["analyses"][0]
    assert analysis["analysis_type"] == "infinitive"
    assert analysis["rule_id"] == "fortune.verbal.infinitive.001"
    assert analysis["slots"]["polarity"]["value"] == "positive"
    assert analysis["slots"]["object"] is None
    assert analysis["slots"]["reflexive"] is None
    assert analysis["slots"]["verb_stem"]["surface"] == "ziva"


@pytest.mark.django_db
def test_analyze_negative_infinitive_kusaziva(client, api_key, current_release):
    lemma = make_verb("-ziva")
    response = analyze(client, api_key, "kusaziva")

    assert response.status_code == 200, response.content
    body = response.json()["data"]
    assert body["count"] == 1
    analysis = body["analyses"][0]
    assert analysis["analysis_type"] == "infinitive"
    assert analysis["lemma"]["public_id"] == lemma.public_id
    assert analysis["slots"]["polarity"] == {
        "surface": "sa",
        "value": "negative",
        "label": "infinitive negative marker",
    }
    assert analysis["slots"]["verb_stem"]["surface"] == "ziva"
    assert analysis["slots"]["final_vowel"] == {"surface": "a", "value": "a"}


@pytest.mark.django_db
def test_analyze_shared_zvi_surface_keeps_object_and_reflexive_readings(
    client, api_key, current_release
):
    lemma = make_verb("-ziva")
    make_class_8()
    response = analyze(client, api_key, "kuzviziva")

    assert response.status_code == 200, response.content
    analyses = response.json()["data"]["analyses"]
    assert len(analyses) == 2
    by_kind = {}
    for analysis in analyses:
        assert analysis["lemma"]["public_id"] == lemma.public_id
        assert analysis["slots"]["verb_stem"]["surface"] == "ziva"
        if analysis["slots"]["reflexive"] is not None:
            by_kind["reflexive"] = analysis
        else:
            by_kind["object"] = analysis
    assert by_kind["reflexive"]["slots"]["reflexive"]["surface"] == "zvi"
    assert by_kind["reflexive"]["slots"]["object"] is None
    assert by_kind["object"]["slots"]["object"]["surface"] == "zvi"
    assert by_kind["object"]["slots"]["object"]["class_number"] == "8"
    assert by_kind["object"]["slots"]["reflexive"] is None


@pytest.mark.django_db
def test_analyze_negative_object_kusazviziva(client, api_key, current_release):
    lemma = make_verb("-ziva")
    make_class_8()
    response = analyze(client, api_key, "kusazviziva")

    assert response.status_code == 200, response.content
    analyses = response.json()["data"]["analyses"]
    assert len(analyses) == 2
    for analysis in analyses:
        assert analysis["lemma"]["public_id"] == lemma.public_id
        assert analysis["slots"]["polarity"]["value"] == "negative"
        assert analysis["slots"]["verb_stem"]["surface"] == "ziva"
    kinds = {
        "reflexive" if item["slots"]["reflexive"] is not None else "object"
        for item in analyses
    }
    assert kinds == {"reflexive", "object"}


@pytest.mark.django_db
def test_analyze_reflexive_only_without_zvi_object_concord(
    client, api_key, current_release
):
    lemma = make_verb("-ziva")
    response = analyze(client, api_key, "kuzviziva")

    assert response.status_code == 200, response.content
    analyses = response.json()["data"]["analyses"]
    assert len(analyses) == 1
    assert analyses[0]["lemma"]["public_id"] == lemma.public_id
    assert analyses[0]["slots"]["reflexive"]["surface"] == "zvi"
    assert analyses[0]["slots"]["object"] is None


# --- Round-trips -----------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "surface,features",
    [
        ("kuziva", infinitive_features()),
        ("kusaziva", infinitive_features(polarity="negative")),
        ("kuzviziva", infinitive_features(reflexive=True)),
        ("kusazviziva", infinitive_features(polarity="negative", reflexive=True)),
        ("kuambura", infinitive_features()),
    ],
)
def test_generated_infinitive_recovers_originating_lemma(
    client, api_key, current_release, surface, features
):
    lemma = make_verb("-ziva" if "ziv" in surface else "-ambura")
    generated = generate(client, api_key, lemma, features).json()["data"][
        "generated"
    ]["form"]
    assert generated == surface

    response = analyze(client, api_key, surface)
    assert response.status_code == 200, response.content
    analyses = response.json()["data"]["analyses"]
    matches = [
        item
        for item in analyses
        if item["lemma"]["public_id"] == lemma.public_id
        and item["slots"]["polarity"]["value"] == features.get("polarity", "positive")
        and (item["slots"]["reflexive"] is not None) == bool(features.get("reflexive"))
    ]
    assert matches, analyses


@pytest.mark.django_db
def test_object_infinitive_round_trip(client, api_key, current_release):
    make_class_8()
    lemma = make_verb("-tora")
    response = generate(
        client,
        api_key,
        lemma,
        infinitive_features(object={"type": "noun_class", "class_number": "8"}),
    )
    assert response.json()["data"]["generated"]["form"] == "kuzvitora"

    analyses = analyze(client, api_key, "kuzvitora").json()["data"]["analyses"]
    object_readings = [
        item
        for item in analyses
        if item["lemma"]["public_id"] == lemma.public_id
        and item["slots"]["object"] is not None
    ]
    assert len(object_readings) == 1
    assert object_readings[0]["slots"]["object"]["class_number"] == "8"


@pytest.mark.django_db
def test_person_object_infinitive_round_trip(client, api_key, current_release):
    lemma = make_verb("-tora")
    response = generate(
        client,
        api_key,
        lemma,
        infinitive_features(
            object={"type": "person", "person": "second", "number": "singular"}
        ),
    )
    assert response.status_code == 200, response.content
    assert response.json()["data"]["generated"]["form"] == "kukutora"

    analyses = analyze(client, api_key, "kukutora").json()["data"]["analyses"]
    assert any(
        item["lemma"]["public_id"] == lemma.public_id
        and item["slots"]["object"] is not None
        and item["slots"]["object"]["person"] == "second"
        for item in analyses
    )


@pytest.mark.django_db
def test_infinitive_with_supported_extension_round_trip(
    client, api_key, current_release
):
    lemma = make_verb("-ziva")
    response = generate(
        client, api_key, lemma, infinitive_features(extensions=["applicative"])
    )

    assert response.status_code == 200, response.content
    generated = response.json()["data"]["generated"]
    assert generated["form"] == "kuzivira"
    assert [item["type"] for item in generated["slots"]["extensions"]] == [
        "applicative"
    ]
    analyses = analyze(client, api_key, "kuzivira").json()["data"]["analyses"]
    assert any(
        item["lemma"]["public_id"] == lemma.public_id
        and [entry["type"] for entry in item["slots"]["extensions"]] == ["applicative"]
        for item in analyses
    )


@pytest.mark.django_db
def test_negative_object_infinitive_with_extension(
    client, api_key, current_release
):
    make_class_8()
    lemma = make_verb("-ziva")
    response = generate(
        client,
        api_key,
        lemma,
        infinitive_features(
            polarity="negative",
            object={"type": "noun_class", "class_number": "8"},
            extensions=["applicative"],
        ),
    )

    assert response.status_code == 200, response.content
    assert response.json()["data"]["generated"]["form"] == "kusazvizivira"


@pytest.mark.django_db
def test_infinitive_object_vowel_stem_is_deferred(client, api_key, current_release):
    make_class_2()
    lemma = make_verb("-ambura")
    response = generate(
        client,
        api_key,
        lemma,
        infinitive_features(object={"type": "noun_class", "class_number": "2"}),
    )

    assert response.status_code == 422, response.content
    detail = response.json()["error"]["detail"]
    assert detail["field"] == "infinitive_boundary"
    assert detail["boundary"] == "object_before_a_initial_stem"
    assert detail["reason"] == "deferred_pending_evidence"

    analyses = analyze(client, api_key, "kuvaambura")
    assert analyses.status_code == 422, analyses.content
    lanes = analyses.json()["error"]["detail"]["future_lanes"]
    assert "deferred_infinitive_boundary" in [lane["code"] for lane in lanes]

@pytest.mark.django_db
@pytest.mark.parametrize("surface", ["kusambura", "kuvambura", "kusaaziva"])
def test_contracted_spellings_without_construction_are_422(
    client, api_key, current_release, surface
):
    """Contracted a-vowel spellings are produced by no v1 construction.

    Verbs retain hiatus (akaenda, kuasakura), so kusambura/kuvambura have no
    supported reading. kusaaziva needs an a-concord (e.g. class 6) to resolve
    its object reading, so it also 422s here.
    """
    make_verb("-ziva")
    make_verb("-ambura")
    response = analyze(client, api_key, surface)
    assert response.status_code == 422, response.content
    assert response.json()["error"]["code"] == "ANALYSIS_UNSUPPORTED"


@pytest.mark.django_db
def test_sa_initial_stem_has_no_negative_phantom(client, api_key, current_release):
    lemma = make_verb("-sara")
    response = analyze(client, api_key, "kusara")

    assert response.status_code == 200, response.content
    analyses = response.json()["data"]["analyses"]
    assert len(analyses) == 1
    assert analyses[0]["lemma"]["public_id"] == lemma.public_id
    assert analyses[0]["slots"]["polarity"]["value"] == "positive"
    assert analyses[0]["slots"]["verb_stem"]["surface"] == "sara"


@pytest.mark.django_db
def test_object_reading_requires_lexical_stem(client, api_key, current_release):
    make_verb("-tora")
    response = analyze(client, api_key, "kumutora")

    assert response.status_code == 200, response.content
    analyses = response.json()["data"]["analyses"]
    # Both "mu" object concords (3rd-singular and 2nd-plural) prefix the stem,
    # so both feature readings are returned; -mutora is not published, so no
    # exact reading competes.
    assert len(analyses) == 2
    for analysis in analyses:
        assert analysis["slots"]["object"]["surface"] == "mu"
        assert analysis["slots"]["verb_stem"]["surface"] == "tora"


@pytest.mark.django_db
def test_published_homograph_keeps_exact_and_object_readings(
    client, api_key, current_release
):
    make_verb("-tora")
    homograph = make_verb("-mutora")
    response = analyze(client, api_key, "kumutora")

    assert response.status_code == 200, response.content
    analyses = response.json()["data"]["analyses"]
    assert {
        (item["lemma"]["headword"], item["slots"]["object"] is not None)
        for item in analyses
    } == {("-mutora", False), ("-tora", True)}


@pytest.mark.django_db
def test_divergent_stem_generation_is_refused(client, api_key, current_release):
    lemma = make_verb("-ti")
    response = generate(client, api_key, lemma, infinitive_features())

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "GENERATION_UNSUPPORTED"
    assert body["error"]["detail"]["field"] == "lemma_stem"


@pytest.mark.django_db
def test_divergent_stem_analyzes_as_own_lemma(client, api_key, current_release):
    lemma = make_verb("-ti")
    response = analyze(client, api_key, "kuti")

    assert response.status_code == 200, response.content
    analyses = response.json()["data"]["analyses"]
    assert len(analyses) == 1
    assert analyses[0]["lemma"]["public_id"] == lemma.public_id
    assert analyses[0]["slots"]["verb_stem"]["surface"] == "ti"
    assert analyses[0]["slots"]["final_vowel"] == {"surface": "i", "value": "i"}


# --- Malformed and unsupported requests --------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "features",
    [
        infinitive_features(reflexive=True, object={"type": "noun_class", "class_number": "8"}),
        infinitive_features(
            subject={"type": "person", "person": "first", "number": "singular"}
        ),
        infinitive_features(tense_aspect="present"),
        infinitive_features(reflexive="yes"),
        infinitive_features(polarity="past"),
        infinitive_features(generation_type="verb_form", reflexive=True),
    ],
)
def test_conflicting_infinitive_features_are_structured_422(
    client, api_key, current_release, features
):
    make_class_8()
    lemma = make_verb("-ziva")
    response = generate(client, api_key, lemma, features)

    assert response.status_code == 422, response.content
    assert response.json()["error"]["code"] == "GENERATION_UNSUPPORTED"


@pytest.mark.django_db
def test_infinitive_generation_refuses_evidence_gated_extension(
    client, api_key, current_release
):
    lemma = make_verb("-ziva")
    response = generate(
        client,
        api_key,
        lemma,
        infinitive_features(extensions=[{"type": "causative", "style": "dz"}]),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "EXTENSION_UNVERIFIED"


@pytest.mark.django_db
def test_infinitive_analysis_excludes_unverified_derivation(
    client, api_key, current_release
):
    make_verb("-ziva")
    response = analyze(client, api_key, "kuzivitsa")

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "ANALYSIS_UNSUPPORTED"
    lane_codes = [
        lane["code"] for lane in body["error"]["detail"]["future_lanes"]
    ]
    assert "unverified_extension_derivation" in lane_codes


@pytest.mark.django_db
def test_published_derived_lemma_resolves_as_itself(client, api_key, current_release):
    derived = make_verb("-zivisa")
    response = analyze(client, api_key, "kuzivisa")

    assert response.status_code == 200, response.content
    analyses = response.json()["data"]["analyses"]
    assert len(analyses) == 1
    assert analyses[0]["lemma"]["public_id"] == derived.public_id
    assert analyses[0]["slots"]["extensions"] == []


@pytest.mark.django_db
def test_independently_reviewed_stem_survives_deferral(client, api_key, current_release):
    """A reviewed -sambura still analyzes as positive ku + sambura.

    Deferral is boundary-precise, not a spelling blacklist: the same surface
    must not be inferred as negative sa + ambura (deferred sa/stem
    boundary), but its exact lexical reading stays available.
    """
    make_verb("-ambura")
    sambura = make_verb("-sambura")
    response = analyze(client, api_key, "kusambura")

    assert response.status_code == 200, response.content
    analyses = response.json()["data"]["analyses"]
    assert len(analyses) == 1
    assert analyses[0]["lemma"]["public_id"] == sambura.public_id
    assert analyses[0]["slots"]["polarity"]["value"] == "positive"
    assert analyses[0]["slots"]["verb_stem"]["surface"] == "sambura"


@pytest.mark.django_db
def test_unsupported_object_class_is_structured_422(
    client, api_key, current_release
):
    lemma = make_verb("-ziva")
    response = generate(
        client,
        api_key,
        lemma,
        infinitive_features(object={"type": "noun_class", "class_number": "99"}),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "GENERATION_UNSUPPORTED"


# --- Search enrichment and version policy --------------------------------------------------


@pytest.mark.django_db
def test_search_matches_negative_infinitive(client, api_key, current_release):
    lemma = make_verb("-ziva")
    Lemma.objects.filter(pk=lemma.pk).update(review_state=ReviewState.PUBLISHED)
    response = client.get(
        "/v1/search",
        {"q": "kusaziva"},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert response.status_code == 200, response.content
    body = response.json()["data"]
    assert body["morphology_enrichment"]["status"] == "matched"
    analyses = body["morphology"]["analyses"]
    assert any(
        item["lemma"]["public_id"] == lemma.public_id
        and item["slots"]["polarity"]["value"] == "negative"
        for item in analyses
    )


@pytest.mark.django_db
def test_previous_rules_version_is_rejected(client, api_key):
    DataRelease.objects.create(
        version="2026.09.0",
        label="Pre-infinitive release",
        rule_set_version="morphology-rules-v3",
        is_current=True,
    )
    lemma = make_verb("-ziva")

    auth = {"HTTP_AUTHORIZATION": f"Api-Key {api_key}"}
    generate_response = client.post(
        "/v1/generate",
        {"lemma_public_id": lemma.public_id, "features": infinitive_features()},
        content_type="application/json",
        **auth,
    )
    assert generate_response.status_code == 503
    assert (
        generate_response.json()["error"]["code"]
        == "MORPHOLOGY_RULES_VERSION_UNSUPPORTED"
    )

    analyze_response = client.post(
        "/v1/analyze",
        {"text": "kusaziva"},
        content_type="application/json",
        **auth,
    )
    assert analyze_response.status_code == 503

    search_response = client.get("/v1/search", {"q": "kusaziva"}, **auth)
    assert search_response.status_code == 200
    assert (
        search_response.json()["data"]["zero_result"]["morphology_enrichment"][
            "status"
        ]
        == "unavailable"
    )


# --- Deferred a-vowel boundaries ------------------------------------------------------------
#
# Two infinitive morpheme boundaries lack applicable source evidence and are
# deferred: sa- before an a-initial object concord or stem, and an a-final
# object concord before an a-initial stem. The nominal a + a > a coalescence
# (Fortune 3.3.9) is explicitly nominal; verb hiatus witnesses (kuasakura,
# akaenda, Usaenda, Ndaatora, kumuona, tisina kumuona) do not establish these
# specific contacts, so neither concatenated nor contracted spellings
# authorize an inferred reading here. Excluded with reasons: kaana (Bemba),
# saakadzama (adverbial sa-), zvaakatya (stem unverified).


def make_class_6():
    return NounClass.objects.create(
        class_number="6",
        display_order=6,
        label="Class 6",
        nominal_prefix="ma",
        subject_concord="a",
        object_concord="a",
        review_state=ReviewState.APPROVED,
    )


@pytest.mark.django_db
def test_generate_negative_class6_object_is_deferred(
    client, api_key, current_release
):
    make_class_6()
    lemma = make_verb("-ziva")
    response = generate(
        client,
        api_key,
        lemma,
        infinitive_features(
            polarity="negative",
            object={"type": "noun_class", "class_number": "6"},
        ),
    )

    assert response.status_code == 422, response.content
    body = response.json()
    assert body["error"]["code"] == "GENERATION_UNSUPPORTED"
    detail = body["error"]["detail"]
    assert detail["field"] == "infinitive_boundary"
    assert detail["boundary"] == "sa_before_a_initial_object"
    assert detail["reason"] == "deferred_pending_evidence"


@pytest.mark.django_db
def test_analyze_kusaaziva_defers_unsupported_boundary(
    client, api_key, current_release
):
    make_verb("-ziva")
    make_class_6()
    response = analyze(client, api_key, "kusaaziva")

    assert response.status_code == 422, response.content
    body = response.json()
    assert body["error"]["code"] == "ANALYSIS_UNSUPPORTED"
    lanes = body["error"]["detail"]["future_lanes"]
    assert [lane["code"] for lane in lanes] == ["deferred_infinitive_boundary"]
    assert lanes[0]["support_status"] == "deferred_pending_evidence"
    assert lanes[0]["boundary"] == "sa_before_a_initial_object"


@pytest.mark.django_db
def test_analyze_kusaziva_is_no_object_only(client, api_key, current_release):
    lemma = make_verb("-ziva")
    make_class_6()
    response = analyze(client, api_key, "kusaziva")

    assert response.status_code == 200, response.content
    analyses = response.json()["data"]["analyses"]
    assert len(analyses) == 1
    assert analyses[0]["lemma"]["public_id"] == lemma.public_id
    assert analyses[0]["slots"]["polarity"]["value"] == "negative"
    assert analyses[0]["slots"]["object"] is None
    assert analyses[0]["slots"]["verb_stem"]["surface"] == "ziva"


@pytest.mark.django_db
def test_positive_class6_object_consonant_stem_round_trip(
    client, api_key, current_release
):
    make_class_6()
    lemma = make_verb("-ziva")
    response = generate(
        client,
        api_key,
        lemma,
        infinitive_features(object={"type": "noun_class", "class_number": "6"}),
    )

    assert response.status_code == 200, response.content
    assert response.json()["data"]["generated"]["form"] == "kuaziva"

    analyses = analyze(client, api_key, "kuaziva").json()["data"]["analyses"]
    assert len(analyses) == 1
    assert analyses[0]["lemma"]["public_id"] == lemma.public_id
    assert analyses[0]["slots"]["object"]["class_number"] == "6"
    assert analyses[0]["slots"]["verb_stem"]["surface"] == "ziva"


@pytest.mark.django_db
def test_positive_class6_object_vowel_stem_is_deferred(
    client, api_key, current_release
):
    make_class_6()
    lemma = make_verb("-ambura")
    response = generate(
        client,
        api_key,
        lemma,
        infinitive_features(object={"type": "noun_class", "class_number": "6"}),
    )

    assert response.status_code == 422, response.content
    detail = response.json()["error"]["detail"]
    assert detail["field"] == "infinitive_boundary"
    assert detail["boundary"] == "object_before_a_initial_stem"
    assert detail["reason"] == "deferred_pending_evidence"

    analyses = analyze(client, api_key, "kuaambura")
    assert analyses.status_code == 422, analyses.content
    lanes = analyses.json()["error"]["detail"]["future_lanes"]
    assert "deferred_infinitive_boundary" in [lane["code"] for lane in lanes]
    deferred = [lane for lane in lanes if lane["code"] == "deferred_infinitive_boundary"]
    assert deferred[0]["boundary"] == "object_before_a_initial_stem"


@pytest.mark.django_db
def test_negative_class6_object_vowel_stem_is_deferred(
    client, api_key, current_release
):
    make_class_6()
    lemma = make_verb("-ambura")
    response = generate(
        client,
        api_key,
        lemma,
        infinitive_features(
            polarity="negative",
            object={"type": "noun_class", "class_number": "6"},
        ),
    )

    assert response.status_code == 422, response.content
    detail = response.json()["error"]["detail"]
    assert detail["field"] == "infinitive_boundary"
    assert detail["boundary"] == "sa_before_a_initial_object"
    assert detail["reason"] == "deferred_pending_evidence"

    analyses = analyze(client, api_key, "kusaaambura")
    assert analyses.status_code == 422, analyses.content
    lanes = analyses.json()["error"]["detail"]["future_lanes"]
    assert "deferred_infinitive_boundary" in [lane["code"] for lane in lanes]


@pytest.mark.django_db
def test_negative_class6_object_with_extension_is_deferred(
    client, api_key, current_release
):
    make_class_6()
    lemma = make_verb("-ziva")
    response = generate(
        client,
        api_key,
        lemma,
        infinitive_features(
            polarity="negative",
            object={"type": "noun_class", "class_number": "6"},
            extensions=["applicative"],
        ),
    )

    assert response.status_code == 422, response.content
    detail = response.json()["error"]["detail"]
    assert detail["boundary"] == "sa_before_a_initial_object"
    assert detail["reason"] == "deferred_pending_evidence"

    analyses = analyze(client, api_key, "kusaazivira")
    assert analyses.status_code == 422, analyses.content
    lanes = analyses.json()["error"]["detail"]["future_lanes"]
    assert [lane["code"] for lane in lanes] == ["deferred_infinitive_boundary"]
    assert lanes[0]["boundary"] == "sa_before_a_initial_object"


@pytest.mark.django_db
def test_search_excludes_deferred_boundary_reading(
    client, api_key, current_release
):
    make_verb("-ziva")
    make_class_6()
    response = client.get(
        "/v1/search",
        {"q": "kusaaziva"},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert response.status_code == 200, response.content
    body = response.json()["data"]
    assert "morphology" not in body
    enrichment = body["zero_result"]["morphology_enrichment"]
    assert enrichment["status"] == "unsupported"
    assert enrichment["code"] == "ANALYSIS_UNSUPPORTED"
    lane_codes = [lane["code"] for lane in enrichment["detail"]["future_lanes"]]
    assert "deferred_infinitive_boundary" in lane_codes


# --- Infinitive feature allowlist ---------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "features",
    [
        infinitive_features(mood="imperative"),
        infinitive_features(mood="indicative", polarity="negative"),
        infinitive_features(aspect="perfective"),
        infinitive_features(tense="past"),
        infinitive_features(dialect="Zezuru"),
    ],
)
def test_unsupported_infinitive_feature_fields_are_structured_422(
    client, api_key, current_release, features
):
    lemma = make_verb("-ziva")
    response = generate(client, api_key, lemma, features)

    assert response.status_code == 422, response.content
    body = response.json()
    assert body["error"]["code"] == "GENERATION_UNSUPPORTED"


@pytest.mark.django_db
def test_infinitive_feature_allowlist_names_offending_field(
    client, api_key, current_release
):
    lemma = make_verb("-ziva")
    response = generate(
        client, api_key, lemma, infinitive_features(mood="imperative")
    )

    assert response.status_code == 422, response.content
    detail = response.json()["error"]["detail"]
    assert detail["field"] == "mood"
    assert detail["received"] == "imperative"
    assert "supported_shape" in detail


@pytest.mark.django_db
@pytest.mark.parametrize(
    "features",
    [
        infinitive_features(),
        infinitive_features(polarity="positive"),
        infinitive_features(polarity="negative"),
        infinitive_features(reflexive=False),
        infinitive_features(object=None),
        infinitive_features(extensions=[]),
    ],
)
def test_supported_infinitive_feature_fields_still_generate(
    client, api_key, current_release, features
):
    lemma = make_verb("-ziva")
    response = generate(client, api_key, lemma, features)

    assert response.status_code == 200, response.content
