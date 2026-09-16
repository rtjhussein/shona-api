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


@pytest.mark.parametrize(
    "headword, recorded, expected, underlying, surface_initial",
    [
        # Fortune 3.3.8(2): "voiced implosive" before /p, t/.
        ("banga", "map-", "mapanga", "p", "b"),
        ("dabwa", "mat-", "matabwa", "t", "d"),
        # Fortune 3.3.8(3): "voiced depressor" before /k, pf, ch, tsv/.
        ("gadzi", "mak-", "makadzi", "k", "g"),
        ("bveni", "mapf-", "mapfeni", "pf", "bv"),
        ("jacha", "mach-", "machacha", "ch", "j"),
        # Fortune 3.3.8(4): "voiced affricate depressor" before /ts, f, s, sv, sh/.
        ("dzanza", "mats-", "matsanza", "ts", "dz"),
        # k -> g with the labialisation preserved.
        ("gwai", "makw-", "makwai", "kw", "gw"),
        # Already voiced: the stated change is voiceless -> voiced, so nothing happens.
        ("biku", "mab-", "mabiku", "b", "b"),
        ("derere", "mad-", "maderere", "d", "d"),
        ("gumbezi", "mag-", "magumbezi", "g", "g"),
        ("jabwanira", "maj-", "majabwanira", "j", "j"),
        ("dzadza", "madz-", "madzadza", "dz", "dz"),
    ],
)
def test_derives_the_source_attested_plural(
    headword, recorded, expected, underlying, surface_initial
):
    derivation = derive_plural(headword, [recorded], noun_class="5")

    assert derivation.surface == expected
    assert derivation.basis == "consonant_final_prefix"
    # The singular's initial is a grapheme, not a character: `bveni` begins `bv`.
    assert derivation.allomorph == (underlying, surface_initial)
    assert derivation.recorded == recorded


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
        # The source states no allomorph for bh or dh, and the graphemes are
        # absent from the phonology inventory, so the pair cannot be checked.
        ("bhachi", ["mabh-"], "5", PLURAL_ALLOMORPH_UNVERIFIED),
        ("dhani", ["madh-"], "5", PLURAL_ALLOMORPH_UNVERIFIED),
        # A vowel-final prefix carries a syllable of the stem (madhi- + dhibha
        # -> madhibha); no verified source states that shape.
        ("dhibha", ["madhi-"], "5", PLURAL_PREFIX_FORM_UNVERIFIED),
        ("dikisa", ["mati-"], "5", PLURAL_PREFIX_FORM_UNVERIFIED),
        # Only the class whose plural rule is established is derived.
        ("gufu", ["vana-"], "1a", PLURAL_CLASS_UNVERIFIED),
        ("kota", ["vak-"], "1", PLURAL_CLASS_UNVERIFIED),
        ("rusero", ["sero 10 k"], "11", PLURAL_CLASS_UNVERIFIED),
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
    """A consumer must be able to tell a cited allomorph from an inferred one."""
    attested = derive_plural("banga", ["map-"], noun_class="5").as_payload()
    inferred = derive_plural("biku", ["mab-"], noun_class="5").as_payload()

    assert attested["basis"] == "consonant_final_prefix"
    assert attested["allomorph"]["evidence"] == "source_attested"
    assert inferred["allomorph"]["evidence"] == "rule_supported"
