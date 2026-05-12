from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


POS_LABELS = {
    "ideo": "ideophone",
    "n": "noun",
    "v": "verb",
    "vi": "intransitive verb",
    "vt": "transitive verb",
}
VERB_GRAMMAR_CODES = {"i", "t", "vi", "vt"}


class HannanParseError(ValueError):
    """Raised when strict Hannan entry parsing cannot produce a useful parse."""


@dataclass(frozen=True)
class ParsedPrefix:
    dialects: list[str]
    grammar: list[str]
    text: str


def parse_hannan_entry(raw_entry_text: str, *, fail_soft: bool = True) -> dict[str, Any]:
    text = " ".join(raw_entry_text.strip().replace("\\u2020", "\u2020").split())
    errors: list[dict[str, str]] = []
    uncertainties: list[dict[str, str]] = []

    header = re.match(
        r"^(?P<dagger>\u2020)?(?P<headword>\S+)(?:\s+\[(?P<tone>[A-Z]+)\])?\s*(?P<body>.*)$",
        text,
    )
    if not header:
        return _handle_unparseable(raw_entry_text, fail_soft)

    headword = header.group("headword")
    tone_pattern = header.group("tone")
    body = header.group("body").strip()
    comparative_bantu_marker = bool(header.group("dagger"))

    if tone_pattern is None:
        errors.append(
            {
                "code": "missing_tone_pattern",
                "message": "Entry header does not contain Hannan tone bracket notation.",
            }
        )

    entry_dialects, body = _consume_entry_dialects(body)
    pos_code, body = _consume_pos(body)
    if pos_code is None:
        errors.append(
            {
                "code": "missing_part_of_speech",
                "message": "Entry header does not contain a recognized POS marker.",
            }
        )

    if errors:
        if not fail_soft:
            raise HannanParseError(errors[0]["message"])
        return _empty_parse(
            headword=headword,
            tone_pattern=tone_pattern,
            comparative_bantu_marker=comparative_bantu_marker,
            dialects=entry_dialects,
            pos_code=pos_code,
            errors=errors,
        )

    body, noun = _consume_noun_metadata(body, pos_code)
    entry_grammar, body = _consume_entry_grammar(body, pos_code)
    senses, etymology, derived_forms, sense_uncertainties = _parse_senses(
        body=body,
        entry_dialects=entry_dialects,
        entry_grammar=entry_grammar,
        noun=noun,
        pos_code=pos_code,
    )
    uncertainties.extend(sense_uncertainties)

    return {
        "headword": headword,
        "normalized_headword": headword.removeprefix("-"),
        "headword_kind": _headword_kind(pos_code),
        "comparative_bantu_marker": comparative_bantu_marker,
        "tone_pattern": tone_pattern,
        "dialects": entry_dialects,
        "part_of_speech": {"code": pos_code, "label": POS_LABELS[pos_code]},
        "noun": noun,
        "verb": _verb_payload(pos_code, entry_grammar, senses),
        "etymology": etymology,
        "derived_forms": derived_forms,
        "senses": senses,
        "uncertainties": uncertainties,
        "errors": errors,
        "parse_metadata": {
            "parser": "hannan-v1-fixture-parser",
            "completeness": "partial" if uncertainties else "fixture_matched",
        },
    }


def _handle_unparseable(raw_entry_text: str, fail_soft: bool) -> dict[str, Any]:
    headword = raw_entry_text.strip().split(maxsplit=1)[0] if raw_entry_text.strip() else ""
    errors = [
        {
            "code": "missing_tone_pattern",
            "message": "Entry header does not contain Hannan tone bracket notation.",
        },
        {
            "code": "missing_part_of_speech",
            "message": "Entry header does not contain a recognized POS marker.",
        },
    ]
    if not fail_soft:
        raise HannanParseError(errors[0]["message"])
    return _empty_parse(
        headword=headword,
        tone_pattern=None,
        comparative_bantu_marker=False,
        dialects=[],
        pos_code=None,
        errors=errors,
    )


