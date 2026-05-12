import pytest
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType

from shona_api.editorial.models import ReviewState
from shona_api.extraction.admin import ExtractionUnitAdmin
from shona_api.extraction.models import ExtractionUnit
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
def test_extraction_unit_stores_hannan_parser_output_as_review_candidate(
    hannan_source,
):
    raw_text = "-buda [H] vi Come out. 2. Rise (sun)."
    parsed = parse_hannan_entry(raw_text)

    unit = ExtractionUnit.objects.create_from_parser_output(
        source=hannan_source,
        source_location_reference="hannan_dictionary.pdf:p.42:entry:-buda",
        raw_text=raw_text,
        parser_output=parsed,
        confidence=0.82,
    )

    unit.refresh_from_db()
    assert unit.source == hannan_source
    assert unit.source_key == "source_hannan"
    assert unit.parser_name == "hannan-v1-fixture-parser"
    assert unit.parser_status == ExtractionUnit.ParserStatus.PARSED
    assert unit.review_state == ReviewState.NEEDS_REVIEW
    assert unit.parser_output["headword"] == "-buda"
    assert unit.parser_output["senses"][0]["definition"] == "Come out."
    assert unit.provenance == {
        "source_key": "source_hannan",
        "source_location_reference": "hannan_dictionary.pdf:p.42:entry:-buda",
        "parser": "hannan-v1-fixture-parser",
    }


@pytest.mark.django_db
def test_extraction_unit_represents_failed_parse_for_review(hannan_source):
    raw_text = "not a compact Hannan entry"
    parsed = parse_hannan_entry(raw_text)

    unit = ExtractionUnit.objects.create_from_parser_output(
        source=hannan_source,
        source_location_reference="hannan_dictionary.pdf:p.99:line:12",
        raw_text=raw_text,
        parser_output=parsed,
        confidence=0.1,
    )

    assert unit.parser_status == ExtractionUnit.ParserStatus.FAILED
    assert unit.review_state == ReviewState.NEEDS_REVIEW
    assert unit.parser_output["errors"]


@pytest.mark.django_db
def test_extraction_unit_can_link_to_future_canonical_record(hannan_source):
    unit = ExtractionUnit.objects.create(
        source=hannan_source,
        source_location_reference="hannan_dictionary.pdf:p.42:entry:-buda",
        raw_text="-buda [H] vi Come out.",
        parser_output={"headword": "-buda"},
        parser_name="hannan-v1-fixture-parser",
        parser_status=ExtractionUnit.ParserStatus.PARSED,
        confidence=0.75,
        canonical_record_content_type=ContentType.objects.get_for_model(Source),
        canonical_record_object_id=str(hannan_source.pk),
    )

    assert unit.canonical_record == hannan_source


def test_extraction_unit_admin_exposes_review_queue_filters():
    model_admin = ExtractionUnitAdmin(ExtractionUnit, admin.site)

    assert model_admin.list_display == (
        "source",
        "source_location_reference",
        "parser_name",
        "parser_status",
        "review_state",
        "confidence",
        "created_at",
    )
    assert model_admin.list_filter == (
        "review_state",
        "parser_status",
        "source",
        "parser_name",
        "created_at",
    )
    assert model_admin.search_fields == (
        "source__source_key",
        "source_location_reference",
        "raw_text",
        "parser_output",
    )
