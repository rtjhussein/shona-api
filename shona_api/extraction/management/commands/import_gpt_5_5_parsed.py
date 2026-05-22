"""
Import GPT-5.5 pre-parsed Hannan dictionary entries from JSONL into ExtractionUnit records.

Usage:
    python manage.py import_gpt_5_5_parsed path/to/GPT-5.5-THINKING-20260521-183447.gpt-5.5-thinking
    python manage.py import_gpt_5_5_parsed path/to/file.jsonl --dry-run
    python manage.py import_gpt_5_5_parsed path/to/file.jsonl --batch-id GPT-5.5-THINKING-20260521-183447

Expected JSONL line shape:
    {
      "source_locator": "...",
      "raw_text": "...",
      "confidence": 1.0,
      "primary_source_page": 12,
      "source_pages": [12],
      "parser_output": {...},
      "provenance": {...}
    }
"""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from shona_api.editorial.models import ReviewState
from shona_api.extraction.gpt_jsonl import normalize_gpt_parser_output
from shona_api.extraction.models import ExtractionUnit, IngestionRun
from shona_api.sources.models import Source


DEFAULT_PARSER_NAME = "gpt-5.5-thinking"
SOURCE_KEY = "source_hannan"


class Command(BaseCommand):
    help = (
        "Import GPT-5.5 pre-parsed Hannan dictionary entries from JSONL "
        "directly into ExtractionUnit records, preserving the LLM parser structure."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "jsonl_path",
            help="Path to the JSONL file produced from GPT-5.5 parsed Hannan pages.",
        )
        parser.add_argument(
            "--batch-id",
            default=None,
            help=(
                "Batch identifier for this import. "
                "Defaults to the JSONL filename stem."
            ),
        )
        parser.add_argument(
            "--parser-name",
            default=DEFAULT_PARSER_NAME,
            help=(
                "Parser name stored on ExtractionUnit.parser_name and provenance. "
                f"Defaults to {DEFAULT_PARSER_NAME}."
            ),
        )
        parser.add_argument(
            "--source-key",
            default=SOURCE_KEY,
            help=f"Source.source_key to attach extraction units to. Defaults to {SOURCE_KEY}.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and count entries without creating records.",
        )
        parser.add_argument(
            "--skip-duplicates",
            action="store_true",
            default=True,
            help="Skip entries with existing source_location_reference for this source. Default.",
        )
        parser.add_argument(
            "--no-skip-duplicates",
            action="store_false",
            dest="skip_duplicates",
            help="Do not skip duplicate entries. Use with care.",
        )

    def handle(self, *args, **options):
        jsonl_path = Path(options["jsonl_path"])
        if not jsonl_path.exists():
            raise CommandError(f"JSONL file not found: {jsonl_path}")

        batch_id = options["batch_id"] or jsonl_path.stem
        parser_name = _clean_required_string(options["parser_name"], "parser_name")
        source_key = _clean_required_string(options["source_key"], "source_key")
        dry_run = options["dry_run"]
        skip_duplicates = options["skip_duplicates"]

        entries = self._load_jsonl(jsonl_path)
        self.stdout.write(f"Loaded {len(entries)} GPT-5.5 parsed entries from {jsonl_path}")

        validation_report = self._validate_entries(entries)
        if dry_run:
            self._dry_run_report(
                entries=entries,
                batch_id=batch_id,
                parser_name=parser_name,
                source_key=source_key,
                validation_report=validation_report,
            )
            return

        try:
            source = Source.objects.get(source_key=source_key)
        except Source.DoesNotExist as exc:
            raise CommandError(
                f"Source '{source_key}' not found. Run 'python manage.py seed_sources' first, "
                "or pass --source-key with an existing source key."
            ) from exc

        existing_locators = set()
        if skip_duplicates:
            existing_locators = set(
                ExtractionUnit.objects.filter(source=source).values_list(
                    "source_location_reference",
                    flat=True,
                )
            )

        imported_count = 0
        duplicate_count = 0
        skipped_invalid_count = 0
        recorded_run = _find_or_create_ingestion_run(
            batch_id=batch_id,
            jsonl_path=jsonl_path,
            parser_name=parser_name,
            dry_run=dry_run,
            skip_duplicates=skip_duplicates,
        )

        try:
            with transaction.atomic():
                for line_number, entry in entries:
                    locator = _as_non_empty_string(entry.get("source_locator"))
                    if not locator:
                        self.stderr.write(
                            self.style.WARNING(
                                f"Skipping line {line_number}: missing source_locator."
                            )
                        )
                        skipped_invalid_count += 1
                        continue

                    if locator in existing_locators:
                        duplicate_count += 1
                        continue

                    parser_output = entry.get("parser_output")
                    if not isinstance(parser_output, dict):
                        self.stderr.write(
                            self.style.WARNING(
                                f"Skipping line {line_number}: parser_output must be an object."
                            )
                        )
                        skipped_invalid_count += 1
                        continue

                    raw_text = _as_string(entry.get("raw_text"))
                    parser_output = normalize_gpt_parser_output(
                        _with_parser_metadata(parser_output, parser_name),
                        raw_text=raw_text,
                    )
                    confidence = _coerce_confidence(entry.get("confidence", 1.0))
                    parser_status = ExtractionUnit.status_from_parser_output(parser_output)

                    provenance = {
                        "source_key": source_key,
                        "source_location_reference": locator,
                        "parser": parser_name,
                        "batch_id": batch_id,
                        "importer": "import_gpt_5_5_parsed.py",
                        "input_jsonl_path": str(jsonl_path),
                        "input_jsonl_line": line_number,
                    }
                    provenance.update(entry.get("provenance") or {})

                    ExtractionUnit.objects.create(
                        source=source,
                        source_location_reference=locator,
                        raw_text=raw_text,
                        parser_output=parser_output,
                        parser_name=parser_name,
                        parser_status=parser_status,
                        confidence=confidence,
                        review_state=ReviewState.NEEDS_REVIEW,
                        provenance=provenance,
                        batch_id=batch_id,
                    )
                    imported_count += 1
            _finish_recorded_ingestion_run(
                recorded_run,
                status=IngestionRun.Status.SUCCEEDED,
                imported_count=imported_count,
                duplicate_count=duplicate_count,
                log_text=(
                    f"Imported {imported_count} GPT-5.5 parsed entries from {jsonl_path}; "
                    f"skipped {duplicate_count} duplicates; "
                    f"skipped {skipped_invalid_count} invalid entries."
                ),
            )
        except Exception as exc:
            _finish_recorded_ingestion_run(
                recorded_run,
                status=IngestionRun.Status.FAILED,
                error_message=str(exc),
                log_text=f"Import failed: {exc}",
            )
            raise

        self.stdout.write(
            self.style.SUCCESS(
                f"Batch {batch_id}: imported {imported_count} GPT-5.5 parsed entries, "
                f"skipped {duplicate_count} duplicates, "
                f"skipped {skipped_invalid_count} invalid entries."
            )
        )

    def _load_jsonl(self, jsonl_path: Path) -> list[tuple[int, dict]]:
        entries: list[tuple[int, dict]] = []
        with jsonl_path.open("r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    payload = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise CommandError(f"Line {line_number} is not valid JSON: {exc}") from exc
                if not isinstance(payload, dict):
                    raise CommandError(f"Line {line_number} must contain a JSON object.")
                entries.append((line_number, payload))
        if not entries:
            raise CommandError("JSONL file contains no entries.")
        return entries

    def _validate_entries(self, entries: list[tuple[int, dict]]) -> dict[str, int]:
        report = {
            "valid": 0,
            "missing_source_locator": 0,
            "missing_or_invalid_parser_output": 0,
            "missing_raw_text": 0,
        }

        for _line_number, entry in entries:
            is_valid = True

            if not _as_non_empty_string(entry.get("source_locator")):
                report["missing_source_locator"] += 1
                is_valid = False

            if not isinstance(entry.get("parser_output"), dict):
                report["missing_or_invalid_parser_output"] += 1
                is_valid = False

            if not _as_non_empty_string(entry.get("raw_text")):
                report["missing_raw_text"] += 1

            if is_valid:
                report["valid"] += 1

        return report

    def _dry_run_report(
        self,
        *,
        entries: list[tuple[int, dict]],
        batch_id: str,
        parser_name: str,
        source_key: str,
        validation_report: dict[str, int],
    ) -> None:
        self.stdout.write(self.style.WARNING("\nDRY RUN: no records created\n"))
        self.stdout.write(f"Batch ID: {batch_id}")
        self.stdout.write(f"Parser name: {parser_name}")
        self.stdout.write(f"Source key: {source_key}")
        self.stdout.write(f"Total JSONL entries: {len(entries)}")
        self.stdout.write(f"Valid importable entries: {validation_report['valid']}")
        self.stdout.write(
            f"Missing source_locator: {validation_report['missing_source_locator']}"
        )
        self.stdout.write(
            "Missing or invalid parser_output: "
            f"{validation_report['missing_or_invalid_parser_output']}"
        )
        self.stdout.write(f"Missing raw_text: {validation_report['missing_raw_text']}")

        headword_kinds: dict[str, int] = {}
        pos_codes: dict[str, int] = {}

        for _line_number, entry in entries:
            parser_output = entry.get("parser_output")
            if not isinstance(parser_output, dict):
                continue

            kind = parser_output.get("headword_kind", "unknown")
            headword_kinds[kind] = headword_kinds.get(kind, 0) + 1

            pos = parser_output.get("part_of_speech") or {}
            if isinstance(pos, dict):
                pos_code = pos.get("code", "unknown")
            else:
                pos_code = "unknown"
            pos_codes[pos_code] = pos_codes.get(pos_code, 0) + 1

        self.stdout.write("\nHeadword kinds:")
        for kind, count in sorted(headword_kinds.items()):
            self.stdout.write(f"  {kind}: {count}")

        self.stdout.write("\nPart of speech codes:")
        for code, count in sorted(pos_codes.items()):
            self.stdout.write(f"  {code}: {count}")

        self.stdout.write("")


def _with_parser_metadata(parser_output: dict, parser_name: str) -> dict:
    output = dict(parser_output)
    parse_metadata = output.get("parse_metadata")
    if not isinstance(parse_metadata, dict):
        parse_metadata = {}
    parse_metadata = {
        **parse_metadata,
        "parser": parser_name,
        "completeness": parse_metadata.get("completeness", "parsed"),
    }
    output["parse_metadata"] = parse_metadata
    return output


def _coerce_confidence(value) -> float:
    if isinstance(value, bool):
        raise CommandError("confidence must be a number from 0.0 to 1.0.")
    if not isinstance(value, (int, float)):
        raise CommandError("confidence must be a number from 0.0 to 1.0.")
    confidence = float(value)
    if not 0.0 <= confidence <= 1.0:
        raise CommandError("confidence must be a number from 0.0 to 1.0.")
    return confidence


def _clean_required_string(value, field_name: str) -> str:
    clean = _as_non_empty_string(value)
    if not clean:
        raise CommandError(f"{field_name} cannot be blank.")
    return clean


def _as_non_empty_string(value) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _as_string(value) -> str:
    if value is None:
        return ""
    return str(value)


def _find_or_create_ingestion_run(
    *,
    batch_id: str,
    jsonl_path: Path,
    parser_name: str,
    dry_run: bool,
    skip_duplicates: bool,
) -> IngestionRun | None:
    if dry_run:
        return None
    existing_run = (
        IngestionRun.objects.filter(
            batch_id=batch_id,
            run_kind=IngestionRun.RunKind.PRECOMPILED_JSONL,
            status=IngestionRun.Status.RUNNING,
        )
        .order_by("-created_at")
        .first()
    )
    if existing_run:
        return None
    now = timezone.now()
    return IngestionRun.objects.create(
        run_kind=IngestionRun.RunKind.PRECOMPILED_JSONL,
        batch_id=batch_id,
        start_page=1,
        end_page=1,
        parser_repo_path=str(jsonl_path.parent.parent),
        pdf_path="",
        output_dir=str(jsonl_path.parent),
        source_jsonl_path=str(jsonl_path),
        jsonl_path=str(jsonl_path),
        import_parser_name=parser_name,
        status=IngestionRun.Status.RUNNING,
        dry_run=dry_run,
        skip_duplicates=skip_duplicates,
        started_at=now,
    )


def _finish_recorded_ingestion_run(
    run: IngestionRun | None,
    *,
    status: str,
    imported_count: int = 0,
    duplicate_count: int = 0,
    log_text: str = "",
    error_message: str = "",
) -> None:
    if run is None:
        return
    run.status = status
    run.imported_count = imported_count
    run.duplicate_count = duplicate_count
    run.error_message = error_message
    if log_text:
        run.append_log(log_text)
    run.finished_at = timezone.now()
    run.save()
