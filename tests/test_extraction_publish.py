import pytest
from django.contrib.contenttypes.models import ContentType

from shona_api.editorial.models import ReviewState
from shona_api.extraction.models import ExtractionUnit
from shona_api.extraction.services import (
    ExtractionUnitPublishError,
    publish_reviewed_extraction_unit,
)
from shona_api.lexicon.models import Form, Lemma, Sense, ToneRecord
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


@pytest.fixture
def approved_extraction_unit(hannan_source):
    raw_text = "-buda [H] vi i Come out. 2. Fade. > mbudo; rubudiko."
    parsed = parse_hannan_entry(raw_text)

    return ExtractionUnit.objects.create_from_parser_output(
        source=hannan_source,
        source_location_reference="hannan_dictionary.pdf:p.42:entry:-buda",
        raw_text=raw_text,
        parser_output=parsed,
        confidence=0.97,
        review_state=ReviewState.APPROVED,
        provenance={"batch_id": "publish-path-fixture"},
    )


@pytest.mark.django_db
def test_reviewed_extraction_unit_publishes_lemma_senses_tone_and_forms(
    approved_extraction_unit,
):
    bundle = publish_reviewed_extraction_unit(approved_extraction_unit)

    approved_extraction_unit.refresh_from_db()
    assert bundle.extraction_unit == approved_extraction_unit
    assert bundle.lemma.headword == "-buda"
    assert bundle.lemma.part_of_speech_code == "vi"
    assert bundle.lemma.part_of_speech_label == "intransitive verb"
    assert bundle.lemma.review_state == ReviewState.PUBLISHED
    assert [sense.definition for sense in bundle.senses] == ["Come out.", "Fade."]
    assert [tone.pattern for tone in bundle.tone_records] == ["H"]
    assert sorted(form.form_text for form in bundle.forms) == [
        "mbudo",
        "rubudiko",
    ]
    assert approved_extraction_unit.review_state == ReviewState.PUBLISHED
    assert approved_extraction_unit.canonical_record == bundle.lemma
    assert approved_extraction_unit.canonical_record_content_type == ContentType.objects.get_for_model(Lemma)
    assert approved_extraction_unit.canonical_record_object_id == str(bundle.lemma.pk)


@pytest.mark.django_db
def test_publish_copies_provenance_to_each_canonical_record(approved_extraction_unit):
    bundle = publish_reviewed_extraction_unit(approved_extraction_unit)

    shared_provenance_keys = {
        "source_key",
        "source_location_reference",
        "parser",
        "parser_status",
        "extraction_unit_id",
        "parser_uncertainties",
    }

    for record in [bundle.lemma, *bundle.senses, *bundle.tone_records, *bundle.forms]:
        assert shared_provenance_keys.issubset(record.provenance)
        assert record.provenance["source_key"] == "source_hannan"
        assert record.provenance["source_location_reference"] == (
            "hannan_dictionary.pdf:p.42:entry:-buda"
        )
        assert record.provenance["parser"] == "hannan-v1-fixture-parser"
        assert record.provenance["extraction_unit_id"] == str(approved_extraction_unit.pk)

    assert bundle.lemma.provenance["record_type"] == "lemma"
    assert bundle.senses[0].provenance["record_type"] == "sense"
    assert bundle.senses[0].provenance["sense_number"] == 1
    assert bundle.tone_records[0].provenance["record_type"] == "tone_record"
    assert bundle.forms[0].provenance["record_type"] == "form"


@pytest.mark.django_db
def test_publish_rejects_unapproved_extraction_unit(hannan_source):
    unit = ExtractionUnit.objects.create_from_parser_output(
        source=hannan_source,
        source_location_reference="hannan_dictionary.pdf:p.42:entry:-buda",
        raw_text="-buda [H] vi i Come out. 2. Fade. > mbudo; rubudiko.",
        parser_output=parse_hannan_entry("-buda [H] vi i Come out. 2. Fade. > mbudo; rubudiko."),
        confidence=0.8,
        review_state=ReviewState.NEEDS_REVIEW,
    )

    with pytest.raises(ExtractionUnitPublishError, match="approved"):
        publish_reviewed_extraction_unit(unit)

    assert Lemma.objects.count() == 0
    assert Sense.objects.count() == 0
    assert ToneRecord.objects.count() == 0
    assert Form.objects.count() == 0


@pytest.mark.django_db
def test_publish_rejects_failed_parser_output(hannan_source):
    unit = ExtractionUnit.objects.create_from_parser_output(
        source=hannan_source,
        source_location_reference="hannan_dictionary.pdf:p.99:line:12",
        raw_text="not a compact Hannan entry",
        parser_output=parse_hannan_entry("not a compact Hannan entry"),
        confidence=0.1,
        review_state=ReviewState.APPROVED,
    )

    assert unit.parser_status == ExtractionUnit.ParserStatus.FAILED

    with pytest.raises(ExtractionUnitPublishError, match="parser"):
        publish_reviewed_extraction_unit(unit)

    assert Lemma.objects.count() == 0
    assert Sense.objects.count() == 0
    assert ToneRecord.objects.count() == 0
    assert Form.objects.count() == 0


@pytest.mark.django_db
def test_publish_preserves_parser_uncertainty_in_provenance(hannan_source):
    parsed = parse_hannan_entry(
        "-buda [H] vi i Come out. 2. Fade. > mbudo; rubudiko."
    )
    parsed["uncertainties"] = [
        {
            "path": "senses[1].definition",
            "message": "Second sense was editorially inferred from the fixture.",
        }
    ]

    unit = ExtractionUnit.objects.create_from_parser_output(
        source=hannan_source,
        source_location_reference="hannan_dictionary.pdf:p.42:entry:-buda",
        raw_text="-buda [H] vi i Come out. 2. Fade. > mbudo; rubudiko.",
        parser_output=parsed,
        confidence=0.74,
        review_state=ReviewState.APPROVED,
    )

    assert unit.parser_status == ExtractionUnit.ParserStatus.PARSED_WITH_UNCERTAINTY

    bundle = publish_reviewed_extraction_unit(unit)

    assert bundle.lemma.provenance["parser_uncertainties"] == parsed["uncertainties"]
    assert bundle.lemma.provenance["parser_status"] == unit.parser_status
    assert bundle.senses[1].provenance["parser_uncertainties"] == parsed["uncertainties"]


@pytest.mark.django_db
def test_publish_records_audit_hook_for_the_state_change(approved_extraction_unit):
    bundle = publish_reviewed_extraction_unit(approved_extraction_unit)

    assert bundle.audit_log.action == "record_state_changed"
    assert bundle.audit_log.target == approved_extraction_unit
    assert bundle.audit_log.metadata["canonical_record_public_id"] == bundle.lemma.public_id
