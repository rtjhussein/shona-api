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


def gpt_v2_bhogodza_jsonl_record():
    raw_text = (
        "-bhogodza [H KM; LHLH Z]KMZ v t Break (something into pieces [KZ]; "
        "stalk of sugar-cane [KZ]; raw sweet potato [M]). Make to break. "
        "2. KZ Cause to cook a large amount (green mealies, pumpkins)."
    )
    return {
        "source_locator": "hannan:page_041:entry_063:bhogodza",
        "raw_text": raw_text,
        "confidence": 1.0,
        "primary_source_page": 17,
        "source_pages": [17],
        "parser_output": {
            "schema_version": "hannan-gpt-jsonl-v2",
            "headword": "-bhogodza",
            "headword_kind": "verb_stem",
            "part_of_speech": {"code": "v t", "label": "transitive verb"},
            "dialects": ["K", "M", "Z"],
            "comparative_bantu_marker": False,
            "tone_pattern": None,
            "tone_records": [
                {"pattern": "H", "dialects": ["K", "M"]},
                {"pattern": "LHLH", "dialects": ["Z"]},
            ],
            "noun": None,
            "senses": [
                {
                    "number": 1,
                    "definition": (
                        "Break (something into pieces [KZ]; stalk of sugar-cane "
                        "[KZ]; raw sweet potato [M]). Make to break."
                    ),
                    "dialects": [],
                    "grammar": [],
                    "examples": [],
                    "cross_references": [],
                },
                {
                    "number": 2,
                    "definition": (
                        "Cause to cook a large amount (green mealies, pumpkins)."
                    ),
                    "dialects": ["K", "Z"],
                    "grammar": [],
                    "examples": [],
                    "cross_references": [],
                },
            ],
            "derived_forms": [],
            "raw_entry_text": raw_text,
            "parse_metadata": {
                "parser": "gpt-5.5-thinking",
                "completeness": "parsed",
            },
            "normalized_headword": "bhogodza",
        },
        "provenance": {
            "source_filename": "Standard Shona Dictionary - Hannan.pdf",
            "pdf_page_number": 41,
            "actual_page_number": 17,
            "model_name": "gpt-5.5-thinking",
            "compiler": "gpt-5.5-direct-jsonl-v2",
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
def test_ingestion_dashboard_starts_precompiled_jsonl_run(
    staff_user,
    monkeypatch,
    tmp_path,
):
    jsonl_path = tmp_path / "GPT-5.5-20260522-160329.jsonl"
    jsonl_path.write_text(json.dumps(gemini_jsonl_record()) + "\n", encoding="utf-8")
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
            "run_kind": IngestionRun.RunKind.PRECOMPILED_JSONL,
            "jsonl_batch_id": "GPT-5.5-UI-001",
            "jsonl_path": str(jsonl_path),
            "auto_approve": "on",
        },
    )

    assert response.status_code == 200
    run = IngestionRun.objects.get(batch_id="GPT-5.5-UI-001")
    assert run.run_kind == IngestionRun.RunKind.PRECOMPILED_JSONL
    assert run.source_jsonl_path == str(jsonl_path)
    assert run.import_parser_name == "gpt-5.5-thinking"
    assert run.auto_approve is True
    assert run.skip_duplicates is True
    assert started == [run.pk]


