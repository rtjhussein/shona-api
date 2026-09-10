"""Bounded imperative analysis/generation (morphology-rules-v6).

Source locators for the construction expectations below (all verified against
the local PDFs; see docs/morphology/imperative-plan-2026-09-10.md and the
rule cards for the full locator list):

- FSI Unit 13, Note 2 (printed pp. 126-127; PDF p. 144): plural affirmative
  imperative = "the stem of the verb, plus /-i/ (in some dialects /-nyi/)"
  (Nyorai, Taurai, Garai pasi; Pindai); the singular lacks the suffix
  (Pinda); "the plural form may be used in speaking to one person, as a mark
  of respect".
- Hannan front matter, TABLE OF VERB FORMS, Imperative Mood (printed p. xvii;
  PDF p. 19): Idya / Idyai / Idyanyi M; "Usadya. Musadya KM" /
  "Usadye. Musadye Z".
- FSI Unit 32, note and exercises 3-4 (printed pp. 323-324; PDF pp.
  341-342): negative commands; final vowel /-a/ (usaputsa) or /-e/
  (usaputse) depending on dialect.
- FSI Unit 34, Notes 1, 2, 4 (printed pp. 338-342; PDF pp. 356-360):
  object-marked imperatives (Ipe, Ape, Adye, Ridye, Imwe, Riise, Uise,
  Muradzike, Varadzike, Aise; negative Usarisa, Usauisa, Usadzise) ending in
  terminal -e, adjacent vowels retained.
- Fortune Vol. 1, 2.10.2.2 (printed p. 20; PDF p. 32) and Tone Conjugation
  II (printed p. 23; PDF p. 35): the imperative inflection completes the
  radical with a terminal vowel (tem-a, bik-a; i-p-a, i-rw-a) and carries
  extended radicals (tauris-a, tever-a, kanganis-a); "penultimate i-" at
  i-d-a (printed p. 37; PDF p. 48).

Source-attested surfaces (verbatim in the sources): pinda (FSI "Pinda"),
taurai (FSI "Taurai"), idyai (Hannan "Idyai"), usadye/usadya and
musadye/musadya (Hannan "Usadye. Musadye Z"/"Usadya. Musadya KM"), the
object-marked shapes riise/aise/muradzike/usauisa/usadzise (FSI Unit 34),
taurisa (Fortune "tauris-a").

Constructed combinations (documented as such, built by the attested general
rules on fixture stems): object-marked forms on non-source stems, the
Manyika -nyi spelling on a non-monosyllabic stem, extension-bearing
imperatives beyond the Fortune radicals.

The fixture radicals reuse the established morphology fixtures (-buda,
-ambura, -ziva) plus -dya/-pinda/-radzika/-isa/-taura/-runga/-dai for the
attested imperative witnesses.
"""

import pytest
from django.core.cache import caches

from shona_api.api_auth.models import APIKey
from shona_api.editorial.models import ReviewState
from shona_api.lexicon.models import Lemma, NounClass
from shona_api.morphology.services import MORPHOLOGY_RULES_VERSION
from shona_api.releases.models import DataRelease


@pytest.fixture(autouse=True)
def imperative_api_settings(settings):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "imperative-tests",
        }
    }
    caches["default"].clear()


@pytest.fixture
def current_release():
    return DataRelease.objects.create(
        version="2026.09.0",
        label="Imperative release",
        rule_set_version=MORPHOLOGY_RULES_VERSION,
        is_current=True,
    )


@pytest.fixture
def api_key():
    _, raw_key = APIKey.objects.create_key(
        name="Imperative client",
        plan=APIKey.Plan.DEVELOPER,
        rate_limit_per_minute=60,
    )
    return raw_key


def make_verb(headword, review_state=ReviewState.PUBLISHED):
    return Lemma.objects.create(
        headword=headword,
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        part_of_speech_code="vt",
        part_of_speech_label="transitive verb",
        provenance={
            "source_key": "source_hannan",
            "entry_locator": "fixture:imperative",
        },
        review_state=review_state,
    )


def make_noun_class(class_number, display_order, object_concord):
    return NounClass.objects.create(
        class_number=class_number,
        display_order=display_order,
        label=f"Class {class_number}",
        nominal_prefix=object_concord,
        subject_concord=object_concord,
        object_concord=object_concord,
        review_state=ReviewState.PUBLISHED,
    )


def make_class(class_number, display_order, object_concord):
    return make_noun_class(class_number, display_order, object_concord)


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


def imperative_features(**overrides):
    features = {"generation_type": "imperative"}
    features.update(overrides)
    return features


def find_imperative_analysis(data, **match):
    analyses = [
        analysis
        for analysis in data["analyses"]
        if analysis["analysis_type"] == "imperative"
        and all(
            analysis["slots"][slot] == value
            if not isinstance(value, dict)
            else all(
                analysis["slots"][slot].get(key) == item
                for key, item in value.items()
            )
            for slot, value in match.items()
        )
    ]
    return analyses


# --- Source-attested generation ------------------------------------------------


@pytest.mark.django_db
def test_generate_positive_singular_imperative_is_the_bare_stem(
    client, api_key, current_release
):
    lemma = make_verb("-pinda")
    response = generate(client, api_key, lemma, imperative_features())

    assert response.status_code == 200, response.content
    generated = response.json()["data"]["generated"]
    assert generated["generation_type"] == "imperative"
    assert generated["form"] == "pinda"
    assert generated["rule_id"] == "fortune.verbal.imperative.001"
    assert generated["slots"]["mood"] == {
        "surface": "",
        "value": "imperative",
        "label": "imperative mood",
    }
    assert generated["slots"]["subject"] is None
    assert generated["slots"]["addressee"] == {
        "surface": "",
        "person": "second",
        "number": "singular",
        "label": "imperative addressee",
    }
    assert generated["slots"]["verb_stem"] == {
        "surface": "pinda",
        "lemma_public_id": lemma.public_id,
    }
    assert generated["slots"]["final_vowel"] == {"surface": "a", "value": "a"}


