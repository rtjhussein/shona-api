from __future__ import annotations

from collections.abc import Callable
from typing import Any


CROSS_REFERENCE_SCHEMA_VERSION = "hannan-cross-reference-v1"

TYPE_KEYS = ("type", "kind", "relation")
TARGET_KEYS = ("target", "headword", "text")
NOTE_KEYS = ("source_note", "raw_source", "raw_text", "note")

CrossReferenceResolver = Callable[[str], dict[str, str] | None]


def normalize_cross_references(
    value: Any,
    *,
    resolver: CrossReferenceResolver | None = None,
) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []

    references: list[dict[str, object]] = []
    for item in value:
        reference = normalize_cross_reference(item, resolver=resolver)
        if reference:
            references.append(reference)
    return references


def normalize_cross_reference(
    value: Any,
    *,
    resolver: CrossReferenceResolver | None = None,
) -> dict[str, object]:
    if isinstance(value, str):
        ref_type, target = _split_reference_text(_clean_text(value))
        source_note = _clean_text(value)
        dialects: list[str] = []
        target_public_id = ""
        target_headword = ""
        existing_resolved = None
    elif isinstance(value, dict):
        ref_type = _first_clean_string(value, TYPE_KEYS) or "reference"
        target = _first_clean_string(value, TARGET_KEYS)
        source_note = _first_clean_string(value, NOTE_KEYS)
        dialects = _clean_string_list(value.get("dialects"))
        target_public_id = _clean_text(value.get("target_public_id"))
        target_headword = _clean_text(value.get("target_headword"))
        existing_resolved = (
            bool(value["resolved"]) if isinstance(value.get("resolved"), bool) else None
        )
    else:
        return {}

    if not target:
        return {}

    reference: dict[str, object] = {
        "type": ref_type,
        "target": target,
        "dialects": dialects,
    }
    if source_note:
        reference["source_note"] = source_note
    if target_public_id:
        reference["target_public_id"] = target_public_id
    if target_headword:
        reference["target_headword"] = target_headword
    if existing_resolved is not None:
        reference["resolved"] = existing_resolved
    if resolver:
        resolved_target = resolver(target)
        if resolved_target:
            reference["resolved"] = True
            reference.update(resolved_target)
        elif "resolved" not in reference:
            reference["resolved"] = False
    return reference


def _split_reference_text(value: str) -> tuple[str, str]:
    if not value:
        return "reference", ""
    parts = value.split(maxsplit=1)
    if len(parts) == 2 and parts[0].casefold() in {"cp", "cf", "qv", "see"}:
        return parts[0].casefold(), parts[1].strip(" .")
    return "reference", value.strip(" .")


def _first_clean_string(value: dict[str, object], keys: tuple[str, ...]) -> str:
    for key in keys:
        text = _clean_text(value.get(key))
        if text:
            return text
    return ""


def _clean_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())


def _clean_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_clean_text(item) for item in value if _clean_text(item)]
