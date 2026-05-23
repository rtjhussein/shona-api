from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from shona_api.lexicon.examples import normalize_example_pairs


GPT_JSONL_V2_SCHEMA_VERSION = "hannan-gpt-jsonl-v2"
GPT_JSONL_V3_SCHEMA_VERSION = "hannan-gpt-jsonl-v3"
NUMBERED_SENSE_RE = re.compile(r"\s+(?=[2-9]\.\s+)")
UNRESOLVED_NUMBERED_SENSE_RE = re.compile(r"\s[2-9]\.\s")
TONE_BRACKET_RE = re.compile(r"^\s*\S+\s+\[(?P<tone>[^\]]+)\]")
TONE_PATTERN_RE = re.compile(r"^[HL]+(?:\s+[HL]+)*$")
NORMALIZER_ERROR_CODES = {
    "invalid_publishable_shape",
    "missing_v2_fields",
    "missing_v3_fields",
    "unparsed_compound_tone",
}
VERB_GRAMMAR_CODES = {"i", "t", "vi", "vt"}
V2_REQUIRED_PARSER_OUTPUT_FIELDS = {
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
    "derived_forms",
    "raw_entry_text",
    "parse_metadata",
    "normalized_headword",
}
V3_REQUIRED_PARSER_OUTPUT_FIELDS = V2_REQUIRED_PARSER_OUTPUT_FIELDS | {
    "idiomatic_expressions",
}


def normalize_gpt_parser_output(
    parser_output: dict[str, Any],
    *,
    raw_text: str = "",
) -> dict[str, Any]:
    output = deepcopy(parser_output)
    if not isinstance(output, dict):
        return {
            "errors": [
                {
                    "code": "invalid_parser_output",
                    "message": "parser_output must be an object.",
                }
            ],
        }

    _clear_normalizer_errors(output)
    if output.get("schema_version") == GPT_JSONL_V2_SCHEMA_VERSION:
        _validate_v2_required_fields(output)
    if output.get("schema_version") == GPT_JSONL_V3_SCHEMA_VERSION:
        _validate_v3_required_fields(output)
    output["senses"] = _normalize_senses(output.get("senses"))
    output["idiomatic_expressions"] = _normalize_idiomatic_expressions(
        output.get("idiomatic_expressions")
    )
    _normalize_tones(output, raw_text=raw_text)
    _validate_publishable_shape(output, raw_text=raw_text)
    return output


def build_tone_record_payloads(parser_output: dict[str, Any]) -> list[dict[str, Any]]:
    tone_records = parser_output.get("tone_records")
    if isinstance(tone_records, list):
        payloads = []
        for record in tone_records:
            if not isinstance(record, dict):
                continue
            pattern = record.get("pattern")
            if not isinstance(pattern, str) or not pattern.strip():
                continue
            payloads.append(
                {
                    "pattern": pattern.strip(),
                    "dialects": _clean_string_list(record.get("dialects")),
                }
            )
        if payloads:
            return payloads

    tone_pattern = parser_output.get("tone_pattern")
    if isinstance(tone_pattern, str) and tone_pattern.strip():
        return [
            {
                "pattern": tone_pattern.strip(),
                "dialects": _clean_string_list(parser_output.get("dialects")),
            }
        ]
    return []


def validate_publishable_parser_output(parser_output: dict[str, Any]) -> list[str]:
    messages: list[str] = []
    for sense in parser_output.get("senses") or []:
        if not isinstance(sense, dict):
            continue
        definition = sense.get("definition")
        if isinstance(definition, str) and UNRESOLVED_NUMBERED_SENSE_RE.search(definition):
            messages.append(
                "Parser output contains unresolved numbered sense markers in a definition."
            )
            break

    tone_pattern = parser_output.get("tone_pattern")
    if isinstance(tone_pattern, str) and _is_malformed_tone_pattern(tone_pattern):
        messages.append("Parser output contains a malformed glued tone pattern.")

    tone_records = parser_output.get("tone_records")
    if isinstance(tone_records, list):
        for record in tone_records:
            if not isinstance(record, dict):
                messages.append("Parser output contains an invalid tone record.")
                break
            pattern = record.get("pattern")
            if not isinstance(pattern, str) or not TONE_PATTERN_RE.fullmatch(pattern.strip()):
                messages.append("Parser output contains an invalid tone record pattern.")
                break
            if not isinstance(record.get("dialects", []), list):
                messages.append("Parser output contains an invalid tone record dialect list.")
                break

    return messages