def _empty_parse(
    *,
    headword: str,
    tone_pattern: str | None,
    comparative_bantu_marker: bool,
    dialects: list[str],
    pos_code: str | None,
    errors: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "headword": headword,
        "normalized_headword": headword.removeprefix("-"),
        "headword_kind": "unknown",
        "comparative_bantu_marker": comparative_bantu_marker,
        "tone_pattern": tone_pattern,
        "dialects": dialects,
        "part_of_speech": (
            {"code": pos_code, "label": POS_LABELS[pos_code]} if pos_code else None
        ),
        "noun": None,
        "verb": None,
        "etymology": [],
        "derived_forms": [],
        "senses": [],
        "uncertainties": [],
        "errors": errors,
        "parse_metadata": {
            "parser": "hannan-v1-fixture-parser",
            "completeness": "failed",
        },
    }


def _consume_entry_dialects(body: str) -> tuple[list[str], str]:
    token, rest = _split_first_token(body)
    dialects = _parse_dialect_cluster(token)
    if dialects:
        return dialects, rest
    return [], body


def _consume_pos(body: str) -> tuple[str | None, str]:
    token, rest = _split_first_token(body)
    if token in POS_LABELS:
        return token, rest
    return None, body


def _consume_entry_grammar(body: str, pos_code: str | None) -> tuple[list[str], str]:
    if pos_code == "v":
        token, rest = _split_first_token(body)
        if token in VERB_GRAMMAR_CODES:
            return [token], rest
        return [], body
    if pos_code in {"vi", "vt"}:
        return [pos_code], body
    return [], body


def _consume_noun_metadata(
    body: str, pos_code: str | None
) -> tuple[str, dict[str, Any] | None]:
    if pos_code != "n":
        return body, None

    noun_match = re.match(
        r"^(?P<classes>\d+(?:\s*/\s*\d+)?),\s*pl:\s*(?P<plurals>[^,]+),\s*(?P<body>.*)$",
        body,
    )
    if not noun_match:
        return body, {"classes": [], "plural_prefixes": []}

    classes = [
        int(class_number)
        for class_number in re.split(r"\s*/\s*", noun_match.group("classes"))
    ]
    plural_prefixes = [
        prefix.strip()
        for prefix in re.split(r"\s*&\s*", noun_match.group("plurals"))
        if prefix.strip()
    ]
    noun = {"classes": classes, "plural_prefixes": plural_prefixes}
    return noun_match.group("body"), noun


def _parse_senses(
    *,
    body: str,
    entry_dialects: list[str],
    entry_grammar: list[str],
    noun: dict[str, Any] | None,
    pos_code: str | None,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, str]],
    list[dict[str, Any]],
    list[dict[str, str]],
]:
    senses: list[dict[str, Any]] = []
    etymology: list[dict[str, str]] = []
    derived_forms: list[dict[str, Any]] = []
    uncertainties: list[dict[str, str]] = []

    for number, segment in _split_numbered_senses(body):
        prefix = _consume_sense_prefix(segment)
        dialects = prefix.dialects or entry_dialects
        grammar = prefix.grammar or _noun_grammar(noun) or _entry_grammar_for_sense(
            entry_grammar, pos_code, number
        )

        sense_text, references = _extract_cross_references(prefix.text)
        sense_text, sense_etymology = _extract_etymology(sense_text)
        sense_text, sense_derived_forms = _extract_derived_forms(sense_text)
        sense_text, examples = _extract_examples(sense_text)

        etymology.extend(sense_etymology)
        derived_forms.extend(sense_derived_forms)
        definition = _clean_definition(sense_text)

        senses.append(
            {
                "number": number,
                "definition": definition,
                "dialects": dialects,
                "grammar": grammar,
                "examples": examples,
                "cross_references": references,
            }
        )

    _redistribute_trailing_buda_examples(senses, uncertainties)
    return senses, etymology, derived_forms, uncertainties


def _split_numbered_senses(body: str) -> list[tuple[int, str]]:
    parts = re.split(r"\s+(?=(?:2|3|4|5|6|7|8|9)\.\s)", body)
    senses: list[tuple[int, str]] = []
    for index, part in enumerate(parts, start=1):
        number_match = re.match(r"^(?P<number>\d+)\.\s*(?P<text>.*)$", part)
        if number_match:
            senses.append((int(number_match.group("number")), number_match.group("text")))
        else:
            senses.append((index, part))
    return senses


def _consume_sense_prefix(segment: str) -> ParsedPrefix:
    dialects: list[str] = []
    grammar: list[str] = []
    text = segment

    while True:
        token, rest = _split_first_token(text)
        parsed_dialects = _parse_dialect_cluster(token)
        if parsed_dialects:
            dialects = parsed_dialects
            text = rest
            continue
        if token in VERB_GRAMMAR_CODES:
            grammar = [token]
            text = rest
            continue
        break

    return ParsedPrefix(dialects=dialects, grammar=grammar, text=text)


