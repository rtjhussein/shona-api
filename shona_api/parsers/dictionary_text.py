"""Read the plural each headword is reported to carry, from the dictionary text.

`local_source_cache/hannan_dictionary.txt` is a text extraction of the Hannan
scan. Where an extraction unit misread the page, this is the better reading:
the scan shows `pl: mad-` for `dikanwa` while the vision pipeline recorded
`madh-`.

Two limits are built in rather than papered over:

- The text is a linear dump with no page or entry locators, so it can only be
  keyed by headword. Hannan records homographs that legitimately carry different
  plurals -- `gwama` appears three times on one page with `magw-`, `makw-` and
  `magw-` -- so a headword with more than one reported plural is **ambiguous**
  and yields nothing. Only a headword the text reports exactly one plural for
  can be used to correct a unit.
- The extraction contains Cyrillic homoglyphs (1,313 characters: `а` U+0430,
  `т` U+0442, `М` U+041C and others), so a value is normalised before use or a
  published form would carry them.

The file is a local cache and is gitignored, so an absent file is not an error:
there is simply nothing to correct from.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

DEFAULT_PATH = Path("local_source_cache/hannan_dictionary.txt")

# Cyrillic lookalikes seen in the extraction, and what they stand for.
HOMOGLYPHS = str.maketrans(
    {
        "\u0430": "a",  # а
        "\u0435": "e",  # е
        "\u043e": "o",  # о
        "\u0440": "p",  # р
        "\u0441": "c",  # с
        "\u0443": "u",  # у
        "\u0445": "x",  # х
        "\u0456": "i",  # і
        "\u0410": "A",
        "\u0412": "B",
        "\u0415": "E",
        "\u041a": "K",
        "\u041c": "M",
        "\u041d": "H",
        "\u041e": "O",
        "\u0420": "P",
        "\u0421": "C",
        "\u0422": "T",
        "\u0423": "U",
        "\u0425": "X",
        "\u043a": "k",
        "\u043c": "m",
        "\u043d": "h",
        "\u0442": "t",
    }
)

PLURAL_RE = re.compile(
    r"(?P<headword>[A-Za-z'\u2019][^\s,]*)\s*\[[^\]]*\]\s*[A-Za-z()]*\s*"
    r"(?:n\s*\d+[a-z]?[^,]{0,40}?,\s*)?pl:\s*(?P<plural>[^\s,.;]+)",
)


def normalise_homoglyphs(value: str) -> str:
    """Replace the Cyrillic lookalikes the extraction contains with Latin ones."""
    return value.translate(HOMOGLYPHS)


def read_plural_index(path: Path = DEFAULT_PATH) -> dict[str, set[str]]:
    """Headword -> the set of plurals the text reports for it.

    A headword with more than one entry carries more than one value here, which
    is exactly why consumers must treat a multi-valued entry as ambiguous.
    """
    index: dict[str, set[str]] = defaultdict(set)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return index
    for line in text.splitlines():
        for match in PLURAL_RE.finditer(normalise_homoglyphs(line)):
            headword = match.group("headword").lstrip("\u2020*").lstrip("-").casefold()
            plural = match.group("plural").strip()
            if headword and plural:
                index[headword].add(plural)
    return index


def unambiguous_plural(index: dict[str, set[str]], headword: str) -> str | None:
    """The single plural the text reports for ``headword``, or ``None``.

    ``None`` covers both "the text does not mention it" and "the text reports
    several, because it is a homograph" -- a consumer must not pick between
    them, since which entry a plural belongs to is not recoverable from a text
    with no entry locators.
    """
    values = index.get(headword.lstrip("\u2020*").lstrip("-").casefold())
    if not values or len(values) != 1:
        return None
    return next(iter(values))
