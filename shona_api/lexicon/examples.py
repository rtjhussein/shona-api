from __future__ import annotations

from typing import Any


EXAMPLE_SCHEMA_VERSION = "hannan-example-pair-v1"

SHONA_KEYS = ("shona", "text", "source_text", "example")
ENGLISH_KEYS = ("english", "translation", "gloss", "meaning")
NOTE_KEYS = ("source_note", "raw_source", "raw_text", "note")


def normalize_example_pairs(value: Any) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []

    examples: list[dict[str, object]] = []
    for item in value:
        example = normalize_example_pair(item)
        if example:
            examples.append(example)
    return examples


def normalize_example_pair(value: Any) -> dict[str, object]:
    if isinstance(value, str):
        shona = _clean_text(value)
        shona, english = _split_example_text(shona)
        return {"shona": shona, "english": english} if shona or english else {}
    if not isinstance(value, dict):
        return {}

    shona = _first_clean_string(value, SHONA_KEYS)
    english = _first_clean_string(value, ENGLISH_KEYS)
    if shona and not english:
        shona, english = _split_example_text(shona)
    if not shona and not english:
        return {}

    example: dict[str, object] = {
        "shona": shona,
        "english": english,
    }
    source_note = _first_clean_string(value, NOTE_KEYS)
    if source_note and source_note not in {shona, english}:
        example["source_note"] = source_note
    dialects = _clean_string_list(value.get("dialects"))
    if dialects:
        example["dialects"] = dialects
    return example


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


def _split_example_text(value: str) -> tuple[str, str]:
    if ":" not in value:
        return value, ""
    shona, english = value.split(":", 1)
    shona = shona.strip()
    english = english.strip()
    if not shona or not english:
        return value, ""
    return shona, english


def _clean_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_clean_text(item) for item in value if _clean_text(item)]
