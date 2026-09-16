"""Tests for the class 5 noun-plural derivation.

The rule comes from Fortune Vol 1 3.3.8 (the class 5 prefix and its allomorphs)
and 3.3.9 (`ma-`, and class 6 as the correlative plural of class 5). Locators are
in the module docstring. These tests pin the derivations the source states, and
-- just as importantly -- the refusals, because a plural invented for an
unverified pair is worse than no plural at all.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shona_api.morphology.plurals import (
    PLURAL_ALLOMORPH_UNVERIFIED,
    PLURAL_CLASS_UNVERIFIED,
    PLURAL_EMPTY_STEM,
    PLURAL_NOT_A_PREFIX,
    PLURAL_PREFIX_FORM_UNVERIFIED,
    NO_RECORDED_PLURAL,
    PluralDerivationError,
    derive_plural,
    strip_dialect_tag,
)


# `allomorph` records the pair only when the prefix's consonant differs from
# the one the singular shows -- that is the depressor change. Where they agree,
# the match is literal and there is no allomorph to report.
@pytest.mark.parametrize(
    "headword, recorded, expected, underlying, surface_initial, allomorphic",
    [
        # Fortune 3.3.8(2): "voiced implosive" before /p, t/.
        ("banga", "map-", "mapanga", "p", "b", True),
        ("dabwa", "mat-", "matabwa", "t", "d", True),
        # Fortune 3.3.8(3): "voiced depressor" before /k, pf, ch, tsv/.
        ("gadzi", "mak-", "makadzi", "k", "g", True),
        ("bveni", "mapf-", "mapfeni", "pf", "bv", True),
        # shona-core-v3 reads bh and dh as one grapheme each, so their prefixes
        # are readable; Fortune lists both in the phoneme inventory (1.6).
        ("bhachi", "mabh-", "mabhachi", "bh", "bh", False),
        ("dhani", "madh-", "madhani", "dh", "dh", False),
        # A vowel-final prefix carries a syllable of the stem, so the plural is
        # the prefix plus what is left: `madhi-` + `dhibha` -> `madhibha`,
        # `mati-` + `dikisa` -> `matikisa`.
        ("dhibha", "madhi-", "madhibha", "dh", "dh", False),
        ("dikisa", "mati-", "matikisa", "t", "d", True),
        ("nyimbiri", "manyi-", "manyimbiri", "ny", "ny", False),
        ("jacha", "mach-", "machacha", "ch", "j", True),
        # Fortune 3.3.8(4): "voiced affricate depressor" before /ts, f, s, sv, sh/.
        ("dzanza", "mats-", "matsanza", "ts", "dz", True),
        # k -> g with the labialisation preserved.
        ("gwai", "makw-", "makwai", "kw", "gw", True),
        # The stated change applied to the labialised series, where the /w/ both
        # forms share is carried through: Hannan attests `bwipwi ... pl: mapw-`
        # and `dwiri ... pl: matw-`.
        ("bwipwi", "mapw-", "mapwipwi", "pw", "bw", True),
        ("dwiri", "matw-", "matwiri", "tw", "dw", True),
        # Already voiced: the stated change is voiceless -> voiced, so nothing happens.
        ("biku", "mab-", "mabiku", "b", "b", False),
        ("derere", "mad-", "maderere", "d", "d", False),
        ("gumbezi", "mag-", "magumbezi", "g", "g", False),
        ("jabwanira", "maj-", "majabwanira", "j", "j", False),
        ("dzadza", "madz-", "madzadza", "dz", "dz", False),
    ],
)
def test_derives_the_source_attested_plural(
    headword, recorded, expected, underlying, surface_initial, allomorphic
):
    derivation = derive_plural(headword, [recorded], noun_class="5")

    assert derivation.surface == expected
    assert derivation.recorded == recorded
    if allomorphic:
        assert derivation.basis == "allomorph_prefix"
        # The singular's initial is a grapheme, not a character: `bveni` is `bv`.
        assert derivation.allomorph == (underlying, surface_initial)
    else:
        assert derivation.basis == "literal_prefix"
        assert derivation.allomorph is None


def test_plural_uses_the_underlying_consonant_not_the_singulars():
    """`gwai` has plural `makwai`, not `magwai`.

    Fortune's own examples show the plural carrying the underlying consonant
    (`banga` cp. `ma-panga`, `gore` cp. `ma-kore`), and the recorded prefix is
    where that underlying consonant survives.
    """
    assert derive_plural("gwai", ["makw-"], noun_class="5").surface == "makwai"
    assert derive_plural("banga", ["map-"], noun_class="5").surface == "mapanga"


def test_a_recorded_full_form_is_published_verbatim():
    """Irregular and suppletive plurals are recorded, never regenerated."""
    derivation = derive_plural("moyo", ["moyo"], noun_class="5")

    assert derivation.surface == "moyo"
    assert derivation.basis == "recorded_form"
    assert derivation.allomorph is None


@pytest.mark.parametrize(
    "recorded, expected",
    [
        ("mab- (M)", "mab-"),
        ("mab-(M)", "mab-"),
        ("mag- Z", "mag-"),
        ("makw- KZ", "makw-"),
        ("mab-", "mab-"),
        ("moyo", "moyo"),
    ],
)
def test_dialect_restrictions_are_stripped_however_they_are_written(recorded, expected):
    assert strip_dialect_tag(recorded) == expected


def test_the_first_recorded_form_wins_and_the_rest_are_alternatives():
    derivation = derive_plural("bimha", ["map-", "mab- (M)"], noun_class="5")

    assert derivation.surface == "mapimha"
    assert derivation.recorded == "map-"


@pytest.mark.parametrize(
    "headword, recorded, noun_class, code",
    [
        # A consonant the source states no allomorph for and the data does not
        # attest as a depressor: `dywai` would need `w -> dy`, which is not a
        # change the source describes.
        ("dywai", ["mady-"], "5", PLURAL_ALLOMORPH_UNVERIFIED),
        # `gwa` records `mag-`, whose final `g` implies a surface `g`, but the
        # headword begins `gw` -- a labialisation the source does not describe.
        ("gwa", ["mag-"], "5", PLURAL_ALLOMORPH_UNVERIFIED),
        # A consonant-final prefix exists to carry the stem's initial, so a
        # prefix sharing nothing with it implies an allomorph the source does
        # not state: `map-` with `bhamadza` would need `p -> bh`.
        ("bhamadza", ["map-"], "5", PLURAL_ALLOMORPH_UNVERIFIED),
        # Only the class whose plural rule is established is derived.
        # No class rule is encoded for 2a yet, so its prefix cannot be applied.
        ("vanabudibudi", ["vavana-"], "2a", PLURAL_CLASS_UNVERIFIED),
        # Class 1 is verified, but `kota` carries none of its singular
        # prefixes, so the plural prefix has nothing to replace.
        ("kota", ["vak-"], "1", PLURAL_ALLOMORPH_UNVERIFIED),
        # The parser put a cross-reference in the plural field; there is no
        # plural to publish.
        ("rusero", ["see bemu."], "11", PLURAL_NOT_A_PREFIX),
        ("biku", [], "5", NO_RECORDED_PLURAL),
        # A recorded value that is neither a trailing-hyphen prefix nor a whole
        # form: malformed rather than irregular, so it is refused, not guessed.
        ("biku", ["ma-b"], "5", PLURAL_NOT_A_PREFIX),
    ],
)
def test_refuses_what_the_sources_do_not_establish(headword, recorded, noun_class, code):
    with pytest.raises(PluralDerivationError) as excinfo:
        derive_plural(headword, recorded, noun_class=noun_class)

    assert excinfo.value.code == code


def test_a_class_is_required_and_checked_before_anything_else():
    with pytest.raises(PluralDerivationError) as excinfo:
        derive_plural("biku", ["mab-"])

    assert excinfo.value.code == PLURAL_CLASS_UNVERIFIED


def test_refuses_an_empty_headword():
    with pytest.raises(PluralDerivationError) as excinfo:
        derive_plural("", ["mab-"], noun_class="5")

    assert excinfo.value.code == PLURAL_EMPTY_STEM


def test_the_payload_states_the_evidence_behind_the_form():
    """A consumer must be able to tell a cited allomorph from an inferred one.

    `map-` with `banga` is Fortune 3.3.8(2), cited; `makw-` with `gwai` is
    `k -> g` with the labialisation preserved, which follows from the change the
    source states rather than appearing in its list.
    """
    cited = derive_plural("banga", ["map-"], noun_class="5").as_payload()
    inferred = derive_plural("gwai", ["makw-"], noun_class="5").as_payload()

    assert cited["basis"] == "allomorph_prefix"
    assert cited["allomorph"]["evidence"] == "source_attested"
    assert inferred["allomorph"]["evidence"] == "rule_supported"


def test_a_class_1a_plural_is_marked_honorific():
    """Fortune 3.3.3 calls the 2a plural of a class 1a noun honorific.

    Without the marker a consumer cannot tell the plural it can count with from
    the one that is honorific, and publishing an honorific plural as the
    ordinary plural misrepresents it.
    """
    honorific = derive_plural("gufu", ["vana-"], noun_class="1a")
    standard = derive_plural("biku", ["mab-"], noun_class="5")

    assert honorific.surface == "vanagufu"
    assert honorific.plural_kind == "honorific"
    assert standard.plural_kind == "standard"


def test_the_honorific_marker_is_labelled_as_rule_supported():
    """Fortune's wording is "almost always honorific", so the kind is inferred
    from a general statement rather than attested for each entry."""
    payload = derive_plural("gufu", ["vana-"], noun_class="1a").as_payload()

    assert payload["plural_kind"] == "honorific"
    assert payload["plural_kind_evidence"] == "rule_supported"
    assert derive_plural("biku", ["mab-"], noun_class="5").as_payload()[
        "plural_kind_evidence"
    ] == "source_attested"


def test_a_shared_vowel_at_the_junction_is_written_once():
    """`mau-` overlaps the `u` that `urizheve` begins with, so the plural is
    `maurizheve`, not the doubled `mauurizheve`."""
    assert derive_plural("urizheve", ["mau-"], noun_class="5").surface == "maurizheve"


# --- the dictionary text as a second reading -------------------------------


def test_homoglyphs_are_normalised_before_a_reading_is_used():
    """The extraction carries Cyrillic lookalikes; publishing them would put
    non-Latin characters in a Shona surface form."""
    from shona_api.parsers.dictionary_text import normalise_homoglyphs

    assert normalise_homoglyphs("m\u0430p-") == "map-"
    assert normalise_homoglyphs("\u0442\u0430p-") == "tap-"


def test_a_headword_the_text_reports_once_can_correct_a_unit(tmp_path):
    from shona_api.parsers.dictionary_text import read_plural_index, unambiguous_plural

    source = tmp_path / "text.txt"
    source.write_text(
        "dikanwa [HHH]KZ n 5, pl: mad-, Necessary, desirable.\n"
        "gwama [HH] MZn 5, pl: magw-, Fruit.\n"
        "gwama [HH K]KMZ n 5, pl: makw-, Leather bag.\n",
        encoding="utf-8",
    )
    index = read_plural_index(source)

    assert unambiguous_plural(index, "dikanwa") == "mad-"
    # Two entries, two plurals, no entry locators: ambiguous, so nothing to use.
    assert unambiguous_plural(index, "gwama") is None
    assert unambiguous_plural(index, "absent") is None


def test_an_absent_text_file_yields_nothing_rather_than_failing(tmp_path):
    """The cache is gitignored, so a checkout without it must still run."""
    from shona_api.parsers.dictionary_text import read_plural_index

    assert read_plural_index(tmp_path / "missing.txt") == {}