@pytest.mark.django_db
def test_generate_plural_imperative_adds_the_attested_i_suffix(
    client, api_key, current_release
):
    # FSI Unit 13 Note 2: "the stem of the verb, plus /-i/" (Taurai).
    lemma = make_verb("-taura")
    response = generate(
        client, api_key, lemma, imperative_features(number="plural")
    )

    assert response.status_code == 200, response.content
    generated = response.json()["data"]["generated"]
    assert generated["form"] == "taurai"
    assert generated["slots"]["mood"]["surface"] == "i"
    assert generated["slots"]["addressee"]["number"] == "plural"
    assert generated["slots"]["verb_stem"]["surface"] == "taura"


@pytest.mark.django_db
def test_generate_monosyllabic_stems_take_the_attested_prothetic_i(
    client, api_key, current_release
):
    # Hannan i- entry and front matter: Idya (sg), Idyai (pl); Fortune
    # 2.10.2.2 i-p-a / i-rw-a.
    dya = make_verb("-dya")
    singular = generate(client, api_key, dya, imperative_features())
    plural = generate(
        client, api_key, dya, imperative_features(number="plural")
    )

    assert singular.status_code == 200, singular.content
    assert singular.json()["data"]["generated"]["form"] == "idya"
    assert plural.status_code == 200, plural.content
    assert plural.json()["data"]["generated"]["form"] == "idyai"


@pytest.mark.django_db
def test_generate_positive_singular_object_imperative_ends_in_e(
    client, api_key, current_release
):
    # FSI Unit 34: Muradzike (mu + radzik + e), Riise (ri + ise), Aise
    # (a + ise), Ipe (i + pe).
    radzika = make_verb("-radzika")
    response = generate(
        client,
        api_key,
        radzika,
        imperative_features(
            object={"type": "person", "person": "third", "number": "singular"}
        ),
    )
    assert response.status_code == 200, response.content
    generated = response.json()["data"]["generated"]
    assert generated["form"] == "muradzike"
    assert generated["slots"]["object"]["surface"] == "mu"
    assert generated["slots"]["verb_stem"]["surface"] == "radzike"
    isa = make_verb("-isa")
    make_class("5", 5, "ri")
    make_class("6", 6, "a")
    make_class("9", 9, "i")
    class_5_response = generate(
        client,
        api_key,
        isa,
        imperative_features(object={"type": "noun_class", "class_number": "5"}),
    )
    class_6_response = generate(
        client,
        api_key,
        isa,
        imperative_features(object={"type": "noun_class", "class_number": "6"}),
    )
    class_9_response = generate(
        client,
        api_key,
        make_verb("-pa"),
        imperative_features(object={"type": "noun_class", "class_number": "9"}),
    )
    assert class_5_response.status_code == 200, class_5_response.content
    assert class_5_response.json()["data"]["generated"]["form"] == "riise"
    assert class_6_response.status_code == 200, class_6_response.content
    assert class_6_response.json()["data"]["generated"]["form"] == "aise"
    assert class_9_response.status_code == 200, class_9_response.content
    assert class_9_response.json()["data"]["generated"]["form"] == "ipe"


@pytest.mark.django_db
def test_generate_negative_imperative_uses_usa_and_the_zezuru_terminal(
    client, api_key, current_release
):
    # Hannan front matter: "Usadye. Musadye Z"; FSI Unit 32 exercises.
    dya = make_verb("-dya")
    pinda = make_verb("-pinda")
    singular = generate(
        client, api_key, dya, imperative_features(polarity="negative")
    )
    pinda_negative = generate(
        client, api_key, pinda, imperative_features(polarity="negative")
    )

    assert singular.status_code == 200, singular.content
    generated = singular.json()["data"]["generated"]
    assert generated["form"] == "usadye"
    assert generated["rule_id"] == "fortune.verbal.imperative.negative.001"
    assert generated["slots"]["polarity"]["surface"] == "sa"
    assert generated["slots"]["addressee"]["surface"] == "usa"
    # Monosyllabic negative imperatives keep the bare stem (Hannan "Usadya").
    assert pinda_negative.status_code == 200, pinda_negative.content
    assert pinda_negative.json()["data"]["generated"]["form"] == "usapinde"


@pytest.mark.django_db
def test_generate_plural_negative_imperative_uses_musa(
    client, api_key, current_release
):
    # Hannan front matter: "Musadye Z"; FSI Unit 32 exercise 4.
    dya = make_verb("-dya")
    response = generate(
        client,
        api_key,
        dya,
        imperative_features(number="plural", polarity="negative"),
    )

    assert response.status_code == 200, response.content
    generated = response.json()["data"]["generated"]
    assert generated["form"] == "musadye"
    assert generated["slots"]["addressee"]["surface"] == "musa"
    assert generated["slots"]["addressee"]["number"] == "plural"


