import json
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client
from django.urls import reverse

from shona_api.editorial.models import ReviewState
from shona_api.extraction.ingestion import execute_ingestion_run
from shona_api.extraction.models import ExtractionUnit, IngestionRun
from shona_api.lexicon.models import Lemma
from shona_api.sources.models import Source


@pytest.fixture
def staff_user():
    return get_user_model().objects.create_user(
        username="staff",
        password="pass",
        is_staff=True,
    )


@pytest.fixture
def hannan_source():
    return Source.objects.create(
        source_key="source_hannan",
        title="Hannan Dictionary",
        authority_level="Backbone lexical authority",
        rights_usage_note="Local-only source material; do not upload source file to git.",
        ingestion_style="Gemini visual-OCR into structured candidates.",
        current_filename="hannan_dictionary.pdf",
    )


def gemini_jsonl_record(locator="hannan:page_005:entry_001:bamba"):
    return {
        "source_locator": locator,
        "raw_text": "bamba [HH] n 5. Effort.",
        "confidence": 1.0,
        "parser_output": {
            "headword": "bamba",
            "headword_kind": "noun",
            "part_of_speech": {"code": "n", "label": "noun"},
            "dialects": [],
            "comparative_bantu_marker": False,
            "tone_pattern": "HH",
            "senses": [
                {
                    "number": 1,
                    "definition": "Effort.",
                    "dialects": [],
                    "grammar": [],
                    "examples": [],
                    "cross_references": [],
                }
            ],
            "derived_forms": [],
            "parse_metadata": {
                "parser": "gemini-2.5-flash-v1",
                "completeness": "parsed",
            },
        },
        "provenance": {
            "source_filename": "Standard Shona Dictionary - Hannan.pdf",
            "pdf_page_number": 29,
            "actual_page_number": 5,
        },
    }


@pytest.mark.django_db
def test_ingestion_dashboard_requires_staff():
    response = Client().get(reverse("ingestion-dashboard"))

    assert response.status_code == 302
    assert "/admin/login/" in response["Location"]


@pytest.mark.django_db
def test_ingestion_dashboard_starts_staff_run(staff_user, monkeypatch):
    started = []
    monkeypatch.setattr(
        "shona_api.web.views.start_ingestion_run_async",
        lambda run_id: started.append(run_id),
    )
    client = Client()
    client.force_login(staff_user)

    response = client.post(
        reverse("ingestion-run-start"),
        {
            "batch_id": "GEMINI-UI-001",
            "start_page": "29",
            "end_page": "30",
            "auto_publish": "on",
        },
    )

    assert response.status_code == 200
    run = IngestionRun.objects.get(batch_id="GEMINI-UI-001")
    assert run.start_page == 29
    assert run.end_page == 30
    assert run.auto_publish is True
    assert started == [run.pk]


@pytest.mark.django_db
def test_ingestion_dashboard_shows_latest_run_after_refresh(staff_user, tmp_path):
    IngestionRun.objects.create(
        batch_id="GEMINI-REFRESH-001",
        start_page=26,
        end_page=26,
        parser_repo_path=str(tmp_path),
        pdf_path=str(tmp_path / "hannan.pdf"),
        output_dir=str(tmp_path),
        status=IngestionRun.Status.RUNNING,
        log_text="Rendering PDF page 26 as PNG...\n",
    )
    client = Client()
    client.force_login(staff_user)

    response = client.get(reverse("ingestion-dashboard"))

    assert response.status_code == 200
    assert b"GEMINI-REFRESH-001" in response.content
    assert b"Rendering PDF page 26 as PNG" in response.content
    assert b"latest-running-run-id" in response.content


@pytest.mark.django_db
def test_execute_ingestion_run_auto_publishes_parseable_gemini_units(
    hannan_source, staff_user, tmp_path, monkeypatch
):
    jsonl_path = tmp_path / "batch.jsonl"
    jsonl_path.write_text(json.dumps(gemini_jsonl_record()) + "\n", encoding="utf-8")

    monkeypatch.setattr("shona_api.extraction.ingestion.resolve_gemini_key", lambda: "key")
    monkeypatch.setattr("shona_api.extraction.ingestion._validate_run_inputs", lambda run: None)
    monkeypatch.setattr(
        "shona_api.extraction.ingestion._run_parser_pipeline",
        lambda run: jsonl_path,
    )
    run = IngestionRun.objects.create(
        batch_id="GEMINI-AUTO-001",
        start_page=29,
        end_page=29,
        parser_repo_path=str(tmp_path),
        pdf_path=str(tmp_path / "hannan.pdf"),
        output_dir=str(tmp_path),
        auto_publish=True,
        created_by=staff_user,
    )

    execute_ingestion_run(run)
    run.refresh_from_db()

    assert run.status == IngestionRun.Status.SUCCEEDED
    assert run.imported_count == 1
    assert run.publishable_count == 1
    assert run.published_count == 1
    assert ExtractionUnit.objects.get(batch_id="GEMINI-AUTO-001").review_state == ReviewState.PUBLISHED
    assert Lemma.objects.get(headword="bamba").review_state == ReviewState.PUBLISHED


@pytest.mark.django_db
def test_cleanup_non_gemini_fixtures_preserves_published_gemini(hannan_source):
    Lemma.objects.create(
        headword="fixture",
        headword_kind=Lemma.HeadwordKind.WORD,
        review_state=ReviewState.APPROVED,
        provenance={"source_key": "browser_fixture"},
    )
    trusted = Lemma.objects.create(
        headword="bamba",
        headword_kind=Lemma.HeadwordKind.NOUN,
        review_state=ReviewState.PUBLISHED,
        provenance={
            "source_key": "source_hannan",
            "parser": "gemini-2.5-flash-v1",
        },
    )
    ExtractionUnit.objects.create(
        source=hannan_source,
        source_location_reference="fixture:entry",
        raw_text="fixture",
        parser_output={"headword": "fixture"},
        parser_name="hannan-v1-fixture-parser",
        parser_status=ExtractionUnit.ParserStatus.PARSED,
        confidence=0.8,
        review_state=ReviewState.NEEDS_REVIEW,
    )

    stdout = StringIO()
    call_command("cleanup_non_gemini_fixtures", stdout=stdout)
    assert "Would delete 1 non gemini unpublished lemmas." in stdout.getvalue()
    assert Lemma.objects.count() == 2

    call_command("cleanup_non_gemini_fixtures", execute=True)

    assert Lemma.objects.filter(pk=trusted.pk).exists()
    assert Lemma.objects.count() == 1
    assert ExtractionUnit.objects.count() == 0
