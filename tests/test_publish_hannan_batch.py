import pytest
from django.core.management import call_command

from shona_api.editorial.models import ReviewState
from shona_api.extraction.models import ExtractionUnit
from shona_api.lexicon.models import Lemma
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
def test_publish_hannan_batch_publishes_approved_units_only(hannan_source):
    approved = ExtractionUnit.objects.create_from_parser_output(
        source=hannan_source,
        source_location_reference="hannan_dictionary.pdf:p.42:entry:-buda",
        raw_text="-buda [H] vi Come out.",
        parser_output=parse_hannan_entry("-buda [H] vi Come out."),
        confidence=0.95,
        review_state=ReviewState.APPROVED,
        provenance={"batch_id": "HANNAN-PILOT-001"},
    )
    ExtractionUnit.objects.create_from_parser_output(
        source=hannan_source,
        source_location_reference="hannan_dictionary.pdf:p.43:entry:-bata",
        raw_text="-bata [H] vt Hold.",
        parser_output=parse_hannan_entry("-bata [H] vt Hold."),
        confidence=0.95,
        review_state=ReviewState.NEEDS_REVIEW,
        provenance={"batch_id": "HANNAN-PILOT-001"},
    )

    call_command("publish_hannan_batch", batch_id="HANNAN-PILOT-001")

    approved.refresh_from_db()
    assert approved.review_state == ReviewState.PUBLISHED
    assert approved.canonical_record == Lemma.objects.get(headword="-buda")
    assert Lemma.objects.count() == 1


@pytest.mark.django_db
def test_publish_hannan_batch_dry_run_does_not_publish(hannan_source):
    ExtractionUnit.objects.create_from_parser_output(
        source=hannan_source,
        source_location_reference="hannan_dictionary.pdf:p.42:entry:-buda",
        raw_text="-buda [H] vi Come out.",
        parser_output=parse_hannan_entry("-buda [H] vi Come out."),
        confidence=0.95,
        review_state=ReviewState.APPROVED,
        provenance={"batch_id": "HANNAN-PILOT-001"},
    )

    call_command("publish_hannan_batch", batch_id="HANNAN-PILOT-001", dry_run=True)

    assert Lemma.objects.count() == 0