@pytest.mark.django_db
def test_generate_negative_object_imperative_retains_attested_vowel_contacts(
    client, api_key, current_release
):
    # FSI Unit 34 Note 2 prints the -a dialect spellings Usariisa / Usauisa
    # / Usadziisa (murivi is class 3); generation emits the Zezuru -e
    # terminal of the same construction.
    isa = make_verb("-isa")
    make_class("5", 5, "ri")
    make_class("3", 3, "u")
    make_class("10", 10, "dzi")
    responses = {
        class_number: generate(
            client,
            api_key,
            isa,
            imperative_features(
                polarity="negative",
                object={"type": "noun_class", "class_number": class_number},
            ),
        )
        for class_number in ("5", "3", "10")
    }
    assert responses["5"].status_code == 200, responses["5"].content
    assert responses["5"].json()["data"]["generated"]["form"] == "usariise"
    assert responses["3"].status_code == 200, responses["3"].content
    assert responses["3"].json()["data"]["generated"]["form"] == "usauise"
    assert responses["10"].status_code == 200, responses["10"].content
    assert responses["10"].json()["data"]["generated"]["form"] == "usadziise"


@pytest.mark.django_db
def test_generate_imperative_supports_attested_extended_radicals(
    client, api_key, current_release
):
    # Fortune TC II carries extended radicals in the imperative inflection
    # (tauris-a); FSI Unit 32 attests applied/causative negative commands
    # (Usafusire, Usadonhese, Musakurungira).
    taura = make_verb("-taura")
    causative = generate(
        client,
        api_key,
        taura,
        imperative_features(extensions=["causative"]),
    )
    assert causative.status_code == 200, causative.content
    assert causative.json()["data"]["generated"]["form"] == "taurisa"

    kurungira = make_verb("-kurungira")
    attested_negative = generate(
        client,
        api_key,
        kurungira,
        imperative_features(number="plural", polarity="negative"),
    )
    assert attested_negative.status_code == 200, attested_negative.content
    generated = attested_negative.json()["data"]["generated"]
    assert generated["form"] == "musakurungire"

    fusa = make_verb("-fusa")
    applied_negative = generate(
        client,
        api_key,
        fusa,
        imperative_features(
            polarity="negative",
            extensions=["applicative"],
        ),
    )
    assert applied_negative.status_code == 200, applied_negative.content
    generated = applied_negative.json()["data"]["generated"]
    assert generated["form"] == "usafusire"
    assert generated["slots"]["extensions"][0]["type"] == "applicative"


# --- Structured refusals -------------------------------------------------------


@pytest.mark.django_db
def test_generate_imperative_rejects_finite_only_feature_fields(
    client, api_key, current_release
):
    lemma = make_verb("-buda")
    for field, features in (
        ("subject", imperative_features(subject={"type": "person", "person": "first", "number": "singular"})),
        ("tense_aspect", imperative_features(tense_aspect="present")),
        ("mood", imperative_features(mood="imperative")),
    ):
        response = generate(client, api_key, lemma, features)
        assert response.status_code == 422, (field, response.content)
        error = response.json()["error"]
        assert error["code"] == "GENERATION_UNSUPPORTED"
        assert error["detail"]["field"] == field


@pytest.mark.django_db
def test_generate_imperative_defers_reflexive_and_plural_object(
    client, api_key, current_release
):
    lemma = make_verb("-dya")
    reflexive = generate(
        client, api_key, lemma, imperative_features(reflexive=True)
    )
    assert reflexive.status_code == 422, reflexive.content
    error = reflexive.json()["error"]
    assert error["code"] == "GENERATION_UNSUPPORTED"
    assert error["detail"]["reason"] == "deferred_pending_evidence"
    assert error["detail"]["boundary"] == "reflexive_imperative"

    explicit_false = generate(
        client, api_key, lemma, imperative_features(reflexive=False)
    )
    assert explicit_false.status_code == 200, explicit_false.content

    make_class("2", 2, "va")
    plural_object = generate(
        client,
        api_key,
        lemma,
        imperative_features(
            number="plural",
            object={"type": "noun_class", "class_number": "2"},
        ),
    )
    assert plural_object.status_code == 422, plural_object.content
    error = plural_object.json()["error"]
    assert error["detail"]["reason"] == "deferred_pending_evidence"
    assert error["detail"]["boundary"] == "plural_with_object_concord"


@pytest.mark.django_db
def test_generate_imperative_rejects_invalid_values_explicitly(
    client, api_key, current_release
):
    lemma = make_verb("-buda")
    number = generate(client, api_key, lemma, imperative_features(number="dual"))
    assert number.status_code == 422, number.content
    assert number.json()["error"]["detail"]["field"] == "number"

    polarity = generate(
        client, api_key, lemma, imperative_features(polarity="interrogative")
    )
    assert polarity.status_code == 422, polarity.content
    assert polarity.json()["error"]["detail"]["field"] == "polarity"


@pytest.mark.django_db
def test_generate_imperative_refuses_divergent_and_pro_verb_stems(
    client, api_key, current_release
):
    divergent = make_verb("-ti")
    response = generate(client, api_key, divergent, imperative_features())
    assert response.status_code == 422, response.content
    error = response.json()["error"]
    assert error["detail"]["field"] == "lemma_stem"
    assert error["detail"]["reason"] == "divergent_stem_without_terminal_a"

    pro_verb = make_verb("-na")
    response = generate(client, api_key, pro_verb, imperative_features())
    assert response.status_code == 422, response.content
    assert response.json()["error"]["detail"]["reason"] == "defective_pro_verb_stem"

    pro_verb_negative = generate(
        client, api_key, pro_verb, imperative_features(polarity="negative")
    )
    assert pro_verb_negative.status_code == 422, pro_verb_negative.content
    assert (
        pro_verb_negative.json()["error"]["detail"]["reason"]
        == "defective_pro_verb_stem"
    )


