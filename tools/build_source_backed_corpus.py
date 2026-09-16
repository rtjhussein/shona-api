"""Deterministic construction and validation of the source-backed corpus.

Owning builder: combines ``fixtures.json`` + ``corpus_part{1,2,3,4}.json``
into ``corpus.json``. The standalone runner and the pytest gate both verify
the stored hash and validate the schema before any request is made.

Hash definition (exact):
- payload = {"version":..., "fixtures":..., "cases":...} (the "hash" field
  itself is excluded);
- canonical bytes = json.dumps(payload, sort_keys=True, ensure_ascii=False,
  indent=2).encode("utf-8");
- stored hash = "sha256:" + hex(SHA-256(canonical bytes)) (full 64 hex chars).

corpus.json on disk is the same dumps of the full dict *including* "hash"
(sort_keys=True, ensure_ascii=False, indent=2) plus a trailing newline.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

CORPUS_VERSION = "source-backed-eval-v1"

CASE_ID_RE = re.compile(r"^(SRC-\d+|CT-[A-Z][A-Z0-9-]*\d+)$")
EVIDENCE_CLASSES = {"source_attested", "rule_supported", "unresolved", "contract"}
REVIEW_STATUSES = {"proposed", "agreed", "disputed_unresolved"}
FLOW_NAMES = {"generate", "analyze", "search"}
GENERATE_KEYS = {
    "lemma_key",
    "features",
    "expected_status",
    "expected_surface",
    "expected_rule_id",
    "expected_code",
    "expected_detail_contains",
    "expected_absent",
}
ANALYZE_KEYS = {
    "text",
    "expected_status",
    "expected_code",
    "expected_lane",
    "exhaustive",
    "required_readings",
    "prohibited_readings",
    "also_allowed",
    "expected_absent",
}
SEARCH_KEYS = {
    "q",
    "expected_status",
    "expected_enrichment_status",
    "expected_text_contains",
    "expected_absent",
    "required_readings",
    "prohibited_readings",
    "also_allowed",
    "expected_lexical_hits",
}
READING_KEYS = {"analysis_type", "rule_id", "lemma", "slots"}
LEMMA_REF_KEYS = {"lemma_key"}
LEXICAL_HIT_KEYS = {"normalized_headword"}
# Maintained nested expectation schema (hand-authored; never imported from
# shona_api.morphology.services so corpus validation stays independent of the
# implementation under test). Keys and structure only — linguistic reference
# *values* (polarity "positive"/"negative", extension types, surfaces) are
# source-backed and deliberately unrestricted here. Partial-map matching
# (maps assert subsets), ordered exact-length list matching, and explicit
# null-versus-missing semantics are preserved by the evaluator; this schema
# only rejects unknown keys and structurally invalid shapes.
SLOT_NAMES = {
    "addressee",
    "extensions",
    "final_vowel",
    "mood",
    "object",
    "polarity",
    "reflexive",
    "subject",
    "tense_aspect",
    "verb_stem",
}
# Allowed nested fields per slot (subset assertions permitted; unknown rejected).
_SUBJECT_OBJECT_FIELDS = {
    "surface",
    "type",
    "label",
    "person",
    "number",
    "class_number",
    "noun_class_public_id",
}
SLOT_FIELD_NAMES = {
    "addressee": {"surface", "person", "number", "label"},
    "mood": {"surface", "value", "label"},
    "polarity": {"surface", "value", "label"},
    "tense_aspect": {"surface", "value", "label"},
    "reflexive": {"surface", "value", "label"},
    "subject": _SUBJECT_OBJECT_FIELDS,
    "object": _SUBJECT_OBJECT_FIELDS,
    "verb_stem": {"surface", "lemma_public_id"},
    "final_vowel": {"surface", "value", "label"},
}
# Flat extension list entries (ordered exact-length matching in evaluator).
EXTENSION_ENTRY_KEYS = {"surface", "type", "style", "label"}


class CorpusError(Exception):
    """Schema or integrity violation with a locator path."""


def canonical_hash_bytes(payload_without_hash: dict) -> bytes:
    return json.dumps(
        payload_without_hash, sort_keys=True, ensure_ascii=False, indent=2
    ).encode("utf-8")


def compute_hash(payload_without_hash: dict) -> str:
    return (
        "sha256:"
        + hashlib.sha256(canonical_hash_bytes(payload_without_hash)).hexdigest()
    )


def _need(cond: bool, path: str, msg: str) -> None:
    if not cond:
        raise CorpusError(f"{path}: {msg}")


def _check_keys(obj: dict, allowed: set[str], path: str, kind: str) -> None:
    unknown = set(obj) - allowed
    if unknown:
        raise CorpusError(
            f"{path}: unknown {kind} key(s) {sorted(unknown)}; allowed: {sorted(allowed)}"
        )


def _check_slots(slots: dict, path: str) -> None:
    _need(isinstance(slots, dict), path, "slots must be an object")
    for slot_name, value in slots.items():
        slot_path = f"{path}.{slot_name}"
        _need(
            slot_name in SLOT_NAMES,
            path,
            f"unknown slot {slot_name!r}; allowed: {sorted(SLOT_NAMES)}",
        )
        if value is None:
            continue
        if slot_name == "extensions":
            _need(
                isinstance(value, list),
                slot_path,
                "extensions must be a list of objects (ordered exact-length matching)",
            )
            for j, entry in enumerate(value):
                entry_path = f"{slot_path}[{j}]"
                _need(
                    isinstance(entry, dict),
                    entry_path,
                    "extension entry must be an object",
                )
                _check_keys(entry, EXTENSION_ENTRY_KEYS, entry_path, "extension entry")
                for field, field_value in entry.items():
                    _need(
                        not isinstance(field_value, (dict, list)),
                        f"{entry_path}.{field}",
                        "extension entry values must be scalars (no nested maps/lists)",
                    )
            continue
        if isinstance(value, list):
            raise CorpusError(
                f"{slot_path}: structurally invalid expectation "
                f"(only extensions may be a list, got {value!r:.120})"
            )
        _need(isinstance(value, dict), slot_path, "slot must be an object or null")
        allowed_fields = SLOT_FIELD_NAMES[slot_name]
        _check_keys(value, allowed_fields, slot_path, f"slot {slot_name!r} field")
        for field, field_value in value.items():
            _need(
                field_value is None or isinstance(field_value, (str, bool, int, float)),
                f"{slot_path}.{field}",
                "slot field values must be scalars or null (no nested maps/lists)",
            )


def _check_reading(reading: dict, path: str, lemma_keys: set[str]) -> None:
    _need(isinstance(reading, dict), path, "reading must be an object")
    _check_keys(reading, READING_KEYS, path, "reading")
    if "analysis_type" in reading:
        _need(
            isinstance(reading["analysis_type"], str),
            f"{path}.analysis_type",
            "must be a string",
        )
    if "rule_id" in reading:
        _need(
            isinstance(reading["rule_id"], str),
            f"{path}.rule_id",
            "must be a string",
        )
    if "lemma" in reading:
        lemma = reading["lemma"]
        _need(isinstance(lemma, dict), f"{path}.lemma", "must be an object")
        _check_keys(lemma, LEMMA_REF_KEYS, f"{path}.lemma", "lemma ref")
        _need(
            "lemma_key" in lemma,
            f"{path}.lemma",
            "lemma ref must be {lemma_key: ...}",
        )
        _need(
            lemma["lemma_key"] in lemma_keys,
            f"{path}.lemma.lemma_key",
            f"unresolvable fixture reference {lemma['lemma_key']!r}",
        )
    if "slots" in reading:
        _check_slots(reading["slots"], f"{path}.slots")


def validate_corpus(corpus: dict) -> None:
    """Raise CorpusError on any structural problem. Pure function (no I/O)."""
    _need(isinstance(corpus, dict), "corpus", "must be an object")
    for key in ("version", "fixtures", "cases"):
        _need(key in corpus, "corpus", f"missing {key!r}")

    fixtures = corpus["fixtures"]
    _need(isinstance(fixtures, dict), "fixtures", "must be an object")
    class_numbers = [nc["class_number"] for nc in fixtures.get("noun_classes", [])]
    _need(
        len(set(class_numbers)) == len(class_numbers),
        "fixtures.noun_classes",
        "duplicate class_number",
    )
    lemma_keys: set[str] = set()
    for lemma in fixtures.get("lemmas", []):
        _need(
            lemma["key"] not in lemma_keys,
            "fixtures.lemmas",
            f"duplicate key {lemma['key']!r}",
        )
        lemma_keys.add(lemma["key"])
        _need(
            isinstance(lemma.get("headword"), str)
            and lemma["headword"].startswith("-"),
            f"fixtures.lemmas.{lemma['key']}",
            "verb-stem headword must start with '-'",
        )

    seen_ids: set[str] = set()
    for case in corpus.get("cases", []):
        base = f"cases.{case.get('case_id', '?')}"
        _need(case.get("case_id") not in seen_ids, base, "duplicate case_id")
        seen_ids.add(case.get("case_id"))
        _need(
            bool(CASE_ID_RE.match(case.get("case_id", ""))),
            base,
            "case_id must look like SRC-001 or CT-XXX-01",
        )
        _need(
            case.get("evidence_class") in EVIDENCE_CLASSES, base, "bad evidence_class"
        )
        _need(case.get("review_status") in REVIEW_STATUSES, base, "bad review_status")
        _need(isinstance(case.get("scored"), bool), base, "scored must be boolean")
        if case.get("evidence_class") == "unresolved":
            _need(
                not case.get("scored"), base, "unresolved evidence must not be scored"
            )
        flows = case.get("flows", [])
        _need(isinstance(flows, list), base, "flows must be a list")
        unknown_flows = set(flows) - FLOW_NAMES
        _need(not unknown_flows, base, f"unknown flows {sorted(unknown_flows)}")
        if not flows:
            _need(
                not case.get("scored"),
                base,
                "scored case with no flows has no assertions",
            )
            continue
        if "lemma_key" in case and case["lemma_key"] is not None:
            _need(
                case["lemma_key"] in lemma_keys,
                f"{base}.lemma_key",
                "unresolvable fixture reference",
            )
        if "generate" in flows:
            g = case.get("generate", {})
            _check_keys(g, GENERATE_KEYS, f"{base}.generate", "generate expectation")
            _need(
                "expected_status" in g, f"{base}.generate", "expected_status required"
            )
            if g.get("lemma_key"):
                _need(
                    g["lemma_key"] in lemma_keys,
                    f"{base}.generate.lemma_key",
                    "unresolvable",
                )
            if g["expected_status"] == 200:
                _need(
                    "expected_surface" in g,
                    f"{base}.generate",
                    "200 needs expected_surface",
                )
            else:
                _need(
                    "expected_code" in g,
                    f"{base}.generate",
                    "non-200 needs expected_code",
                )
        if "analyze" in flows:
            an = case.get("analyze", {})
            _check_keys(an, ANALYZE_KEYS, f"{base}.analyze", "analyze expectation")
            _need(
                "expected_status" in an, f"{base}.analyze", "expected_status required"
            )
            _need(
                "exhaustive" in an or an["expected_status"] != 200,
                f"{base}.analyze",
                "analyze-200 needs explicit exhaustive boolean",
            )
            for list_key in (
                "required_readings",
                "prohibited_readings",
                "also_allowed",
            ):
                _need(
                    isinstance(an.get(list_key, []), list),
                    f"{base}.analyze.{list_key}",
                    "must be a list of reading objects",
                )
            for i, req in enumerate(an.get("required_readings", [])):
                _check_reading(
                    req, f"{base}.analyze.required_readings[{i}]", lemma_keys
                )
            for i, req in enumerate(an.get("prohibited_readings", [])):
                _check_reading(
                    req, f"{base}.analyze.prohibited_readings[{i}]", lemma_keys
                )
            for i, req in enumerate(an.get("also_allowed", [])):
                _check_reading(req, f"{base}.analyze.also_allowed[{i}]", lemma_keys)
            if an["expected_status"] == 200:
                _need(
                    an.get("required_readings"),
                    f"{base}.analyze",
                    "analyze-200 needs at least one required reading",
                )
            else:
                _need(
                    "expected_code" in an,
                    f"{base}.analyze",
                    "non-200 needs expected_code",
                )
        if "search" in flows:
            se = case.get("search", {})
            _check_keys(se, SEARCH_KEYS, f"{base}.search", "search expectation")
            _need("expected_status" in se, f"{base}.search", "expected_status required")
            has_assertion = any(
                se.get(k)
                for k in (
                    "expected_enrichment_status",
                    "expected_text_contains",
                    "expected_absent",
                    "required_readings",
                    "prohibited_readings",
                    "expected_lexical_hits",
                )
            )
            _need(
                has_assertion, f"{base}.search", "search needs at least one assertion"
            )
            for list_key in (
                "required_readings",
                "prohibited_readings",
                "also_allowed",
            ):
                _need(
                    isinstance(se.get(list_key, []), list),
                    f"{base}.search.{list_key}",
                    "must be a list of reading objects",
                )
            for i, req in enumerate(se.get("required_readings", [])):
                _check_reading(req, f"{base}.search.required_readings[{i}]", lemma_keys)
            for i, req in enumerate(se.get("prohibited_readings", [])):
                _check_reading(
                    req, f"{base}.search.prohibited_readings[{i}]", lemma_keys
                )
            for i, req in enumerate(se.get("also_allowed", [])):
                _check_reading(req, f"{base}.search.also_allowed[{i}]", lemma_keys)
            _need(
                isinstance(se.get("expected_lexical_hits", []), list),
                f"{base}.search.expected_lexical_hits",
                "must be a list",
            )
            for hit in se.get("expected_lexical_hits", []):
                _check_keys(
                    hit, LEXICAL_HIT_KEYS, f"{base}.search.lexical_hit", "lexical hit"
                )
        if case.get("round_trip") is not None:
            _need(
                "generate" in flows
                and case.get("generate", {}).get("expected_status") == 200,
                f"{base}.round_trip",
                "round_trip requires a successful generation request",
            )
            rt = case["round_trip"]
            _need(
                isinstance(rt, dict) and isinstance(rt.get("required_reading"), dict),
                f"{base}.round_trip",
                "round_trip must be {required_reading: {...}}",
            )
            _check_reading(
                rt["required_reading"],
                f"{base}.round_trip.required_reading",
                lemma_keys,
            )
        if case.get("scored") and flows:
            _need(
                _case_has_assertions(case),
                base,
                "scored case with flows but no meaningful assertions",
            )


def _case_has_assertions(case: dict) -> bool:
    flows = case.get("flows", [])
    if "generate" in flows:
        g = case.get("generate", {})
        if g.get("expected_status") == 200 and "expected_surface" in g:
            return True
        if g.get("expected_status") != 200 and "expected_code" in g:
            return True
    if "analyze" in flows:
        an = case.get("analyze", {})
        if an.get("expected_status") == 200 and an.get("required_readings"):
            return True
        if an.get("expected_status") != 200 and "expected_code" in an:
            return True
    if "search" in flows:
        se = case.get("search", {})
        if any(
            se.get(k)
            for k in (
                "expected_enrichment_status",
                "expected_text_contains",
                "expected_absent",
                "required_readings",
                "prohibited_readings",
                "expected_lexical_hits",
            )
        ):
            return True
    return False


def verify_hash(corpus: dict) -> str:
    """Recompute the hash over the payload and compare with the stored value."""
    stored = corpus.get("hash", "")
    payload = {k: corpus[k] for k in ("version", "fixtures", "cases")}
    recomputed = compute_hash(payload)
    if stored != recomputed:
        raise CorpusError(
            f"corpus hash mismatch: stored {stored!r} != recomputed {recomputed!r}; "
            "rebuild with tools/build_source_backed_corpus.py and record the change."
        )
    return recomputed


def load_parts(parts_dir: Path) -> tuple[dict, list[dict]]:
    fixtures = json.loads((parts_dir / "fixtures.json").read_text(encoding="utf-8"))
    cases: list[dict] = []
    for name in (
        "corpus_part1.json",
        "corpus_part2.json",
        "corpus_part3.json",
        "corpus_part4.json",
    ):
        part = json.loads((parts_dir / name).read_text(encoding="utf-8"))
        cases.extend(part["cases"])
    return fixtures, cases


def build_corpus(
    parts_dir: Path, *, version: str = CORPUS_VERSION
) -> tuple[dict, bytes]:
    """Combine parts+fixtures, validate, hash. Returns (corpus_dict, file_bytes)."""
    fixtures, cases = load_parts(parts_dir)
    corpus = {
        "version": version,
        "protocol": "docs/morphology/source-backed-evaluation-protocol.md",
        "code_base": "01e8ce7 (PR #113, morphology-rules-v6)",
        "fixtures": fixtures,
        "cases": cases,
    }
    corpus["hash"] = compute_hash(
        {k: corpus[k] for k in ("version", "fixtures", "cases")}
    )
    validate_corpus(corpus)
    file_bytes = (
        json.dumps(corpus, sort_keys=True, ensure_ascii=False, indent=2).encode("utf-8")
        + b"\n"
    )
    return corpus, file_bytes


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Build and validate corpus.json")
    parser.add_argument("--parts", default="evaluation/source_backed/v1")
    parser.add_argument("--out", default="evaluation/source_backed/v1/corpus.json")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    parts_dir = Path(args.parts)
    if args.check_only:
        corpus = json.loads(Path(args.out).read_text(encoding="utf-8"))
        verify_hash(corpus)
        validate_corpus(corpus)
        print(f"corpus ok: {corpus['hash']} ({len(corpus['cases'])} cases)")
        return 0
    corpus, file_bytes = build_corpus(parts_dir)
    Path(args.out).write_bytes(file_bytes)
    print(f"built {args.out}: {corpus['hash']} ({len(corpus['cases'])} cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
