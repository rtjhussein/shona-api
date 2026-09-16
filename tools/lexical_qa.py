"""Independent reader for Hannan dictionary lines, used for lexical QA.

This module is deliberately dependency-free -- it imports nothing from
``shona_api`` -- so that expectations derived here are produced by a separate
implementation from the one under test. Comparing the two is the point: the
published corpus was produced by LLM parsers, and a reader written from the
documented line format is an independent check on their output.

Hannan's line format (product requirements, section 17.1)::

    banga [LH] KZ ideo of Putting in safe place; of Packing up. 2. M Second sense. cp chirambakudzimba KZ.
    bimha [LL]KMZ n 5, pl: map-, mab- (M), Reedbuck R 292.
    -bikura [H]KZ v t Snatch and carry away.
    -bimhidza [H M; LHLH Z]MZ v t, see -bhimhidza.

which is: headword, tone bracket, dialect restriction, part of speech,
primary definition, sense markers, cross-references. A line without a tone
bracket is not the structured entry shape this reader understands, and is
reported as unparseable rather than guessed at.
"""

from __future__ import annotations

import re
from typing import Any

# Headword may carry Hannan's annotation markers and a leading hyphen marking a
# verb stem; multi-word entries such as "munhu basi" also occur.
ENTRY_RE = re.compile(
    r"^(?P<markers>[†*]*)(?P<hyphen>-)?(?P<headword>.+?)\s+\[(?P<tone>[^\]]+)\]\s*(?P<rest>.*)$"
)

# Dialect restriction immediately after the bracket: K, Ko, KMZ, MZ, Ko(B)Z, ...
DIALECT_RUN_RE = re.compile(r"^(?P<dialects>[KMoZBdNu]+(?:\([A-Za-z]+\))?[KMoZBdNu]*)(?=\s|$)")

# Tone segments are separated by ';'. A segment is one or more H/L runs: a
# multi-word headword carries one pattern group per word ("[LLL HH]" for
# "munhondo churu"), and a dialect restriction may follow the last group
# ("LLH Z"). Dialect codes never consist solely of H and L, so a following
# all-H/L token continues the pattern and anything else is the restriction.
TONE_SEGMENT_RE = re.compile(r"^(?P<pattern>[HL]+(?:\s+[HL]+)*)")

NOUN_RE = re.compile(r"^n\s+(?P<class_number>\d+[a-z]?)\b")
PLURAL_RE = re.compile(r"\bpl:\s*(?P<forms>[^,.;]+)")
# A plural entry is a prefix ("map-"), sometimes with a dialect restriction
# ("mab- (M)"). Anything longer is the definition, which is where the list ends.
PLURAL_ITEM_RE = re.compile(r"[A-Za-z'’\-]+(?:\s*\([A-Za-z]+\))?")
# Sense boundaries: Hannan marks the second and later senses as "2.", "3.".
SENSE_MARKER_RE = re.compile(r"\s[2-9]\.\s")


def _read_plural_forms(rest: str) -> list[str]:
    """Read the comma-separated plural prefixes after ``pl:``.

    The list runs to the definition, and a definition may itself contain commas
    (``pl: map-, mab- (M), Reedbuck R 292.``), so items are consumed only while
    they still look like plural prefixes.
    """
    match = PLURAL_RE.search(rest)
    if match is None:
        return []
    forms = [match.group("forms").strip()]
    tail = rest[match.end() :]
    if tail.startswith(","):
        for item in tail.split(",")[1:]:
            candidate = item.strip()
            if not PLURAL_ITEM_RE.fullmatch(candidate):
                break
            forms.append(candidate)
    return [form for form in forms if form]


# Part of speech as written at the head of the remainder. Longest first: "v t"
# must be tried before bare "v".
POS_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(rf"^{pattern}\b"), family)
    for pattern, family in (
        (r"v\s+t\s*&\s*i", "verb_stem"),
        (r"vt&i", "verb_stem"),
        (r"vt_i", "verb_stem"),
        (r"vi&t", "verb_stem"),
        (r"v\s+t", "verb_stem"),
        (r"v\s+i", "verb_stem"),
        (r"vti", "verb_stem"),
        (r"vt", "verb_stem"),
        (r"vi", "verb_stem"),
        (r"defective\s+v", "verb_stem"),
        (r"def\s+v", "verb_stem"),
        (r"v", "verb_stem"),
        (r"n", "noun"),
        (r"ideophone", "ideophone"),
        (r"ideo", "ideophone"),
    )
)


