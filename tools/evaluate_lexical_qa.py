"""Score the published lexicon against the Hannan lines it came from.

Usage::

    python tools/evaluate_lexical_qa.py --corpus evaluation/lexical_qa/v1/corpus.json \
        --out evaluation/lexical_qa/v1/results

Reads the live database read-only. Each frozen case pairs the verbatim source
line with the extraction unit that produced a published record; the source
line is read by ``tools.lexical_qa`` (independent of ``shona_api``) and the
result is compared with the record the API actually serves.

This measures the product, not the parser: a wrong value that never reached a
canonical record is not a public defect, while a value the parser recorded
correctly and promotion dropped is.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_lexical_qa_corpus import corpus_hash  # noqa: E402

DEFAULT_DB_PATH = Path("db/shona.sqlite3")

# Independent residue signature: a part-of-speech category name never carries
# tone brackets, cross-reference markers, or a trailing sentence stop.
LABEL_RESIDUE_RE = re.compile(r"[\[\]]|\bcp\b|\bsee\b|\.\s*$")
MAX_LABEL_LENGTH = 60

CHECKS = ("headword", "word_class", "noun_class", "tone", "part_of_speech_label")


def normalise(value: str) -> str:
    """Case-fold, collapse whitespace, and drop Hannan's leading markers."""
    return " ".join(str(value).split()).casefold().lstrip("†*-")


def normalise_tone(pattern: str) -> str:
    """Tone comparison ignores word grouping: ``H H H`` and ``HHH`` agree."""
    return "".join(str(pattern).split())


def load_published_records(db_path: Path, locators: list[str]) -> dict[str, dict[str, Any]]:
    """Return the published lemma for each locator, read-only."""
    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        unit_links = dict(
            connection.execute(
                """
                SELECT source_location_reference, canonical_record_object_id
                FROM extraction_extractionunit
                WHERE canonical_record_object_id IS NOT NULL
                  AND canonical_record_object_id != ''
                """
            ).fetchall()
        )
        records: dict[str, dict[str, Any]] = {}
        wanted = [(locator, unit_links[locator]) for locator in locators if locator in unit_links]
        for locator, lemma_id in wanted:
            row = connection.execute(
                """
                SELECT l.headword, l.normalized_headword, l.headword_kind,
                       l.part_of_speech_code, l.part_of_speech_label,
                       nc.class_number
                FROM lexicon_lemma l
                LEFT JOIN lexicon_nounclass nc ON nc.id = l.noun_class_id
                WHERE l.id = ?
                """,
                (lemma_id.replace("-", ""),),
            ).fetchone()
            if row is None:
                continue
            tones = [
                pattern
                for (pattern,) in connection.execute(
                    "SELECT pattern FROM lexicon_tonerecord WHERE lemma_id = ?",
                    (lemma_id.replace("-", ""),),
                )
            ]
            forms = [
                text
                for (text,) in connection.execute(
                    """
                    SELECT f.form_text FROM lexicon_form f
                    JOIN lexicon_lemma l ON l.id = f.lemma_id
                    WHERE f.lemma_id = ?
                    """,
                    (lemma_id.replace("-", ""),),
                )
            ]
            records[locator] = {
                "headword": row[0],
                "normalized_headword": row[1],
                "headword_kind": row[2],
                "part_of_speech_code": row[3],
                "part_of_speech_label": row[4],
                "noun_class": row[5],
                "tone_patterns": tones,
                "forms": forms,
            }
        return records
    finally:
        connection.close()


