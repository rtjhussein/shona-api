import json

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from shona_api.extraction.models import ExtractionUnit
from shona_api.extraction.hannan_import import (
    assemble_hannan_raw_entries,
    build_hannan_batch_payload,
)
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


def write_batch(tmp_path, entries):
    path = tmp_path / "HANNAN-PILOT-001.hannan-batch.json"
    path.write_text(
        json.dumps(
            {
                "format_version": "hannan-local-batch-v1",
                "batch_id": "HANNAN-PILOT-001",
                "entries": entries,
            }
        ),
        encoding="utf-8",
    )
    return path


@pytest.mark.django_db
def test_import_hannan_batch_dry_run_parses_without_creating_records(
    tmp_path,
    hannan_source,
):
    path = write_batch(
        tmp_path,
        [
            {
                "locator": "hannan_dictionary.pdf:p.42:entry:-buda",
                "raw_entry_text": "-buda [H] vi Come out.",
                "confidence": 0.9,
            }
        ],
    )

    call_command("import_hannan_batch", str(path), dry_run=True)

    assert ExtractionUnit.objects.count() == 0


@pytest.mark.django_db
def test_import_hannan_batch_creates_reviewable_extraction_units(
    tmp_path,
    hannan_source,
):
    path = write_batch(
        tmp_path,
        [
            {
                "locator": "hannan_dictionary.pdf:p.42:entry:-buda",
                "raw_entry_text": "-buda [H] vi Come out.",
                "confidence": 0.9,
                "provenance": {"page_reference": "PDF page 42"},
            }
        ],
    )

    call_command("import_hannan_batch", str(path))

    unit = ExtractionUnit.objects.get()
    assert unit.source == hannan_source
    assert unit.source_location_reference == "hannan_dictionary.pdf:p.42:entry:-buda"
    assert unit.parser_output["headword"] == "-buda"
    assert unit.provenance["batch_id"] == "HANNAN-PILOT-001"
    assert unit.provenance["batch_entry_index"] == 1
    assert unit.provenance["page_reference"] == "PDF page 42"


@pytest.mark.django_db
def test_import_hannan_batch_rejects_duplicate_locators(tmp_path, hannan_source):
    duplicate_entry = {
        "locator": "hannan_dictionary.pdf:p.42:entry:-buda",
        "raw_entry_text": "-buda [H] vi Come out.",
    }
    path = write_batch(tmp_path, [duplicate_entry, duplicate_entry])

    with pytest.raises(CommandError, match="Duplicate locator"):
        call_command("import_hannan_batch", str(path))

    assert ExtractionUnit.objects.count() == 0


@pytest.mark.django_db
def test_import_hannan_batch_skips_existing_source_locator(tmp_path, hannan_source):
    path = write_batch(
        tmp_path,
        [
            {
                "locator": "hannan_dictionary.pdf:p.42:entry:-buda",
                "raw_entry_text": "-buda [H] vi Come out.",
            }
        ],
    )

    call_command("import_hannan_batch", str(path))
    call_command("import_hannan_batch", str(path))

    assert ExtractionUnit.objects.count() == 1


def test_assemble_hannan_raw_entries_keeps_multiline_entries_together():
    raw_text = "\n".join(
        [
            "ambuya [HLL]Z n 2b, see vambuya.",
            "ambuyamuderere [LHLLLLH]Z n 2b, pl: va-, vana-, sp",
            "Green praying mantis. cp muputsa- hari M; zimbuyambuya",
            "K.",
            "ambuyawasha [HLLLL]Z n 2b, pl: va-, Wife of man's",
            "brother-in-law. cp mbuya. M; mbuyawasha K.",
        ]
    )

    entries = assemble_hannan_raw_entries(raw_text)

    assert len(entries) == 3
    assert entries[1].start_line == 2
    assert entries[1].end_line == 4
    assert entries[1].raw_entry_text == (
        "ambuyamuderere [LHLLLLH]Z n 2b, pl: va-, vana-, sp "
        "Green praying mantis. cp muputsa- hari M; zimbuyambuya K."
    )


def test_assemble_hannan_raw_entries_uses_unsupported_headers_as_boundaries():
    raw_text = "\n".join(
        [
            "a [H] n 1a & 9. The letter a.",
            "â€ -a- [H]KKoMZ oc [op] 6. Ndakaaona: I saw them.",
            "aa [HH]KMZ inter of Prohibition.",
            "adhiresi [HLLL] n 9 Address. <Eng. cp kero.",
        ]
    )

    entries = assemble_hannan_raw_entries(raw_text)

    assert [entry.raw_entry_text for entry in entries] == [
        "a [H] n 1a & 9. The letter a.",
        "†-a- [H]KKoMZ oc [op] 6. Ndakaaona: I saw them.",
        "aa [HH]KMZ inter of Prohibition.",
        "adhiresi [HLLL] n 9 Address. <Eng. cp kero.",
    ]


def test_assemble_hannan_raw_entries_uses_no_tone_headers_as_boundaries():
    raw_text = "\n".join(
        [
            "-amwa [H] M v t Suck (at breast). cp -mwa K; -yamwa KoZ.",
            "-ana KKoMZ n sfx > diminutive; mbudzi >mbudzana: kid.",
            "kuranga> kurangana: to plot together.",
            "amburenzi [HLLL] n 9 Ambulance. < Eng.",
        ]
    )

    entries = assemble_hannan_raw_entries(raw_text)

    assert [entry.raw_entry_text for entry in entries] == [
        "-amwa [H] M v t Suck (at breast). cp -mwa K; -yamwa KoZ.",
        "-ana KKoMZ n sfx > diminutive; mbudzi >mbudzana: kid. kuranga> kurangana: to plot together.",
        "amburenzi [HLLL] n 9 Ambulance. < Eng.",
    ]


def test_build_hannan_batch_payload_skips_truncated_candidate_entries():
    raw_text = "\n".join(
        [
            "ambuyamuderere [LHLLLLH]Z n 2b, pl: va-, vana-, sp",
            "ambuyawasha [HLLLL]Z n 2b, pl: va-, Wife of man's",
            "brother-in-law. cp mbuya. M; mbuyawasha K.",
        ]
    )

    payload = build_hannan_batch_payload(
        raw_text,
        batch_id="HANNAN-PILOT-001",
        limit=25,
    )

    assert len(payload["entries"]) == 1
    assert payload["entries"][0]["raw_entry_text"].startswith("ambuyawasha")


def test_build_hannan_batch_payload_can_start_at_raw_line():
    raw_text = "\n".join(
        [
            "a [H] n 1a & 9. The letter a.",
            "adhiresi [HLLL] n 9 Address. <Eng. cp kero.",
            "ambuyamuderere [LHLLLLH]Z n 2b, pl: va-, vana-, sp",
            "Green praying mantis. cp muputsa- hari M; zimbuyambuya",
            "K.",
        ]
    )

    payload = build_hannan_batch_payload(
        raw_text,
        batch_id="HANNAN-PILOT-001",
        limit=1,
        start_line=3,
    )

    assert payload["entries"][0]["locator"].startswith(
        "hannan_dictionary.raw.txt:lines-3-5"
    )
    assert payload["entries"][0]["raw_entry_text"].startswith("ambuyamuderere")
