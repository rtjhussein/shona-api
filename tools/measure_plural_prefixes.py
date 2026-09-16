"""Measure the noun-plural prefixes the published corpus records.

Evidence for `docs/morphology/noun-plural-plan-2026-09-16.md`. Hannan records a
plural as a prefix with a trailing hyphen (`pl: map-`) or, for irregular
plurals, as a complete form (`pl: moyo`). The plan's rule is that a
consonant-final prefix carries the stem's *underlying* initial consonant -- the
class 5 prefix has already changed that consonant in the singular -- so this
prints the observed (underlying, surface) initial pairs with counts, so each one
can be checked against the source rather than assumed.

Initials are read with the grapheme inventory, not by character: `mats-` ends in
the single grapheme `ts`, and reading the last character would report `s`.

Reads `db/shona.sqlite3` read-only.

Usage::

    python tools/measure_plural_prefixes.py
"""

from __future__ import annotations

import collections
import json
import sqlite3
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY_ROOT))

from shona_api.phonology import segment_graphemes  # noqa: E402

DEFAULT_DB_PATH = Path("db/shona.sqlite3")
SAMPLE_PER_PAIR = 2


def load_lemmas(connection: sqlite3.Connection) -> dict[str, tuple[str, str | None]]:
    """Published nouns keyed by hyphen-free lemma id.

    The unit stores a hyphenated UUID while the lemma's primary key is stored
    without hyphens; comparing them raw silently matches nothing.
    """
    lemmas: dict[str, tuple[str, str | None]] = {}
    rows = connection.execute(
        """
        SELECT l.id, l.headword, nc.class_number
        FROM lexicon_lemma l
        LEFT JOIN lexicon_nounclass nc ON nc.id = l.noun_class_id
        WHERE l.headword_kind = 'noun'
        """
    )
    for lemma_id, headword, class_number in rows:
        lemmas[str(lemma_id).replace("-", "").lower()] = (headword, class_number)
    return lemmas


def measure(db_path: Path = DEFAULT_DB_PATH) -> dict[str, object]:
    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        lemmas = load_lemmas(connection)
        shapes: collections.Counter[str] = collections.Counter()
        by_class: collections.Counter[str] = collections.Counter()
        pairs: collections.Counter[tuple[str, str]] = collections.Counter()
        samples: dict[tuple[str, str], list[str]] = collections.defaultdict(list)

        rows = connection.execute(
            """
            SELECT canonical_record_object_id, parser_output
            FROM extraction_extractionunit
            WHERE canonical_record_object_id != '' AND parser_output LIKE '%plural%'
            """
        )
        while True:
            batch = rows.fetchmany(2000)
            if not batch:
                break
            for canonical_id, parser_output in batch:
                key = (canonical_id or "").replace("-", "").strip().lower()
                entry = lemmas.get(key)
                if entry is None:
                    continue
                headword, class_number = entry
                data = json.loads(parser_output)
                noun = data.get("noun")
                if not isinstance(noun, dict):
                    continue
                forms = [
                    form
                    for form in (noun.get("plural_forms") or [])
                    if isinstance(form, str) and form.strip()
                ]
                if not forms or not headword:
                    continue

                prefix = forms[0].strip()
                if prefix.endswith("-"):
                    shapes["prefix (ends with -)"] += 1
                    by_class[str(class_number)] += 1
                    prefix_graphemes = segment_graphemes(prefix[:-1])
                    underlying = prefix_graphemes[-1] if prefix_graphemes else ""
                    headword_graphemes = segment_graphemes(headword)
                    initial = headword_graphemes[0] if headword_graphemes else ""
                    pairs[(underlying, initial)] += 1
                    if len(samples[(underlying, initial)]) < SAMPLE_PER_PAIR:
                        samples[(underlying, initial)].append(
                            f"{headword} ({class_number}) pl:{prefix}"
                        )
                elif "-" in prefix:
                    shapes["prefix with internal hyphen"] += 1
                else:
                    shapes["full form (not a prefix)"] += 1

        return {
            "lemmas": len(lemmas),
            "shapes": dict(shapes),
            "by_class": dict(by_class),
            "pairs": [
                {
                    "underlying": underlying,
                    "surface_initial": initial,
                    "count": count,
                    "samples": samples[(underlying, initial)],
                }
                for (underlying, initial), count in pairs.most_common()
            ],
        }
    finally:
        connection.close()


def main() -> int:
    result = measure()
    print(f"published nouns with a class: {result['lemmas']:,}")
    print()
    for shape, count in sorted(result["shapes"].items(), key=lambda item: -item[1]):
        print(f"  {count:>6}  {shape}")
    print()
    print("classes carrying a trailing-hyphen prefix:")
    for class_number, count in sorted(result["by_class"].items(), key=lambda item: -item[1]):
        print(f"  class {class_number:<6} {count:>5}")
    print()
    print("underlying consonant (prefix) vs surface initial (headword):")
    for pair in result["pairs"]:
        example = pair["samples"][0]
        print(
            f"  {pair['count']:>5}  {pair['underlying']!r} -> "
            f"{pair['surface_initial']!r:<7} e.g. {example}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
