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

import re
from dataclasses import dataclass
from typing import Sequence

from shona_api.phonology import segment_graphemes

NO_RECORDED_PLURAL = "NO_RECORDED_PLURAL"
PLURAL_NOT_A_PREFIX = "PLURAL_NOT_A_PREFIX"
PLURAL_NASAL_PLACEHOLDER = "PLURAL_NASAL_PLACEHOLDER"
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
@dataclass(frozen=True)
class PluralClassRule:
    """What the source states about one class's correlative plural.

    ``prefixes`` are the plural-class prefixes the source gives for the class
    (with their allomorphs); a recorded prefix has to start with one of them.
    ``singular_prefixes`` are the class's own prefixes, which the plural
    *replaces* -- Fortune 3.3.14 describes the class 11 plural as formed with a
    prefix "substituted for or superimposed on the prefix /ru-/", and the same
    shape holds wherever the singular carries a prefix of its own. An empty
    tuple means the singular prefix is realised within the stem (class 5) or is
    /ø-/, so the plural attaches to the headword as recorded.
    """

    plural_class: str
    prefixes: tuple[str, ...]
    singular_prefixes: tuple[str, ...]
    kind: str
    locator: str


# Fortune Vol 1. PDF page = printed page + 12, the offset used elsewhere here.
PLURAL_CLASS_RULES: dict[str, PluralClassRule] = {
    "1": PluralClassRule(
        # Class 1 plurals are "predominantly" in class 2, with class 6 for the
        # tribe names of group (3) (3.3.1, printed p.39); class 6 in turn lists
        # class 1 among its correlating singulars (3.3.9, printed p.52).
        "2", ("va", "v", "ma"), ("mu", "mw", "m"), "standard",
        "3.3.1/3.3.2 printed pp.39-42: '/va-/' with '/v-/ before underived vowel-commencing "
        "stems', and class 6 for group (3); prefix substitution per 3.2.6 printed p.34",
    ),
    "3": PluralClassRule(
        "4", ("mi", "mw"), ("mu", "mw", "m"), "standard",
        "3.3.7 Noun class 4, printed p.49: '/mi-/', '/mw-/ before underived vowel-commencing "
        "stems'; prefix substitution per 3.2.6 printed p.34",
    ),
    "5": PluralClassRule(
        "6", ("ma",), (), "standard",
        "3.3.8/3.3.9 printed pp.50-52: class 6 '/ma-/' is the correlative plural of class 5",
    ),
    "7": PluralClassRule(
        "8", ("zvi", "zv", "zva"), ("chi", "ch"), "standard",
        "3.3.11 Noun class 8, printed p.60: '/zvi-/', allomorphs '/zv-/' and '/zva-/' "
        "corresponding to '/chi-/' and '/cha-/'",
    ),
    "9": PluralClassRule(
        "10", ("dzi",), (), "standard",
        "3.3.13 Noun class 10, printed p.65: '/dzi-/', allomorph '/\u00d8-/'",
    ),
    "11": PluralClassRule(
        # Fortune states both mechanisms -- "substituted for or superimposed on
        # the prefix /ru-/" -- and never says which stems take which. The
        # recorded value decides per entry: `ruvi` records `maruvi`, the
        # superimposing shape, while 104 other class 11 nouns record a bare
        # prefix (`mab-`, `mad-`) whose plural has no `ru`, i.e. substitution.
        # The recorded form is the source's own statement of the plural's
        # shape, so the rule never has to choose between the two.
        "10", ("dzi", "ma"), ("ru", "rw", "r"), "standard",
        "3.3.14 Noun class 11, printed p.67: plurals 'either in cl. 10, with prefix /\u00d8-N-/ "
        "substituted for or superimposed on the prefix /ru-/, or, less often, in cl. 6, with prefix /ma-/'",
    ),
    "14": PluralClassRule(
        "6", ("ma",), ("u", "ru"), "standard",
        "3.3.17 Noun class 14, printed p.74: 'singular with plurals of cl. 6'",
    ),
    "1a": PluralClassRule(
        "2a", ("va", "vana"), (), "honorific",
        "3.3.3/3.3.4 printed pp.42-44: the class 2a plural is 'almost always honorific'",
    ),
}

SOURCE_VERIFIED_PLURAL_CLASSES = frozenset(PLURAL_CLASS_RULES)

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
    # Breathy-voiced consonants are already voiced, so the change from
    # voiceless to voiced does not touch them. Fortune lists /bh/ and /dh/ in
    # the phoneme inventory of 1.6 (printed pp. 3-6); shona-core-v2 could not
    # read them as one grapheme, which is why a prefix like `mabh-` arrived
    # here as a trailing `h`.
    "bh": "bh",
    "dh": "dh",
    # Labialised consonants whose base is already voiced.
    "dw": "dw",
    "dyw": "dyw",
}

PLURAL_ALLOMORPHS = SOURCE_ATTESTED_ALLOMORPHS | RULE_SUPPORTED_ALLOMORPHS

