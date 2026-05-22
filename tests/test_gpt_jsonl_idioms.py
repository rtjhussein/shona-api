from pathlib import Path

from shona_api.extraction.gpt_jsonl import normalize_gpt_parser_output


def _munhu_v3_parser_output():
    return {
        "schema_version": "hannan-gpt-jsonl-v3",
        "headword": "munhu",
        "headword_kind": "noun",
        "part_of_speech": {"code": "n", "label": "noun"},
        "dialects": ["K", "Ko", "M", "Z"],
        "comparative_bantu_marker": False,
        "tone_pattern": "LL",
        "tone_records": [{"pattern": "LL", "dialects": ["K", "Ko", "M", "Z"]}],
        "noun": {"classes": ["1"], "plural_prefixes": [], "plural_classes": []},
        "senses": [
            {
                "number": 1,
                "definition": "Person.",
                "dialects": [],
                "grammar": [],
                "examples": [],
                "cross_references": [],
            },
            {
                "number": 2,
                "definition": "Part of the ear (antitragus).",
                "dialects": ["K", "M", "Z"],
                "grammar": [],
                "examples": [],
                "cross_references": [],
            },
        ],
        "idiomatic_expressions": [
            {
                "expression_text": " Munhu chivhudzi ",
                "idiomatic_meaning": " commoner (having no authority). ",
                "english_rendering": " commoner (having no authority). ",
                "dialects": ["K", "Z"],
                "linked_headwords": ["munhu"],
                "source_sense_number": None,
                "usage_note": "",
            }
        ],
        "derived_forms": [],
        "raw_entry_text": (
            "munhu [LL]KKoMZ n 1 Person. 2. KMZ Part of the ear "
            "(antitragus). Munhu chivhudzi (KZ): commoner (having no authority)."
        ),
        "parse_metadata": {"parser": "gpt-5.5-thinking", "completeness": "parsed"},
        "normalized_headword": "munhu",
    }


def test_gpt_v3_normalization_preserves_hannan_embedded_idioms():
    raw_text = _munhu_v3_parser_output()["raw_entry_text"]

    normalized = normalize_gpt_parser_output(
        _munhu_v3_parser_output(),
        raw_text=raw_text,
    )

    assert [sense["definition"] for sense in normalized["senses"]] == [
        "Person.",
        "Part of the ear (antitragus).",
    ]
    assert normalized["idiomatic_expressions"] == [
        {
            "expression_text": "Munhu chivhudzi",
            "idiomatic_meaning": "commoner (having no authority).",
            "english_rendering": "commoner (having no authority).",
            "dialects": ["K", "Z"],
            "linked_headwords": ["munhu"],
            "source_sense_number": None,
            "usage_note": "",
        }
    ]
    assert all(
        "Munhu chivhudzi" not in sense["definition"]
        for sense in normalized["senses"]
    )
    assert all(
        example.get("shona") != "Munhu chivhudzi"
        for sense in normalized["senses"]
        for example in sense["examples"]
    )


def test_gpt_v2_normalization_defaults_idiomatic_expressions_to_empty_list():
    parser_output = _munhu_v3_parser_output()
    parser_output["schema_version"] = "hannan-gpt-jsonl-v2"
    parser_output.pop("idiomatic_expressions")

    normalized = normalize_gpt_parser_output(
        parser_output,
        raw_text=parser_output["raw_entry_text"],
    )

    assert normalized["idiomatic_expressions"] == []
    assert "errors" not in normalized


def test_gpt_normalization_accepts_multiword_hannan_tone_patterns():
    parser_output = {
        "schema_version": "hannan-gpt-jsonl-v2",
        "headword": "munhundurwa mukuru",
        "headword_kind": "noun",
        "part_of_speech": {"code": "n", "label": "noun"},
        "dialects": ["K", "Z"],
        "comparative_bantu_marker": False,
        "tone_pattern": "LLHL LHH",
        "tone_records": [{"pattern": "LLHL LHH", "dialects": ["K", "Z"]}],
        "noun": {"classes": ["1"], "plural_prefixes": []},
        "senses": [
            {
                "number": 1,
                "definition": "see munhombororo.",
                "dialects": [],
                "grammar": [],
                "examples": [],
                "cross_references": [
                    {"type": "see", "target": "munhombororo", "dialects": []}
                ],
            }
        ],
        "derived_forms": [],
        "raw_entry_text": (
            "munhundurwa mukuru [LLHL LHH]KZ n 1, see munhombororo."
        ),
        "parse_metadata": {"parser": "gpt-5.5-thinking", "completeness": "parsed"},
        "normalized_headword": "munhundurwa mukuru",
        "errors": [
            {
                "code": "invalid_publishable_shape",
                "message": "Parser output contains a malformed glued tone pattern.",
            },
            {
                "code": "invalid_publishable_shape",
                "message": "Parser output contains an invalid tone record pattern.",
            },
        ],
    }

    normalized = normalize_gpt_parser_output(
        parser_output,
        raw_text=parser_output["raw_entry_text"],
    )

    assert normalized["tone_pattern"] == "LLHL LHH"
    assert normalized["tone_records"] == [{"pattern": "LLHL LHH", "dialects": ["K", "Z"]}]
    assert "errors" not in normalized


def test_gpt_v3_prompt_documents_the_embedded_idiom_lane():
    prompt = Path("docs/data_population/gpt_5_5_jsonl_prompt_v3.md").read_text(
        encoding="utf-8"
    )

    assert "hannan-gpt-jsonl-v3" in prompt
    assert "idiomatic_expressions" in prompt
    assert "Do not put idiomatic expressions in examples." in prompt
    assert "A named Shona expression with a non-literal meaning" in prompt
