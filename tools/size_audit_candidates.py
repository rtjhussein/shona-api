"""Size three defect classes the field audit found, without reading the scan.

The audit found (a) multi-word ideophones losing tone, (b) headwords whose
consonant was read as a neighbour, and (c) published spellings carrying more
than one record. Before repairing any of them the size has to be known -- four
records or four hundred changes whether this is a fix or a project. All three
can be screened from data already held; the scan then verifies a sample rather
than being read 40,000 times.

Screen 1 -- ideophone tone. A multi-word ideophone's bracket carries one group
per word (`kwakwara kwakwara [LLL LLL]`, stored as `LLL LLL`). A stored pattern
with fewer groups than the headword has words, or with no space at all and a
length that is not divisible by the word count, is a candidate.

Screen 2 -- headword consonants. The dictionary text is a second reading of the
same pages. Where it holds a spelling one character away from the published one,
and the differing characters are a pair the audit has already seen confused
(b/h, v/w, d/dh), the published spelling is a candidate.

Screen 3 -- spellings with more than one record. A dictionary holds homographs,
so two records for one spelling are not by themselves a defect; the split that
matters is whether they came from one printed entry or from several. The test is
the extraction unit's locator, and the whole locator string cannot carry it --
see `locator_entry` for why that screen returns a guaranteed zero.

Reads `db/shona.sqlite3` read-only and `local_source_cache/hannan_dictionary.txt`.
"""

from __future__ import annotations

import collections
import os
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
    published = set()
    heads = []
    for (headword,) in cursor.execute(
        "select headword from lexicon_lemma where review_state='published'"
    ):
        head = (headword or "").strip()
        published.add(head.lstrip("-").casefold())
        if len(head) < 4 or " " in head:
            continue
        heads.append(head)

    # A candidate whose text spelling is ALREADY a published headword is not a
    # misread -- the correct spelling is in the corpus beside it, so the record is
    # a duplicate and renaming it would collide. Every headword defect found so
    # far by reading the page sorted this way: `n'a n'a`, `dzimbahwe` and `nzwa`
    # each had their corrected spelling already published, while `bve bve`,
    # `shwa shwaba shwaba` and `shakahuni` did not and were renames. The two
    # classes need different work, so the screen separates them rather than
    # sending a reviewer to the page to discover which one it is.
    for head in heads:
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
    return checked, onepair, candidates, published, heads


# Every unit locator has the shape `<source>:page_<page>:entry_<n>:<slug>`. The
# slug is the headword the parser read off that entry, sometimes with a numeric
# suffix the extraction added when the same slug had already occurred, and it
# moves whenever the headword does; the entry number, not the slug, is what names
# the printed entry. All 40,572 units carry distinct whole locators, so equal
# whole strings would mean one headword read off one entry twice -- and the
# screen would still return zero for the documented `bimha`/`bimba` collision,
# where two spellings cite one entry and differ in the slug. The entry key is the
# locator without its slug.
ENTRY_LOCATOR_RE = re.compile(r"^(?P<entry>[^:]+:page_[^:]+:entry_[^:]+):")

# The screen's positive control is `hannan:page_021:entry_007`, cited by both
# `bimha` and `bimba`: without it a zero from either test would be as likely to
# mean a broken join as a clean corpus.
KNOWN_COLLISION = "hannan:page_021:entry_007"


def locator_entry(locator: str | None) -> str | None:
    """A locator's printed-entry key: everything before the headword slug."""
    match = ENTRY_LOCATOR_RE.match(locator or "")
    return match.group("entry") if match else None


