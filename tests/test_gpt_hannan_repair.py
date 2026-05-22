from io import StringIO

import pytest
from django.core.management import call_command

from shona_api.editorial.models import ReviewState
from shona_api.extraction.models import ExtractionUnit
from shona_api.lexicon.models import Lemma, Sense, ToneRecord
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
def test_repair_gpt_hannan_structuring_preserves_lemma_and_rebuilds_children(
    hannan_source,
):
    raw_text = (
        "-bhogodza [H KM; LHLH Z]KMZ v t Break (something into pieces [KZ]; "
        "stalk of sugar-cane [KZ]; raw sweet potato [M]). Make to break. "
        "2. KZ Cause to cook a large amount (green mealies, pumpkins)."
    )
    parser_output = {
        "headword": "-bhogodza",
        "headword_kind": "verb_stem",
        "part_of_speech": {"code": "v t", "label": "transitive verb"},
        "dialects": ["K", "M", "Z"],
        "comparative_bantu_marker": False,
        "tone_pattern": "HKM;LHLHZ",
        "senses": [
            {
                "number": 1,
                "definition": (
                    "Break (something into pieces [KZ]; stalk of sugar-cane [KZ]; "
                    "raw sweet potato [M]). Make to break. 2. KZ Cause to cook a "
                    "large amount (green mealies, pumpkins)."
                ),
                "dialects": [],
                "grammar": [],
                "examples": [],
                "cross_references": [],
            }
        ],
        "derived_forms": [],
        "raw_entry_text": raw_text,
        "parse_metadata": {
            "parser": "gpt-5.5-thinking",
            "completeness": "parsed",
        },
    }
    unit = ExtractionUnit.objects.create(
        source=hannan_source,
        source_location_reference="hannan:page_041:entry_063:bhogodza",
        raw_text=raw_text,
        parser_output=parser_output,
        parser_name="gpt-5.5-thinking",
        parser_status=ExtractionUnit.ParserStatus.PARSED,
        confidence=1.0,
        review_state=ReviewState.PUBLISHED,
        batch_id="GPT-5.5-REPAIR-001",
    )
    lemma = Lemma.objects.create(
        headword="-bhogodza",
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        part_of_speech_code="v t",
        part_of_speech_label="transitive verb",
        dialects=["K", "M", "Z"],
        review_state=ReviewState.PUBLISHED,
    )
    unit.canonical_record = lemma
    unit.save(update_fields=("canonical_record_content_type", "canonical_record_object_id"))
    Sense.objects.create(
        lemma=lemma,
        number=1,
        definition=parser_output["senses"][0]["definition"],
        review_state=ReviewState.PUBLISHED,
    )
    bad_tone = ToneRecord.objects.create(
        lemma=lemma,
        pattern="HKM;LHLHZ",
        review_state=ReviewState.PUBLISHED,
    )

    call_command(
        "repair_gpt_hannan_structuring",
        batch_id="GPT-5.5-REPAIR-001",
        stdout=StringIO(),
    )

    unit.refresh_from_db()
    lemma.refresh_from_db()
    assert lemma.public_id
    assert unit.canonical_record == lemma
    assert list(lemma.senses.values_list("number", "definition", "dialects")) == [
        (
            1,
            (
                "Break (something into pieces [KZ]; stalk of sugar-cane [KZ]; "
                "raw sweet potato [M]). Make to break."
            ),
            [],
        ),
        (
            2,
            "Cause to cook a large amount (green mealies, pumpkins).",
            ["K", "Z"],
        ),
    ]
    assert [
        (tone.pattern, tone.dialects, tone.public_id)
        for tone in lemma.tone_records.order_by("created_at", "pk")
    ] == [
        ("H", ["K", "M"], bad_tone.public_id),
        ("LHLH", ["Z"], lemma.tone_records.order_by("created_at", "pk")[1].public_id),
    ]
