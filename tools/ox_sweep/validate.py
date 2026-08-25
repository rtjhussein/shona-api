"""Validate an ox-sweep Hannan JSONL chunk (multi-page) without DB writes.

Usage: python local_batches/ox-sweep/validate.py <file.jsonl> <book_start> <book_end>

Checks per line: valid JSON; required parser_output fields; project normalizer +
publishable validator; tone rules (H/L runs, space-separated groups allowed for
multi-word headwords; null top-level tone_pattern when multiple dialect-scoped
records); locator pages within range; entry sequence contiguous per page from
entry_001; no duplicate locators.
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import django

django.setup()

from shona_api.extraction.gpt_jsonl import (  # noqa: E402
    normalize_gpt_parser_output,
    validate_publishable_parser_output,
)

REQUIRED = {
    "schema_version",
    "headword",
    "headword_kind",
    "part_of_speech",
    "dialects",
    "comparative_bantu_marker",
    "tone_pattern",
    "tone_records",
    "noun",
    "senses",
    "idiomatic_expressions",
    "derived_forms",
    "raw_entry_text",
    "parse_metadata",
    "normalized_headword",
}

TONE_RE = re.compile(r"[HL]+( [HL]+)*")


def main(path: str, book_start: int, book_end: int) -> int:
    failures = 0
    seq_by_page = defaultdict(list)
    locators = []
    lines = [
        ln
        for ln in Path(path).read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    for i, line in enumerate(lines, 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            print(f"line {i}: INVALID JSON: {exc}")
            failures += 1
            continue

        po = row.get("parser_output") or {}
        missing = REQUIRED - set(po)
        if missing:
            print(f"line {i}: missing parser_output fields: {sorted(missing)}")
            failures += 1

        normalized = normalize_gpt_parser_output(
            po, raw_text=row.get("raw_text", "")
        )
        if isinstance(normalized, dict) and normalized.get("errors"):
            print(f"line {i}: normalizer errors: {normalized['errors']}")
            failures += 1

        for msg in validate_publishable_parser_output(po):
            print(f"line {i}: validator: {msg}")
            failures += 1

        tp = po.get("tone_pattern")
        records = po.get("tone_records") or []
        if tp is not None and not TONE_RE.fullmatch(str(tp)):
            print(f"line {i}: tone_pattern {tp!r} not an H/L run")
            failures += 1
        if len(records) > 1 and tp is not None:
            print(
                f"line {i}: {len(records)} tone_records but tone_pattern="
                f"{tp!r}; must be null for dialect-scoped brackets"
            )
            failures += 1
        for rec in records:
            if not TONE_RE.fullmatch(str(rec.get("pattern", ""))):
                print(f"line {i}: tone record pattern {rec.get('pattern')!r} invalid")
                failures += 1

        loc = str(row.get("source_locator", ""))
        locators.append(loc)
        m = re.match(r"hannan:page_(\d+):entry_(\d+):", loc)
        if not m:
            print(f"line {i}: bad locator {loc!r}")
            failures += 1
            continue
        page, seq = int(m.group(1)), int(m.group(2))
        if not book_start <= page <= book_end:
            print(f"line {i}: locator page {page} outside {book_start}..{book_end}")
            failures += 1
        seq_by_page[page].append(seq)

    for page, seqs in seq_by_page.items():
        if seqs != list(range(1, len(seqs) + 1)):
            print(f"page {page}: entry sequence not contiguous from 001: {seqs}")
            failures += 1

    if len(locators) != len(set(locators)):
        print("duplicate locators present")
        failures += 1

    print(f"{path}: {len(lines)} lines, {failures} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3])))