def unit_index(cursor) -> dict[str, tuple[str, str]]:
    """Locator and raw text by de-dashed, casefolded canonical record object id.

    That key is the join: the unit stores the lemma's id dashed and lowercase
    where the lemma holds it undashed, so comparing the raw values matches only
    lexicographic accidents. Units with an empty object id are left out -- they
    belong to no lemma and would otherwise all collide on the empty key.
    """
    units: dict[str, tuple[str, str]] = {}
    for object_id, locator, raw_text in cursor.execute(
        "select canonical_record_object_id, source_location_reference, raw_text "
        "from extraction_extractionunit"
    ):
        key = (object_id or "").replace("-", "").casefold()
        if key:
            units[key] = (locator or "", raw_text or "")
    return units


def unit_locator_counts(cursor) -> tuple[int, int, int]:
    """Units, distinct whole locators among them, units holding no object id.

    The third number is the join's other edge: a unit with no object id points at
    no lemma, so no lemma can reach it however the two tables are keyed.
    """
    locators: set[str] = set()
    total = 0
    orphan = 0
    for object_id, locator in cursor.execute(
        "select canonical_record_object_id, source_location_reference "
        "from extraction_extractionunit"
    ):
        total += 1
        locators.add(locator or "")
        if not (object_id or "").replace("-", "").casefold():
            orphan += 1
    return total, len(locators), orphan


# A looser comparison runs beside the strict one so the strict count cannot be a
# near-miss artefact: truncating at 60 characters also flags a line re-read with
# a differing tail. Both flag the same single spelling in this corpus.
RAW_TEXT_PREFIX_LENGTH = 60


def raw_text_key(text: str | None, limit: int | None = None) -> str:
    """A printed line's identity, ignoring case and punctuation.

    With `limit` the key is truncated, which also catches a re-extraction that
    diverges later in the line; without it the whole line must match.
    """
    normalised = re.sub(r"[^a-z0-9]", "", (text or "").casefold())
    return normalised if limit is None else normalised[:limit]