def _validate_v2_required_fields(output: dict[str, Any]) -> None:
    missing = sorted(V2_REQUIRED_PARSER_OUTPUT_FIELDS.difference(output))
    if not missing:
        return
    _append_error(
        output,
        "missing_v2_fields",
        f"parser_output is missing required v2 fields: {', '.join(missing)}.",
    )


def _validate_v3_required_fields(output: dict[str, Any]) -> None:
    missing = sorted(V3_REQUIRED_PARSER_OUTPUT_FIELDS.difference(output))
    if not missing:
        return
    _append_error(
        output,
        "missing_v3_fields",
        f"parser_output is missing required v3 fields: {', '.join(missing)}.",
    )


def _normalize_senses(raw_senses: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_senses, list):
        return []

    normalized: list[dict[str, Any]] = []
    for raw_sense in raw_senses:
        if not isinstance(raw_sense, dict):
            continue
        normalized.extend(_split_collapsed_sense(raw_sense))

    for index, sense in enumerate(normalized, start=1):
        sense["number"] = index
        sense.setdefault("definition", "")
        sense["dialects"] = _clean_string_list(sense.get("dialects"))
        sense["grammar"] = _clean_string_list(sense.get("grammar"))
        sense["examples"] = _clean_examples(sense.get("examples"))
        sense["cross_references"] = _clean_cross_references(
            sense.get("cross_references")
        )
    return normalized