VOWELS = frozenset({"a", "e", "i", "o", "u"})

# The depressor change is a class 5 phenomenon: the class 5 prefix voices the
# stem's initial, so only there does a recorded plural prefix carry a consonant
# other than the one the singular shows. Everywhere else the prefix repeats the
# stem's own initial (`vak-` with `kota`), which the literal match below finds.
DEPRESSOR_CLASSES = frozenset({"5"})

# Fortune 3.3.3: "A few class 1a nouns have three plurals, one in class 2a and
# the others with prefixes of 2a and 10, 6 and 10 respectively. Plurals in 2a
# are almost always honorific, the others almost always numerical." The hedge
# is the source's, so the kind is recorded as rule-supported rather than
# attested per entry.
HONORIFIC_PLURAL_CLASSES = frozenset({"1a"})


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
    plural_kind: str = "standard"
    allomorph: tuple[str, str] | None = None

    def as_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "surface": self.surface,
            "recorded": self.recorded,
            "basis": self.basis,
            "plural_kind": self.plural_kind,
            "plural_kind_evidence": (
                "rule_supported" if self.plural_kind == "honorific" else "source_attested"
            ),
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


def prefix_of(recorded: str) -> str:
    """The recorded plural without its trailing hyphen, for shape checks."""
    text = strip_dialect_tag(recorded)
    return text[:-1] if text.endswith("-") else text


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


# A recorded plural that is not a prefix must look like a word. Parsers
# occasionally put the rest of the dictionary line in the plural field
# (`pl: of jahwi q v. 2. M Muddy water. cp matakasvina KZ.`), and publishing
# that as a plural would be worse than publishing nothing.
RECORDED_FORM_RE = re.compile(r"^[^\s\-]+$")
# A recorded form may carry its own class as an annotation -- `mhamburo 10`, or
# `sero 10 k` with a dialect too. The annotation describes the plural, so the
# surface is the token before it.
ANNOTATED_FORM_RE = re.compile(
    r"^(?P<form>[^\s]+)\s+\d+[a-z]?(?:\s+[A-Za-z()]+)?$"
)


def derive_plural(
    headword: str,
    recorded_forms: Sequence[str],
    *,
    noun_class: str | None = None,
) -> PluralDerivation:
    """Derive the plural surface for ``headword`` from the recorded plural forms.

    Raises :class:`PluralDerivationError` with a stable code when the recorded
    material does not establish the plural.

    A plural the source writes out in full is **attested**, not derived, so it
    is published whatever the noun's class: no rule is being applied, and
    gating it on a class rule would withhold a plural the source states
    outright. The class gate applies only where a recorded *prefix* has to be
    applied to the stem, which is where a wrong rule would invent a form.
    """
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
        annotated = ANNOTATED_FORM_RE.match(stripped)
        if annotated is not None:
            stripped = annotated.group("form")
        if "-" in stripped or not RECORDED_FORM_RE.match(stripped):
            raise PluralDerivationError(
                PLURAL_NOT_A_PREFIX,
                "The recorded plural is neither a trailing-hyphen prefix nor a "
                "single complete form.",
                detail={"recorded": recorded},
            )
        return PluralDerivation(
            surface=stripped,
            recorded=recorded,
            basis="recorded_form",
            plural_kind=(
                "honorific" if noun_class in HONORIFIC_PLURAL_CLASSES else "standard"
            ),
        )

    if noun_class not in SOURCE_VERIFIED_PLURAL_CLASSES:
        raise PluralDerivationError(
            PLURAL_CLASS_UNVERIFIED,
            "A recorded plural prefix can only be applied where the sources "
            "establish that class's rule; verified so far: "
            f"{sorted(SOURCE_VERIFIED_PLURAL_CLASSES)}; this noun is "
            f"class {noun_class!r}.",
            detail={"noun_class": noun_class, "recorded": recorded},
        )

    # Hannan writes a capital N for a nasal that assimilates to whatever follows
    # (`maNg-`), and segmentation case-folds, which would silently read it as
    # the ordinary `ng`. Resolving it needs an assimilation rule no source here
    # states, so it is refused rather than read as an `ng`.
    if "N" in headword or "N" in prefix_of(stripped):
        raise PluralDerivationError(
            PLURAL_NASAL_PLACEHOLDER,
            "The entry uses Hannan's capital-N placeholder for a nasal that "
            "assimilates to the following consonant; no available source states "
            "the assimilation.",
            detail={"recorded": recorded, "headword": headword},
        )

    rule = PLURAL_CLASS_RULES[noun_class]
    prefix = stripped[:-1]
    if not _plural_prefix_allowed(prefix, rule):
        raise PluralDerivationError(
            PLURAL_ALLOMORPH_UNVERIFIED,
            f"The recorded prefix {prefix + '-'!r} does not begin with a prefix the "
            f"sources state for class {noun_class} (class {rule.plural_class}: "
            f"{', '.join(rule.prefixes)}).",
            detail={"recorded": recorded, "noun_class": noun_class, "rule": rule.locator},
        )

    stem = headword
    if rule.singular_prefixes:
        stripped_stem = _strip_singular_prefix(headword, rule)
        if stripped_stem is None:
            raise PluralDerivationError(
                PLURAL_ALLOMORPH_UNVERIFIED,
                f"The headword does not begin with any class {noun_class} prefix the "
                f"sources state ({', '.join(rule.singular_prefixes)}), so the plural "
                "prefix has nothing to replace.",
                detail={"recorded": recorded, "headword": headword, "rule": rule.locator},
            )
        stem = stripped_stem

    stem_graphemes = segment_graphemes(stem)
    if not prefix or not stem_graphemes:
        raise PluralDerivationError(
            PLURAL_EMPTY_STEM,
            "The headword or the recorded prefix is empty.",
            detail={"recorded": recorded, "headword": headword},
        )

    prefix_graphemes = segment_graphemes(prefix)
    size, basis = _shared_span(prefix_graphemes, stem_graphemes, noun_class)
    surface = prefix + "".join(stem_graphemes[size:])

    # A consonant-final prefix exists to carry the stem's initial, so a prefix
    # that shares nothing with the stem means the pair is one the table does not
    # have: `map-` with `bhamadza` implies `p -> bh`, which the source's
    # allomorph list does not state. Appending the whole stem here would publish
    # `mapbhamadza`.
    if size == 0 and prefix_graphemes[-1] not in VOWELS:
        raise PluralDerivationError(
            PLURAL_ALLOMORPH_UNVERIFIED,
            "The recorded prefix ends with a consonant but shares no span with "
            "the headword, so the allomorph it implies is not one the sources "
            "state.",
            detail={
                "recorded": recorded,
                "prefix_final": prefix_graphemes[-1],
                "headword_initial": stem_graphemes[0],
            },
        )

    allomorph = None
    if size and basis == "allomorph":
        allomorph = (prefix_graphemes[-size], stem_graphemes[0])

    return PluralDerivation(
        surface=surface,
        recorded=recorded,
        basis=f"{basis}_prefix" if size else "prefix_plus_stem",
        plural_kind=rule.kind,
        allomorph=allomorph,
    )