@pytest.mark.django_db
def test_ingestion_dashboard_lists_integrated_jsonl_files(
    staff_user,
    monkeypatch,
    tmp_path,
):
    imported_jsonl_path = tmp_path / "GPT-5.5-20260522-160329.jsonl"
    fresh_jsonl_path = tmp_path / "GPT-5.5-20260522-170000.jsonl"
    imported_jsonl_path.write_text(
        json.dumps(gemini_jsonl_record()) + "\n",
        encoding="utf-8",
    )
    fresh_jsonl_path.write_text(
        json.dumps(gemini_jsonl_record("hannan:page_005:entry_002:bango")) + "\n",
        encoding="utf-8",
    )
    IngestionRun.objects.create(
        run_kind=IngestionRun.RunKind.PRECOMPILED_JSONL,
        batch_id="GPT-5.5-IMPORTED-001",
        start_page=1,
        end_page=1,
        parser_repo_path=str(tmp_path),
        pdf_path="",
        output_dir=str(tmp_path),
        source_jsonl_path=str(imported_jsonl_path),
        status=IngestionRun.Status.SUCCEEDED,
        imported_count=12,
        duplicate_count=3,
    )
    monkeypatch.setattr("shona_api.web.views.DEFAULT_OUTPUT_DIR", tmp_path)
    client = Client()
    client.force_login(staff_user)

    response = client.get(reverse("ingestion-jsonl-list"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["folder"] == str(tmp_path)
    files_by_name = {file["name"]: file for file in payload["files"]}
    assert files_by_name[imported_jsonl_path.name]["path"] == str(imported_jsonl_path)
    assert files_by_name[imported_jsonl_path.name]["import_status"] == {
        "state": "imported",
        "label": "Imported",
        "detail": "Batch GPT-5.5-IMPORTED-001: imported 12, duplicates 3.",
        "batch_id": "GPT-5.5-IMPORTED-001",
        "run_status": IngestionRun.Status.SUCCEEDED,
        "imported_count": 12,
        "duplicate_count": 3,
        "dry_run": False,
        "created_at": IngestionRun.objects.get(
            batch_id="GPT-5.5-IMPORTED-001"
        ).created_at.isoformat(),
        "finished_at": "",
    }
    assert files_by_name[fresh_jsonl_path.name]["import_status"] == {
        "state": "not_imported",
        "label": "Not imported",
        "detail": "No import run found for this file.",
    }


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
    IngestionRun.objects.create(
        run_kind=IngestionRun.RunKind.PRECOMPILED_JSONL,
        batch_id="GPT-REFRESH-001",
        start_page=1,
        end_page=1,
        parser_repo_path=str(tmp_path),
        pdf_path="",
        output_dir=str(tmp_path),
        source_jsonl_path=str(tmp_path / "batch.jsonl"),
        jsonl_path=str(tmp_path / "batch.jsonl"),
        status=IngestionRun.Status.RUNNING,
        log_text="Using precompiled JSONL...\n",
    )
    client = Client()
    client.force_login(staff_user)

    response = client.get(reverse("ingestion-dashboard"))

    assert response.status_code == 200
    assert b"GPT-REFRESH-001" in response.content
    assert b"Using precompiled JSONL" in response.content
    assert b"GEMINI-REFRESH-001" not in response.content
    assert b"latest-running-run-id" in response.content
    assert b"data-run-feedback" in response.content
    assert b"Gemini access" not in response.content
    assert b"Gemini fallback" not in response.content


@pytest.mark.django_db
def test_running_gemini_does_not_block_jsonl_import(staff_user, monkeypatch, tmp_path):
    IngestionRun.objects.create(
        batch_id="GEMINI-STUCK-001",
        start_page=35,
        end_page=40,
        parser_repo_path=str(tmp_path),
        pdf_path=str(tmp_path / "hannan.pdf"),
        output_dir=str(tmp_path),
        status=IngestionRun.Status.RUNNING,
    )
    jsonl_path = tmp_path / "GPT-5.5-20260522-160329.jsonl"
    jsonl_path.write_text(json.dumps(gemini_jsonl_record()) + "\n", encoding="utf-8")
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
            "run_kind": IngestionRun.RunKind.PRECOMPILED_JSONL,
            "jsonl_batch_id": "GPT-5.5-UNBLOCKED-001",
            "jsonl_path": str(jsonl_path),
            "auto_approve": "on",
        },
    )

    assert response.status_code == 200
    assert IngestionRun.objects.filter(batch_id="GPT-5.5-UNBLOCKED-001").exists()
    assert started


