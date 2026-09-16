"""Freeze a source-backed lexical QA corpus from the published Hannan units.

Usage::

    python tools/build_lexical_qa_corpus.py --out evaluation/lexical_qa/v1
    python tools/build_lexical_qa_corpus.py --check-only

Every extraction unit stores the verbatim Hannan line it came from
(``raw_text``) next to the parser output that produced its published record.
That pairing turns the corpus itself into a checkable contract: an independent
reader (``tools.lexical_qa``, which imports nothing from ``shona_api``) derives
what the source line attests, and the evaluator compares it with what was
published.

Sampling is deterministic: units are ordered by source locator and a fixed
number is drawn per (parser, source word class) stratum, so a rebuild from the
same database reproduces the same corpus and the hash stays stable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sqlite3
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lexical_qa import HannanLineError, read_hannan_line  # noqa: E402

CORPUS_VERSION = "lexical-qa-v1"
SAMPLE_SEED = 20260916
SAMPLES_PER_STRATUM = 18
DEFAULT_DB_PATH = Path("db/shona.sqlite3")


def read_units(db_path: Path) -> list[dict[str, Any]]:
    """Read the published units, read-only, with the source line and parser."""
    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            """
            SELECT source_location_reference, parser_name, raw_text, parser_output
            FROM extraction_extractionunit
            WHERE canonical_record_object_id IS NOT NULL
              AND canonical_record_object_id != ''
            ORDER BY source_location_reference
            """
        ).fetchall()
    finally:
        connection.close()

    units: list[dict[str, Any]] = []
    for locator, parser_name, raw_text, parser_output in rows:
        units.append(
            {
                "locator": locator,
                "parser_name": parser_name,
                "raw_text": raw_text,
                "parser_output": json.loads(parser_output) if parser_output else {},
            }
        )
    return units


def build_corpus(db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    units = read_units(db_path)

    strata: dict[tuple[str, str], list[dict[str, Any]]] = {}
    unparseable = 0
    for unit in units:
        try:
            source = read_hannan_line(unit["raw_text"])
        except HannanLineError:
            unparseable += 1
            continue
        # "other" lines (notes, letters, particles) carry no word class the
        # reader can judge, so they are not scored; they are counted instead.
        if source["headword_kind"] == "other":
            continue
        # Stratify by the shape of the *source line*, not by anything the
        # implementation produced, so a uniform draw cannot quietly miss the
        # entries where parsing is hard.
        key = (unit["parser_name"] or "", source["source_shape"])
        strata.setdefault(key, []).append({"unit": unit, "source": source})

    rng = random.Random(SAMPLE_SEED)
    cases: list[dict[str, Any]] = []
    for (parser_name, word_class), members in sorted(strata.items()):
        drawn = sorted(
            rng.sample(members, min(SAMPLES_PER_STRATUM, len(members))),
            key=lambda member: member["unit"]["locator"],
        )
        for member in drawn:
            unit = member["unit"]
            source = member["source"]
            parser_output = unit["parser_output"]
            noun_payload = parser_output.get("noun")
            parser_classes = (
                noun_payload.get("classes") if isinstance(noun_payload, dict) else None
            )
            cases.append(
                {
                    "case_id": unit["locator"],
                    "parser_name": parser_name,
                    "raw_entry_text": unit["raw_text"],
                    "source": {
                        "headword": source["headword"],
                        "headword_kind": source["headword_kind"],
                        "noun_class": source["noun_class"],
                        "tone_patterns": source["tone_patterns"],
                        "plural_forms": source["plural_forms"],
                        "source_shape": source["source_shape"],
                    },
                    "parser_claimed": {
                        "headword_kind": parser_output.get("headword_kind"),
                        "classes": parser_classes,
                        "tone_patterns": [
                            record.get("pattern")
                            for record in (parser_output.get("tone_records") or [])
                            if isinstance(record, dict)
                        ],
                    },
                }
            )

    cases.sort(key=lambda case: case["case_id"])
    corpus = {
        "version": CORPUS_VERSION,
        "sample_seed": SAMPLE_SEED,
        "samples_per_stratum": SAMPLES_PER_STRATUM,
        "source_units": len(units),
        "units_not_scored": unparseable,
        "strata": [
            {"parser_name": parser_name, "source_shape": word_class, "size": len(members)}
            for (parser_name, word_class), members in sorted(strata.items())
        ],
        "cases": cases,
    }
    corpus["hash"] = corpus_hash(corpus)
    return corpus


def corpus_hash(corpus: dict[str, Any]) -> str:
    """SHA-256 over the scored content, excluding the hash field itself."""
    payload = {
        "version": corpus["version"],
        "cases": corpus["cases"],
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_hash(corpus: dict[str, Any]) -> None:
    expected = corpus_hash(corpus)
    if corpus.get("hash") != expected:
        raise SystemExit(
            f"Corpus hash mismatch: stored {corpus.get('hash')!r}, recomputed {expected!r}"
        )


def write_corpus(corpus: dict[str, Any], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "corpus.json"
    path.write_text(json.dumps(corpus, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("evaluation/lexical_qa/v1"))
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Rebuild and compare with the frozen corpus without writing.",
    )
    args = parser.parse_args()

    corpus = build_corpus(args.db)
    if args.check_only:
        frozen_path = args.out / "corpus.json"
        frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
        verify_hash(frozen)
        same = corpus_hash(frozen) == corpus_hash(corpus)
        print(
            f"frozen={frozen['hash']} rebuilt={corpus['hash']} identical={same} "
            f"(cases {len(frozen['cases'])} vs {len(corpus['cases'])})"
        )
        return 0 if same else 1

    path = write_corpus(corpus, args.out)
    print(
        f"wrote {path} cases={len(corpus['cases'])} "
        f"strata={len(corpus['strata'])} not_scored={corpus['units_not_scored']} "
        f"hash={corpus['hash']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