def evaluate_case(case: dict[str, Any], record: dict[str, Any] | None) -> dict[str, Any]:
    """Compare one frozen case against the published record it produced."""
    checks: dict[str, dict[str, Any]] = {}
    source = case["source"]

    if record is None:
        for check in CHECKS:
            checks[check] = {"status": "fail", "detail": "no published record for locator"}
        return {"case_id": case["case_id"], "checks": checks, "unresolved": True}

    checks["headword"] = {
        "status": "pass"
        if record["normalized_headword"] == normalise(source["headword"])
        else "fail",
        "expected": normalise(source["headword"]),
        "actual": record["normalized_headword"],
    }

    checks["word_class"] = {
        "status": "pass"
        if record["headword_kind"] == source["headword_kind"]
        else "fail",
        "expected": source["headword_kind"],
        "actual": record["headword_kind"],
    }

    if source["noun_class"] is None:
        checks["noun_class"] = {"status": "not_applicable"}
    else:
        checks["noun_class"] = {
            "status": "pass"
            if str(record["noun_class"]) == str(source["noun_class"])
            else "fail",
            "expected": source["noun_class"],
            "actual": record["noun_class"],
        }

    expected_tones = {normalise_tone(pattern) for pattern in source["tone_patterns"]}
    actual_tones = {normalise_tone(pattern) for pattern in record["tone_patterns"]}
    missing = sorted(expected_tones - actual_tones)
    checks["tone"] = {
        "status": "pass" if not missing else "fail",
        "expected": sorted(expected_tones),
        "actual": sorted(actual_tones),
        "missing": missing,
        "extra": sorted(actual_tones - expected_tones),
    }

    label = record["part_of_speech_label"] or ""
    residue = bool(LABEL_RESIDUE_RE.search(label)) or len(label) > MAX_LABEL_LENGTH
    checks["part_of_speech_label"] = {
        "status": "fail" if residue else "pass",
        "actual": label,
    }

    return {"case_id": case["case_id"], "checks": checks, "unresolved": False}