def screen_duplicates(cursor, units) -> dict:
    """Published spellings carrying more than one record, split by cause.

    Three units are counted separately and the report never mixes them: a
    SPELLING is one distinct stored headword, a ROW is one published
    `lexicon_lemma`, an ENTRY is one printed entry however many rows cite it.
    Groups are counted, not spellings, so a spelling appearing three times is one
    group and is classified once -- where one of its pairs shares an entry and
    another does not, the group is counted under both signals and named here.
    """
    class_number = dict(cursor.execute("select id, class_number from lexicon_nounclass"))

    spellings: dict[str, list[tuple[str, str | None, str | None]]] = collections.defaultdict(list)
    matched = 0
    for lemma_id, headword, pos, noun_class in cursor.execute(
        "select id, headword, part_of_speech_code, noun_class_id "
        "from lexicon_lemma where review_state='published'"
    ):
        if lemma_id.replace("-", "").casefold() in units:
            matched += 1
        spellings[(headword or "").strip()].append((lemma_id, pos, noun_class))
    duplicated = {head: rows for head, rows in spellings.items() if len(rows) > 1}

    def row_locator(lemma_id: str) -> str | None:
        entry = units.get(lemma_id.replace("-", "").casefold())
        return entry[0] if entry and entry[0] else None

    def repeats(values) -> bool:
        return any(count > 1 for count in collections.Counter(value for value in values if value).values())

    def shares_locator(rows) -> bool:
        return repeats(row_locator(lemma_id) for lemma_id, _, _ in rows)

    def shares_entry(rows) -> bool:
        return repeats(locator_entry(row_locator(lemma_id)) for lemma_id, _, _ in rows)

    def shares_text(rows, limit: int | None = None) -> bool:
        return repeats(
            raw_text_key(units[lemma_id.replace("-", "").casefold()][1], limit)
            for lemma_id, _, _ in rows
            if lemma_id.replace("-", "").casefold() in units
        )

    def traits(rows) -> set[tuple[str | None, str | None]]:
        return {(pos, noun_class) for _, pos, noun_class in rows}

    shared_locator = [head for head, rows in duplicated.items() if shares_locator(rows)]
    shared_entry = [head for head, rows in duplicated.items() if shares_entry(rows)]
    unshared = [head for head, rows in duplicated.items() if not shares_entry(rows)]
    differ = [head for head, rows in duplicated.items() if len(traits(rows)) > 1]
    agree = [head for head, rows in duplicated.items() if len(traits(rows)) == 1]
    # More rows than distinct traits means some pair inside the group agrees
    # while another does not, so the group answers to both classes and is counted
    # under both rather than rounded into one of them.
    mixed = [
        head
        for head, rows in duplicated.items()
        if len(traits(rows)) > 1 and len(traits(rows)) < len(rows)
    ]
    same_raw = [head for head, rows in duplicated.items() if shares_text(rows)]
    same_raw_prefix = [
        head for head, rows in duplicated.items() if shares_text(rows, RAW_TEXT_PREFIX_LENGTH)
    ]
    rows_without_unit = [
        head
        for head, rows in duplicated.items()
        if any(row_locator(lemma_id) is None for lemma_id, _, _ in rows)
    ]

    # `Spelling` could mean the stored string or the string casefolded, and the
    # two disagree: 17 further groups appear when `Chikara` and `chikara` count as
    # one spelling. Both are measured so the split cannot be an artefact of the
    # definition chosen, and the reported one is the stored string.
    casefolded: dict[str, list[tuple[str, str | None, str | None]]] = collections.defaultdict(list)
    for head, rows in spellings.items():
        casefolded[head.casefold()].extend(rows)
    folded = {head: rows for head, rows in casefolded.items() if len(rows) > 1}

    # Printed entries claimed by more than one unit. That is the defective shape
    # the locator test is built to find, and it is not confined to spellings
    # published twice: `bimha` and `bimba` are two spellings citing one entry, so
    # a screen that only looks inside duplicate-spelling groups cannot see it.
    by_entry: dict[str, list[str]] = collections.defaultdict(list)
    for key, (locator, _) in units.items():
        entry = locator_entry(locator)
        if entry:
            by_entry[entry].append(key)
    collisions = {entry: keys for entry, keys in by_entry.items() if len(keys) > 1}

    missing_unit = [
        (headword, review_state)
        for lemma_id, headword, review_state in cursor.execute(
            "select id, headword, review_state from lexicon_lemma"
        )
        if lemma_id.replace("-", "").casefold() not in units
    ]

    def examples(heads: list[str]) -> list[tuple[str, list[tuple[str, str, str]]]]:
        """Headword with one (locator, part of speech, noun class) row per record.

        Five groups, largest first: a group with eight rows says more about the
        screen than the first five alphabetically would.
        """
        chosen = sorted(heads, key=lambda head: (-len(duplicated[head]), head))[:5]
        return [
            (
                head,
                [
                    (
                        row_locator(lemma_id) or "no extraction unit",
                        pos or "unknown",
                        class_number.get(noun_class, "") if noun_class else "none",
                    )
                    for lemma_id, pos, noun_class in duplicated[head]
                ],
            )
            for head in chosen
        ]

    return {
        "spellings": len(duplicated),
        "extra_rows": sum(len(rows) - 1 for rows in duplicated.values()),
        "rows": sum(len(rows) for rows in duplicated.values()),
        "sizes": collections.Counter(len(rows) for rows in duplicated.values()),
        "shared_locator": sorted(shared_locator),
        "shared_entry": sorted(shared_entry),
        "unshared": sorted(unshared),
        "differ": sorted(differ),
        "agree": sorted(agree),
        "mixed": sorted(mixed),
        "same_raw": sorted(same_raw),
        "same_raw_prefix": sorted(same_raw_prefix),
        "casefold": {
            "spellings": len(folded),
            "extra_rows": sum(len(rows) - 1 for rows in folded.values()),
            "shared_entry": sum(1 for rows in folded.values() if shares_entry(rows)),
            "differ": sum(1 for rows in folded.values() if len(traits(rows)) > 1),
        },
        "rows_without_unit": sorted(set(rows_without_unit)),
        "missing_unit": sorted(missing_unit),
        "published_rows": sum(len(rows) for rows in spellings.values()),
        "matched": matched,
        "collisions": {
            entry: [units[key][0] for key in sorted(keys)] for entry, keys in sorted(collisions.items())
        },
        "control_found": KNOWN_COLLISION in collisions,
        "examples": {
            "shared_entry": examples(shared_entry),
            "differ": examples(differ),
            "agree": examples(agree),
            "same_raw": examples(same_raw),
        },
    }