def _normalize_idiomatic_expressions(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    expressions = []
    for item in value:
        if not isinstance(item, dict):
            continue
        expression_text = _clean_text(item.get("expression_text"))
        idiomatic_meaning = _clean_text(item.get("idiomatic_meaning"))
        english_rendering = _clean_text(item.get("english_rendering"))
        if not expression_text or not (idiomatic_meaning or english_rendering):
            continue
        expressions.append(
            {
                "expression_text": expression_text,
                "idiomatic_meaning": idiomatic_meaning,
                "english_rendering": english_rendering,
                "dialects": _clean_string_list(item.get("dialects")),
                "linked_headwords": _clean_string_list(item.get("linked_headwords")),
                "source_sense_number": _clean_positive_int_or_none(
                    item.get("source_sense_number")
                ),
                "usage_note": _clean_text(item.get("usage_note")),
            }
        )
    return expressions


def _split_collapsed_sense(sense: dict[str, Any]) -> list[dict[str, Any]]:
    definition = sense.get("definition")
    if not isinstance(definition, str) or not UNRESOLVED_NUMBERED_SENSE_RE.search(definition):
        return [dict(sense)]

    parts = [part.strip() for part in NUMBERED_SENSE_RE.split(definition) if part.strip()]
    if len(parts) <= 1:
        return [dict(sense)]

    split_senses = []
    first = dict(sense)
    first["definition"] = _strip_number_marker(parts[0])
    split_senses.append(first)

    for part in parts[1:]:
        clean = _strip_number_marker(part)
        dialects, grammar, clean = _consume_sense_prefix(clean)
        split_senses.append(
            {
                "definition": clean,
                "dialects": dialects,
                "grammar": grammar,
                "examples": [],
                "cross_references": [],
            }
        )
    return split_senses


def _strip_number_marker(text: str) -> str:
    return re.sub(r"^[2-9]\.\s*", "", text).strip()


def _consume_sense_prefix(text: str) -> tuple[list[str], list[str], str]:
    dialects: list[str] = []
    grammar: list[str] = []
    rest = text.strip()

    while rest:
        token, next_rest = _split_first_token(rest)
        parsed_dialects = parse_dialect_cluster(token)
        if parsed_dialects:
            dialects = parsed_dialects
            rest = next_rest
            continue
        if token in VERB_GRAMMAR_CODES:
            grammar = [token]
            rest = next_rest
            continue
        break
    return dialects, grammar, rest


def _normalize_tones(output: dict[str, Any], *, raw_text: str) -> None:
    tone_records = output.get("tone_records")
    if isinstance(tone_records, list):
        cleaned = []
        for record in tone_records:
            if not isinstance(record, dict):
                continue
            pattern = record.get("pattern")
            if not isinstance(pattern, str) or not pattern.strip():
                continue
            cleaned.append(
                {
                    "pattern": pattern.strip(),
                    "dialects": _clean_string_list(record.get("dialects")),
                }
            )
        output["tone_records"] = cleaned
        if len(cleaned) > 1:
            output["tone_pattern"] = None
        return

    bracket_tone = extract_tone_bracket(raw_text or output.get("raw_entry_text", ""))
    if bracket_tone:
        parsed = parse_tone_records(
            bracket_tone,
            entry_dialects=_clean_string_list(output.get("dialects")),
        )
        if parsed:
            output["tone_records"] = parsed
            output["tone_pattern"] = parsed[0]["pattern"] if len(parsed) == 1 else None
            return

    tone_pattern = output.get("tone_pattern")
    if isinstance(tone_pattern, str) and tone_pattern.strip():
        output["tone_records"] = [
            {
                "pattern": tone_pattern.strip(),
                "dialects": _clean_string_list(output.get("dialects")),
            }
        ]
    else:
        output["tone_records"] = []


def extract_tone_bracket(raw_text: str) -> str:
    match = TONE_BRACKET_RE.search(raw_text or "")
    return match.group("tone").strip() if match else ""


def parse_tone_records(
    bracket_tone: str,
    *,
    entry_dialects: list[str] | None = None,
) -> list[dict[str, Any]]:
    entry_dialects = entry_dialects or []
    parts = [part.strip() for part in bracket_tone.split(";") if part.strip()]
    if not parts:
        return []

    records = []
    for part in parts:
        tokens = part.split()
        if not tokens:
            continue
        pattern = tokens[0].strip()
        dialect_text = "".join(tokens[1:]).strip()
        dialects = parse_dialect_cluster(dialect_text) if dialect_text else []
        if not dialects and len(parts) == 1 and TONE_PATTERN_RE.fullmatch(pattern):
            dialects = list(entry_dialects)
        records.append({"pattern": pattern, "dialects": dialects})
    return records


def parse_dialect_cluster(token: str) -> list[str]:
    token = (token or "").strip()
    if not token:
        return []

    dialects: list[str] = []
    index = 0
    while index < len(token):
        if token.startswith("Ko(B)", index):
            dialects.append("Ko(B)")
            index += 5
            continue
        if token.startswith("Ko", index):
            dialects.append("Ko")
            index += 2
            continue
        char = token[index]
        if char in {"K", "M", "Z"}:
            dialects.append(char)
            index += 1
            continue
        return []
    return dialects


def _validate_publishable_shape(output: dict[str, Any], *, raw_text: str) -> None:
    for message in validate_publishable_parser_output(output):
        _append_error(output, "invalid_publishable_shape", message)

    bracket_tone = extract_tone_bracket(raw_text or output.get("raw_entry_text", ""))
    tone_records = output.get("tone_records")
    if ";" in bracket_tone and not (isinstance(tone_records, list) and len(tone_records) > 1):
        _append_error(
            output,
            "unparsed_compound_tone",
            "Compound Hannan tone bracket was not split into multiple tone records.",
        )


def _is_malformed_tone_pattern(pattern: str) -> bool:
    clean = pattern.strip()
    return bool(clean and not TONE_PATTERN_RE.fullmatch(clean))


def _append_error(output: dict[str, Any], code: str, message: str) -> None:
    errors = output.get("errors")
    if not isinstance(errors, list):
        errors = []
    if not any(error.get("code") == code and error.get("message") == message for error in errors if isinstance(error, dict)):
        errors.append({"code": code, "message": message})
    output["errors"] = errors


def _clear_normalizer_errors(output: dict[str, Any]) -> None:
    errors = output.get("errors")
    if not isinstance(errors, list):
        return
    preserved = [
        error
        for error in errors
        if not (
            isinstance(error, dict)
            and error.get("code") in NORMALIZER_ERROR_CODES
        )
    ]
    if preserved:
        output["errors"] = preserved
    else:
        output.pop("errors", None)


def _clean_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _clean_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())


def _clean_positive_int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    return None


def _clean_examples(value: Any) -> list[dict[str, object]]:
    return normalize_example_pairs(value)


def _clean_cross_references(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    references = []
    for item in value:
        if not isinstance(item, dict):
            continue
        ref_type = item.get("type")
        target = item.get("target")
        if isinstance(ref_type, str) and isinstance(target, str):
            references.append(
                {
                    "type": ref_type.strip(),
                    "target": target.strip(),
                    "dialects": _clean_string_list(item.get("dialects")),
                }
            )
    return references


def _split_first_token(text: str) -> tuple[str, str]:
    parts = text.strip().split(maxsplit=1)
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]
