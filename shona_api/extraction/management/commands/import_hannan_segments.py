"""
Import segmented Hannan dictionary entries from JSONL into ExtractionUnit records.

This command reads JSONL output from the continuous_extractor.py tool and creates
ExtractionUnit rows in the database. Each entry is stored with its raw text,
confidence score, and provenance, ready for editorial review.

Usage:
    python manage.py import_hannan_segments path/to/entries.jsonl
    python manage.py import_hannan_segments entries.jsonl --dry-run
    python manage.py import_hannan_segments entries.jsonl --batch-id SEG-2026-001
    python manage.py import_hannan_segments entries.jsonl --min-confidence 100
"""

import json
import uuid
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from shona_api.editorial.models import ReviewState
from shona_api.extraction.models import ExtractionUnit
from shona_api.sources.models import Source


PARSER_NAME = "hannan-segmenter-v1"
SOURCE_KEY = "source_hannan"


class Command(BaseCommand):
    help = (
        "Import segmented Hannan dictionary entries from JSONL "
        "into ExtractionUnit records."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "jsonl_path",
            help="Path to the JSONL file from continuous_extractor.py.",
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
            "--min-confidence",
            type=int,
            default=0,
            help="Minimum confidence threshold (0-100, default: 0 = all).",
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

    def handle(self, *args, **options):
        jsonl_path = Path(options["jsonl_path"])
        if not jsonl_path.exists():
            raise CommandError(f"JSONL file not found: {jsonl_path}")

        dry_run = options["dry_run"]
        min_confidence = options["min_confidence"]
        skip_duplicates = options["skip_duplicates"]
        batch_id = options["batch_id"] or f"SEG-{uuid.uuid4().hex[:8].upper()}"

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
                if entry.get("confidence", 0) >= min_confidence:
                    entries.append(entry)

        self.stdout.write(
            f"Loaded {len(entries)} entries from {jsonl_path} "
            f"(min confidence: {min_confidence})"
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
        skipped_count = 0
        duplicate_count = 0

        with transaction.atomic():
            for entry in entries:
                locator = entry.get("source_locator", "")
                if not locator:
                    locator = (
                        f"hannan:entry_{entry.get('global_entry_number', 0):05d}"
                    )

                if locator in existing_locators:
                    duplicate_count += 1
                    continue

                # Map confidence from 0-100 to 0.0-1.0
                confidence_pct = entry.get("confidence", 0)
                confidence_float = max(0.0, min(1.0, confidence_pct / 100.0))
                primary_source_page = entry.get("primary_source_page")
                source_pages = entry.get("source_pages", [])
                segmenter_warnings = entry.get("warnings", [])

                # Build parser output — segmentation metadata only
                parser_output = {
                    "headword": entry.get("headword", ""),
                    "entry_kind": entry.get("entry_kind", "dictionary_entry"),
                    "header": entry.get("header", ""),
                    "primary_source_page": primary_source_page,
                    "source_pages": source_pages,
                    "segmenter_confidence": confidence_pct,
                    "segmenter_warnings": segmenter_warnings,
                    "parse_metadata": {
                        "parser": PARSER_NAME,
                        "completeness": "segmented_only",
                    },
                }

                # Determine parser status
                if confidence_pct >= 100:
                    parser_status = ExtractionUnit.ParserStatus.PARSED
                elif confidence_pct >= 70:
                    parser_status = (
                        ExtractionUnit.ParserStatus.PARSED_WITH_UNCERTAINTY
                    )
                else:
                    parser_status = ExtractionUnit.ParserStatus.FAILED

                provenance = {
                    "source_key": SOURCE_KEY,
                    "source_location_reference": locator,
                    "parser": PARSER_NAME,
                    "batch_id": batch_id,
                    "source_locator": locator,
                    "primary_source_page": primary_source_page,
                    "source_pages": source_pages,
                    "segmenter_confidence": confidence_pct,
                    "segmenter_warnings": segmenter_warnings,
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
                f"Batch {batch_id}: imported {imported_count} entries, "
                f"skipped {duplicate_count} duplicates."
            )
        )

    def _dry_run_report(self, entries, batch_id):
        """Print a summary without creating any records."""
        self.stdout.write(self.style.WARNING("\n  DRY RUN — no records created\n"))

        confidence_buckets = {}
        entry_kinds = {}
        cross_page = 0

        for entry in entries:
            conf = entry.get("confidence", 0)
            bucket = (conf // 10) * 10
            confidence_buckets[bucket] = confidence_buckets.get(bucket, 0) + 1

            kind = entry.get("entry_kind", "unknown")
            entry_kinds[kind] = entry_kinds.get(kind, 0) + 1

            if len(entry.get("source_pages", [])) > 1:
                cross_page += 1

        self.stdout.write(f"  Batch ID: {batch_id}")
        self.stdout.write(f"  Total entries: {len(entries)}")
        self.stdout.write(f"  Cross-page entries: {cross_page}")
        self.stdout.write(f"\n  Entry kinds:")
        for kind, count in sorted(entry_kinds.items()):
            self.stdout.write(f"    {kind}: {count}")
        self.stdout.write(f"\n  Confidence distribution:")
        for bucket in sorted(confidence_buckets.keys()):
            count = confidence_buckets[bucket]
            self.stdout.write(f"    {bucket:3d}-{bucket+9:3d}: {count}")
        self.stdout.write("")