@pytest.mark.django_db
def test_generate_imperative_defers_unwitnessed_a_vowel_boundaries(
    client, api_key, current_release
):
    ambura = make_verb("-ambura")
    make_class("6", 6, "a")

    object_boundary = generate(
        client,
        api_key,
        ambura,
        imperative_features(object={"type": "noun_class", "class_number": "6"}),
    )
    assert object_boundary.status_code == 422, object_boundary.content
    error = object_boundary.json()["error"]
    assert error["detail"]["field"] == "imperative_boundary"
    assert error["detail"]["boundary"] == "object_before_a_initial_stem"
    assert error["detail"]["reason"] == "deferred_pending_evidence"

    sa_stem = generate(
        client, api_key, ambura, imperative_features(polarity="negative")
    )
    assert sa_stem.status_code == 422, sa_stem.content
    assert (
        sa_stem.json()["error"]["detail"]["boundary"] == "sa_before_a_initial_stem"
    )

    sa_object = generate(
        client,
        api_key,
        ambura,
        imperative_features(
            polarity="negative",
            object={"type": "noun_class", "class_number": "6"},
        ),
    )
    assert sa_object.status_code == 422, sa_object.content
    assert (
        sa_object.json()["error"]["detail"]["boundary"]
        == "sa_before_a_initial_object"
    )

    # Extended stems evaluate the boundary on the stem as built.
    extended_boundary = generate(
        client,
        api_key,
        ambura,
        imperative_features(
            polarity="negative", extensions=["causative"]
        ),
    )
    assert extended_boundary.status_code == 422, extended_boundary.content
    assert (
        extended_boundary.json()["error"]["detail"]["boundary"]
        == "sa_before_a_initial_stem"
    )


@pytest.mark.django_db
def test_generate_imperative_shares_the_extension_evidence_gates(
    client, api_key, current_release
):
    lemma = make_verb("-buda")
    gated = generate(
        client,
        api_key,
        lemma,
        imperative_features(extensions=[{"type": "causative", "style": "dz"}]),
    )
    assert gated.status_code == 422, gated.content
    assert gated.json()["error"]["code"] == "EXTENSION_UNVERIFIED"

    malformed = generate(
        client,
        api_key,
        lemma,
        imperative_features(extensions=[{"type": "causative", "style": 3}]),
    )
    assert malformed.status_code == 422, malformed.content
    assert malformed.json()["error"]["code"] == "GENERATION_UNSUPPORTED"


# --- Analysis ------------------------------------------------------------------


@pytest.mark.django_db
def test_analyze_positive_imperatives(client, api_key, current_release):
    pinda = make_verb("-pinda")
    taura = make_verb("-taura")
    dya = make_verb("-dya")

    singular = analyze(client, api_key, "pinda")
    assert singular.status_code == 200, singular.content
    analyses = find_imperative_analysis(
        singular.json()["data"], polarity={"value": "positive"}
    )
    assert len(analyses) == 1
    assert analyses[0]["lemma"]["public_id"] == pinda.public_id
    assert analyses[0]["slots"]["addressee"]["number"] == "singular"
    assert analyses[0]["slots"]["subject"] is None

    plural = analyze(client, api_key, "taurai")
    assert plural.status_code == 200, plural.content
    analyses = find_imperative_analysis(
        plural.json()["data"], mood={"surface": "i"}
    )
    assert len(analyses) == 1
    assert analyses[0]["lemma"]["public_id"] == taura.public_id
    assert analyses[0]["slots"]["addressee"]["number"] == "plural"

    prothetic = analyze(client, api_key, "idya")
    assert prothetic.status_code == 200, prothetic.content
    analyses = find_imperative_analysis(prothetic.json()["data"])
    assert len(analyses) == 1
    assert analyses[0]["lemma"]["public_id"] == dya.public_id

    prothetic_plural = analyze(client, api_key, "idyai")
    assert prothetic_plural.status_code == 200, prothetic_plural.content
    analyses = find_imperative_analysis(
        prothetic_plural.json()["data"], mood={"surface": "i"}
    )
    assert len(analyses) == 1
    assert analyses[0]["lemma"]["public_id"] == dya.public_id


@pytest.mark.django_db
def test_analyze_bare_monosyllabic_spelling_is_not_an_imperative(
    client, api_key, current_release
):
    # The imperative of -dya is idya (Hannan i- entry), not dya: the bare
    # vowelless-radical spelling gets no imperative reading.
    make_verb("-dya")
    response = analyze(client, api_key, "dya")
    assert response.status_code == 422, response.content
    body = response.json()["error"]
    assert body["code"] == "ANALYSIS_UNSUPPORTED"
    lanes = body["detail"].get("future_lanes", [])
    assert not [
        lane
        for lane in lanes
        if lane["code"] == "deferred_imperative_boundary"
    ]


@pytest.mark.django_db
def test_analyze_manyika_plural_variant(client, api_key, current_release):
    # Hannan -nyi entry (PDF p. 513): "-nyi ... sfx form > pl imperative";
    # front matter "Idyanyi M". Analyzed, never generated.
    taura = make_verb("-taura")
    response = analyze(client, api_key, "tauranyi")
    assert response.status_code == 200, response.content
    analyses = find_imperative_analysis(
        response.json()["data"], mood={"surface": "nyi"}
    )
    assert len(analyses) == 1
    assert analyses[0]["lemma"]["public_id"] == taura.public_id
    assert analyses[0]["slots"]["addressee"]["number"] == "plural"

    generated = generate(
        client, api_key, taura, imperative_features(number="plural")
    )
    assert generated.json()["data"]["generated"]["form"] == "taurai"


