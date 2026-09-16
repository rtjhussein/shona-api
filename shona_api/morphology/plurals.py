"""Derive a noun plural from the plural the source line records.

Hannan records a plural either as a prefix with a trailing hyphen (``pl: map-``,
``pl: vana-``) or, for irregular plurals, as a complete form (``pl: moyo``). The
prefix carries the stem's **underlying** initial consonant, because the class 5
prefix has already changed that consonant in the singular: Fortune Vol 1 3.3.8
gives ``(ri-) + -pangá > banga`` with plural ``ma-panga`` (3.3.9), so the plural
of the surface form ``banga`` is ``ma`` + ``panga``, not ``ma`` + ``banga``.

Locators (Fortune Vol 1, printed page / PDF page = printed + 12):

- 3.3.8 Noun class 5, printed p.50 / PDF p.62 -- the prefix and its allomorphs.
- 3.3.9 Noun class 6, printed p.52 / PDF p.64 -- ``ma-``, and the statement that
  class 6 is the correlative plural of classes 5, 11, 21, 1a, 1 and 14.
- 3.3.3 Noun class 1a, printed p.42 / PDF p.54, and 3.3.4 Noun class 2a,
  printed p.44 / PDF p.56 -- whose plurals are honorific rather than numerical.

Nothing here invents a stem. A plural is only produced when the source line
records one, and only when the pair of consonants involved is one the source
states or that follows directly from the direction of the change it states.
Everything else is refused with a stable code, named in the message, and left
for review -- a wrong plural is worse than a missing one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from shona_api.phonology import segment_graphemes

NO_RECORDED_PLURAL = "NO_RECORDED_PLURAL"
PLURAL_NOT_A_PREFIX = "PLURAL_NOT_A_PREFIX"
PLURAL_ALLOMORPH_UNVERIFIED = "PLURAL_ALLOMORPH_UNVERIFIED"
PLURAL_EMPTY_STEM = "PLURAL_EMPTY_STEM"
PLURAL_CLASS_UNVERIFIED = "PLURAL_CLASS_UNVERIFIED"
PLURAL_PREFIX_FORM_UNVERIFIED = "PLURAL_PREFIX_FORM_UNVERIFIED"

# The class whose plural derivation the sources establish end to end: Fortune
# 3.3.8 gives the class 5 prefix and its allomorphs, 3.3.9 gives class 6 as its
# correlative plural. Other classes take plurals too -- class 1a takes an
# honorific 2a plural (3.3.3, 3.3.4), class 1 takes 2a, class 9 takes 10 -- but
# each needs its own source work before a surface can be published as fact.
#
# 1,956 of the 2,060 published nouns carrying a plural prefix are class 5.
SOURCE_VERIFIED_PLURAL_CLASSES = frozenset({"5"})

# Underlying consonant -> the initial the singular shows, from Fortune 3.3.8:
# (2) "voiced implosive" before /p, t/; (3) "voiced depressor" before
# /k, pf, ch, tsv/; (4) "voiced affricate depressor" before /ts, f, s, sv, sh/.
SOURCE_ATTESTED_ALLOMORPHS = {
    "p": "b",
    "t": "d",
    "k": "g",
    "pf": "bv",
    "ch": "j",
    "tsv": "dzv",
    "ts": "dz",
    "f": "bv",
    "s": "dz",
    "sv": "dzv",
    "sh": "j",
}

# Pairs the source does not list but that follow from the change it states: it
# is a change from voiceless to voiced, so a consonant already voiced undergoes
# nothing. Recorded here so the table is explicit rather than implied, and so a
# reviewer can see exactly which pairs are inferred rather than cited.
RULE_SUPPORTED_ALLOMORPHS = {
    "b": "b",
    "d": "d",
    "g": "g",
    "j": "j",
    "dz": "dz",
    "bv": "bv",
    "dzv": "dzv",
    "gw": "gw",
    "bw": "bw",
    # k -> g with the labialisation preserved.
    "kw": "gw",
}

PLURAL_ALLOMORPHS = SOURCE_ATTESTED_ALLOMORPHS | RULE_SUPPORTED_ALLOMORPHS

VOWELS = frozenset({"a", "e", "i", "o", "u"})


class PluralDerivationError(ValueError):
    """A plural cannot be derived from what the source line records."""

    def __init__(self, code: str, message: str, *, detail: dict[str, object] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail or {}


@dataclass(frozen=True)
class PluralDerivation:
    surface: str
    recorded: str
    basis: str
    allomorph: tuple[str, str] | None = None

    def as_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "surface": self.surface,
            "recorded": self.recorded,
            "basis": self.basis,
        }
        if self.allomorph is not None:
            payload["allomorph"] = {
                "underlying": self.allomorph[0],
                "surface_initial": self.allomorph[1],
                "evidence": (
                    "source_attested"
                    if self.allomorph[0] in SOURCE_ATTESTED_ALLOMORPHS
                    else "rule_supported"
                ),
            }
        return payload


def strip_dialect_tag(recorded: str) -> str:
    """Drop a dialect restriction, however the source wrote it.

    Hannan and the parsers express the same thing three ways -- ``mab- (M)``,
    ``mab-(M)``, and a bare trailing code ``mag- Z``, ``makw- KZ`` -- and a
    plural prefix is the token that ends with the hyphen, not the whole string.
    """
    text = recorded.strip()
    first, _, rest = text.partition(" ")
    if rest and first.endswith("-"):
        return first
    if text.endswith(")") and "(" in text:
        return text[: text.rindex("(")].strip()
    return text


def derive_plural(
    headword: str,
    recorded_forms: Sequence[str],
    *,
    noun_class: str | None = None,
) -> PluralDerivation:
    """Derive the plural surface for ``headword`` from the recorded plural forms.

    Raises :class:`PluralDerivationError` with a stable code when the recorded
    material does not establish the plural. ``noun_class`` is required: the rule
    below is the class 5 -> class 6 one, and applying it to a class whose plural
    the sources state differently would invent a form.
    """
    if noun_class not in SOURCE_VERIFIED_PLURAL_CLASSES:
        raise PluralDerivationError(
            PLURAL_CLASS_UNVERIFIED,
            "The sources verified so far establish the plural rule for "
            f"{sorted(SOURCE_VERIFIED_PLURAL_CLASSES)} only; this noun is "
            f"class {noun_class!r}.",
            detail={"noun_class": noun_class},
        )

    recorded = next(
        (form for form in recorded_forms if isinstance(form, str) and form.strip()),
        None,
    )
    if recorded is None:
        raise PluralDerivationError(
            NO_RECORDED_PLURAL,
            "The source line records no plural for this noun.",
            detail={"headword": headword},
        )

    stripped = strip_dialect_tag(recorded)
    # A recorded form with no trailing hyphen is the complete plural, written
    # out because it is irregular (`pl: moyo`) or suppletive (`pl: meno`).
    if not stripped.endswith("-"):
        if "-" in stripped:
            raise PluralDerivationError(
                PLURAL_NOT_A_PREFIX,
                "The recorded plural is neither a trailing-hyphen prefix nor a "
                "complete form.",
                detail={"recorded": recorded},
            )
        return PluralDerivation(surface=stripped, recorded=recorded, basis="recorded_form")

    prefix = stripped[:-1]
    stem_graphemes = segment_graphemes(headword)
    if not prefix or not stem_graphemes:
        raise PluralDerivationError(
            PLURAL_EMPTY_STEM,
            "The headword or the recorded prefix is empty.",
            detail={"recorded": recorded, "headword": headword},
        )

    prefix_graphemes = segment_graphemes(prefix)
    final = prefix_graphemes[-1]
    if final in VOWELS:
        # A vowel-final prefix carries a syllable of the stem, not just a
        # consonant: `madhi-` with `dhibha` gives `madhibha`, and `mati-` with
        # `dikisa` gives `matikisa`, so the plural is neither the stem intact
        # (`madhidhibha`) nor the stem minus one grapheme. Fortune 3.3.9
        # describes `ma-` plus the class 5 stem, not this syllable-plus-remainder
        # shape, so it is refused rather than guessed.
        raise PluralDerivationError(
            PLURAL_PREFIX_FORM_UNVERIFIED,
            "The recorded plural prefix ends with a vowel and carries part of "
            "the stem; the sources verified so far state no rule for that shape.",
            detail={"recorded": recorded, "prefix": prefix, "headword": headword},
        )

    expected_initial = PLURAL_ALLOMORPHS.get(final)
    if expected_initial is None:
        raise PluralDerivationError(
            PLURAL_ALLOMORPH_UNVERIFIED,
            f"The source states no class 5 allomorph for the consonant {final!r}, "
            "so the plural prefix cannot be applied to this stem.",
            detail={"recorded": recorded, "underlying": final},
        )
    if stem_graphemes[0] != expected_initial:
        raise PluralDerivationError(
            PLURAL_ALLOMORPH_UNVERIFIED,
            f"The recorded prefix implies the underlying consonant {final!r}, "
            f"whose attested form here is {expected_initial!r}, but the headword "
            f"begins with {stem_graphemes[0]!r}.",
            detail={
                "recorded": recorded,
                "underlying": final,
                "expected_initial": expected_initial,
                "headword_initial": stem_graphemes[0],
            },
        )

    return PluralDerivation(
        surface=prefix + "".join(stem_graphemes[1:]),
        recorded=recorded,
        basis="consonant_final_prefix",
        allomorph=(final, stem_graphemes[0]),
    )
