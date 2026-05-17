"""
Structure previously-segmented ExtractionUnit records.

This command takes ExtractionUnit records that were imported by the segmenter
(parser_name = "hannan-segmenter-v1") and runs the structured parser on each
entry's raw_text to produce a complete parse output with headword, POS, tone,
senses, examples, etc.

This cleanly separates segmentation (reliable) from structuring (improvable).

Usage:
    python manage.py structure_extraction_units
    python manage.py structure_extraction_units --batch-id SEG-2026-001
    python manage.py structure_extraction_units --limit 100 --dry-run
    python manage.py structure_extraction_units --include-unapproved
"""

from django.core.management.base import BaseCommand

from shona_api.editorial.models import ReviewState
from shona_api.extraction.models import ExtractionUnit
from shona_api.parsers.hannan import parse_hannan_entry


SEGMENTER_PARSER_NAME = "hannan-segmenter-v1"
STRUCTURED_PARSER_NAME = "hannan-structured-parser-v1"


class Command(BaseCommand):
    help = (
        "Run the structured parser on segmented ExtractionUnit records "
        "to produce complete parse outputs."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-id",
            default=None,
            help="Only structure entries from this batch.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Maximum number of entries to process (0 = all).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse entries and report results without saving.",
        )
        parser.add_argument(
            "--re-structure",
            action="store_true",
            help=(
                "Re-run structuring on entries already structured "
                "(useful after parser improvements)."
            ),
        )
        parser.add_argument(
            "--include-unapproved",
            action="store_true",
            help=(
                "Also structure entries that have not reached API approval. "
                "By default only approved ExtractionUnit records advance."
            ),
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        limit = options["limit"]
        batch_id = options["batch_id"]
        re_structure = options["re_structure"]
        include_unapproved = options["include_unapproved"]

        # Build queryset
        qs = ExtractionUnit.objects.all()
        if include_unapproved:
            qs = qs.filter(
                review_state__in=[
                    ReviewState.NEEDS_REVIEW,
                    ReviewState.IN_REVIEW,
                    ReviewState.APPROVED,
                ],
            )
        else:
            qs = qs.filter(review_state=ReviewState.APPROVED)

        if not re_structure:
            qs = qs.filter(parser_name=SEGMENTER_PARSER_NAME)
        else:
            qs = qs.filter(
                parser_name__in=[
                    SEGMENTER_PARSER_NAME,
                    STRUCTURED_PARSER_NAME,
                ]
            )

        if batch_id:
            qs = qs.filter(batch_id=batch_id)

        qs = qs.order_by("created_at")
        if limit:
            qs = qs[:limit]

        entries = list(qs)
        self.stdout.write(f"Found {len(entries)} entries to structure.")

        if not entries:
            return

        parsed_count = 0
        uncertain_count = 0
        failed_count = 0

        for unit in entries:
            raw_text = unit.raw_text.strip()
            if not raw_text:
                failed_count += 1
                continue

            try:
                structured = parse_hannan_entry(raw_text, fail_soft=True)
            except Exception as exc:
                self.stderr.write(
                    self.style.WARNING(
                        f"  Error structuring {unit.source_location_reference}: {exc}"
                    )
                )
                failed_count += 1
                continue

            # Determine new parser status
            errors = structured.get("errors", [])
            uncertainties = structured.get("uncertainties", [])

            if errors:
                status = ExtractionUnit.ParserStatus.FAILED
                failed_count += 1
            elif uncertainties:
                status = ExtractionUnit.ParserStatus.PARSED_WITH_UNCERTAINTY
                uncertain_count += 1
            else:
                status = ExtractionUnit.ParserStatus.PARSED
                parsed_count += 1

            if not dry_run:
                # Preserve segmenter metadata in the output
                segmenter_meta = unit.parser_output.get("segmenter_confidence")
                structured["segmenter_confidence"] = segmenter_meta
                structured["parse_metadata"]["parser"] = STRUCTURED_PARSER_NAME

                unit.parser_output = structured
                unit.parser_name = STRUCTURED_PARSER_NAME
                unit.parser_status = status
                unit.save(
                    update_fields=[
                        "parser_output",
                        "parser_name",
                        "parser_status",
                        "updated_at",
                    ]
                )

        verb = "Would structure" if dry_run else "Structured"
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{verb} {len(entries)} entries:\n"
                f"  Parsed:          {parsed_count}\n"
                f"  With uncertainty: {uncertain_count}\n"
                f"  Failed:          {failed_count}"
            )
        )