@pytest.mark.django_db
def test_analyze_object_marked_positive_imperatives(
    client, api_key, current_release
):
    radzika = make_verb("-radzika")
    isa = make_verb("-isa")
    pa = make_verb("-pa")
    make_class("5", 5, "ri")
    make_class("6", 6, "a")
    make_class("9", 9, "i")

    person_object = analyze(client, api_key, "muradzike")
    assert person_object.status_code == 200, person_object.content
    analyses = find_imperative_analysis(
        person_object.json()["data"], object={"surface": "mu"}
    )
    # The shared mu surface keeps both person readings distinct (3rd
    # singular and 2nd plural object concords), like the finite lanes.
    assert len(analyses) == 2
    assert {analysis["slots"]["object"]["person"] for analysis in analyses} == {
        "third",
        "second",
    }
    assert all(
        analysis["lemma"]["public_id"] == radzika.public_id
        for analysis in analyses
    )
    assert analyses[0]["slots"]["verb_stem"]["surface"] == "radzike"

    class_5 = analyze(client, api_key, "riise")
    assert class_5.status_code == 200, class_5.content
    analyses = find_imperative_analysis(
        class_5.json()["data"], object={"surface": "ri"}
    )
    assert len(analyses) == 1
    assert analyses[0]["lemma"]["public_id"] == isa.public_id
    assert analyses[0]["slots"]["verb_stem"]["surface"] == "ise"

    class_6 = analyze(client, api_key, "aise")
    assert class_6.status_code == 200, class_6.content
    analyses = find_imperative_analysis(
        class_6.json()["data"], object={"surface": "a"}
    )
    assert len(analyses) == 1
    assert analyses[0]["lemma"]["public_id"] == isa.public_id

    class_9 = analyze(client, api_key, "ipe")
    assert class_9.status_code == 200, class_9.content
    analyses = find_imperative_analysis(
        class_9.json()["data"], object={"surface": "i"}
    )
    assert len(analyses) == 1
    assert analyses[0]["lemma"]["public_id"] == pa.public_id


@pytest.mark.django_db
def test_analyze_negative_imperatives_and_dialect_variants(
    client, api_key, current_release
):
    dya = make_verb("-dya")

    zezuru = analyze(client, api_key, "usadye")
    assert zezuru.status_code == 200, zezuru.content
    analyses = find_imperative_analysis(
        zezuru.json()["data"], polarity={"value": "negative"}
    )
    assert len(analyses) == 1
    assert analyses[0]["lemma"]["public_id"] == dya.public_id
    assert analyses[0]["slots"]["addressee"]["surface"] == "usa"
    assert analyses[0]["slots"]["verb_stem"]["surface"] == "dye"

    karanga = analyze(client, api_key, "usadya")
    assert karanga.status_code == 200, karanga.content
    analyses = find_imperative_analysis(
        karanga.json()["data"], polarity={"value": "negative"}
    )
    assert len(analyses) == 1
    assert analyses[0]["lemma"]["public_id"] == dya.public_id

    plural = analyze(client, api_key, "musadye")
    assert plural.status_code == 200, plural.content
    analyses = find_imperative_analysis(
        plural.json()["data"], polarity={"value": "negative"}
    )
    assert len(analyses) == 1
    assert analyses[0]["slots"]["addressee"]["surface"] == "musa"
    assert analyses[0]["slots"]["addressee"]["number"] == "plural"


@pytest.mark.django_db
def test_analyze_negative_object_imperatives(
    client, api_key, current_release
):
    isa = make_verb("-isa")
    make_class("5", 5, "ri")
    make_class("3", 3, "u")
    make_class("10", 10, "dzi")

    # FSI Unit 34 Note 2 prints the -a dialect spellings (Usariisa,
    # Usauisa, Usadziisa); the -e spellings are the same construction in
    # the generated Zezuru terminal. Both analyze.
    attested_a = analyze(client, api_key, "usariisa")
    assert attested_a.status_code == 200, attested_a.content
    analyses = find_imperative_analysis(
        attested_a.json()["data"], object={"surface": "ri"}
    )
    assert len(analyses) == 1
    assert analyses[0]["lemma"]["public_id"] == isa.public_id
    assert analyses[0]["slots"]["verb_stem"]["surface"] == "isa"

    zezuru_e = analyze(client, api_key, "usariise")
    assert zezuru_e.status_code == 200, zezuru_e.content
    analyses = find_imperative_analysis(
        zezuru_e.json()["data"], object={"surface": "ri"}
    )
    assert len(analyses) == 1
    assert analyses[0]["lemma"]["public_id"] == isa.public_id
    assert analyses[0]["slots"]["verb_stem"]["surface"] == "ise"

    # FSI Unit 34: "Usauisa muhari" (murivi, class 3) retains the sa|u and
    # u|i contacts.
    class_3 = analyze(client, api_key, "usauisa")
    assert class_3.status_code == 200, class_3.content
    analyses = find_imperative_analysis(
        class_3.json()["data"], object={"surface": "u"}
    )
    assert len(analyses) == 1
    assert analyses[0]["lemma"]["public_id"] == isa.public_id

    class_10 = analyze(client, api_key, "usadziisa")
    assert class_10.status_code == 200, class_10.content
    analyses = find_imperative_analysis(
        class_10.json()["data"], object={"surface": "dzi"}
    )
    assert len(analyses) == 1
    assert analyses[0]["lemma"]["public_id"] == isa.public_id

@pytest.mark.django_db
def test_analyze_extension_bearing_imperatives(client, api_key, current_release):
    taura = make_verb("-taura")
    kurungira = make_verb("-kurungira")

    causative = analyze(client, api_key, "taurisa")
    assert causative.status_code == 200, causative.content
    analyses = find_imperative_analysis(causative.json()["data"])
    assert len(analyses) == 1
    assert analyses[0]["lemma"]["public_id"] == taura.public_id
    assert analyses[0]["slots"]["extensions"][0]["type"] == "causative"

    applied = analyze(client, api_key, "musakurungire")
    assert applied.status_code == 200, applied.content
    analyses = find_imperative_analysis(applied.json()["data"])
    assert len(analyses) == 1
    assert analyses[0]["lemma"]["public_id"] == kurungira.public_id
    assert analyses[0]["slots"]["extensions"] == []
    assert analyses[0]["slots"]["addressee"]["surface"] == "musa"