class HannanLineError(ValueError):
    """The line does not carry the structured entry shape this reader expects."""


def read_hannan_line(raw_text: str) -> dict[str, Any]:
    """Parse a Hannan entry line into the facts a lexicon record must carry.

    Returns ``headword``, ``headword_kind`` (``noun``/``verb_stem``/
    ``ideophone``/``other``), ``noun_class`` (or ``None``), ``tone_patterns``
    (the distinct tone alternatives the bracket attests), ``plural_forms`` as
    written after ``pl:``, the dialect restriction, and the part of speech as
    the source abbreviates it.
    """
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise HannanLineError("empty line")

    match = ENTRY_RE.match(" ".join(raw_text.split()))
    if match is None:
        raise HannanLineError("no tone bracket found; not a structured entry line")

    headword = match.group("headword").strip()
    if not headword:
        raise HannanLineError("empty headword")

    tone_patterns: list[str] = []
    for segment in match.group("tone").split(";"):
        segment_match = TONE_SEGMENT_RE.match(segment.strip())
        if segment_match is None:
            raise HannanLineError(f"unreadable tone segment {segment.strip()!r}")
        pattern = segment_match.group("pattern")
        if pattern not in tone_patterns:
            tone_patterns.append(pattern)

    rest = match.group("rest").strip()
    dialect_match = DIALECT_RUN_RE.match(rest)
    dialects: list[str] = []
    if dialect_match is not None:
        dialects = [dialect_match.group("dialects")]
        rest = rest[dialect_match.end() :].strip()

    headword_kind = "other"
    matched_pos = ""
    for pattern, family in POS_PATTERNS:
        match_pos = pattern.match(rest)
        if match_pos is not None:
            headword_kind = family
            matched_pos = match_pos.group(0)
            break

    noun_class = None
    plural_forms: list[str] = []
    if headword_kind == "noun":
        class_match = NOUN_RE.match(rest)
        if class_match is not None:
            noun_class = class_match.group("class_number")
        plural_forms = _read_plural_forms(rest)

    return {
        "headword": headword.lstrip("-").lstrip("†*").strip(),
        "headword_kind": headword_kind,
        "noun_class": noun_class,
        "tone_patterns": tone_patterns,
        "plural_forms": plural_forms,
        "dialects": dialects,
        "part_of_speech": rest[:40],
        "source_shape": source_shape(
            headword=headword,
            headword_kind=headword_kind,
            part_of_speech=matched_pos,
            noun_class=noun_class,
            plural_forms=plural_forms,
            raw_text=raw_text,
        ),
    }


def source_shape(
    *,
    headword: str,
    headword_kind: str,
    part_of_speech: str,
    noun_class: str | None,
    plural_forms: list[str],
    raw_text: str,
) -> str:
    """Classify a line by the feature of its *source form* that it exercises.

    Stratifying the QA sample by these shapes -- rather than uniformly -- is
    what lets the instrument reach the entries where parsing is hard: a noun
    written with a sub-class such as ``1a``, a headword the parser may split
    on spaces, a line carrying several senses. Each shape is a property of the
    Hannan line, never of the implementation's output.
    """
    if " " in headword.strip():
        return "multiword_headword"
    if headword_kind == "noun":
        if noun_class and any(character.isalpha() for character in noun_class):
            return "noun_subclass"
        if plural_forms:
            return "noun_with_plural"
        return "noun_plain"
    if headword_kind == "verb_stem":
        if "&" in part_of_speech or part_of_speech.replace(" ", "") in {"vti", "vt&i"}:
            return "verb_ambitransitive"
        if part_of_speech.replace(" ", "").startswith("vi"):
            return "verb_intransitive"
        if part_of_speech.replace(" ", "").startswith("vt"):
            return "verb_transitive"
        return "verb_other"
    if headword_kind == "ideophone":
        return "ideophone"
    if SENSE_MARKER_RE.search(raw_text):
        return "multi_sense_other"
    return "other"


def source_headword_kind(raw_text: str) -> str:
    """Convenience wrapper returning only the word class the source attests."""
    return read_hannan_line(raw_text)["headword_kind"]
