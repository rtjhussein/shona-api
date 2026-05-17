from django.core.management.base import BaseCommand

from shona_api.extraction.hannan_import import import_hannan_batch_file


class Command(BaseCommand):
    help = (
        "LEGACY: import a local-only Hannan batch JSON file into "
        "ExtractionUnit records. Prefer import_hannan_segments for dashboard JSONL."
    )

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and parse the batch without creating records.",
        )

    def handle(self, *args, **options):
        result = import_hannan_batch_file(
            options["path"],
            dry_run=options["dry_run"],
        )
        verb = "Would import" if result.dry_run else "Imported"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb} Hannan batch {result.batch_id}: "
                f"{result.imported_count} entries, {result.skipped_count} skipped."
            )
        )