# --- Ambiguity -----------------------------------------------------------------


@pytest.mark.django_db
def test_imperative_reading_coexists_with_infinitive_reading(
    client, api_key, current_release
):
    # "kudai" is both the ku- infinitive of -dai and (attested general rule)
    # the plural imperative of -kuda. Both readings stay available.
    dai = make_verb("-dai")
    kuda = make_verb("-kuda")
    response = analyze(client, api_key, "kudai")
    assert response.status_code == 200, response.content
    body = response.json()["data"]
    types = {analysis["analysis_type"] for analysis in body["analyses"]}
    assert types == {"infinitive", "imperative"}
    lemma_ids = {analysis["lemma"]["public_id"] for analysis in body["analyses"]}
    assert lemma_ids == {dai.public_id, kuda.public_id}


@pytest.mark.django_db
def test_imperative_reading_coexists_with_finite_reading(
    client, api_key, current_release
):
    # "vabuda" is not a supported imperative: positive object imperatives
    # end in -e, so the -a surface gets no imperative reading and stays
    # unsupported.
    make_verb("-buda")
    make_class("2", 2, "va")
    response = analyze(client, api_key, "vabuda")
    assert response.status_code == 422, response.content


@pytest.mark.django_db
def test_object_e_imperative_reading_and_finite_present_distinct(
    client, api_key, current_release
):
    # "vabude" is the object-marked positive imperative of -buda (the
    # class-2 concord before the -e object-imperative terminal).
    buda = make_verb("-buda")
    make_class("2", 2, "va")
    response = analyze(client, api_key, "vabude")
    assert response.status_code == 200, response.content
    analyses = find_imperative_analysis(
        response.json()["data"], object={"surface": "va"}
    )
    # The shared va surface keeps the person-3pl and class-2 object readings
    # distinct, like the finite lanes.
    assert len(analyses) == 2
    assert all(
        analysis["lemma"]["public_id"] == buda.public_id
        for analysis in analyses
    )
    types = {
        analysis["analysis_type"]
        for analysis in response.json()["data"]["analyses"]
    }
    assert types == {"imperative"}


# --- Deferred boundaries in analysis -------------------------------------------


@pytest.mark.django_db
def test_analyze_deferred_imperative_boundaries(client, api_key, current_release):
    make_verb("-ambura")
    make_class("6", 6, "a")

    object_boundary = analyze(client, api_key, "aambure")
    assert object_boundary.status_code == 422, object_boundary.content
    lanes = object_boundary.json()["error"]["detail"]["future_lanes"]
    assert [lane for lane in lanes if lane["code"] == "deferred_imperative_boundary"]
    lane = next(
        lane for lane in lanes if lane["code"] == "deferred_imperative_boundary"
    )
    assert lane["boundary"] == "object_before_a_initial_stem"
    assert lane["support_status"] == "deferred_pending_evidence"

    sa_stem = analyze(client, api_key, "usaambure")
    assert sa_stem.status_code == 422, sa_stem.content
    lanes = sa_stem.json()["error"]["detail"]["future_lanes"]
    lane = next(
        lane for lane in lanes if lane["code"] == "deferred_imperative_boundary"
    )
    assert lane["boundary"] == "sa_before_a_initial_stem"

    # The same surfaces with no reviewed lexical material stay plain
    # unsupported without claiming a deferred construction.
    unrelated = analyze(client, api_key, "aayeerera")
    assert unrelated.status_code == 422, unrelated.content
    lanes = unrelated.json()["error"].get("detail", {}).get("future_lanes", [])
    assert not [
        lane for lane in lanes if lane["code"] == "deferred_imperative_boundary"
    ]


# --- Round-trips ---------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "headword,features,form",
    [
        ("-buda", {}, "buda"),
        ("-buda", {"number": "plural"}, "budai"),
        ("-taura", {"number": "plural"}, "taurai"),
        ("-dya", {}, "idya"),
        ("-dya", {"number": "plural"}, "idyai"),
        (
            "-radzika",
            {"object": {"type": "person", "person": "third", "number": "singular"}},
            "muradzike",
        ),
        ("-isa", {"object": {"type": "noun_class", "class_number": "5"}}, "riise"),
        ("-isa", {"object": {"type": "noun_class", "class_number": "6"}}, "aise"),
        ("-pinda", {"polarity": "negative"}, "usapinde"),
        ("-dya", {"polarity": "negative"}, "usadye"),
        (
            "-dya",
            {"number": "plural", "polarity": "negative"},
            "musadye",
        ),
        (
            "-isa",
            {
                "polarity": "negative",
                "object": {"type": "noun_class", "class_number": "3"},
            },
            "usauise",
        ),
        (
            "-kurungira",
            {"number": "plural", "polarity": "negative"},
            "musakurungire",
        ),
    ],
)
def test_imperative_generation_round_trips_through_analysis(
    client, api_key, current_release, headword, features, form
):
    lemma = make_verb(headword)
    make_class("5", 5, "ri")
    make_class("6", 6, "a")
    make_class("3", 3, "u")
    generation = generate(client, api_key, lemma, imperative_features(**features))
    assert generation.status_code == 200, generation.content
    assert generation.json()["data"]["generated"]["form"] == form

    analysis = analyze(client, api_key, form)
    assert analysis.status_code == 200, analysis.content
    body = analysis.json()["data"]
    readings = find_imperative_analysis(
        body,
        polarity={"value": features.get("polarity", "positive")},
    )
    assert readings, body
    assert any(
        reading["lemma"]["public_id"] == lemma.public_id for reading in readings
    )


