"""Reproducible source-backed morphology evaluation runner (repaired edition).

Loads a versioned corpus (hash-verified, schema-validated), builds isolated
fixtures, exercises routed /v1/generate, /v1/analyze, /v1/search, and writes
machine-readable results plus a metrics report with explicit denominators.

Isolation: standalone mode uses config.settings.eval with EVAL_DB_PATH pointing
at a fresh temporary file the runner owns. It never reads DATABASE_URL (the
project .env would override it) and never deletes anything in --out.

Reference expectations are plain data; this runner never calls morphology
implementation helpers to manufacture expected surfaces. Reading matches use
explicit partial-match semantics: expected maps assert a subset of keys,
expected lists assert ordered exact-length sequences, expected null asserts a
present null (missing fails), unknown expectation keys (including nested slot
names, slot fields, and extension entry keys against the maintained schema
shared with the corpus builder) fail loudly via ExpectationError before any
matching, so a malformed prohibited pattern can never pass as a non-match.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.build_source_backed_corpus import (  # noqa: E402
    EXTENSION_ENTRY_KEYS,
    SLOT_FIELD_NAMES,
    SLOT_NAMES,
    CorpusError,
    validate_corpus,
    verify_hash,
)

READING_KEYS = {"analysis_type", "rule_id", "lemma", "slots"}
LEMMA_KEYS = {"lemma_public_id"}


class ExpectationError(Exception):
    """A reference expectation is malformed (unknown key, bad reference)."""


def _resolve(obj, lemma_ids: dict):
    """Recursively replace {"lemma_key": k} with {"lemma_public_id": id}."""
    if isinstance(obj, dict):
        if set(obj) == {"lemma_key"}:
            key = obj["lemma_key"]
            if key not in lemma_ids:
                raise ExpectationError(f"unresolvable lemma_key {key!r}")
            return {"lemma_public_id": lemma_ids[key]}
        return {k: _resolve(v, lemma_ids) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve(v, lemma_ids) for v in obj]
    return obj


def _validate_resolved_slots(slots: dict, path: str) -> None:
    """Validate nested slot structure of a resolved expectation.

    Mirrors the builder's maintained schema (SLOT_NAMES / SLOT_FIELD_NAMES /
    EXTENSION_ENTRY_KEYS) but raises ExpectationError so a malformed pattern
    fails loudly in evaluate_case instead of becoming a silent non-match
    (which would wrongly pass a prohibited-reading check).
    """
    if not isinstance(slots, dict):
        raise ExpectationError(f"{path}: slots must be an object")
    for slot_name, value in slots.items():
        slot_path = f"{path}.{slot_name}"
        if slot_name not in SLOT_NAMES:
            raise ExpectationError(
                f"{path}: unknown slot {slot_name!r}; allowed: {sorted(SLOT_NAMES)}"
            )
        if value is None:
            continue
        if slot_name == "extensions":
            if not isinstance(value, list):
                raise ExpectationError(
                    f"{slot_path}: extensions must be a list of objects"
                )
            for j, entry in enumerate(value):
                entry_path = f"{slot_path}[{j}]"
                if not isinstance(entry, dict):
                    raise ExpectationError(
                        f"{entry_path}: extension entry must be an object"
                    )
                unknown = set(entry) - EXTENSION_ENTRY_KEYS
                if unknown:
                    raise ExpectationError(
                        f"{entry_path}: unknown extension entry key(s) "
                        f"{sorted(unknown)}; allowed: {sorted(EXTENSION_ENTRY_KEYS)}"
                    )
                for field, field_value in entry.items():
                    if isinstance(field_value, (dict, list)):
                        raise ExpectationError(
                            f"{entry_path}.{field}: extension entry values must be "
                            "scalars (no nested maps/lists)"
                        )
            continue
        if isinstance(value, list):
            raise ExpectationError(
                f"{slot_path}: structurally invalid expectation "
                "(only extensions may be a list)"
            )
        if not isinstance(value, dict):
            raise ExpectationError(f"{slot_path}: slot must be an object or null")
        allowed = SLOT_FIELD_NAMES[slot_name]
        unknown = set(value) - allowed
        if unknown:
            raise ExpectationError(
                f"{slot_path}: unknown slot field(s) {sorted(unknown)}; "
                f"allowed: {sorted(allowed)}"
            )
        for field, field_value in value.items():
            if field_value is not None and not isinstance(
                field_value, (str, bool, int, float)
            ):
                raise ExpectationError(
                    f"{slot_path}.{field}: slot field values must be scalars or null"
                )


def _validate_resolved_reading(expected: dict, path: str) -> None:
    """Validate a resolved reading expectation; raise ExpectationError."""
    if not isinstance(expected, dict):
        raise ExpectationError(f"{path}: reading must be an object")
    unknown = set(expected) - READING_KEYS
    if unknown:
        raise ExpectationError(f"{path}: unknown expectation key(s) {sorted(unknown)}")
    for key in ("analysis_type", "rule_id"):
        if key in expected and not isinstance(expected[key], str):
            raise ExpectationError(f"{path}.{key}: must be a string")
    if "lemma" in expected:
        want_lemma = expected["lemma"]
        if not isinstance(want_lemma, dict):
            raise ExpectationError(f"{path}.lemma: must be an object")
        unknown_lemma = set(want_lemma) - LEMMA_KEYS
        if unknown_lemma:
            raise ExpectationError(
                f"{path}.lemma: unknown lemma expectation key(s) "
                f"{sorted(unknown_lemma)}"
            )
    if "slots" in expected:
        _validate_resolved_slots(expected["slots"], f"{path}.slots")


def match_value(actual, expected, path: str) -> tuple[bool, str]:
    """Partial-match semantics: maps assert subsets, lists assert ordered
    exact-length sequences, None asserts a present null. Missing keys fail."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False, f"{path}: want object, got {actual!r:.120}"
        for key, want in expected.items():
            if key not in actual:
                return False, f"{path}.{key}: missing (want {want!r:.120})"
            ok, detail = match_value(actual[key], want, f"{path}.{key}")
            if not ok:
                return False, detail
        return True, ""
    if isinstance(expected, list):
        if not isinstance(actual, list):
            return False, f"{path}: want list of {len(expected)}, got {actual!r:.120}"
        if len(actual) != len(expected):
            return (
                False,
                f"{path}: want {len(expected)} item(s), got {len(actual)}: {actual!r:.200}",
            )
        for i, (got_item, want_item) in enumerate(zip(actual, expected)):
            ok, detail = match_value(got_item, want_item, f"{path}[{i}]")
            if not ok:
                return False, detail
        return True, ""
    if expected is None:
        if actual is None:
            return True, ""
        return False, f"{path}: want null, got {actual!r:.120}"
    if actual == expected:
        return True, ""
    return False, f"{path}: want {expected!r:.120}, got {actual!r:.120}"


