from tests.fixtures.hannan import iter_hannan_fixture_entries, load_hannan_fixtures


REQUIRED_COVERAGE_TAGS = {
    "comparative_bantu_marker",
    "cross_reference",
    "derivation_marker",
    "dialect_scoped_sense",
    "example_sentence",
    "ideophone",
    "multiple_plural_prefixes",
    "noun_class",
    "tone_pattern",
    "verb_transitivity",
}


def test_hannan_fixture_corpus_has_loader_contract():
    fixtures = load_hannan_fixtures()

    assert fixtures["fixture_format_version"] == "hannan-fixture-v1"
    assert fixtures["source"]["source_key"] == "source_hannan"
    assert fixtures["source"]["source_filename"] == "hannan_dictionary.pdf"
    assert isinstance(fixtures["entries"], list)
    assert len(fixtures["entries"]) >= 8


def test_hannan_fixture_entries_have_required_annotation_shape():
    seen_ids = set()

    for entry in iter_hannan_fixture_entries():
        assert set(entry) >= {
            "id",
            "raw_entry_text",
            "expected_parse",
            "coverage_tags",
            "provenance",
            "annotation",
        }
        assert entry["id"] not in seen_ids
        seen_ids.add(entry["id"])

        assert entry["raw_entry_text"].strip()
        assert entry["coverage_tags"]

        expected_parse = entry["expected_parse"]
        assert set(expected_parse) >= {
            "headword",
            "headword_kind",
            "tone_pattern",
            "dialects",
            "part_of_speech",
            "senses",
        }
        assert expected_parse["headword"]
        assert isinstance(expected_parse["dialects"], list)
        assert isinstance(expected_parse["senses"], list)
        assert expected_parse["senses"]

        for sense in expected_parse["senses"]:
            assert set(sense) >= {
                "number",
                "definition",
                "dialects",
                "grammar",
                "examples",
                "cross_references",
            }
            assert sense["definition"]

        provenance = entry["provenance"]
        assert provenance["source_key"] == "source_hannan"
        assert provenance["source_filename"] == "hannan_dictionary.pdf"
        assert provenance["entry_locator"]
        assert provenance["extraction_method"]

        annotation = entry["annotation"]
        assert annotation["annotator"] == "codex"
        assert annotation["annotated_on"] == "2026-05-12"
        assert "confidence" in annotation
        assert isinstance(annotation["uncertainties"], list)
        assert isinstance(annotation["notes"], list)


def test_hannan_fixture_corpus_covers_representative_notation_patterns():
    observed_tags = {
        tag
        for entry in iter_hannan_fixture_entries()
        for tag in entry["coverage_tags"]
    }

    assert REQUIRED_COVERAGE_TAGS <= observed_tags


def test_hannan_fixture_corpus_records_uncertainty_and_provenance_notes():
    entries = list(iter_hannan_fixture_entries())

    assert any(entry["annotation"]["uncertainties"] for entry in entries)
    assert all(entry["provenance"]["page_reference"] for entry in entries)