# --- Search enrichment ---------------------------------------------------------


@pytest.mark.django_db
def test_search_reports_imperative_morphology_enrichment(
    client, api_key, current_release
):
    make_verb("-dya")
    response = client.get(
        "/v1/search",
        {"q": "usadye"},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200, response.content
    body = response.json()["data"]
    assert body["morphology_enrichment"]["status"] == "matched"
    analyses = body["morphology"]["analyses"]
    assert analyses
    assert analyses[0]["analysis_type"] == "imperative"
    assert analyses[0]["slots"]["polarity"]["value"] == "negative"
    assert analyses[0]["slots"]["addressee"]["surface"] == "usa"


@pytest.mark.django_db
def test_search_keeps_lexical_results_alongside_imperative_enrichment(
    client, api_key, current_release
):
    # The exact lexical reading of a bare stem spelling is unaffected: the
    # imperative reading is additive, never a replacement.
    lemma = make_verb("-buda")
    response = client.get(
        "/v1/search",
        {"q": "buda"},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200, response.content
    body = response.json()["data"]
    assert body["morphology_enrichment"]["status"] == "matched"
    exact = [
        result
        for result in body["results"]
        if result["result_type"] == "lemma"
        and result["lemma"]["public_id"] == lemma.public_id
    ]
    assert exact
    analyses = find_imperative_analysis(body["morphology"])
    assert analyses
    assert analyses[0]["lemma"]["public_id"] == lemma.public_id


@pytest.mark.django_db
def test_search_never_reports_deferred_imperative_as_matched(
    client, api_key, current_release
):
    make_verb("-ambura")
    make_class("6", 6, "a")
    response = client.get(
        "/v1/search",
        {"q": "aambure"},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200, response.content
    body = response.json()["data"]
    # The deferred construction is never reported as matched morphology,
    # whatever fuzzy lexical matches the search tiers return.
    assert "morphology" not in body
    if body["count"] == 0:
        enrichment = body["zero_result"]["morphology_enrichment"]
        assert enrichment["status"] == "unsupported"
        lanes = enrichment["detail"]["future_lanes"]
        assert [
            lane
            for lane in lanes
            if lane["code"] == "deferred_imperative_boundary"
        ]
    else:
        assert "morphology_enrichment" not in body


# --- Shared generation/analysis scope (supervisor correction pass) -------------


@pytest.mark.django_db
def test_plural_with_object_deferral_agrees_across_generation_and_analysis(
    client, api_key, current_release
):
    # No available source attests a plural imperative with an object concord
    # (FSI Unit 34's object-marked commands are all singular-addressee), so
    # generation refuses the combination and analysis infers no such
    # reading, for either negative terminal variant and through
    # extension-derived candidates.
    dya = make_verb("-dya")
    make_class("5", 5, "ri")
    object_features = {"object": {"type": "noun_class", "class_number": "5"}}

    generation = generate(
        client,
        api_key,
        dya,
        imperative_features(number="plural", polarity="negative", **object_features),
    )
    assert generation.status_code == 422, generation.content
    error = generation.json()["error"]
    assert error["detail"]["boundary"] == "plural_with_object_concord"
    assert error["detail"]["reason"] == "deferred_pending_evidence"

    extended_generation = generate(
        client,
        api_key,
        dya,
        imperative_features(
            number="plural",
            polarity="negative",
            extensions=["causative"],
            **object_features,
        ),
    )
    assert extended_generation.status_code == 422, extended_generation.content
    assert (
        extended_generation.json()["error"]["detail"]["boundary"]
        == "plural_with_object_concord"
    )

    for text in ("musaridye", "musaridya", "musaridyise"):
        analysis = analyze(client, api_key, text)
        assert analysis.status_code == 422, (text, analysis.content)
        error = analysis.json()["error"]
        assert error["code"] == "ANALYSIS_UNSUPPORTED"
        lanes = error["detail"]["future_lanes"]
        lane = next(
            item
            for item in lanes
            if item["code"] == "deferred_imperative_plural_object"
        )
        assert lane["boundary"] == "plural_with_object_concord"
        assert lane["support_status"] == "deferred_pending_evidence"


@pytest.mark.django_db
def test_plural_object_deferral_preserves_supported_imperatives(
    client, api_key, current_release
):
    # Plural commands without objects, singular object-marked commands
    # (both terminal variants), and positive object-marked imperatives stay
    # supported on the same lemma.
    dya = make_verb("-dya")
    make_class("5", 5, "ri")
    expected = {
        "musadye": ("plural", None),
        "musadya": ("plural", None),
        "usaridye": ("singular", "ri"),
        "usaridya": ("singular", "ri"),
        "ridye": ("singular", "ri"),
    }
    for text, (number, object_surface) in expected.items():
        polarity = (
            "negative" if text.startswith(("usa", "musa")) else "positive"
        )
        analysis = analyze(client, api_key, text)
        assert analysis.status_code == 200, (text, analysis.content)
        readings = find_imperative_analysis(
            analysis.json()["data"], polarity={"value": polarity}
        )
        assert readings, (text, analysis.content)
        assert all(
            reading["slots"]["addressee"]["number"] == number
            for reading in readings
        )
        if object_surface is None:
            assert all(reading["slots"]["object"] is None for reading in readings)
        else:
            assert all(
                reading["slots"]["object"]["surface"] == object_surface
                for reading in readings
            )


@pytest.mark.django_db
def test_divergent_stems_are_excluded_from_imperative_readings(
    client, api_key, current_release
):
    # Divergent stems (-ti, -nzi; Fortune 3.3.18) have no attested
    # imperative shape: generation refuses them and analysis infers no
    # imperative reading, with an identifiable lane naming the excluded
    # stem. The restriction covers the exact identity lookups that produced
    # the reported leak.
    ti = make_verb("-ti")
    make_verb("-nzi")

    generation = generate(client, api_key, ti, imperative_features())
    assert generation.status_code == 422, generation.content
    assert (
        generation.json()["error"]["detail"]["reason"]
        == "divergent_stem_without_terminal_a"
    )

    for text, headword in (("ti", "-ti"), ("nzi", "-nzi")):
        analysis = analyze(client, api_key, text)
        assert analysis.status_code == 422, (text, analysis.content)
        error = analysis.json()["error"]
        assert error["code"] == "ANALYSIS_UNSUPPORTED"
        lane = next(
            item
            for item in error["detail"]["future_lanes"]
            if item["code"] == "excluded_divergent_stem_imperative"
        )
        assert lane["excluded_stem_headwords"] == [headword]
        assert lane["support_status"] == "not_supported"


@pytest.mark.django_db
def test_divergent_stem_restriction_covers_bypass_paths(
    client, api_key, current_release
):
    # No imperative candidate path may authorize a divergent-stem reading:
    # the shared stem gate sits inside the resolution used by the bare,
    # prothetic, plural, object-marked, and negative paths, and by
    # extension-derived candidates. Extension-derived readings structurally
    # rebuild canonical stems with terminal -a, so a causative surface on a
    # divergent stem resolves to no candidate at all (no lane, no reading).
    make_verb("-ti")
    for text in ("iti", "tisai", "usatisa"):
        analysis = analyze(client, api_key, text)
        assert analysis.status_code == 422, (text, analysis.content)
        body = analysis.json()["error"]
        assert not [
            item
            for item in body.get("detail", {}).get("future_lanes", [])
            if item["code"] == "deferred_imperative_plural_object"
        ]
        readings = [
            item
            for item in body.get("detail", {}).get("future_lanes", [])
        ]
        if readings:
            # Whatever lane fires, it must never claim a supported
            # imperative reading of the divergent stem.
            assert all(
                item["support_status"] != "matched" for item in readings
            )


@pytest.mark.django_db
def test_divergent_stems_keep_finite_and_infinitive_readings(
    client, api_key, current_release
):
    # The restriction is imperative-lane-only: the exact lexical entry and
    # the supported finite and infinitive constructions on the same lemma
    # remain intact.
    make_verb("-ti")
    infinitive = analyze(client, api_key, "kuti")
    assert infinitive.status_code == 200, infinitive.content
    assert any(
        analysis["analysis_type"] == "infinitive"
        and analysis["lemma"]["normalized_headword"] == "ti"
        for analysis in infinitive.json()["data"]["analyses"]
    )

    finite = analyze(client, api_key, "handiti")
    assert finite.status_code == 200, finite.content
    assert any(
        analysis["analysis_type"] == "verb_form"
        and analysis["lemma"]["normalized_headword"] == "ti"
        for analysis in finite.json()["data"]["analyses"]
    )


@pytest.mark.django_db
def test_search_follows_the_corrected_imperative_scope(
    client, api_key, current_release
):
    # Excluded imperative readings never surface as matched morphology,
    # while exact lexical results and independently supported readings
    # (the kuti infinitive) survive.
    make_verb("-dya")
    make_verb("-ti")
    make_verb("-nzi")
    make_class("5", 5, "ri")

    plural_object = client.get(
        "/v1/search", {"q": "musaridye"}, HTTP_AUTHORIZATION=f"Api-Key {api_key}"
    )
    assert plural_object.status_code == 200, plural_object.content
    body = plural_object.json()["data"]
    assert "morphology" not in body
    assert body["count"] == 0
    enrichment = body["zero_result"]["morphology_enrichment"]
    assert enrichment["status"] == "unsupported"
    assert [
        lane
        for lane in enrichment["detail"]["future_lanes"]
        if lane["code"] == "deferred_imperative_plural_object"
    ]

    for text in ("ti", "nzi"):
        response = client.get(
            "/v1/search", {"q": text}, HTTP_AUTHORIZATION=f"Api-Key {api_key}"
        )
        assert response.status_code == 200, (text, response.content)
        body = response.json()["data"]
        assert "morphology" not in body
        assert body["count"] >= 1
        assert any(
            result["result_type"] == "lemma"
            and result["lemma"]["normalized_headword"] == text
            for result in body["results"]
        )

    infinitive = client.get(
        "/v1/search", {"q": "kuti"}, HTTP_AUTHORIZATION=f"Api-Key {api_key}"
    )
    assert infinitive.status_code == 200, infinitive.content
    body = infinitive.json()["data"]
    assert body["morphology_enrichment"]["status"] == "matched"
    assert any(
        analysis["analysis_type"] == "infinitive"
        for analysis in body["morphology"]["analyses"]
    )



# --- Rules-version gate --------------------------------------------------------


@pytest.mark.django_db
def test_imperative_generation_validates_the_serving_rules_version(
    client, api_key
):
    DataRelease.objects.create(
        version="2026.08.0",
        label="Stale release",
        rule_set_version="morphology-rules-v2",
        is_current=True,
    )
    lemma = make_verb("-buda")
    response = generate(client, api_key, lemma, imperative_features())
    assert response.status_code == 503, response.content
    assert (
        response.json()["error"]["code"] == "MORPHOLOGY_RULES_VERSION_UNSUPPORTED"
    )