PREFIX_SUBSTITUTION_LOCATOR = (
    "Fortune Vol 1 3.2.6 'Position of primary and secondary prefixes', printed p.34: "
    "a secondary prefix is 'one which is substituted for a primary prefix', "
    "e.g. chi-kadzi (7) cp. mu-kadzi (1)"
)


def _strip_singular_prefix(headword: str, rule: PluralClassRule) -> str | None:
    """Remove the singular's own primary prefix, which the plural replaces.

    `mu-kadzi` (1) cp. `chi-kadzi` (7) shows the plural attaching to the stem,
    not to the prefixed form it replaces (3.2.6). Returns ``None`` when the
    headword does not begin with any prefix the class states.
    """
    graphemes = segment_graphemes(headword)
    for candidate in sorted(rule.singular_prefixes, key=len, reverse=True):
        candidate_graphemes = segment_graphemes(candidate)
        if graphemes[: len(candidate_graphemes)] == candidate_graphemes:
            return "".join(graphemes[len(candidate_graphemes) :])
    return None


def _plural_prefix_allowed(prefix: str, rule: PluralClassRule) -> bool:
    """The recorded prefix must begin with one the source states for the class."""
    graphemes = segment_graphemes(prefix)
    for candidate in rule.prefixes:
        candidate_graphemes = segment_graphemes(candidate)
        if graphemes[: len(candidate_graphemes)] == candidate_graphemes:
            return True
    return False


def _shared_span(
    prefix_graphemes: list[str],
    stem_graphemes: list[str],
    noun_class: str | None,
) -> tuple[int, str | None]:
    """Longest suffix of the prefix that introduces the stem, and how.

    The prefix carries as much of the stem's beginning as it repeats, so the
    plural is the prefix plus the *remainder* of the stem:

    - `mab-` + `biku` -> `mabiku` (the `b` is shared literally)
    - `madhi-` + `dhibha` -> `madhibha` (the whole `dhi` is shared)
    - `mab-` + `ovu`-style stems share nothing, so the stem follows intact
    - `map-` + `banga` -> `mapanga`: `p` is not the stem's `b`, but under the
      class 5 depressor change `p` is the underlying consonant whose surface
      form is `b`, so the pair matches through the allomorph table.
    """
    limit = min(len(prefix_graphemes), len(stem_graphemes))
    for size in range(limit, 0, -1):
        tail = prefix_graphemes[-size:]
        head = stem_graphemes[:size]
        if tail == head:
            return size, "literal"
        if noun_class in DEPRESSOR_CLASSES:
            surface_initial = PLURAL_ALLOMORPHS.get(tail[0])
            if surface_initial == head[0] and len(tail) == len(head) and [surface_initial] + tail[1:] == head:
                return size, "allomorph"
    return 0, None
