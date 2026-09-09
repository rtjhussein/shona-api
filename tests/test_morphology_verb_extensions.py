"""Verb-extension regression tests grounded in Fortune Vol. 1, section 2.10.2.3.3.

Source locator for all extension expectations below:
Fortune, Shona Grammatical Constructions Vol. 1 (1985), section 2.10.2.3.3
"Extended radicals", PDF p. 33 (printed p. 21), plus the -eC- footnote.

Each test citing that locator distinguishes:
- source_attested: the radical relationship appears verbatim in the source
  (e.g. -pfek- -> -pfekenur-, -chat- -> -chatanur-), finite forms built from
  those radicals are constructed combinations of an attested derivation with
  the supported present construction;
- constructed_combination: the derivation applies a source-stated productive
  pattern (height harmony, vowel copy) to a fixture radical.

The four assignment reproductions are covered by:
- test_causative_round_trip_on_extension_looking_root (repro 1, -ambura)
- test_reversive_long_uses_vowel_copy_not_repetition (repro 2, -kora)
- test_reversive_enur_matches_source_radical_pair (repro 3, -pfeka)
- test_nonsense_extension_style_is_structured_422 (repro 4, -buda)
"""

import pytest
from django.core.cache import caches

from shona_api.api_auth.models import APIKey
from shona_api.editorial.models import ReviewState
from shona_api.lexicon.models import Lemma
from shona_api.releases.models import DataRelease


@pytest.fixture(autouse=True)
def extension_api_settings(settings):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "verb-extension-tests",
        }
    }
    caches["default"].clear()


@pytest.fixture
def current_release():
    return DataRelease.objects.create(
        version="2026.09.0",
        label="Extension correction release",
        rule_set_version="morphology-rules-v3",
        is_current=True,
    )


@pytest.fixture
def api_key():
    _, raw_key = APIKey.objects.create_key(
        name="Verb extension client",
        plan=APIKey.Plan.DEVELOPER,
        rate_limit_per_minute=60,
    )
    return raw_key


def make_verb(headword, review_state=ReviewState.PUBLISHED, pos="vt"):
    return Lemma.objects.create(
        headword=headword,
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        part_of_speech_code=pos,
        part_of_speech_label="transitive verb",
        provenance={
            "source_key": "source_hannan",
            "entry_locator": "fixture:extensions",
        },
        review_state=review_state,
    )


def generate(client, api_key, lemma, features):
    return client.post(
        "/v1/generate",
        {"lemma_public_id": lemma.public_id, "features": features},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )


def present_positive(features_extra=None):
    features = {
        "generation_type": "verb_form",
        "subject": {"type": "person", "person": "first", "number": "singular"},
        "tense_aspect": "present",
        "polarity": "positive",
    }
    features.update(features_extra or {})
    return features


def analyze(client, api_key, text):
    return client.post(
        "/v1/analyze",
        {"text": text},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )


# --- Assignment reproductions -------------------------------------------------


@pytest.mark.django_db
def test_causative_round_trip_on_extension_looking_root(
    client, api_key, current_release
):
    """Repro 1: -ambura ends in -ur- (reversive-looking) but is lexical.

    Generation of ndinoamburisa must analyze back to -ambura + causative
    instead of greedily stripping -ur- past the lexical boundary.
    """
    lemma = make_verb("-ambura")
    response = generate(
        client, api_key, lemma, present_positive({"extensions": ["causative"]})
    )
    assert response.status_code == 200
    assert response.json()["data"]["generated"]["form"] == "ndinoamburisa"

    response = analyze(client, api_key, "ndinoamburisa")
    assert response.status_code == 200
    analysis = response.json()["data"]["analyses"][0]
    assert analysis["lemma"]["public_id"] == lemma.public_id
    assert analysis["slots"]["extensions"] == [
        {
            "surface": "is",
            "type": "causative",
            "label": "causative extension (-is- / -es-)",
        }
    ]


