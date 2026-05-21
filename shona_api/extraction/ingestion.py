from __future__ import annotations

import io
import os
import re
import subprocess
import sys
import threading
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.db import close_old_connections
from django.utils import timezone

from shona_api.editorial.models import ReviewState

from .models import ExtractionUnit, IngestionRun
from .services import ExtractionUnitPublishError, publish_reviewed_extraction_unit


TRUSTED_GEMINI_PARSER = "gemini-2.5-flash-v1"
LOCAL_GEMINI_ENV_PATH = Path(settings.BASE_DIR) / ".local_gemini.env"
DEFAULT_PARSER_REPO_PATH = (
    Path(settings.BASE_DIR).parent / "parsers" / "hannan-parser"
)
DEFAULT_PDF_PATH = (
    DEFAULT_PARSER_REPO_PATH / "Standard Shona Dictionary - Hannan.pdf"
)
DEFAULT_OUTPUT_DIR = DEFAULT_PARSER_REPO_PATH / "llm_extracted_batches"


def read_saved_gemini_key() -> str:
    if not LOCAL_GEMINI_ENV_PATH.exists():
        return ""
    for line in LOCAL_GEMINI_ENV_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("GEMINI_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"')
    return ""


def save_gemini_key(raw_key: str) -> None:
    key = raw_key.strip()
    if not key:
        raise ValueError("Gemini API key cannot be blank.")
    LOCAL_GEMINI_ENV_PATH.write_text(
        f'GEMINI_API_KEY="{key}"\n',
        encoding="utf-8",
    )


def resolve_gemini_key() -> str:
    return os.environ.get("GEMINI_API_KEY", "").strip() or read_saved_gemini_key()


def build_ingestion_readiness() -> dict[str, object]:
    parser_repo = DEFAULT_PARSER_REPO_PATH
    pdf_path = DEFAULT_PDF_PATH
    return {
        "gemini_key_configured": bool(resolve_gemini_key()),
        "gemini_key_source": "environment"
        if os.environ.get("GEMINI_API_KEY")
        else ("local env file" if read_saved_gemini_key() else ""),
        "parser_repo_path": str(parser_repo),
        "parser_repo_exists": parser_repo.exists(),
        "pdf_path": str(pdf_path),
        "pdf_exists": pdf_path.exists(),
        "extract_script_exists": (parser_repo / "parse_page_29_test.py").exists(),
        "compile_script_exists": (parser_repo / "compile_llm_batches.py").exists(),
        "output_dir": str(DEFAULT_OUTPUT_DIR),
    }


def start_ingestion_run_async(run_id: int) -> None:
    thread = threading.Thread(
        target=_thread_entrypoint,
        args=(run_id,),
        daemon=True,
    )
    thread.start()


def _thread_entrypoint(run_id: int) -> None:
    close_old_connections()
    try:
        execute_ingestion_run(IngestionRun.objects.get(pk=run_id))
    finally:
        close_old_connections()


def execute_ingestion_run(run: IngestionRun) -> IngestionRun:
    if run.status == IngestionRun.Status.RUNNING:
        return run

    run.status = IngestionRun.Status.RUNNING
    run.started_at = timezone.now()
    run.error_message = ""
    run.append_log(f"Starting {run.page_label} for batch {run.batch_id}.")
    run.save()

    try:
        _validate_run_inputs(run)
        jsonl_path = _run_parser_pipeline(run)
        run.jsonl_path = str(jsonl_path)
        run.save(update_fields=("jsonl_path", "log_text"))
        _import_jsonl(run, jsonl_path)
        if run.auto_publish and not run.dry_run:
            _auto_publish_run(run)
        run.status = IngestionRun.Status.SUCCEEDED
        run.append_log("Pipeline completed.")
    except Exception as exc:
        run.status = IngestionRun.Status.FAILED
        run.error_message = str(exc)
        run.append_log(f"Pipeline failed: {exc}")
    finally:
        run.finished_at = timezone.now()
        run.save()
    return run


def _validate_run_inputs(run: IngestionRun) -> None:
    if run.end_page < run.start_page:
        raise ValueError("End page must be greater than or equal to start page.")
    if not resolve_gemini_key():
        raise ValueError("GEMINI_API_KEY is not configured.")
    parser_repo = Path(run.parser_repo_path)
    pdf_path = Path(run.pdf_path)
    if not parser_repo.exists():
        raise ValueError(f"Parser repo not found: {parser_repo}")
    if not pdf_path.exists():
        raise ValueError(f"Hannan PDF not found: {pdf_path}")
    for script_name in ("parse_page_29_test.py", "compile_llm_batches.py"):
        if not (parser_repo / script_name).exists():
            raise ValueError(f"Parser script not found: {script_name}")


def _run_parser_pipeline(run: IngestionRun) -> Path:
    parser_repo = Path(run.parser_repo_path)
    output_dir = Path(run.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_dir / f"{run.batch_id}.gemini.jsonl"

    extract_cmd = [
        sys.executable,
        "-u",
        "parse_page_29_test.py",
        "--start-page",
        str(run.start_page),
        "--end-page",
        str(run.end_page),
        "--pdf-path",
        run.pdf_path,
        "--output-dir",
        str(output_dir),
    ]
    if run.overwrite_pages:
        extract_cmd.append("--overwrite")

    compile_cmd = [
        sys.executable,
        "-u",
        "compile_llm_batches.py",
        "--input-dir",
        str(output_dir),
        "--output-jsonl",
        str(jsonl_path),
        "--start-page",
        str(run.start_page),
        "--end-page",
        str(run.end_page),
    ]

    _run_subprocess(run, extract_cmd, parser_repo)
    _run_subprocess(run, compile_cmd, parser_repo)
    return jsonl_path


def _run_subprocess(run: IngestionRun, command: list[str], cwd: Path) -> None:
    run.append_log(f"$ {' '.join(command)}")
    run.save(update_fields=("log_text",))
    env = os.environ.copy()
    env["GEMINI_API_KEY"] = resolve_gemini_key()
    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert process.stdout is not None
    for line in process.stdout:
        run.append_log(line)
        run.save(update_fields=("log_text",))
    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"Command failed with exit code {return_code}.")


def _import_jsonl(run: IngestionRun, jsonl_path: Path) -> None:
    before_count = ExtractionUnit.objects.filter(
        batch_id=run.batch_id,
        parser_name=TRUSTED_GEMINI_PARSER,
    ).count()
    stdout = io.StringIO()
    stderr = io.StringIO()
    call_command(
        "import_gemini_parsed",
        str(jsonl_path),
        batch_id=run.batch_id,
        dry_run=run.dry_run,
        stdout=stdout,
        stderr=stderr,
    )
    command_output = "\n".join(
        part for part in (stdout.getvalue().strip(), stderr.getvalue().strip()) if part
    )
    if command_output:
        run.append_log(command_output)

    after_count = ExtractionUnit.objects.filter(
        batch_id=run.batch_id,
        parser_name=TRUSTED_GEMINI_PARSER,
    ).count()
    duplicate_match = re.search(r"skipped (\d+) duplicates", command_output)
    run.imported_count = max(after_count - before_count, 0)
    run.duplicate_count = int(duplicate_match.group(1)) if duplicate_match else 0
    run.save(update_fields=("imported_count", "duplicate_count", "log_text"))


def _auto_publish_run(run: IngestionRun) -> None:
    units = ExtractionUnit.objects.filter(
        batch_id=run.batch_id,
        parser_name=TRUSTED_GEMINI_PARSER,
        review_state=ReviewState.NEEDS_REVIEW,
        canonical_record_object_id="",
    ).exclude(parser_status=ExtractionUnit.ParserStatus.FAILED)

    publishable = [
        unit for unit in units.order_by("source_location_reference", "pk")
        if not (unit.parser_output or {}).get("errors")
    ]
    run.publishable_count = len(publishable)
    run.append_log(f"Auto-publish enabled for {run.publishable_count} parseable unit(s).")
    run.save(update_fields=("publishable_count", "log_text"))

    if not publishable:
        return

    ExtractionUnit.objects.filter(pk__in=[unit.pk for unit in publishable]).update(
        review_state=ReviewState.APPROVED,
    )

    published = 0
    failed = 0
    for unit in publishable:
        unit.refresh_from_db()
        try:
            publish_reviewed_extraction_unit(unit, decided_by=run.created_by)
        except ExtractionUnitPublishError as exc:
            failed += 1
            run.append_log(f"Could not publish {unit.source_location_reference}: {exc}")
            continue
        published += 1

    run.published_count = published
    run.failed_publish_count = failed
    run.append_log(f"Auto-published {published} unit(s); {failed} failed.")
    run.save(
        update_fields=(
            "published_count",
            "failed_publish_count",
            "log_text",
        )
    )