def compute_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Raw numerators and denominators per check; nothing is blended."""
    metrics: dict[str, Any] = {}
    for check in CHECKS:
        passed = 0
        failed = 0
        not_applicable = 0
        for result in results:
            status = result["checks"][check]["status"]
            if status == "pass":
                passed += 1
            elif status == "fail":
                failed += 1
            else:
                not_applicable += 1
        metrics[check] = {
            "passed": passed,
            "failed": failed,
            "not_applicable": not_applicable,
            "denominator": passed + failed,
        }
    metrics["unresolved_records"] = sum(1 for result in results if result["unresolved"])
    return metrics


def summarise_failures(results: list[dict[str, Any]]) -> dict[str, list[str]]:
    failures: dict[str, list[str]] = defaultdict(list)
    for result in results:
        for check, outcome in result["checks"].items():
            if outcome["status"] == "fail":
                failures[check].append(result["case_id"])
    return dict(failures)


def compute_plural_coverage(
    cases: list[dict[str, Any]], records: dict[str, dict[str, Any]]
) -> dict[str, int]:
    """How much recorded plural data reaches a published Form record.

    Reported as coverage, not as a correctness check: the parser records plural
    prefixes for thousands of nouns that have no published form, so this is a
    gap in what the lexicon surfaces rather than a wrong value on a record.
    """
    with_plural = 0
    surfaced = 0
    for case in cases:
        prefixes = case["source"].get("plural_forms") or []
        if not prefixes:
            continue
        record = records.get(case["case_id"])
        if record is None:
            continue
        with_plural += 1
        stems = [
            prefix.split("(")[0].strip().rstrip("-").casefold() for prefix in prefixes
        ]
        texts = [normalise(form) for form in record.get("forms", [])]
        if any(stem and text.startswith(stem) for stem in stems for text in texts):
            surfaced += 1
    return {"nouns_with_source_plural": with_plural, "with_a_published_form": surfaced}


def write_report(
    *,
    corpus: dict[str, Any],
    results: list[dict[str, Any]],
    metrics: dict[str, Any],
    coverage: dict[str, int],
    out_dir: Path,
    db_path: Path,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    by_check = metrics
    failures = summarise_failures(results)

    lines = [
        f"# Lexical QA report ({corpus['version']})",
        f"Corpus: {corpus['version']} {corpus['hash']}",
        f"Database: {db_path} (read-only)",
        f"Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"Cases: {len(corpus['cases'])} sampled from {corpus['source_units']} published units "
        f"({corpus['units_not_scored']} lines carry no scoreable word class)",
        "",
        "## Metrics (raw numerators/denominators; measures are not blended)",
    ]
    for check in CHECKS:
        row = by_check[check]
        lines.append(
            f"- {check}: {row['passed']}/{row['denominator']} correct "
            f"({row['not_applicable']} not applicable)"
        )
    lines.append(f"- published records not found: {by_check['unresolved_records']}")
    lines.append("")
    lines.append("## Coverage (not scored)")
    lines.append(
        f"- nouns whose source line records a plural: "
        f"{coverage['nouns_with_source_plural']}; published with a form matching one "
        f"of those prefixes: {coverage['with_a_published_form']}"
    )

    lines.append("")
    lines.append("## Failures by check")
    if not failures:
        lines.append("- none")
    for check, case_ids in sorted(failures.items()):
        lines.append(f"- {check}: {len(case_ids)}")
        for case_id in case_ids[:15]:
            lines.append(f"  - {case_id}")

    extra_tones = [
        (result["case_id"], result["checks"]["tone"].get("extra"))
        for result in results
        if result["checks"]["tone"].get("extra")
    ]
    if extra_tones:
        lines.append("")
        lines.append(f"## Informational: extra tone alternatives beyond the source ({len(extra_tones)})")
        for case_id, extra in extra_tones[:15]:
            lines.append(f"- {case_id}: {extra}")

    report = "\n".join(lines) + "\n"
    path = out_dir / "report.md"
    path.write_text(report, encoding="utf-8")
    return path


def baseline_regressions(
    *,
    metrics: dict[str, Any],
    coverage: dict[str, int],
    baseline: dict[str, Any],
    corpus_hash: str,
) -> list[str]:
    """Return the ways this run falls short of a frozen baseline.

    The corpus is a sample, so absolute counts only mean something against the
    sample they were measured on: the baseline records the corpus hash it was
    written for and is rejected if that no longer matches. Denominators must be
    identical (a changed denominator means the measure itself moved), while
    `passed` may only rise -- a fix improves the number, a regression fails.
    """
    problems: list[str] = []
    if baseline.get("corpus_hash") != corpus_hash:
        return [
            "baseline was written for corpus "
            f"{baseline.get('corpus_hash')!r}, current corpus is {corpus_hash!r}"
        ]

    for check in CHECKS:
        expected = baseline.get("metrics", {}).get(check)
        if expected is None:
            problems.append(f"{check}: baseline records no expectation")
            continue
        actual = metrics[check]
        if actual["denominator"] != expected["denominator"]:
            problems.append(
                f"{check}: denominator moved from {expected['denominator']} "
                f"to {actual['denominator']}"
            )
            continue
        if actual["passed"] < expected["passed"]:
            problems.append(
                f"{check}: {actual['passed']}/{actual['denominator']} correct, "
                f"baseline is {expected['passed']}/{expected['denominator']}"
            )

    expected_coverage = baseline.get("coverage", {})
    for key, value in coverage.items():
        if key not in expected_coverage:
            continue
        if value < expected_coverage[key]:
            problems.append(
                f"coverage {key}: {value}, baseline is {expected_coverage[key]}"
            )
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument(
        "--baseline",
        type=Path,
        help="Fail with a non-zero exit if this run falls short of the baseline.",
    )
    parser.add_argument(
        "--write-baseline",
        type=Path,
        help="Record this run's metrics as the baseline for the frozen corpus.",
    )
    args = parser.parse_args()

    corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
    if corpus.get("hash") != corpus_hash(corpus):
        raise SystemExit("Corpus hash mismatch; refusing to evaluate a modified corpus.")

    cases = corpus["cases"]
    records = load_published_records(args.db, [case["case_id"] for case in cases])
    results = [evaluate_case(case, records.get(case["case_id"])) for case in cases]
    metrics = compute_metrics(results)
    coverage = compute_plural_coverage(cases, records)

    args.out.mkdir(parents=True, exist_ok=True)
    report_path = write_report(
        corpus=corpus,
        results=results,
        metrics=metrics,
        coverage=coverage,
        out_dir=args.out,
        db_path=args.db,
    )
    (args.out / "results.json").write_text(
        json.dumps(
            {
                "corpus": corpus["hash"],
                "metrics": metrics,
                "coverage": coverage,
                "results": results,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    if args.write_baseline:
        args.write_baseline.write_text(
            json.dumps(
                {
                    "corpus_hash": corpus["hash"],
                    "metrics": {
                        check: {
                            "passed": metrics[check]["passed"],
                            "denominator": metrics[check]["denominator"],
                        }
                        for check in CHECKS
                    },
                    "coverage": coverage,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"wrote baseline {args.write_baseline}")

    summary = " ".join(
        f"{check}={metrics[check]['passed']}/{metrics[check]['denominator']}" for check in CHECKS
    )
    print(f"cases={len(cases)} {summary} report={report_path}")

    if args.baseline:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        problems = baseline_regressions(
            metrics=metrics,
            coverage=coverage,
            baseline=baseline,
            corpus_hash=corpus["hash"],
        )
        if problems:
            print(f"BASELINE FAILED ({len(problems)} regression(s)):", file=sys.stderr)
            for problem in problems:
                print(f"  - {problem}", file=sys.stderr)
            return 1
        print(f"baseline ok ({args.baseline})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