def main() -> int:
    connection = sqlite3.connect("file:db/shona.sqlite3?mode=ro", uri=True)
    cursor = connection.cursor()

    total, ideophones = screen_ideophones(cursor)
    print(f"multi-word ideophones: {total:,}")
    print(f"  tone cannot cover every word: {len(ideophones):,}")
    for headword, words, pattern in ideophones[:10]:
        print(f"    {headword!r} ({words} words) -> pattern {pattern!r}")

    buckets = text_headwords()
    checked, onepair, samples, published, heads = screen_headwords(cursor, buckets)
    print()
    print(f"published headwords screened against the text: {checked:,}")
    print(f"  one confusable character from the text's spelling: {onepair:,}")

    duplicates = 0
    misreads = 0
    misread_pairs = []
    for head in heads:
        key_word = head.lstrip("-").casefold()
        near = buckets.get((len(key_word), key_word[:2]))
        for candidate in near or ():
            if one_confusable_difference(key_word, candidate):
                if candidate in published:
                    duplicates += 1
                else:
                    misreads += 1
                    misread_pairs.append((head, candidate))
                break
    # Both units are printed because they differ, and confusing them costs an
    # afternoon: the counts above are INSTANCES, one per published row, while the
    # queue holds distinct (headword, spelling) PAIRS. They diverge wherever a
    # spelling is published more than once -- and 2,915 published spellings are,
    # so 72 instances of the misread class are 60 distinct pairs.
    print(f"    whose text spelling is already published (duplicate class): {duplicates:,}")
    print(f"    whose text spelling is absent (misread class):              {misreads:,}")
    print(f"      of which distinct spellings:                             {len(set(misread_pairs)):,}")
    for published_head, text_form in samples[:10]:
        print(f"    published {published_head!r}  text {text_form!r}")

    units = unit_index(cursor)
    multi = screen_duplicates(cursor, units)
    unit_total, locator_total, orphan_units = unit_locator_counts(cursor)
    print()
    print("Screen 3 -- spellings carrying more than one published record")
    print(f"  spellings (one distinct stored headword each): {multi['spellings']:,}")
    print(f"  extra rows beyond the first row of each:       {multi['extra_rows']:,}")
    print(f"  rows inside those spellings:                   {multi['rows']:,}")
    print(
        "  group sizes: "
        + ", ".join(f"{size} rows x {count:,}" for size, count in sorted(multi["sizes"].items()))
    )
    print(
        f"  (grouping case-insensitively instead: {multi['casefold']['spellings']:,} spellings, "
        f"{multi['casefold']['extra_rows']:,} extra rows, "
        f"{multi['casefold']['shared_entry']:,} sharing a printed entry, "
        f"{multi['casefold']['differ']:,} differing in part of speech or noun class)"
    )
    print()
    print("  which of those spellings have rows from one printed entry")
    print(f"    entry shared, i.e. locators agreeing before the headword slug: {len(multi['shared_entry']):,} spellings")
    print(f"    whole locator strings identical:                               {len(multi['shared_locator']):,} spellings")
    print(f"    no shared entry -- separate printed entries:                   {len(multi['unshared']):,} spellings")
    print(f"    ({unit_total:,} extraction units carry {locator_total:,} distinct whole locators,")
    print("     so equal whole strings can only mean one headword read off one entry and")
    print("     the test is structurally zero here; the slug-free test is the one that")
    print("     bites, and the entry list below is its positive control)")
    print()
    print("  the no-shared-entry group, by what the rows say about themselves")
    print(f"    rows differ in part of speech or noun class: {len(multi['differ']):,} spellings")
    print(f"      of which also hold a pair agreeing on both: {len(multi['mixed']):,} spellings")
    print(f"    rows agree on both:                          {len(multi['agree']):,} spellings")
    print()
    print(
        "  spellings whose rows hold byte-identical extraction text under "
        f"different locators: {len(multi['same_raw']):,}"
    )
    print(f"    (a looser first-{RAW_TEXT_PREFIX_LENGTH}-characters comparison flags {len(multi['same_raw_prefix']):,}; "
          "the strict count is not a near-miss artefact)")
    print(f"    -> the entry test alone finds {len(multi['shared_entry']):,} duplicate; a printed line re-extracted")
    print("       under a fresh entry number is invisible to it, which is why the text test")
    print("       runs beside it. A row it does not flag is UNPROVEN, not proved distinct.")

    def show(label: str, name: str) -> None:
        heads = multi[name]
        print(f"    {label}: {len(heads):,} spellings, 5 largest shown")
        if not multi["examples"][name]:
            print("      (none -- the group is empty)")
        for head, rows in multi["examples"][name]:
            print(f"      {head!r}")
            for locator, pos, noun_class in rows:
                print(f"        {locator}  pos={pos} class={noun_class}")

    show("sharing a printed entry", "shared_entry")
    show("rows differing in part of speech or noun class", "differ")
    show("rows agreeing on both", "agree")
    show("rows with identical extraction text", "same_raw")

    print()
    print(f"  printed entries cited by more than one extraction unit: {len(multi['collisions']):,}")
    print(f"    positive control {KNOWN_COLLISION!r} found: {multi['control_found']}")
    for entry, locators in multi["collisions"].items():
        print(f"    {entry}")
        for locator in locators:
            print(f"      {locator}")
    print()
    print(f"  lemmas with no extraction unit at all: {len(multi['missing_unit']):,}")
    for headword, review_state in multi["missing_unit"]:
        print(f"    {headword!r} ({review_state})")
    print(f"    spellings in the groups above left partly unclassified by this: {len(multi['rows_without_unit']):,}")
    print(f"  extraction units naming no lemma, the join's other edge: {orphan_units:,}")
    print(
        f"  reach: {multi['matched']:,} of {multi['published_rows']:,} published lemmas have a locator; "
        f"{unit_total:,} units exist for {locator_total:,} distinct locators"
    )

    queue = os.environ.get("AUDIT_QUEUE")
    if queue:
        # Pages come from the published record's own extraction unit: the text
        # spelling lives in the flat cache file and carries no locator, but the
        # record derived from that entry does, and it is the same page.
        pages = {}
        for object_id, locator in cursor.execute(
            "select canonical_record_object_id, source_location_reference "
            "from extraction_extractionunit where canonical_record_object_id is not null"
        ):
            if object_id:
                pages.setdefault(str(object_id).replace("-", "").casefold(), locator)
        by_headword = {}
        for lemma_id, headword in cursor.execute(
            "select id, headword from lexicon_lemma where review_state='published'"
        ):
            by_headword[(headword or "").strip()] = pages.get(
                str(lemma_id).replace("-", "").casefold(), "locate_by_search"
            )
        with open(queue, "w", encoding="utf-8") as handle:
            handle.write("published_headword\ttext_spelling\tsource_locator\n")
            for head, text_form in sorted(set(misread_pairs)):
                handle.write(f"{head}\t{text_form}\t{by_headword.get(head, 'locate_by_search')}\n")
        print(f"    queue written: {queue} ({len(set(misread_pairs)):,} rows)")
    connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