@pytest.mark.django_db
def test_execute_precompiled_jsonl_run_auto_approves_units(
    hannan_source, staff_user, tmp_path
):
    jsonl_path = tmp_path / "GPT-5.5-20260522-160329.jsonl"
    jsonl_path.write_text(json.dumps(gemini_jsonl_record()) + "\n", encoding="utf-8")
    run = IngestionRun.objects.create(
        run_kind=IngestionRun.RunKind.PRECOMPILED_JSONL,
        batch_id="GPT-5.5-AUTO-001",
        start_page=1,
        end_page=1,
        parser_repo_path=str(tmp_path),
        pdf_path=str(tmp_path / "hannan.pdf"),
        output_dir=str(tmp_path),
        source_jsonl_path=str(jsonl_path),
        import_parser_name="gpt-5.5-thinking",
        auto_approve=True,
        created_by=staff_user,
    )

    execute_ingestion_run(run)
    run.refresh_from_db()

    unit = ExtractionUnit.objects.get(batch_id="GPT-5.5-AUTO-001")
    assert run.status == IngestionRun.Status.SUCCEEDED
    assert run.imported_count == 1
    assert run.publishable_count == 1
    assert unit.parser_name == "gpt-5.5-thinking"
    assert unit.review_state == ReviewState.APPROVED
    assert unit.provenance["input_jsonl_path"] == str(jsonl_path)
    assert IngestionRun.objects.filter(batch_id="GPT-5.5-AUTO-001").count() == 1


@pytest.mark.django_db
def test_direct_gpt_import_records_ingestion_run(hannan_source, tmp_path):
    jsonl_path = tmp_path / "GPT-5.5-direct.jsonl"
    jsonl_path.write_text(json.dumps(gemini_jsonl_record()) + "\n", encoding="utf-8")

    call_command(
        "import_gpt_5_5_parsed",
        str(jsonl_path),
        batch_id="GPT-5.5-DIRECT-001",
        stdout=StringIO(),
    )

    run = IngestionRun.objects.get(batch_id="GPT-5.5-DIRECT-001")
    assert run.run_kind == IngestionRun.RunKind.PRECOMPILED_JSONL
    assert run.status == IngestionRun.Status.SUCCEEDED
    assert run.source_jsonl_path == str(jsonl_path)
    assert run.imported_count == 1
    assert run.duplicate_count == 0


@pytest.mark.django_db
def test_gpt_v2_import_preserves_structured_senses_and_tone_records(
    hannan_source,
    tmp_path,
):
    jsonl_path = tmp_path / "GPT-5.5-v2.jsonl"
    jsonl_path.write_text(
        json.dumps(gpt_v2_bhogodza_jsonl_record()) + "\n",
        encoding="utf-8",
    )

    call_command(
        "import_gpt_5_5_parsed",
        str(jsonl_path),
        batch_id="GPT-5.5-V2-001",
        stdout=StringIO(),
    )

    unit = ExtractionUnit.objects.get(batch_id="GPT-5.5-V2-001")
    assert unit.parser_status == ExtractionUnit.ParserStatus.PARSED
    assert [sense["definition"] for sense in unit.parser_output["senses"]] == [
        (
            "Break (something into pieces [KZ]; stalk of sugar-cane [KZ]; "
            "raw sweet potato [M]). Make to break."
        ),
        "Cause to cook a large amount (green mealies, pumpkins).",
    ]
    assert unit.parser_output["tone_records"] == [
        {"pattern": "H", "dialects": ["K", "M"]},
        {"pattern": "LHLH", "dialects": ["Z"]},
    ]
    assert unit.parser_output["idiomatic_expressions"] == []


@pytest.mark.django_db
def test_gpt_import_normalizes_legacy_collapsed_sense_and_compound_tone(
    hannan_source,
    tmp_path,
):
    record = gpt_v2_bhogodza_jsonl_record()
    record["parser_output"].pop("schema_version")
    record["parser_output"].pop("tone_records")
    record["parser_output"]["tone_pattern"] = "HKM;LHLHZ"
    record["parser_output"]["senses"] = [
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
    ]
    jsonl_path = tmp_path / "GPT-5.5-legacy.jsonl"
    jsonl_path.write_text(json.dumps(record) + "\n", encoding="utf-8")

    call_command(
        "import_gpt_5_5_parsed",
        str(jsonl_path),
        batch_id="GPT-5.5-LEGACY-001",
        stdout=StringIO(),
    )

    unit = ExtractionUnit.objects.get(batch_id="GPT-5.5-LEGACY-001")
    assert unit.parser_status == ExtractionUnit.ParserStatus.PARSED
    assert len(unit.parser_output["senses"]) == 2
    assert unit.parser_output["senses"][1]["dialects"] == ["K", "Z"]
    assert unit.parser_output["tone_pattern"] is None
    assert unit.parser_output["tone_records"] == [
        {"pattern": "H", "dialects": ["K", "M"]},
        {"pattern": "LHLH", "dialects": ["Z"]},
    ]


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