def match_reading(analysis: dict, expected: dict) -> tuple[bool, str]:
    if not isinstance(analysis, dict):
        return (
            False,
            f"malformed reading object: want object, got {_json_type(analysis)}",
        )
    if not isinstance(expected, dict):
        return False, f"malformed expectation: want object, got {_json_type(expected)}"
    unknown = set(expected) - READING_KEYS
    if unknown:
        return False, f"unknown expectation key(s) {sorted(unknown)}"
    for key in ("analysis_type", "rule_id"):
        if key in expected and analysis.get(key) != expected[key]:
            return False, f"{key}: want {expected[key]!r}, got {analysis.get(key)!r}"
    if "lemma" in expected:
        want_lemma = expected["lemma"]
        if not isinstance(want_lemma, dict):
            return False, "lemma: malformed lemma expectation (must be an object)"
        unknown_lemma = set(want_lemma) - LEMMA_KEYS
        if unknown_lemma:
            return False, f"unknown lemma expectation key(s) {sorted(unknown_lemma)}"
        got_lemma = analysis.get("lemma")
        if not isinstance(got_lemma, dict):
            return False, "lemma: missing lemma object"
        if (
            "lemma_public_id" in want_lemma
            and got_lemma.get("public_id") != want_lemma["lemma_public_id"]
        ):
            return False, (
                f"lemma: want public_id {want_lemma['lemma_public_id']!r}, "
                f"got {got_lemma.get('public_id')!r}"
            )
    if "slots" in expected:
        try:
            _validate_resolved_slots(expected["slots"], "slots")
        except ExpectationError as exc:
            return False, str(exc)
        actual_slots = analysis.get("slots", {})
        if not isinstance(actual_slots, dict):
            return False, f"slots: want object, got {_json_type(actual_slots)}"
        return match_value(actual_slots, expected["slots"], "slots")
    return True, ""


def _summarize_analysis(analysis: dict) -> str:
    if not isinstance(analysis, dict):
        return f"<malformed reading: {_json_type(analysis)}>"
    lemma = analysis.get("lemma")
    if not isinstance(lemma, dict):
        lemma = {}
    return (
        f"{analysis.get('analysis_type')}/{analysis.get('rule_id')}"
        f" lemma={lemma.get('headword', lemma.get('public_id'))}"
    )


def _auth(api_key: str) -> dict:
    return {"HTTP_AUTHORIZATION": f"Api-Key {api_key}"}


def _generated_form(data: dict) -> tuple:
    gen = data.get("generated", {})
    if not isinstance(gen, dict):
        return None, None
    return gen.get("form"), gen.get("rule_id")


_MISSING = object()


