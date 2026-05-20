"""
Import Gemini pre-parsed Hannan dictionary entries from JSONL into ExtractionUnit records.

Usage:
    python manage.py import_gemini_parsed path/to/hannan_gemini_batch.jsonl
    python manage.py import_gemini_parsed hannan_gemini_batch.jsonl --dry-run
    python manage.py import_gemini_parsed hannan_gemini_batch.jsonl --batch-id GEMINI-2026-05-21
"""

import json
import uuid
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from shona_api.editorial.models import ReviewState
from shona_api.extraction.models import ExtractionUnit
from shona_api.sources.models import Source


PARSER_NAME = "gemini-2.5-flash-v1"
SOURCE_KEY = "source_hannan"


class Command(BaseCommand):
    help = (
        "Import Gemini pre-parsed Hannan dictionary entries from JSONL "
        "directly into ExtractionUnit records, preserving structure."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "jsonl_path",
            help="Path to the consolidated JSONL file from compile_llm_batches.py.",
        )
        parser.add_argument(
            "--batch-id",
            default=None,
            help=(
                "Batch identifier for this import. "
                "Auto-generated if not provided."
            ),
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
            help="Skip entries with existing source_location_reference (default).",
        )
        parser.add_argument(
            "--no-skip-duplicates",
            action="store_false",
            dest="skip_duplicates",
            help="Do not skip duplicate entries; allow re-importing.",
        )

    def handle(self, *args, **options):
        jsonl_path = Path(options["jsonl_path"])
        if not jsonl_path.exists():
            raise CommandError(f"JSONL file not found: {jsonl_path}")

        dry_run = options["dry_run"]
        skip_duplicates = options["skip_duplicates"]
        batch_id = options["batch_id"] or f"GEMINI-{uuid.uuid4().hex[:8].upper()}"

        # Load entries from JSONL
        entries = []
        with jsonl_path.open("r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError as exc:
                    self.stderr.write(
                        self.style.WARNING(
                            f"Skipping malformed line {line_num}: {exc}"
                        )
                    )
                    continue
                entries.append(entry)

        self.stdout.write(
            f"Loaded {len(entries)} pre-parsed entries from {jsonl_path}"
        )

        if dry_run:
            self._dry_run_report(entries, batch_id)
            return

        # Get the Hannan source record
        try:
            source = Source.objects.get(source_key=SOURCE_KEY)
        except Source.DoesNotExist:
            raise CommandError(
                f"Source '{SOURCE_KEY}' not found. "
                f"Run 'manage.py seed_sources' first."
            )

        # Collect existing locators for deduplication
        existing_locators = set()
        if skip_duplicates:
            existing_locators = set(
                ExtractionUnit.objects.filter(
                    source=source,
                ).values_list(
                    "source_location_reference", flat=True
                )
            )

        imported_count = 0
        duplicate_count = 0

        with transaction.atomic():
            for entry in entries:
                locator = entry.get("source_locator", "")
                if not locator:
                    self.stderr.write(
                        self.style.WARNING(
                            "Skipping entry: missing source_locator metadata."
                        )
                    )
                    continue

                if locator in existing_locators:
                    duplicate_count += 1
                    continue

                parser_output = entry.get("parser_output", {})
                confidence_float = entry.get("confidence", 1.0)
                parser_status = ExtractionUnit.status_from_parser_output(parser_output)

                provenance = {
                    "source_key": SOURCE_KEY,
                    "source_location_reference": locator,
                    "parser": PARSER_NAME,
                    "batch_id": batch_id,
                }
                provenance.update(entry.get("provenance") or {})

                ExtractionUnit.objects.create(
                    source=source,
                    source_location_reference=locator,
                    raw_text=entry.get("raw_text", ""),
                    parser_output=parser_output,
                    parser_name=PARSER_NAME,
                    parser_status=parser_status,
                    confidence=confidence_float,
                    review_state=ReviewState.NEEDS_REVIEW,
                    provenance=provenance,
                    batch_id=batch_id,
                )
                imported_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Batch {batch_id}: imported {imported_count} pre-parsed entries, "
                f"skipped {duplicate_count} duplicates."
            )
        )

    def _dry_run_report(self, entries, batch_id):
        """Print a summary of what would be imported."""
        self.stdout.write(self.style.WARNING("\n  DRY RUN — no records created\n"))

        headword_kinds = {}
        pos_codes = {}

        for entry in entries:
            parser_output = entry.get("parser_output", {})
            kind = parser_output.get("headword_kind", "unknown")
            headword_kinds[kind] = headword_kinds.get(kind, 0) + 1

            pos = parser_output.get("part_of_speech", {})
            pos_code = pos.get("code", "unknown")
            pos_codes[pos_code] = pos_codes.get(pos_code, 0) + 1

        self.stdout.write(f"  Batch ID: {batch_id}")
        self.stdout.write(f"  Total entries to import: {len(entries)}")
        self.stdout.write(f"\n  Headword kinds:")
        for kind, count in sorted(headword_kinds.items()):
            self.stdout.write(f"    {kind}: {count}")
        self.stdout.write(f"\n  Part of Speech codes:")
        for code, count in sorted(pos_codes.items()):
            self.stdout.write(f"    {code}: {count}")
        self.stdout.write("")
