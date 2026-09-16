"""Tests for the source-conflict register and its sync onto ReviewNote rows.

The register is the record of what the sources disagree about and what would
settle it. These tests guard the two things that make it usable: that every
entry carries the fields a reader needs, and that syncing is idempotent so it
can be re-run as new records appear.
"""

import json
import sys
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shona_api.editorial.models import ReviewNote, ReviewState
from shona_api.extraction.models import ExtractionUnit
from shona_api.lexicon.models import Lemma
from shona_api.sources.models import Source

REGISTER_PATH = Path("evaluation/conflicts/open.json")

REQUIRED_KEYS = (
    "id",
    "title",
    "field",
    "status",
    "kind",
    "summary",
    "sources",
    "evidence",
    "resolution_needed",
)


def test_every_register_entry_carries_what_a_reader_needs():
    """A conflict without a locator or a resolution path is an opinion, not a finding."""
    register = json.loads(REGISTER_PATH.read_text(encoding="utf-8"))
    conflicts = register["conflicts"]

    assert conflicts, "the register must not be empty"
    ids = [conflict["id"] for conflict in conflicts]
    assert len(ids) == len(set(ids)), "conflict ids must be unique; they key note creation"

    for conflict in conflicts:
        for key in REQUIRED_KEYS:
            assert conflict.get(key), f"{conflict.get('id')}: missing {key}"
        for source in conflict["sources"]:
            assert source.get("source") and source.get("locator"), (
                f"{conflict['id']}: every side of the disagreement needs a source "
                "and a locator; a claim without one cannot be checked"
            )
        assert conflict["status"] in {"open", "mitigated", "resolved"}


@pytest.fixture
def hannan_source():
    return Source.objects.create(
        source_key="source_hannan",
        title="Hannan Dictionary",
        authority_level="Backbone lexical authority",
        rights_usage_note="Local-only.",
        ingestion_style="Digitized.",
        current_filename="hannan_dictionary.pdf",
    )


@pytest.fixture
def register(tmp_path):
    path = tmp_path / "open.json"
    path.write_text(
        json.dumps(
            {
                "version": "test",
                "conflicts": [
                    {
                        "id": "test-conflict",
                        "title": "A disagreement",
                        "field": "noun_class",
                        "status": "open",
                        "kind": "source_conflict",
                        "summary": "Two sources differ.",
                        "sources": [
                            {"source": "Fortune", "locator": "p.1", "claim": "one"},
                            {"source": "Hannan", "locator": "p.2", "claim": "other"},
                        ],
                        "evidence": ["checked"],
                        "resolution_needed": "An expert ruling.",
                        "affected_worklist": str(tmp_path / "worklist.tsv"),
                        "affected_filter": "^mab",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "worklist.tsv").write_text(
        "dict_page\theadword\tclass\tunit_recorded_prefix\tsource_locator\n"
        "028\tbudiriro\t9\tmab-\thannan:page_028:entry_001:budiriro\n"
        "030\tgomo\t5\tmag-\thannan:page_030:entry_002:gomo\n",
        encoding="utf-8",
    )
    return path


@pytest.mark.django_db
def test_sync_notes_only_the_records_the_filter_selects(
    register, hannan_source, tmp_path
):
    """The filter is part of the finding: `^mab` must not capture `mag-` rows."""
    wanted = Lemma.objects.create(headword="budiriro", headword_kind="noun")
    other = Lemma.objects.create(headword="gomo", headword_kind="noun")
    ExtractionUnit.objects.create(
        source=hannan_source,
        source_location_reference="hannan:page_028:entry_001:budiriro",
        raw_text="budiriro [HHHL]KMZ n 9, pl: mab-, Success.",
        parser_output={},
        confidence=1.0,
        canonical_record_object_id=str(budiriro_id := wanted.pk),
    )
    ExtractionUnit.objects.create(
        source=hannan_source,
        source_location_reference="hannan:page_030:entry_002:gomo",
        raw_text="gomo [HL] n 5, pl: mag-, Hill.",
        parser_output={},
        confidence=1.0,
        canonical_record_object_id=str(other.pk),
    )

    call_command("sync_source_conflicts", "--register", str(register), stdout=StringIO())

    noted = {
        note.target_object_id for note in ReviewNote.objects.all()
    }
    assert noted == {str(budiriro_id)}
    assert ReviewNote.objects.get().state == ReviewState.NEEDS_REVIEW


@pytest.mark.django_db
def test_sync_is_idempotent(register, hannan_source):
    """Re-running must not pile up duplicate notes."""
    lemma = Lemma.objects.create(headword="budiriro", headword_kind="noun")
    ExtractionUnit.objects.create(
        source=hannan_source,
        source_location_reference="hannan:page_028:entry_001:budiriro",
        raw_text="budiriro [HHHL]KMZ n 9, pl: mab-, Success.",
        parser_output={},
        confidence=1.0,
        canonical_record_object_id=str(lemma.pk),
    )

    call_command("sync_source_conflicts", "--register", str(register), stdout=StringIO())
    call_command("sync_source_conflicts", "--register", str(register), stdout=StringIO())

    assert ReviewNote.objects.filter(target_object_id=str(lemma.pk)).count() == 1
