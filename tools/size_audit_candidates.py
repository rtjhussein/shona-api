"""Size two defect classes the field audit found, without reading the scan.

The audit found (a) multi-word ideophones losing tone and (b) headwords whose
consonant was read as a neighbour. Before repairing either, the size has to be
known -- four records or four hundred changes whether this is a fix or a
project. Both can be screened from data already held; the scan then verifies a
sample rather than being read 40,000 times.

Screen 1 -- ideophone tone. A multi-word ideophone's bracket carries one group
per word (`kwakwara kwakwara [LLL LLL]`, stored as `LLL LLL`). A stored pattern
with fewer groups than the headword has words, or with no space at all and a
length that is not divisible by the word count, is a candidate.

Screen 2 -- headword consonants. The dictionary text is a second reading of the
same pages. Where it holds a spelling one character away from the published one,
and the differing characters are a pair the audit has already seen confused
(b/h, v/w, d/dh), the published spelling is a candidate.

Reads `db/shona.sqlite3` read-only and `local_source_cache/hannan_dictionary.txt`.
"""

from __future__ import annotations

import collections
import re
import sqlite3
import sys
from pathlib import Path

# This file lives in tools/, so the repository root is one level up. Resolving
# it to `parent` made every repository path below miss, and the text index came
# back empty -- which the screen then reported as zero defects.
REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY_ROOT))

from shona_api.parsers.dictionary_text import normalise_homoglyphs  # noqa: E402

# Pairs the audit has actually observed confused: `b` read as `h` (`-kwamba` ->
# `-kwamha`), `v` as `w` (`nzwaivhi` -> `nzwaiwhi`), `zv` dropped or split
# (`nzvinzvi-i` -> `nzvinzi-i`), and the depressor series from the plural work.
CONFUSABLE_PAIRS = (
    ("b", "h"),
    ("v", "w"),
    ("d", "dh"),
    ("z", "zv"),
    ("s", "sh"),
    ("t", "th"),
    ("k", "kh"),
)

# Not anchored to the line start: the extraction holds two printed columns per
# line, so the second column's headword is mid-line. An earlier version required
# a line start, indexed only the first column, and then reported zero candidates
# for divergences that are real.
HEADWORD_RE = re.compile(r"(?<![A-Za-z'\u2019-])(?P<head>[A-Za-z'\u2019][^\s,\[]*)\s*\[")


def screen_ideophones(cursor) -> tuple[int, list[tuple[str, int, str]]]:
    """Multi-word ideophones whose stored tone cannot cover every word."""
    candidates = []
    total = 0
    for headword, pattern in cursor.execute(
        """select l.headword, t.pattern
           from lexicon_lemma l
           join lexicon_tonerecord t on t.lemma_id = l.id
           where l.headword_kind = 'ideophone' and l.headword like '% %'"""
    ):
        total += 1
        words = [word for word in (headword or "").split() if word]
        groups = [group for group in (pattern or "").split() if group]
        if len(words) < 2:
            continue
        joined = "".join(groups)
        if len(groups) < len(words) and len(joined) % len(words) != 0:
            candidates.append((headword, len(words), pattern))
        elif len(groups) < len(words) and len(joined) < len(words):
            candidates.append((headword, len(words), pattern))
    return total, candidates


def text_headwords() -> dict[tuple[int, str], set[str]]:
    """Dictionary-text headwords bucketed by length and first two characters."""
    path = REPOSITORY_ROOT / "local_source_cache" / "hannan_dictionary.txt"
    buckets: dict[tuple[int, str], set[str]] = collections.defaultdict(set)
    try:
        text = normalise_homoglyphs(path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return buckets
    for match in HEADWORD_RE.finditer(text):
        head = (match.group("head") or match.group("head2") or "").lstrip("\u2020*").lstrip("-")
        head = head.casefold()
        if len(head) >= 4:
            buckets[(len(head), head[:2])].add(head)
    return buckets


def one_confusable_difference(left: str, right: str) -> tuple[str, str] | None:
    """The differing characters when two spellings differ in exactly one of them.

    Comparing position by position is the point: an earlier version replaced the
    first occurrence of a character, which silently missed a difference later in
    the word (`nzwaivhi` / `nzwaiwhi` differ at the fifth character) and reported
    zero candidates for a defect that is real.
    """
    if len(left) != len(right):
        return None
    differing = [
        (a, b) for a, b in zip(left, right) if a != b
    ]
    if len(differing) != 1:
        return None
    a, b = differing[0]
    for first, second in CONFUSABLE_PAIRS:
        if (a, b) in ((first, second), (second, first)):
            return (a, b)
    return None


def screen_headwords(cursor, buckets) -> tuple[int, int, list[tuple[str, str]]]:
    """Published headwords one confusable character away from the text's spelling."""
    checked = 0
    onepair = 0
    candidates = []
    for (headword,) in cursor.execute(
        "select headword from lexicon_lemma where review_state='published'"
    ):
        head = (headword or "").strip()
        if len(head) < 4 or " " in head:
            continue
        checked += 1
        key_word = head.lstrip("-").casefold()
        near = buckets.get((len(key_word), key_word[:2]))
        if not near:
            continue
        for candidate in near:
            difference = one_confusable_difference(key_word, candidate)
            if difference:
                onepair += 1
                if len(candidates) < 40:
                    candidates.append((head, candidate))
                break
    return checked, onepair, candidates


def main() -> int:
    connection = sqlite3.connect("file:db/shona.sqlite3?mode=ro", uri=True)
    cursor = connection.cursor()

    total, ideophones = screen_ideophones(cursor)
    print(f"multi-word ideophones: {total:,}")
    print(f"  tone cannot cover every word: {len(ideophones):,}")
    for headword, words, pattern in ideophones[:10]:
        print(f"    {headword!r} ({words} words) -> pattern {pattern!r}")

    buckets = text_headwords()
    checked, onepair, samples = screen_headwords(cursor, buckets)
    print()
    print(f"published headwords screened against the text: {checked:,}")
    print(f"  one confusable character from the text's spelling: {onepair:,}")
    for published, text_form in samples[:10]:
        print(f"    published {published!r}  text {text_form!r}")
    connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
