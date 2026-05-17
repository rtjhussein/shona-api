import pytest

from shona_api.editorial.models import ReviewState
from shona_api.extraction.models import ExtractionUnit
from shona_api.extraction.reports import build_batch_quality_report
from shona_api.parsers.hannan import parse_hannan_entry
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


@pytest.mark.django_db
def test_batch_quality_report_summarizes_parser_review_and_publish_states(
    hannan_source,
):
    parsed = parse_hannan_entry("-buda [H] vi Come out.")
    parsed["uncertainties"] = [{"path": "senses[0].definition"}]
    unit = ExtractionUnit.objects.create_from_parser_output(
        source=hannan_source,
        source_location_reference="hannan_dictionary.pdf:p.42:entry:-buda",
        raw_text="-buda [H] vi Come out.",
        parser_output=parsed,
        confidence=0.75,
        review_state=ReviewState.PUBLISHED,
        provenance={"batch_id": "HANNAN-PILOT-001"},
    )
    unit.canonical_record_object_id = "lemma_demo"
    unit.save(update_fields=("canonical_record_object_id", "updated_at"))
    ExtractionUnit.objects.create_from_parser_output(
        source=hannan_source,
        source_location_reference="hannan_dictionary.pdf:p.99:line:12",
        raw_text="not a compact Hannan entry",
        parser_output=parse_hannan_entry("not a compact Hannan entry"),
        confidence=0.1,
        provenance={"batch_id": "HANNAN-PILOT-001"},
    )

    report = build_batch_quality_report("HANNAN-PILOT-001")

    assert report["imported_count"] == 2
    assert report["published_count"] == 1
    assert report["failed_count"] == 1
    assert report["uncertain_count"] == 1
    assert report["parseable_rate"] == 0.5
    assert report["review_state_counts"][ReviewState.PUBLISHED] == 1
    assert report["common_error_codes"][0]["code"] == "missing_tone_pattern"
    assert report["common_uncertainty_codes"] == [
        {"code": "senses[0].definition", "count": 1}
    ]