def _json_type(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _extract_data(resp, prefix: str, check) -> dict | None:
    """Return resp.json()['data'] when it is a dict, else fail {prefix}_body.

    Valid JSON with a malformed envelope (missing/non-object 'data') is a
    response failure, not an unreadable body and never a crash. Returns None
    on failure so callers skip field checks; the emitted body failure marks
    the case. An empty-but-valid {} envelope returns {} (field checks then
    report the missing fields).
    """
    try:
        data = resp.json()["data"]
    except Exception as exc:  # noqa: BLE001
        check(f"{prefix}_body", False, f"unreadable body: {exc}")
        return None
    if not isinstance(data, dict):
        check(
            f"{prefix}_body",
            False,
            f"malformed {prefix} response: 'data' must be an object, "
            f"got {_json_type(data)}",
        )
        return None
    return data


def _reading_list(
    container: dict,
    field: str,
    location: str,
    prefix: str,
    check,
    missing_ok: bool = False,
) -> list:
    """Validate container[field] as a list of reading objects, else fail body.

    Returns the list (possibly empty — a legitimate empty result) or [] after
    emitting a field-specific {prefix}_body failure. Missing fields fail too
    unless missing_ok (search morphology, where absent enrichment is a
    legitimate contract outcome). Sanitized output lets callers iterate,
    slice, and match without further guards.
    """
    raw = container.get(field, _MISSING)
    if raw is _MISSING:
        if missing_ok:
            return []
        check(
            f"{prefix}_body",
            False,
            f"malformed {prefix} response: missing {location!r}",
        )
        return []
    if not isinstance(raw, list):
        check(
            f"{prefix}_body",
            False,
            f"malformed {prefix} response: {location!r} must be a list, "
            f"got {_json_type(raw)}",
        )
        return []
    for j, entry in enumerate(raw):
        if not isinstance(entry, dict):
            check(
                f"{prefix}_body",
                False,
                f"malformed {prefix} response: {location}[{j}] must be an "
                f"object, got {_json_type(entry)}",
            )
            return []
    return raw


def evaluate_case(client, api_key: str, case: dict, lemma_ids: dict) -> dict:
    result: dict = {
        "case_id": case["case_id"],
        "category": case.get("category"),
        "scored": bool(case.get("scored", True)),
        "checks": [],
        "status": "pass",
        "calls": 0,
    }
    failures: list[str] = []
    notes: list[str] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        result["checks"].append(
            {"name": name, "passed": bool(passed), "detail": detail}
        )
        if not passed:
            failures.append(f"{name}: {detail}")
            result["status"] = "fail"

    def check_absent(prefix: str, body: bytes, items) -> None:
        text = body.decode("utf-8", "replace")
        for item in items or []:
            check(
                f"{prefix}_absent:{item[:60]}",
                item not in text,
                f"prohibited output {item!r} present in body" if item in text else "",
            )

    flows = case.get("flows", [])
    if not flows:
        result["status"] = "not_evaluated"
        result["failures"] = []
        result["notes"] = ["evidence-only case: no executable flows"]
        return result

    generated_form = None
    if "generate" in flows:
        g = case.get("generate", {})
        lemma_key = g.get("lemma_key")
        public_id = lemma_ids.get(lemma_key, lemma_key) if lemma_key else None
        payload = {"lemma_public_id": public_id, "features": g.get("features", {})}
        resp = client.post(
            "/v1/generate", payload, content_type="application/json", **_auth(api_key)
        )
        result["calls"] += 1
        exp_status = g.get("expected_status", 200)
        check(
            "generate_status",
            resp.status_code == exp_status,
            f"got {resp.status_code}, want {exp_status}: {resp.content[:400]!r}",
        )
        if resp.status_code == 200 and exp_status == 200:
            data = _extract_data(resp, "generate", check)
            if data is not None:
                gen = data.get("generated", _MISSING)
                if gen is _MISSING:
                    check(
                        "generate_body",
                        False,
                        "malformed generate response: missing 'generated'",
                    )
                elif not isinstance(gen, dict):
                    check(
                        "generate_body",
                        False,
                        f"malformed generate response: 'generated' must be an "
                        f"object, got {_json_type(gen)}",
                    )
                else:
                    form, rule_id = _generated_form(data)
                    generated_form = form
                    if "expected_surface" in g:
                        surface_ok = form == g["expected_surface"]
                        check(
                            "generate_surface",
                            surface_ok,
                            f"got {form!r}, want {g['expected_surface']!r}",
                        )
                    if "expected_rule_id" in g:
                        rule_ok = rule_id == g["expected_rule_id"]
                        check(
                            "generate_rule",
                            rule_ok,
                            f"got {rule_id!r}, want {g['expected_rule_id']!r}",
                        )
        elif resp.status_code == exp_status:
            if "expected_code" in g:
                try:
                    blob = resp.json()
                    code = (blob.get("error", {}) or {}).get("code") or blob.get("code")
                    check(
                        "generate_code",
                        code == g["expected_code"],
                        f"got {code!r}, want {g['expected_code']!r}",
                    )
                except Exception as exc:  # noqa: BLE001
                    check("generate_code", False, f"unreadable error body: {exc}")
            if "expected_detail_contains" in g:
                text = resp.content.decode("utf-8", "replace")
                check(
                    "generate_detail",
                    g["expected_detail_contains"] in text,
                    f"want {g['expected_detail_contains']!r} in body",
                )
        check_absent("generate", resp.content, g.get("expected_absent"))

    if "analyze" in flows:
        an = case.get("analyze", {})
        resp = client.post(
            "/v1/analyze",
            {"text": an.get("text", "")},
            content_type="application/json",
            **_auth(api_key),
        )
        result["calls"] += 1
        exp_status = an.get("expected_status", 200)
        check(
            "analyze_status",
            resp.status_code == exp_status,
            f"got {resp.status_code}, want {exp_status}: {resp.content[:400]!r}",
        )
        if resp.status_code == 200 and exp_status == 200:
            data = _extract_data(resp, "analyze", check)
            analyses = (
                _reading_list(data, "analyses", "data.analyses", "analyze", check)
                if data is not None
                else []
            )
            try:
                required = [
                    _resolve(r, lemma_ids) for r in an.get("required_readings", [])
                ]
                prohibited = [
                    _resolve(p, lemma_ids) for p in an.get("prohibited_readings", [])
                ]
                allowed_extra = [
                    _resolve(a, lemma_ids) for a in an.get("also_allowed", [])
                ]
                for j, pat in enumerate(required):
                    _validate_resolved_reading(pat, f"analyze.required_readings[{j}]")
                for j, pat in enumerate(prohibited):
                    _validate_resolved_reading(pat, f"analyze.prohibited_readings[{j}]")
                for j, pat in enumerate(allowed_extra):
                    _validate_resolved_reading(pat, f"analyze.also_allowed[{j}]")
                allowed = required + allowed_extra
            except ExpectationError as exc:
                check("analyze_expectation", False, str(exc))
                required, prohibited, allowed = [], [], []
            else:
                for raw, req in zip(an.get("required_readings", []), required):
                    found = any(match_reading(a, req)[0] for a in analyses)
                    check(
                        f"analyze_required:{json.dumps(raw, sort_keys=True)[:90]}",
                        found,
                        f"required reading not recovered among {len(analyses)}: "
                        + ", ".join(_summarize_analysis(a) for a in analyses[:6]),
                    )
                for raw, pro in zip(an.get("prohibited_readings", []), prohibited):
                    hits = [a for a in analyses if match_reading(a, pro)[0]]
                    check(
                        f"analyze_prohibited:{json.dumps(raw, sort_keys=True)[:90]}",
                        not hits,
                        "prohibited reading produced: "
                        + ", ".join(_summarize_analysis(a) for a in hits[:3]),
                    )
                if an.get("exhaustive", False):
                    unmatched = [
                        a
                        for a in analyses
                        if not any(match_reading(a, pat)[0] for pat in allowed)
                    ]
                    check(
                        "analyze_exhaustive",
                        not unmatched,
                        f"{len(unmatched)} unlisted reading(s): "
                        + ", ".join(_summarize_analysis(a) for a in unmatched[:5]),
                    )
                    result["unadjudicated_extras"] = 0
                else:
                    unadjudicated = [
                        a
                        for a in analyses
                        if not any(match_reading(a, pat)[0] for pat in required)
                        and not any(match_reading(a, pat)[0] for pat in prohibited)
                    ]
                    result["unadjudicated_extras"] = len(unadjudicated)
                    if unadjudicated:
                        notes.append(
                            f"{len(unadjudicated)} unadjudicated reading(s): "
                            + ", ".join(
                                _summarize_analysis(a) for a in unadjudicated[:5]
                            )
                        )
                    else:
                        result["unadjudicated_extras"] = 0
        elif resp.status_code == exp_status:
            if "expected_code" in an:
                try:
                    blob = resp.json()
                    code = (blob.get("error", {}) or {}).get("code") or blob.get("code")
                    check(
                        "analyze_code",
                        code == an["expected_code"],
                        f"got {code!r}, want {an['expected_code']!r}",
                    )
                except Exception as exc:  # noqa: BLE001
                    check("analyze_code", False, f"unreadable error body: {exc}")
            if "expected_lane" in an:
                text = resp.content.decode("utf-8", "replace")
                check(
                    "analyze_lane",
                    an["expected_lane"] in text,
                    f"want lane {an['expected_lane']!r} in body",
                )
            if an.get("prohibited_readings") or an.get("required_readings"):
                notes.append("reading lists trivially settled on 4xx (no analyses)")
                result["unadjudicated_extras"] = 0
        check_absent("analyze", resp.content, an.get("expected_absent"))

    if "search" in flows:
        se = case.get("search", {})
        resp = client.get("/v1/search", {"q": se.get("q", "")}, **_auth(api_key))
        result["calls"] += 1
        check(
            "search_status",
            resp.status_code == se.get("expected_status", 200),
            f"got {resp.status_code}, want {se.get('expected_status', 200)}",
        )
        if resp.status_code == 200:
            data = _extract_data(resp, "search", check)
            if data is None:
                data = {}
            text = resp.content.decode("utf-8", "replace")
            if "expected_enrichment_status" in se:
                try:
                    status_val = data["morphology_enrichment"]["status"]
                    check(
                        "search_enrichment",
                        status_val == se["expected_enrichment_status"],
                        f"got {status_val!r}, want {se['expected_enrichment_status']!r}",
                    )
                except Exception as exc:  # noqa: BLE001
                    check("search_enrichment", False, f"unreadable enrichment: {exc}")
            if "expected_text_contains" in se:
                check(
                    "search_text",
                    se["expected_text_contains"] in text,
                    f"want {se['expected_text_contains']!r} in body",
                )
            results_raw = data.get("results", [])
            if not isinstance(results_raw, list):
                check(
                    "search_body",
                    False,
                    f"malformed search response: 'results' must be a list, "
                    f"got {_json_type(results_raw)}",
                )
                results_raw = []
            heads = []
            for entry in results_raw:
                if not isinstance(entry, dict):
                    check(
                        "search_body",
                        False,
                        "malformed search response: 'results' entries must be "
                        f"objects, got {_json_type(entry)}",
                    )
                    heads = []
                    break
                lemma = entry.get("lemma")
                if lemma is not None and not isinstance(lemma, dict):
                    check(
                        "search_body",
                        False,
                        "malformed search response: result 'lemma' must be an "
                        f"object, got {_json_type(lemma)}",
                    )
                    heads = []
                    break
                heads.append((lemma or {}).get("normalized_headword"))
            for hit in se.get("expected_lexical_hits", []):
                check(
                    f"search_lexical:{hit.get('normalized_headword')}",
                    hit.get("normalized_headword") in heads,
                    f"want lexical hit {hit!r} among {heads[:8]!r}",
                )
            morphology = data.get("morphology")
            if morphology is None:
                morphology = {}
            elif not isinstance(morphology, dict):
                check(
                    "search_body",
                    False,
                    "malformed search response: 'morphology' must be an object, "
                    f"got {_json_type(morphology)}",
                )
                morphology = {}
            search_analyses = _reading_list(
                morphology,
                "analyses",
                "morphology.analyses",
                "search",
                check,
                missing_ok=True,
            )
            try:
                s_required = [
                    _resolve(r, lemma_ids) for r in se.get("required_readings", [])
                ]
                s_prohibited = [
                    _resolve(p, lemma_ids) for p in se.get("prohibited_readings", [])
                ]
                s_allowed_extra = [
                    _resolve(a, lemma_ids) for a in se.get("also_allowed", [])
                ]
                for j, pat in enumerate(s_required):
                    _validate_resolved_reading(pat, f"search.required_readings[{j}]")
                for j, pat in enumerate(s_prohibited):
                    _validate_resolved_reading(pat, f"search.prohibited_readings[{j}]")
                for j, pat in enumerate(s_allowed_extra):
                    _validate_resolved_reading(pat, f"search.also_allowed[{j}]")
            except ExpectationError as exc:
                check("search_expectation", False, str(exc))
                s_required, s_prohibited = [], []
            else:
                if s_required and not search_analyses:
                    check(
                        "search_morphology_empty",
                        False,
                        "no morphology analyses in search response to match required readings",
                    )
                for raw, req in zip(se.get("required_readings", []), s_required):
                    found = any(match_reading(a, req)[0] for a in search_analyses)
                    check(
                        f"search_morphology_required:{json.dumps(raw, sort_keys=True)[:80]}",
                        found,
                        "required morphology reading absent from search: "
                        + ", ".join(
                            _summarize_analysis(a) for a in search_analyses[:6]
                        ),
                    )
                for raw, pro in zip(se.get("prohibited_readings", []), s_prohibited):
                    hits = [a for a in search_analyses if match_reading(a, pro)[0]]
                    check(
                        f"search_morphology_prohibited:{json.dumps(raw, sort_keys=True)[:80]}",
                        not hits,
                        "excluded morphology reading exposed through search: "
                        + ", ".join(_summarize_analysis(a) for a in hits[:3]),
                    )
            try:
                result["enrichment"] = data.get("morphology_enrichment", {})
            except Exception:  # noqa: BLE001
                result["enrichment"] = "unreadable"
        check_absent("search", resp.content, se.get("expected_absent"))

    if case.get("round_trip") is not None:
        try:
            rt_reading = _resolve(case["round_trip"]["required_reading"], lemma_ids)
            _validate_resolved_reading(rt_reading, "round_trip.required_reading")
        except ExpectationError as exc:
            check("round_trip_expectation", False, str(exc))
            rt_reading = None
        if rt_reading is None:
            pass
        elif generated_form is None:
            check(
                "round_trip_recovered",
                False,
                "no generated form: generation failed or was refused",
            )
        else:
            resp = client.post(
                "/v1/analyze",
                {"text": generated_form},
                content_type="application/json",
                **_auth(api_key),
            )
            result["calls"] += 1
            if resp.status_code != 200:
                check(
                    "round_trip_recovered",
                    False,
                    f"generated form {generated_form!r} analyzes as {resp.status_code}: "
                    f"{resp.content[:300]!r}",
                )
            else:
                data = _extract_data(resp, "round_trip", check)
                analyses = (
                    _reading_list(
                        data, "analyses", "data.analyses", "round_trip", check
                    )
                    if data is not None
                    else []
                )
                found = any(match_reading(a, rt_reading)[0] for a in analyses)
                check(
                    "round_trip_recovered",
                    found,
                    f"originating reading of generated {generated_form!r} not recovered among "
                    f"{len(analyses)}: "
                    + ", ".join(_summarize_analysis(a) for a in analyses[:6]),
                )

    if not result["scored"] and result["status"] == "fail":
        result["status"] = "fail_unscored"
    result["failures"] = failures
    result["notes"] = notes
    result["triage"] = _triage(case, result)
    return result


def _triage(case: dict, result: dict) -> list[str]:
    """Candidate failure classes for human adjudication (heuristic, not proof).

    Declared categories only; a missing/unpublished fixture is reported as a
    lexical-data gap, never as a linguistic rule defect.
    """
    if result["status"] == "pass":
        return []
    classes: list[str] = []
    failed = {c["name"].split(":")[0] for c in result["checks"] if not c["passed"]}
    if any(n in failed for n in ("generate_status", "analyze_status")):
        exp200 = (
            "generate" in case.get("flows", [])
            and case.get("generate", {}).get("expected_status") == 200
        ) or (
            "analyze" in case.get("flows", [])
            and case.get("analyze", {}).get("expected_status") == 200
        )
        if exp200 and any(
            "got 4" in c.get("detail", "") for c in result["checks"] if not c["passed"]
        ):
            classes.append("unnecessary_refusal_of_supported")
        if any(
            "got 200" in c.get("detail", "")
            for c in result["checks"]
            if not c["passed"]
        ):
            classes.append("invalid_input_handling_failure")
    if "round_trip_recovered" in failed:
        classes.append("generation_analysis_disagreement")
    if any(n.startswith("search_morphology") for n in failed):
        classes.append("search_propagation_defect")
    if any(
        n.startswith("analyze_prohibited")
        or n.startswith("search_morphology_prohibited")
        for n in failed
    ):
        classes.append("linguistic_rule_defect")
    if any(n.startswith("analyze_required") for n in failed):
        classes.append("linguistic_rule_defect_or_lexical_data_gap")
    if not classes:
        classes.append("unclassified_check_failure")
    return sorted(set(classes))


def evaluate(client, api_key: str, corpus: dict, lemma_ids: dict) -> dict:
    return {
        "results": [
            evaluate_case(client, api_key, c, lemma_ids)
            for c in corpus.get("cases", [])
        ]
    }


def create_fixtures(corpus: dict) -> tuple[str, dict[str, str]]:
    """Create the eval release, API key, and reviewed lexical fixtures.

    Returns (raw_api_key, lemma_ids). Callers must already run on an isolated
    database; this function performs writes.
    """
    from shona_api.api_auth.models import APIKey
    from shona_api.editorial.models import ReviewState
    from shona_api.lexicon.models import Lemma, NounClass
    from shona_api.morphology.services import MORPHOLOGY_RULES_VERSION
    from shona_api.releases.models import DataRelease

    DataRelease.objects.create(
        version="eval-release",
        label="eval",
        rule_set_version=MORPHOLOGY_RULES_VERSION,
        is_current=True,
    )
    _, raw_key = APIKey.objects.create_key(
        name="eval", plan=APIKey.Plan.DEVELOPER, rate_limit_per_minute=1000
    )
    for nc in corpus.get("fixtures", {}).get("noun_classes", []):
        NounClass.objects.create(
            class_number=nc["class_number"],
            display_order=int(nc["class_number"])
            if str(nc["class_number"]).isdigit()
            else 900,
            label=nc.get("label", f"Class {nc['class_number']}"),
            nominal_prefix=nc.get("prefix", nc.get("object_concord", "x")),
            subject_concord=nc.get("subject_concord", ""),
            object_concord=nc.get("object_concord", ""),
            review_state=ReviewState.PUBLISHED,
        )
    lemma_ids: dict[str, str] = {}
    for lm in corpus.get("fixtures", {}).get("lemmas", []):
        state = (
            ReviewState.PUBLISHED if lm.get("published", True) else ReviewState.DRAFT
        )
        obj = Lemma.objects.create(
            headword=lm["headword"],
            headword_kind=Lemma.HeadwordKind.VERB_STEM,
            part_of_speech_code=lm.get("pos", "vt"),
            part_of_speech_label=lm.get("pos_label", "verb"),
            provenance={
                "source_key": lm.get("source_key", "eval"),
                "source_location_reference": lm.get("locator", ""),
                "regression_corpus": "source_backed_eval_v1",
            },
            review_state=state,
        )
        lemma_ids[lm["key"]] = obj.public_id
    return raw_key, lemma_ids


def _is_linguistic(case_id: str) -> bool:
    return case_id.startswith("SRC-")


def compute_metrics(corpus: dict, eval_out: dict) -> dict:
    """Predeclared metrics with explicit denominators. No blended accuracy.

    Units (also documented in the protocol and the report):
    - generation_correct: requests [correct, declared supported generate requests].
    - required_recall: readings [recovered, declared required readings].
      Declared = analyze-200 required_readings + search-200 required_readings
      + 1 per round_trip. Numerators count passed per-reading checks; a
      supported request that returns 4xx/5xx or an unreadable body emits no
      (or failing) per-reading checks, so the missing readings count as
      unrecovered. The search empty-aggregate diagnostic
      (search_morphology_empty) is excluded from both counts.
    - prohibited_produced / unadjudicated_extras: readings (counts).
    - supported_refusals: requests [4xx refusals, declared supported
      generate/analyze requests]. Only explicit 4xx counts as a refusal;
      5xx/unreadable stays in the denominator but not the numerator, keeping
      refusals distinguishable from server failures while neither disappears.
    - deferred_invalid_ok: requests [correctly handled, declared deferred
      generate/analyze/search requests].
    - agreement_gen_analyze: cases (1 round-trip each); agreement_analyze_search:
      cases with search morphology expectations. Linguistic vs contract buckets
      are preserved (SRC-* vs CT-*).
    All denominators derive from declared executable expectations, never from
    emitted checks, response status, or body shape. Multi-flow cases contribute
    each flow's expectations independently (e.g. generate-422 + analyze-200
    counts as one deferred request and one supported request).
    """
    cases = {c["case_id"]: c for c in corpus.get("cases", [])}
    results = {r["case_id"]: r for r in eval_out["results"]}
    metrics: dict = {"linguistic": {}, "contract": {}, "overall": {}}

    def scope(case_id: str) -> str:
        return "linguistic" if _is_linguistic(case_id) else "contract"

    for bucket, ids in (
        ("linguistic", [i for i in cases if _is_linguistic(i)]),
        ("contract", [i for i in cases if not _is_linguistic(i)]),
    ):
        scored = [i for i in ids if cases[i].get("scored") and cases[i].get("flows")]
        gen_supported = [
            i
            for i in scored
            if "generate" in cases[i].get("flows", [])
            and cases[i].get("generate", {}).get("expected_status") == 200
        ]
        gen_ok = [
            i for i in gen_supported if _generate_request_ok(cases[i], results[i])
        ]
        req_total = _declared_required_total(cases, scored)
        req_ok = _recovered_required_total(results, scored)
        supported = _supported_requests(cases, scored)
        refused = [
            (i, f) for (i, f) in supported if _supported_request_refused(results[i], f)
        ]
        deferred = _deferred_requests(cases, scored)
        deferred_ok = [
            (i, f)
            for (i, f) in deferred
            if _deferred_request_ok(cases[i], results[i], f)
        ]
        rt_total = [i for i in scored if cases[i].get("round_trip") is not None]
        rt_ok = [i for i in rt_total if _check_pass(results[i], "round_trip_recovered")]
        search_morph = [
            i
            for i in scored
            if "search" in cases[i].get("flows", [])
            and (
                cases[i].get("search", {}).get("required_readings")
                or cases[i].get("search", {}).get("prohibited_readings")
            )
        ]
        search_ok = [i for i in search_morph if _search_morph_pass(results[i])]
        metrics[bucket] = {
            "generation_correct": [len(gen_ok), len(gen_supported)],
            "required_recall": [req_ok, req_total],
            "prohibited_produced": _count_failed(
                results, scored, ("analyze_prohibited", "search_morphology_prohibited")
            ),
            "unadjudicated_extras": sum(
                int(results[i].get("unadjudicated_extras", 0) or 0) for i in scored
            ),
            "supported_refusals": [len(refused), len(supported)],
            "deferred_invalid_ok": [len(deferred_ok), len(deferred)],
            "agreement_gen_analyze": [len(rt_ok), len(rt_total)],
            "agreement_analyze_search": [len(search_ok), len(search_morph)],
        }
    metrics["overall"] = {
        "cases": len(cases),
        "evaluated": sum(1 for c in cases.values() if c.get("flows")),
        "not_evaluated": [
            r["case_id"] for r in eval_out["results"] if r["status"] == "not_evaluated"
        ],
        "unresolved_evidence": [
            i for i, c in cases.items() if c.get("evidence_class") == "unresolved"
        ],
        "endpoint_calls": sum(r.get("calls", 0) for r in eval_out["results"]),
        "unadjudicated_extras": sum(
            int(r.get("unadjudicated_extras", 0) or 0) for r in eval_out["results"]
        ),
    }
    return metrics


def _declared_required_total(cases: dict, scored: list) -> int:
    """Declared required readings (response-independent denominator)."""
    total = 0
    for i in scored:
        case = cases[i]
        if (
            "analyze" in case.get("flows", [])
            and case.get("analyze", {}).get("expected_status") == 200
        ):
            total += len(case.get("analyze", {}).get("required_readings", []) or [])
        if (
            "search" in case.get("flows", [])
            and case.get("search", {}).get("expected_status", 200) == 200
        ):
            total += len(case.get("search", {}).get("required_readings", []) or [])
        if case.get("round_trip") is not None:
            total += 1
    return total


def _recovered_required_total(results: dict, scored: list) -> int:
    """Passed per-reading checks; missing readings count as unrecovered.

    Excludes the search empty-aggregate diagnostic (search_morphology_empty and
    the legacy search_morphology_required:*), which must not add a reading to
    either count.
    """
    recovered = 0
    for i in scored:
        for c in results[i].get("checks", []):
            base = c["name"].split(":")[0]
            if c["name"] in ("search_morphology_required:*", "search_morphology_empty"):
                continue
            if base in (
                "analyze_required",
                "round_trip_recovered",
                "search_morphology_required",
            ):
                recovered += bool(c["passed"])
    return recovered


def _supported_requests(cases: dict, scored: list) -> list:
    """Declared supported generate/analyze requests (response-independent)."""
    out = []
    for i in scored:
        case = cases[i]
        for flow in ("generate", "analyze"):
            if (
                flow in case.get("flows", [])
                and case.get(flow, {}).get("expected_status") == 200
            ):
                out.append((i, flow))
    return out


def _supported_request_refused(result: dict, flow: str) -> bool:
    """True only for an explicit 4xx on a supported request (not 5xx)."""
    status_check = next(
        (c for c in result.get("checks", []) if c["name"] == f"{flow}_status"),
        None,
    )
    return bool(
        status_check
        and not status_check["passed"]
        and "got 4" in status_check.get("detail", "")
    )


def _deferred_requests(cases: dict, scored: list) -> list:
    """Declared deferred generate/analyze/search requests."""
    out = []
    for i in scored:
        case = cases[i]
        for flow in ("generate", "analyze", "search"):
            if flow in case.get("flows", []) and case.get(flow, {}).get(
                "expected_status"
            ) not in (200, None):
                out.append((i, flow))
    return out


def _deferred_request_ok(case: dict, result: dict, flow: str) -> bool:
    """A deferred request is handled iff its flow checks all pass."""
    status_check = next(
        (c for c in result.get("checks", []) if c["name"] == f"{flow}_status"),
        None,
    )
    if status_check is None or not status_check["passed"]:
        return False
    if "expected_code" in case.get(flow, {}):
        code_check = next(
            (c for c in result.get("checks", []) if c["name"] == f"{flow}_code"),
            None,
        )
        if code_check is None or not code_check["passed"]:
            return False
    if flow == "analyze" and "expected_lane" in case.get(flow, {}):
        lane_check = next(
            (c for c in result.get("checks", []) if c["name"] == "analyze_lane"),
            None,
        )
        if lane_check is None or not lane_check["passed"]:
            return False
    for c in result.get("checks", []):
        if c["name"] == f"{flow}_status" or c["name"].startswith(f"{flow}_"):
            if not c["passed"]:
                return False
    return True


def _generate_request_ok(case: dict, result: dict) -> bool:
    """A supported generate request is correct iff status + declared surface /
    rule pass and the body was readable (missing declared checks fail)."""
    checks = {c["name"]: c for c in result.get("checks", [])}
    status_check = checks.get("generate_status")
    if status_check is None or not status_check["passed"]:
        return False
    if any(
        c["name"] == "generate_body" and not c["passed"]
        for c in result.get("checks", [])
    ):
        return False
    if "expected_surface" in case.get("generate", {}):
        surface_check = checks.get("generate_surface")
        if surface_check is None or not surface_check["passed"]:
            return False
    if "expected_rule_id" in case.get("generate", {}):
        rule_check = checks.get("generate_rule")
        if rule_check is None or not rule_check["passed"]:
            return False
    return True


def _checks_pass(result: dict, prefixes: tuple[str, ...]) -> bool:
    relevant = [
        c for c in result.get("checks", []) if c["name"].split(":")[0] in prefixes
    ]
    return bool(relevant) and all(c["passed"] for c in relevant)


def _check_pass(result: dict, name: str) -> bool:
    return any(c["name"] == name and c["passed"] for c in result.get("checks", []))


def _named_checks(
    results: dict, scored: list, prefixes: tuple[str, ...]
) -> tuple[int, int]:
    passed = total = 0
    for i in scored:
        for c in results[i].get("checks", []):
            if c["name"].split(":")[0] in prefixes:
                total += 1
                passed += bool(c["passed"])
    return passed, total


def _count_failed(results: dict, scored: list, prefixes: tuple[str, ...]) -> int:
    return sum(
        1
        for i in scored
        for c in results[i].get("checks", [])
        if c["name"].split(":")[0] in prefixes and not c["passed"]
    )


def _expected_200_got_4xx(case: dict, result: dict) -> bool:
    for flow in ("generate", "analyze"):
        if (
            flow in case.get("flows", [])
            and case.get(flow, {}).get("expected_status") == 200
        ):
            status_check = next(
                (c for c in result.get("checks", []) if c["name"] == f"{flow}_status"),
                None,
            )
            if (
                status_check
                and not status_check["passed"]
                and "got 4" in status_check.get("detail", "")
            ):
                return True
    return False


def _expects_4xx(case: dict) -> bool:
    return any(
        flow in case.get("flows", [])
        and case.get(flow, {}).get("expected_status") not in (200, None)
        for flow in ("generate", "analyze", "search")
    )


def _search_morph_pass(result: dict) -> bool:
    relevant = [
        c
        for c in result.get("checks", [])
        if c["name"].split(":")[0].startswith("search_morphology")
    ]
    return bool(relevant) and all(c["passed"] for c in relevant)


def write_report(
    corpus: dict,
    eval_out: dict,
    metrics: dict,
    code_rev: str,
    dirty: bool,
    evaluator_hash: str,
    out_dir: Path,
) -> Path:
    results = {r["case_id"]: r for r in eval_out["results"]}
    cases = {c["case_id"]: c for c in corpus.get("cases", [])}
    lines = [
        f"# Source-backed evaluation report ({corpus.get('version')})",
        f"Code revision: {code_rev}{' (dirty worktree)' if dirty else ''}",
        f"Evaluator: tools/evaluate_source_backed.py sha256:{evaluator_hash}",
        f"Corpus: {corpus.get('version')} {corpus.get('hash')}",
        f"Cases: {metrics['overall']['cases']} total, "
        f"{metrics['overall']['evaluated']} evaluated, "
        f"{len(metrics['overall']['not_evaluated'])} not evaluated (evidence-only), "
        f"{metrics['overall']['endpoint_calls']} endpoint calls.",
        "",
        "## Metrics (raw numerators/denominators; incompatible measures are not blended)",
    ]
    for bucket in ("linguistic", "contract"):
        m = metrics[bucket]
        lines.append(f"### {bucket}")
        lines.append(
            f"- correct generation among scored supported requests (requests): {m['generation_correct'][0]}/{m['generation_correct'][1]} supported generate requests correct"
        )
        lines.append(
            f"- required-analysis recall (readings: analyze required + round-trip + search morphology required): {m['required_recall'][0]}/{m['required_recall'][1]} readings recovered (missing on 4xx/5xx/unreadable counts as unrecovered; search empty-aggregate excluded)"
        )
        lines.append(
            f"- explicitly prohibited readings produced (readings): {m['prohibited_produced']}"
        )
        lines.append(
            f"- unadjudicated extra analyses (readings): {m['unadjudicated_extras']}"
        )
        lines.append(
            f"- refusals of declared supported requests (requests; 4xx only — 5xx/unreadable stay in denominator): {m['supported_refusals'][0]} of {m['supported_refusals'][1]} supported generate/analyze requests refused"
        )
        lines.append(
            f"- correct deferred/invalid-request handling (requests): {m['deferred_invalid_ok'][0]}/{m['deferred_invalid_ok'][1]} deferred requests handled"
        )
        lines.append(
            f"- generation-to-analysis agreement (cases/round-trips): {m['agreement_gen_analyze'][0]}/{m['agreement_gen_analyze'][1]}"
        )
        lines.append(
            f"- analysis-to-search agreement (cases): {m['agreement_analyze_search'][0]}/{m['agreement_analyze_search'][1]}"
        )
    lines += [
        "",
        f"Unresolved evidence: {len(metrics['overall']['unresolved_evidence'])} "
        f"({', '.join(metrics['overall']['unresolved_evidence'])})",
        f"Not evaluated (evidence-only, no flows): {len(metrics['overall']['not_evaluated'])} "
        f"({', '.join(metrics['overall']['not_evaluated'])})",
        "",
        "## Failures by capability (triage classes are candidates for adjudication)",
    ]
    by_cat: dict[str, list] = {}
    for cid, case in cases.items():
        by_cat.setdefault(case.get("category", "?"), []).append(cid)
    for cat in sorted(by_cat):
        scored = [
            i for i in by_cat[cat] if cases[i].get("scored") and cases[i].get("flows")
        ]
        passed = [i for i in scored if results[i]["status"] == "pass"]
        lines.append(
            f"- {cat}: {len(passed)}/{len(scored)} scored pass ({len(by_cat[cat])} total)"
        )
        for i in scored:
            if results[i]["status"] != "pass":
                lines.append(
                    f"  - FAIL {i} [{','.join(results[i].get('triage', []))}]: "
                    + "; ".join(results[i].get("failures", []))[:320]
                )
        for i in by_cat[cat]:
            if results[i]["status"] == "not_evaluated":
                lines.append(f"  - EVIDENCE-ONLY {i}")
            elif results[i]["status"] == "fail_unscored":
                lines.append(
                    f"  - WATCH-MISMATCH {i}: "
                    + "; ".join(results[i].get("failures", []))[:220]
                )
    lines += [
        "",
        "## Reproduce",
        "python tools/build_source_backed_corpus.py --check-only",
        "python tools/evaluate_source_backed.py --corpus evaluation/source_backed/v1/corpus.json --out evaluation/source_backed/v1/results",
        "pytest tests/test_source_backed_evaluation.py -q",
    ]
    report = "\n".join(lines) + "\n"
    (out_dir / "report.md").write_text(report, encoding="utf-8")
    return out_dir / "report.md"


def _repo_info() -> tuple[str, bool]:
    try:
        rev = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"], capture_output=True, text=True
            ).stdout.strip()
        )
        return rev or "unknown", dirty
    except Exception:  # noqa: BLE001
        return "unknown", False