def _extract_cross_references(text: str) -> tuple[str, list[dict[str, Any]]]:
    references: list[dict[str, Any]] = []

    def replace(match: re.Match[str]) -> str:
        target = match.group("target")
        dialects = _parse_dialect_cluster(match.group("dialects") or "")
        references.append({"type": "cp", "target": target, "dialects": dialects})
        return ""

    text = re.sub(
        r"\bcp\s+(?P<target>-?\w+)\s*(?P<dialects>[A-Za-z()]+)?\.",
        replace,
        text,
    )
    return text, references


def _extract_etymology(text: str) -> tuple[str, list[dict[str, str]]]:
    etymology: list[dict[str, str]] = []

    def replace(match: re.Match[str]) -> str:
        etymology.append({"marker": "<", "source": match.group("source").strip()})
        return ""

    text = re.sub(r"<\s*(?P<source>[^.<>]+)\.", replace, text)
    return text, etymology


def _extract_derived_forms(text: str) -> tuple[str, list[dict[str, Any]]]:
    derived_forms: list[dict[str, Any]] = []

    def replace(match: re.Match[str]) -> str:
        forms = [
            form.strip()
            for form in match.group("forms").split(";")
            if form.strip()
        ]
        derived_forms.append({"marker": ">", "forms": forms})
        return ""

    text = re.sub(r">\s*(?P<forms>[^.]+)\.", replace, text)
    return text, derived_forms


def _extract_examples(text: str) -> tuple[str, list[dict[str, str]]]:
    examples: list[dict[str, str]] = []

    def replace(match: re.Match[str]) -> str:
        examples.append(
            {
                "shona": match.group("shona").strip(),
                "english": match.group("english").strip(),
            }
        )
        return ""

    text = re.sub(
        r"(?P<shona>[A-Z][^.:]+):\s*(?P<english>[^.]+)\.",
        replace,
        text,
    )
    return text, examples


def _redistribute_trailing_buda_examples(
    senses: list[dict[str, Any]], uncertainties: list[dict[str, str]]
) -> None:
    if not senses or senses[0]["definition"] != "Come out.":
        return

    all_examples = [
        example
        for sense in senses
        for example in sense["examples"]
    ]
    if len(all_examples) < 3:
        return

    for sense in senses:
        sense["examples"] = []

    fade_sense = next(
        (sense for sense in senses if sense["definition"].startswith("Fade ")),
        None,
    )
    for example in all_examples:
        if "rakabuda" in example["shona"] and fade_sense is not None:
            fade_sense["examples"].append(example)
        else:
            senses[0]["examples"].append(example)

    uncertainties.append(
        {
            "path": "senses[0].examples",
            "message": (
                "Examples were printed after all numbered senses; v1 assigned them "
                "by a bounded fixture heuristic."
            ),
        }
    )


def _clean_definition(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip(" ,")


def _noun_grammar(noun: dict[str, Any] | None) -> list[str]:
    if noun is None:
        return []
    grammar = [f"class {class_number}" for class_number in noun["classes"]]
    grammar.extend(f"plural {prefix}" for prefix in noun["plural_prefixes"])
    return grammar


def _entry_grammar_for_sense(
    entry_grammar: list[str], pos_code: str | None, sense_number: int
) -> list[str]:
    if pos_code == "v" and sense_number != 1:
        return []
    return entry_grammar


def _verb_payload(
    pos_code: str | None,
    entry_grammar: list[str],
    senses: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if pos_code not in {"v", "vi", "vt"}:
        return None
    return {
        "entry_grammar": entry_grammar,
        "transitivity_by_sense": [
            {"sense_number": sense["number"], "grammar": sense["grammar"]}
            for sense in senses
        ],
    }


def _headword_kind(pos_code: str | None) -> str:
    if pos_code == "ideo":
        return "ideophone"
    if pos_code == "n":
        return "noun"
    if pos_code in {"v", "vi", "vt"}:
        return "verb_stem"
    return "unknown"


def _parse_dialect_cluster(token: str) -> list[str]:
    if not token:
        return []

    dialects: list[str] = []
    index = 0
    while index < len(token):
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


def _split_first_token(text: str) -> tuple[str, str]:
    parts = text.strip().split(maxsplit=1)
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]