@pytest.mark.django_db
def test_reversive_long_uses_vowel_copy_not_repetition(
    client, api_key, current_release
):
    """Repro 2: -urur-/-oror- is repetitive, not reversive (source section c vs b).

    -kora + reversive must yield -koronor- (vowel copy, o -> -onor-), while
    -kororor- remains available as the repetitive reading.
    """
    lemma = make_verb("-kora")
    response = generate(
        client,
        api_key,
        lemma,
        present_positive({"extensions": [{"type": "reversive", "style": "long"}]}),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["generated"]["form"] == "ndinokoronora"
    assert body["data"]["generated"]["slots"]["extensions"] == [
        {
            "surface": "onor",
            "type": "reversive",
            "style": "long",
            "label": "reversive extension (-anur- / -enur- / -inur- / -onor- / -unur-)",
        }
    ]

    response = analyze(client, api_key, "ndinokoronora")
    assert response.status_code == 200
    analysis = response.json()["data"]["analyses"][0]
    assert analysis["lemma"]["public_id"] == lemma.public_id
    assert analysis["slots"]["extensions"][0]["type"] == "reversive"
    assert analysis["slots"]["extensions"][0]["surface"] == "onor"

    # The old mislabeled surface is the repetitive, and still analyzes as such.
    response = generate(
        client,
        api_key,
        lemma,
        present_positive({"extensions": [{"type": "repetitive"}]}),
    )
    assert response.status_code == 200
    assert response.json()["data"]["generated"]["form"] == "ndinokororora"
    response = analyze(client, api_key, "ndinokororora")
    assert response.status_code == 200
    analysis = response.json()["data"]["analyses"][0]
    assert analysis["lemma"]["public_id"] == lemma.public_id
    assert analysis["slots"]["extensions"] == [
        {
            "surface": "oror",
            "type": "repetitive",
            "label": "repetitive extension (-urur- / -oror-)",
        }
    ]


@pytest.mark.django_db
def test_reversive_enur_matches_source_radical_pair(client, api_key, current_release):
    """Repro 3: source gives -pfek- -> -pfekenur-, not *-pfekunur-.

    Statuses: radical pair source_attested; finite ndinopfekenura a
    constructed_combination of that pair with the present construction.
    """
    lemma = make_verb("-pfeka")
    response = generate(
        client,
        api_key,
        lemma,
        present_positive({"extensions": [{"type": "reversive", "style": "long"}]}),
    )
    assert response.status_code == 200
    assert response.json()["data"]["generated"]["form"] == "ndinopfekenura"

    response = analyze(client, api_key, "ndinopfekenura")
    assert response.status_code == 200
    analysis = response.json()["data"]["analyses"][0]
    assert analysis["lemma"]["public_id"] == lemma.public_id
    assert analysis["slots"]["extensions"][0] == {
        "surface": "enur",
        "type": "reversive",
        "style": "long",
        "label": "reversive extension (-anur- / -enur- / -inur- / -onor- / -unur-)",
    }


@pytest.mark.django_db
def test_nonsense_extension_style_is_structured_422(client, api_key, current_release):
    """Repro 4: unknown styles must not silently fall back to the default."""
    lemma = make_verb("-buda")
    response = generate(
        client,
        api_key,
        lemma,
        present_positive({"extensions": [{"type": "causative", "style": "nonsense"}]}),
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "GENERATION_UNSUPPORTED"
    assert body["error"]["detail"]["field"] == "extensions"


# --- Allomorph conditions -----------------------------------------------------


@pytest.mark.django_db
def test_height_harmony_conditions_across_families(client, api_key, current_release):
    """Source footnote: -iC- extensions surface as -eC- after radical /e/ or /o/."""
    buda = make_verb("-buda")
    tenga = make_verb("-tenga")
    gova = make_verb("-gova")

    cases = [
        # (lemma, extensions, form, applied extensions)
        (
            buda,
            ["causative"],
            "ndinobudisa",
            [
                {
                    "surface": "is",
                    "type": "causative",
                    "label": "causative extension (-is- / -es-)",
                }
            ],
        ),
        (
            tenga,
            ["causative"],
            "ndinotengesa",
            [
                {
                    "surface": "es",
                    "type": "causative",
                    "label": "causative extension (-is- / -es-)",
                }
            ],
        ),
        (
            buda,
            ["applicative"],
            "ndinobudira",
            [
                {
                    "surface": "ir",
                    "type": "applicative",
                    "label": "applicative extension (-ir- / -er-)",
                }
            ],
        ),
        (
            tenga,
            ["applicative"],
            "ndinotengera",
            [
                {
                    "surface": "er",
                    "type": "applicative",
                    "label": "applicative extension (-ir- / -er-)",
                }
            ],
        ),
        (
            gova,
            ["applicative"],
            "ndinogovera",
            [
                {
                    "surface": "er",
                    "type": "applicative",
                    "label": "applicative extension (-ir- / -er-)",
                }
            ],
        ),
        (
            buda,
            ["neuter"],
            "ndinobudika",
            [
                {
                    "surface": "ik",
                    "type": "neuter",
                    "label": "neuter extension (-ik- / -ek-)",
                }
            ],
        ),
        (
            gova,
            ["neuter"],
            "ndinogoveka",
            [
                {
                    "surface": "ek",
                    "type": "neuter",
                    "label": "neuter extension (-ik- / -ek-)",
                }
            ],
        ),
        (
            buda,
            ["passive"],
            "ndinobudwa",
            [{"surface": "w", "type": "passive", "label": "passive extension (-w-)"}],
        ),
        (
            tenga,
            ["passive"],
            "ndinotengwa",
            [{"surface": "w", "type": "passive", "label": "passive extension (-w-)"}],
        ),
    ]
    for lemma, extensions, form, applied in cases:
        response = generate(
            client, api_key, lemma, present_positive({"extensions": extensions})
        )
        assert response.status_code == 200, (lemma.headword, extensions)
        body = response.json()
        assert body["data"]["generated"]["form"] == form, (lemma.headword, extensions)
        assert body["data"]["generated"]["slots"]["extensions"] == applied

        response = analyze(client, api_key, form)
        assert response.status_code == 200, form
        analysis = response.json()["data"]["analyses"][0]
        assert analysis["lemma"]["public_id"] == lemma.public_id, form
        assert analysis["slots"]["extensions"] == applied, form


@pytest.mark.django_db
def test_source_attested_reversive_pairs_generate_and_analyze(
    client, api_key, current_release
):
    """All five source reversive pairs from section 2.10.2.3.3(c)."""
    cases = [
        ("-chata", "ndinochatanura", "anur"),
        ("-pfeka", "ndinopfekenura", "enur"),
        ("-pinga", "ndinopinginura", "inur"),
        ("-roya", "ndinoroyonora", "onor"),
        ("-sunga", "ndinosungunura", "unur"),
    ]
    for headword, form, surface in cases:
        lemma = make_verb(headword)
        response = generate(
            client,
            api_key,
            lemma,
            present_positive({"extensions": [{"type": "reversive"}]}),
        )
        assert response.status_code == 200, headword
        assert response.json()["data"]["generated"]["form"] == form, headword

        response = analyze(client, api_key, form)
        assert response.status_code == 200, form
        analysis = response.json()["data"]["analyses"][0]
        assert analysis["lemma"]["public_id"] == lemma.public_id, form
        assert analysis["slots"]["extensions"][0]["surface"] == surface, form
        assert analysis["slots"]["extensions"][0]["type"] == "reversive", form


@pytest.mark.django_db
def test_repetitive_vowel_condition_matches_source(client, api_key, current_release):
    """Source section (b): -urur- default, -oror- after radical /o/."""
    tuka = make_verb("-tuka")
    senda = make_verb("-senda")
    ronda = make_verb("-ronda")
    for lemma, form, surface in [
        (tuka, "ndinotukurura", "urur"),
        (senda, "ndinosendurura", "urur"),
        (ronda, "ndinorondorora", "oror"),
    ]:
        response = generate(
            client, api_key, lemma, present_positive({"extensions": ["repetitive"]})
        )
        assert response.status_code == 200, form
        assert response.json()["data"]["generated"]["form"] == form, lemma.headword
        response = analyze(client, api_key, form)
        assert response.status_code == 200, form
        analysis = response.json()["data"]["analyses"][0]
        assert analysis["slots"]["extensions"] == [
            {
                "surface": surface,
                "type": "repetitive",
                "label": "repetitive extension (-urur- / -oror-)",
            }
        ]


@pytest.mark.django_db
def test_harmony_violations_do_not_analyze(client, api_key, current_release):
    make_verb("-tenga")
    make_verb("-buda")
    for bad in ("ndinotengisa", "ndinobudesa", "ndinotengika", "ndinobudeka"):
        assert analyze(client, api_key, bad).status_code == 422, bad
    # Reversive vowel-copy violations: e-radical with u-second-vowel, etc.
    make_verb("-pfeka")
    assert analyze(client, api_key, "ndinopfekunura").status_code == 422
    # -anur- on an e-radical is not the long reversive; the only remaining
    # decomposition would be the reciprocal + short-reversive stack, whose
    # short-reversive derivation is evidence-gated. The unverified reading is
    # excluded rather than presented as a supported analysis.
    response = analyze(client, api_key, "ndinopfekanura")
    assert response.status_code == 422
    lane_codes = [
        lane["code"] for lane in response.json()["error"]["detail"]["future_lanes"]
    ]
    assert "unverified_extension_derivation" in lane_codes


# --- Strict validation --------------------------------------------------------


@pytest.mark.django_db
def test_unsupported_extension_styles_and_combinations_rejected(
    client, api_key, current_release
):
    lemma = make_verb("-buda")
    bad_extension_lists = [
        [{"type": "passive", "style": "long"}],
        [{"type": "applicative", "style": "dz"}],
        [{"type": "neuter", "style": "short"}],
        [{"type": "reciprocal", "style": "long"}],
        [{"type": "repetitive", "style": "long"}],
        [{"type": "reversive", "style": "nonsense"}],
        [{"type": "reversive", "style": "long_urur"}],
        [{"type": "reversive", "style": "long_unur"}],
        [{"type": "reversive", "style": "urur"}],
        [{"type": "causative", "style": "nonsense"}],
        [{"type": "intensive"}],
        [{"type": "extensive"}],
        [{"type": "perfective"}],
        # Passive must be outermost: causative outside passive is unsupported.
        [{"type": "passive"}, {"type": "causative"}],
        # Same extension twice has no source-backed boundary.
        ["causative", "causative"],
        # Resource bound: at most three extensions per request.
        ["causative", "applicative", "reciprocal", "passive"],
        ["unknown-string"],
    ]
    for extensions in bad_extension_lists:
        response = generate(
            client, api_key, lemma, present_positive({"extensions": extensions})
        )
        assert response.status_code == 422, extensions
        assert response.json()["error"]["code"] == "GENERATION_UNSUPPORTED", extensions

    # Evidence-gated allomorphs refuse with the dedicated structured code.
    for extensions in [
        [{"type": "reversive"}, {"type": "reversive", "style": "short"}],
        [{"type": "causative", "style": "dz"}],
        [{"type": "causative", "style": "ts"}],
    ]:
        response = generate(
            client, api_key, lemma, present_positive({"extensions": extensions})
        )
        assert response.status_code == 422, extensions
        assert response.json()["error"]["code"] == "EXTENSION_UNVERIFIED", extensions

    response = generate(
        client, api_key, lemma, present_positive({"extensions": "causative"})
    )
    assert response.status_code == 422


@pytest.mark.django_db
def test_reversive_legacy_long_urur_style_points_to_repetitive(
    client, api_key, current_release
):
    lemma = make_verb("-kora")
    response = generate(
        client,
        api_key,
        lemma,
        present_positive({"extensions": [{"type": "reversive", "style": "long_urur"}]}),
    )
    assert response.status_code == 422
    detail = response.json()["error"]["detail"]
    assert detail["field"] == "extensions"
    assert "repetitive" in response.json()["error"]["message"]


@pytest.mark.django_db
def test_supported_stack_generates_and_round_trips(client, api_key, current_release):
    """Causative + applicative + passive respects the supported order boundary."""
    lemma = make_verb("-buda")
    response = generate(
        client,
        api_key,
        lemma,
        present_positive({"extensions": ["causative", "applicative", "passive"]}),
    )
    assert response.status_code == 200
    assert response.json()["data"]["generated"]["form"] == "ndinobudisirwa"
    response = analyze(client, api_key, "ndinobudisirwa")
    assert response.status_code == 200
    analysis = response.json()["data"]["analyses"][0]
    assert analysis["lemma"]["public_id"] == lemma.public_id
    assert [ext["type"] for ext in analysis["slots"]["extensions"]] == [
        "causative",
        "applicative",
        "passive",
    ]


# --- Construction interactions ------------------------------------------------


@pytest.mark.django_db
def test_extension_round_trip_negative_and_object_variants(
    client, api_key, current_release
):
    ambura = make_verb("-ambura")

    response = generate(
        client,
        api_key,
        ambura,
        {
            "generation_type": "verb_form",
            "subject": {"type": "person", "person": "first", "number": "singular"},
            "tense_aspect": "present",
            "polarity": "negative",
            "extensions": ["causative"],
        },
    )
    assert response.status_code == 200
    assert response.json()["data"]["generated"]["form"] == "handiamburise"
    response = analyze(client, api_key, "handiamburise")
    assert response.status_code == 200
    analysis = response.json()["data"]["analyses"][0]
    assert analysis["lemma"]["public_id"] == ambura.public_id
    assert analysis["slots"]["extensions"][0]["type"] == "causative"

    buda = make_verb("-buda")
    response = generate(
        client,
        api_key,
        buda,
        {
            **present_positive({"extensions": ["causative"]}),
            "object": {"type": "person", "person": "second", "number": "singular"},
        },
    )
    assert response.status_code == 200
    assert response.json()["data"]["generated"]["form"] == "ndinokubudisa"
    response = analyze(client, api_key, "ndinokubudisa")
    assert response.status_code == 200
    analysis = response.json()["data"]["analyses"][0]
    assert analysis["lemma"]["public_id"] == buda.public_id
    assert analysis["slots"]["object"]["surface"] == "ku"
    assert analysis["slots"]["extensions"][0]["type"] == "causative"


@pytest.mark.django_db
def test_infinitive_with_extensions_analyzes(client, api_key, current_release):
    buda = make_verb("-buda")
    for text, surfaces in [("kubudisa", ["is"]), ("kubudiswa", ["is", "w"])]:
        response = analyze(client, api_key, text)
        assert response.status_code == 200, text
        analysis = response.json()["data"]["analyses"][0]
        assert analysis["analysis_type"] == "infinitive", text
        assert analysis["lemma"]["public_id"] == buda.public_id, text
        assert [
            ext["surface"] for ext in analysis["slots"]["extensions"]
        ] == surfaces, text


# --- Lexical boundaries and ambiguity ------------------------------------------


@pytest.mark.django_db
def test_extension_looking_roots_prefer_exact_lexical_match(
    client, api_key, current_release
):
    """-tera ends in applicative-looking -er- but analyzes as a bare stem."""
    tera = make_verb("-tera")
    kora = make_verb("-kora")
    for text, lemma in [("ndinotera", tera), ("ndinokora", kora)]:
        response = analyze(client, api_key, text)
        assert response.status_code == 200, text
        analysis = response.json()["data"]["analyses"][0]
        assert analysis["lemma"]["public_id"] == lemma.public_id, text
        assert analysis["slots"]["extensions"] == [], text


@pytest.mark.django_db
def test_exact_derived_lemma_and_base_both_returned_in_order(
    client, api_key, current_release
):
    """A published derived stem (-budisa) yields the exact reading first."""
    buda = make_verb("-buda")
    budisa = make_verb("-budisa")
    response = analyze(client, api_key, "ndinobudisa")
    assert response.status_code == 200
    analyses = response.json()["data"]["analyses"]
    by_lemma = [analysis["lemma"]["public_id"] for analysis in analyses]
    assert by_lemma[0] == budisa.public_id
    assert buda.public_id in by_lemma[1:]
    assert analyses[0]["slots"]["extensions"] == []
    derived = next(a for a in analyses if a["lemma"]["public_id"] == buda.public_id)
    assert derived["slots"]["extensions"][0]["type"] == "causative"


@pytest.mark.django_db
def test_homograph_lemmas_yield_deterministic_analyses(
    client, api_key, current_release
):
    first = make_verb("-buda", pos="vi")
    second = make_verb("-buda", pos="vt")
    response = analyze(client, api_key, "ndinobuda")
    assert response.status_code == 200
    analyses = response.json()["data"]["analyses"]
    assert [a["lemma"]["public_id"] for a in analyses] == sorted(
        [first.public_id, second.public_id]
    )


# --- Search enrichment ----------------------------------------------------------


@pytest.mark.django_db
def test_search_enrichment_resolves_extended_verb_form(
    client, api_key, current_release
):
    lemma = make_verb("-buda")
    response = client.get(
        "/v1/search",
        {"q": "ndinobudisa"},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["morphology_enrichment"]["status"] == "matched"
    analyses = body["data"]["morphology"]["analyses"]
    assert analyses[0]["lemma"]["public_id"] == lemma.public_id
    assert analyses[0]["slots"]["extensions"][0]["type"] == "causative"


@pytest.mark.django_db
def test_unverified_allomorphs_refused_on_both_sides_of_the_api(
    client, api_key, current_release
):
    """Finding 4 plus the supervisor blocker: dz/ts and short-reversive
    allomorphs are refused at generation with a structured unsupported result,
    and the analyzer must not present the same unverified derivations as
    supported analyses. A reviewed base lemma is not evidence for an arbitrary
    derivation; only exact reviewed entries resolve such surfaces."""
    buda = make_verb("-buda")
    for style in ("dz", "ts"):
        response = generate(
            client,
            api_key,
            buda,
            present_positive({"extensions": [{"type": "causative", "style": style}]}),
        )
        assert response.status_code == 422, style
        error = response.json()["error"]
        assert error["code"] == "EXTENSION_UNVERIFIED", style
        assert error["detail"]["field"] == "extensions", style
        assert error["detail"]["reason"] == "lexical_distribution_unverified", style
        # No warning may substitute for the refusal.
        assert response.json().get("data") is None

    # Base-only fixtures cannot authorize the derivations on the analysis side
    # either: the gated readings are excluded and the structured unsupported
    # response explains why.
    make_verb("-kora")
    for text in ("kubudidza", "kubuditsa", "ndinokorora"):
        response = analyze(client, api_key, text)
        assert response.status_code == 422, text
        error = response.json()["error"]
        assert error["code"] == "ANALYSIS_UNSUPPORTED", text
        lane_codes = [
            lane["code"] for lane in error["detail"]["future_lanes"]
        ]
        assert "unverified_extension_derivation" in lane_codes, text

    # Rule-card attribution for the still-supported patterns.
    kora = Lemma.objects.get(headword="-kora")
    response = generate(
        client, api_key, kora, present_positive({"extensions": [{"type": "reversive"}]})
    )
    body = response.json()
    assert body["data"]["metadata"]["supported_rule_ids"] == [
        "fortune.verbal.slots.001",
        "fortune.verbal.reversive.001",
    ]

    response = generate(
        client, api_key, buda, present_positive({"extensions": ["reciprocal"]})
    )
    body = response.json()
    assert body["data"]["metadata"]["supported_rule_ids"] == [
        "fortune.verbal.slots.001",
        "fortune.verbal.reciprocal.001",
    ]

    response = generate(
        client, api_key, buda, present_positive({"extensions": ["causative"]})
    )
    body = response.json()
    assert body["data"]["metadata"]["supported_rule_ids"] == [
        "fortune.verbal.slots.001",
        "fortune.verbal.extensions.001",
    ]


@pytest.mark.django_db
def test_published_derived_lemma_resolves_as_own_entry_without_derivation_claim(
    client, api_key, current_release
):
    """If -buditsa is independently published, its inflections analyze as that
    lexical entry; the unverified -buda + causative-ts derivation is neither
    the reading nor added alongside it."""
    make_verb("-buda")
    make_verb("-buditsa")

    for text in ("kubuditsa", "ndinobuditsa"):
        response = analyze(client, api_key, text)
        assert response.status_code == 200, text
        analyses = response.json()["data"]["analyses"]
        assert analyses, text
        assert all(
            analysis["lemma"]["normalized_headword"] == "buditsa"
            for analysis in analyses
        ), text
        assert all(
            analysis["slots"]["extensions"] == [] for analysis in analyses
        ), text

    # The same holds for the short reversive: with -korora and -kora both
    # published, the exact -korora entry resolves and the gated -kora +
    # short-reversive derivation is not added alongside it.
    make_verb("-kora")
    make_verb("-korora")
    response = analyze(client, api_key, "ndinokorora")
    assert response.status_code == 200
    analyses = response.json()["data"]["analyses"]
    assert [a["lemma"]["normalized_headword"] for a in analyses] == ["korora"]
    assert analyses[0]["slots"]["extensions"] == []

    # Supported (ungated) competing readings are untouched: an exact derived
    # entry and the evidenced derivation of its base both remain available.
    make_verb("-budisa")
    response = analyze(client, api_key, "ndinobudisa")
    assert response.status_code == 200
    readings = [
        (a["lemma"]["normalized_headword"], [e["type"] for e in a["slots"]["extensions"]])
        for a in response.json()["data"]["analyses"]
    ]
    assert readings[0] == ("budisa", []), readings
    assert ("buda", ["causative"]) in readings, readings


@pytest.mark.django_db
def test_search_never_reports_matched_for_excluded_derivations(
    client, api_key, current_release
):
    """Search follows the analysis policy: a base-only fixture must not produce
    a "matched" enrichment for an excluded derivation, while ordinary exact
    lexical results stay available; publishing the derived lemma restores a
    truthful matched enrichment."""
    make_verb("-buda")

    # Base only: the gated derivation is excluded, so enrichment cannot claim
    # a match.
    response = client.get(
        "/v1/search",
        {"q": "ndinobuditsa"},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert "morphology" not in body
    assert "morphology_enrichment" not in body
    assert body["zero_result"]["morphology_enrichment"]["status"] == "unsupported"
    lanes = body["zero_result"]["morphology_enrichment"]["detail"]["future_lanes"]
    assert any(lane["code"] == "unverified_extension_derivation" for lane in lanes)

    # Ordinary analysis of supported forms is unaffected by the evidence gate.
    response = client.get(
        "/v1/search",
        {"q": "ndinobuda"},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["morphology_enrichment"]["status"] == "matched"

    # Publishing -buditsa makes the enrichment truthfully matched again: the
    # analyzer now resolves the surface as that exact reviewed entry, and the
    # exact headword itself stays an ordinary lexical result.
    make_verb("-buditsa")
    response = client.get(
        "/v1/search",
        {"q": "kubuditsa"},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["morphology_enrichment"]["status"] == "matched"
    analyses = body["morphology"]["analyses"]
    assert analyses
    assert all(
        analysis["lemma"]["normalized_headword"] == "buditsa"
        for analysis in analyses
    )

    response = client.get(
        "/v1/search",
        {"q": "buditsa"},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["count"] >= 1
    assert any(
        result["lemma"]["normalized_headword"] == "buditsa"
        for result in body["results"]
    )



@pytest.mark.django_db
def test_stem_candidates_bounded_and_deterministic(client, api_key, current_release):
    for _ in range(30):
        make_verb("-buda")
    first = analyze(client, api_key, "ndinobuda")
    second = analyze(client, api_key, "ndinobuda")
    assert first.status_code == 200
    # One matching subject here, so the per-stem bound (8) applies.
    assert first.json()["data"]["count"] == 8
    assert [a["lemma"]["public_id"] for a in first.json()["data"]["analyses"]] == [
        a["lemma"]["public_id"] for a in second.json()["data"]["analyses"]
    ]


@pytest.mark.django_db
def test_analyses_list_has_global_cap(client, api_key, current_release):
    from shona_api.editorial.models import ReviewState as RS
    from shona_api.lexicon.models import NounClass

    make_verb("-buda")
    for index in range(30):
        NounClass.objects.create(
            class_number=f"900{index}",
            display_order=900 + index,
            label=f"Cap class {index}",
            nominal_prefix="x",
            subject_concord="ndi",
            object_concord="",
            review_state=RS.APPROVED,
        )
    first = analyze(client, api_key, "ndinobuda")
    second = analyze(client, api_key, "ndinobuda")
    assert first.status_code == 200
    assert first.json()["data"]["count"] == 25
    assert [a["lemma"]["public_id"] for a in first.json()["data"]["analyses"]] == [
        a["lemma"]["public_id"] for a in second.json()["data"]["analyses"]
    ]


@pytest.mark.django_db
def test_corpus_passive_surface_analyzes_with_full_construction(
    client, api_key, current_release
):
    """The corpus documents bare `badanudzwa` as unsupported, but the fully
    inflected form must resolve to -badanudza + passive."""
    from shona_api.editorial.models import ReviewState as RS
    from shona_api.lexicon.models import NounClass

    lemma = make_verb("-badanudza")
    NounClass.objects.create(
        class_number="2",
        display_order=2,
        label="Class 2",
        nominal_prefix="va",
        subject_concord="va",
        object_concord="va",
        review_state=RS.APPROVED,
    )
    response = analyze(client, api_key, "vanobadanudzwa")
    assert response.status_code == 200
    analysis = response.json()["data"]["analyses"][0]
    assert analysis["lemma"]["public_id"] == lemma.public_id
    assert analysis["slots"]["extensions"] == [
        {"surface": "w", "type": "passive", "label": "passive extension (-w-)"}
    ]


# --- Correction-pass regressions (2026-09-09) --------------------------------


@pytest.mark.django_db
def test_malformed_extension_type_and_style_values_are_structured_422(
    client, api_key, current_release
):
    """Finding 1: unhashable JSON values previously escaped as TypeError 500s
    inside the legacy-style membership tests; every malformed value must now
    return the documented structured client error."""
    lemma = make_verb("-buda")
    for style in ([], {}, True, False, 3, 0.5, "0"):
        response = generate(
            client,
            api_key,
            lemma,
            present_positive({"extensions": [{"type": "reversive", "style": style}]}),
        )
        assert response.status_code == 422, style
        error = response.json()["error"]
        assert error["code"] == "GENERATION_UNSUPPORTED", style
        assert error["detail"]["field"] == "extensions", style

    for ext_type in ([], {}, True, 7, None):
        response = generate(
            client,
            api_key,
            lemma,
            present_positive({"extensions": [{"type": ext_type}]}),
        )
        assert response.status_code == 422, ext_type
        assert response.json()["error"]["code"] == "GENERATION_UNSUPPORTED", ext_type

    # Explicit null style matches the omitted-style contract.
    response = generate(
        client,
        api_key,
        lemma,
        present_positive({"extensions": [{"type": "causative", "style": None}]}),
    )
    assert response.status_code == 200
    assert response.json()["data"]["generated"]["form"] == "ndinobudisa"


@pytest.mark.django_db
def test_ambiguity_keeps_originating_lemma_across_object_readings(
    client, api_key, current_release
):
    """Finding 2: analyzing a generated form must retain the originating lemma
    alongside competing object-concord readings, for both polarities."""
    kura = make_verb("-kura")
    make_verb("-ra")

    for polarity, form in [
        ("positive", "ndinokurisa"),
        ("negative", "handikurise"),
    ]:
        features = {
            "generation_type": "verb_form",
            "subject": {"type": "person", "person": "first", "number": "singular"},
            "tense_aspect": "present",
            "polarity": polarity,
            "extensions": ["causative"],
        }
        response = generate(client, api_key, kura, features)
        assert response.status_code == 200, polarity
        assert response.json()["data"]["generated"]["form"] == form, polarity

        response = analyze(client, api_key, form)
        assert response.status_code == 200, polarity
        analyses = response.json()["data"]["analyses"]
        readings = [
            (
                analysis["lemma"]["normalized_headword"],
                analysis["slots"]["object"]["surface"] if analysis["slots"]["object"] else None,
                [ext["type"] for ext in analysis["slots"]["extensions"]],
            )
            for analysis in analyses
        ]
        # No-object reading of the originating lemma ranks first; the competing
        # object reading (ku + -ra + causative) is retained, not dropped.
        assert readings == [
            ("kura", None, ["causative"]),
            ("ra", "ku", ["causative"]),
        ], polarity



@pytest.mark.django_db
def test_competing_object_concords_stay_distinct(
    client, api_key, current_release
):
    """Finding 2: object concords sharing a surface ("mu" 3rd-singular person
    versus "mu" 2nd-plural person) produce distinct feature readings."""
    kura = make_verb("-kura")
    response = analyze(client, api_key, "ndinomukura")
    assert response.status_code == 200
    analyses = response.json()["data"]["analyses"]
    object_slots = [
        (analysis["slots"]["object"]["person"], analysis["slots"]["object"]["number"])
        for analysis in analyses
        if analysis["slots"]["object"]
    ]
    assert object_slots == [
        ("third", "singular"),
        ("second", "plural"),
    ]
    assert all(
        analysis["lemma"]["public_id"] == kura.public_id for analysis in analyses
    )


@pytest.mark.django_db
def test_coalesced_object_reading_survives_competition(
    client, api_key, current_release
):
    """Finding 2: the coalescence alternative is a viable reading of the same
    surface and must be considered alongside the plain segmentation."""
    from shona_api.lexicon.models import NounClass

    ambura = make_verb("-ambura")
    NounClass.objects.get_or_create(
        class_number="2",
        defaults=dict(
            display_order=2,
            label="Class 2",
            nominal_prefix="va",
            subject_concord="va",
            object_concord="va",
            review_state=ReviewState.APPROVED,
        ),
    )
    response = analyze(client, api_key, "ndinovambura")
    assert response.status_code == 200
    analyses = response.json()["data"]["analyses"]
    coalesced = [
        analysis
        for analysis in analyses
        if analysis["slots"]["object"]
        and analysis["slots"]["object"]["surface"] == "va"
        and analysis["slots"]["verb_stem"]["surface"] == "ambura"
    ]
    assert coalesced, analyses
    assert coalesced[0]["lemma"]["public_id"] == ambura.public_id


@pytest.mark.django_db
def test_sequence_policy_shared_between_generator_and_analyzer(
    client, api_key, current_release
):
    """Finding 3: one sequence convention governs both sides. Sequences the
    generator refuses are not accidentally analyzable, and vice versa."""
    buda = make_verb("-buda")

    response = generate(
        client, api_key, buda, present_positive({"extensions": ["passive", "causative"]})
    )
    assert response.status_code == 422
    response = analyze(client, api_key, "ndinobudwisa")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ANALYSIS_UNSUPPORTED"


    response = generate(
        client, api_key, buda, present_positive({"extensions": ["causative", "causative"]})
    )
    assert response.status_code == 422
    response = analyze(client, api_key, "ndinobudisisa")
    assert response.status_code == 422

    # The conforming stack keeps its round trip.
    response = generate(
        client,
        api_key,
        buda,
        present_positive({"extensions": ["causative", "applicative", "passive"]}),
    )
    assert response.status_code == 200
    assert response.json()["data"]["generated"]["form"] == "ndinobudisirwa"
    response = analyze(client, api_key, "ndinobudisirwa")
    assert response.status_code == 200
    analysis = response.json()["data"]["analyses"][0]
    assert [ext["type"] for ext in analysis["slots"]["extensions"]] == [
        "causative",
        "applicative",
        "passive",
    ]