def _file_hash(path: Path) -> str:
    import hashlib as _hl

    return _hl.sha256(path.read_bytes()).hexdigest()[:16]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    corpus_path = Path(args.corpus)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Isolated temporary database owned by this run. Nothing under --out is
    # ever deleted or replaced; pre-existing files there are left alone.
    tmpdir = tempfile.mkdtemp(prefix="shona-eval-")
    db_path = str(Path(tmpdir) / "eval.sqlite3")
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.eval"
    os.environ["EVAL_DB_PATH"] = db_path

    import django  # noqa: E402

    django.setup()
    from django.db import connections as _connections  # noqa: E402
    from django.test.utils import setup_test_environment as _setup_test_env  # noqa: E402

    _setup_test_env()
    live = os.path.realpath(_connections["default"].settings_dict.get("NAME", ""))
    if os.path.realpath(db_path) != live:
        raise SystemExit(
            f"REFUSING TO RUN: live database {live!r} != intended {db_path!r}. "
            "Aborting before any migration or write."
        )

    from django.core.management import call_command  # noqa: E402

    call_command("migrate", run_syncdb=True, verbosity=0)

    from django.test import Client  # noqa: E402
    from shona_api.morphology.services import MORPHOLOGY_RULES_VERSION  # noqa: E402

    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    try:
        stored_hash = verify_hash(corpus)
        validate_corpus(corpus)
    except CorpusError as exc:
        raise SystemExit(f"REFUSING TO RUN: invalid corpus: {exc}")

    raw_key, lemma_ids = create_fixtures(corpus)

    code_rev, dirty = _repo_info()
    client = Client()
    eval_out = evaluate(client, raw_key, corpus, lemma_ids)
    metrics = compute_metrics(corpus, eval_out)
    payload = {
        "version": corpus.get("version"),
        "corpus_hash": stored_hash,
        "code_revision": code_rev,
        "code_dirty": dirty,
        "evaluator_hash": _file_hash(Path(__file__).resolve()),
        "rule_set_version": MORPHOLOGY_RULES_VERSION,
        "metrics": metrics,
        "results": eval_out["results"],
    }
    if (out_dir / "results.json").exists() or (out_dir / "report.md").exists():
        archive = out_dir / "history"
        archive.mkdir(exist_ok=True)
        import time as _time

        dest = archive / f"run-{int(_time.time())}"
        dest.mkdir(exist_ok=True)
        for name in ("results.json", "report.md"):
            src = out_dir / name
            if src.exists():
                src.rename(dest / name)
    (out_dir / "results.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    report_path = write_report(
        corpus, eval_out, metrics, code_rev, dirty, payload["evaluator_hash"], out_dir
    )
    failed = [r for r in eval_out["results"] if r["status"] == "fail"]
    print(
        f"cases={len(eval_out['results'])} scored_fail={len(failed)} "
        f"db={db_path} report={report_path}"
    )
    for r in failed[:25]:
        print(f"FAIL {r['case_id']}: {'; '.join(r.get('failures', []))[:240]}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
