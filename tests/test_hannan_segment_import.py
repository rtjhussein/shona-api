import json

import pytest
from django.core.management import call_command

from shona_api.editorial.models import ReviewState
from shona_api.extraction.models import ExtractionUnit
from shona_api.sources.models import Source


@pytest.fixture
def hannan_source():
    return Source.objects.create(
        source_key="source_hannan",
        title="Hannan Dictionary",
        authority_level="Backbone lexical authority",
        rights_usage_note="Local-only source material; do not upload source file to git.",
        ingestion_style="Digitized dictionary-entry parsing into structured candidates.",
        current_filename="hannan_dictionary.pdf",
    )


def write_jsonl(tmp_path, *entries):
    path = tmp_path / "segments.jsonl"
    path.write_text(
        "".join(json.dumps(entry, ensure_ascii=False) + "\n" for entry in entries),
        encoding="utf-8",
    )
    return path


@pytest.mark.django_db
def test_import_hannan_segments_preserves_dashboard_provenance(
    tmp_path,
    hannan_source,
):
    path = write_jsonl(
        tmp_path,
        {
            "global_entry_number": 83,
            "source_locator": "hannan:page_027:entry_083",
            "headword": "asima",
            "entry_kind": "dictionary_entry",
            "header": "[HLL] n 9",
            "confidence": 93,
            "primary_source_page": 27,
            "source_pages": [27],
            "raw_text": "asima [HLL] n 9 Asthma. <Eng.",
            "warnings": ["human approved after provenance repair"],
            "provenance": {"previous_source_locator": "hannan:page_026:entry_083"},
        },
    )

    call_command("import_hannan_segments", str(path), batch_id="SEG-PROV-001")

    unit = ExtractionUnit.objects.get()
    assert unit.source == hannan_source
    assert unit.source_location_reference == "hannan:page_027:entry_083"
    assert unit.review_state == ReviewState.NEEDS_REVIEW
    assert unit.batch_id == "SEG-PROV-001"
    assert unit.parser_output["primary_source_page"] == 27
    assert unit.parser_output["source_pages"] == [27]
    assert unit.provenance["source_locator"] == "hannan:page_027:entry_083"
    assert unit.provenance["primary_source_page"] == 27
    assert unit.provenance["segmenter_warnings"] == [
        "human approved after provenance repair"
    ]
    assert unit.provenance["previous_source_locator"] == "hannan:page_026:entry_083"


@pytest.mark.django_db
def test_structure_extraction_units_defaults_to_api_approved_segments(hannan_source):
    approved = ExtractionUnit.objects.create(
        source=hannan_source,
        source_location_reference="hannan:page_042:entry_001",
        raw_text="-buda [H] vi Come out.",
        parser_output={
            "headword": "-buda",
            "segmenter_confidence": 100,
            "parse_metadata": {"parser": "hannan-segmenter-v1"},
        },
        parser_name="hannan-segmenter-v1",
        parser_status=ExtractionUnit.ParserStatus.PARSED,
        confidence=1.0,
        review_state=ReviewState.APPROVED,
        provenance={"batch_id": "SEG-PROV-001"},
        batch_id="SEG-PROV-001",
    )
    pending = ExtractionUnit.objects.create(
        source=hannan_source,
        source_location_reference="hannan:page_043:entry_001",
        raw_text="-bata [H] vt Hold.",
        parser_output={
            "headword": "-bata",
            "segmenter_confidence": 100,
            "parse_metadata": {"parser": "hannan-segmenter-v1"},
        },
        parser_name="hannan-segmenter-v1",
        parser_status=ExtractionUnit.ParserStatus.PARSED,
        confidence=1.0,
        review_state=ReviewState.NEEDS_REVIEW,
        provenance={"batch_id": "SEG-PROV-001"},
        batch_id="SEG-PROV-001",
    )

    call_command("structure_extraction_units", batch_id="SEG-PROV-001")

    approved.refresh_from_db()
    pending.refresh_from_db()
    assert approved.parser_name == "hannan-structured-parser-v1"
    assert approved.parser_output["headword"] == "-buda"
    assert pending.parser_name == "hannan-segmenter-v1"
