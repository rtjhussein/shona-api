from django.core.management.base import BaseCommand

from shona_api.editorial.models import ReviewState
from shona_api.extraction.reports import get_batch_units
from shona_api.extraction.services import (
    ExtractionUnitPublishError,
    publish_reviewed_extraction_unit,
)


class Command(BaseCommand):
    help = "Publish approved Hannan extraction units for a batch."

    def add_arguments(self, parser):
        parser.add_argument("--batch-id", required=True)
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show how many approved units would publish without writing records.",
        )

    def handle(self, *args, **options):
        batch_id = options["batch_id"]
        units = get_batch_units(batch_id).filter(review_state=ReviewState.APPROVED)
        publishable = units.filter(canonical_record_object_id="")
        already_linked = units.exclude(canonical_record_object_id="").count()

        if options["dry_run"]:
            self.stdout.write(
                f"Would publish {publishable.count()} approved units from {batch_id}; "
                f"{already_linked} already linked."
            )
            return

        published = 0
        failed = 0
        for unit in publishable.order_by("source_location_reference", "pk"):
            try:
                publish_reviewed_extraction_unit(unit)
            except ExtractionUnitPublishError as exc:
                failed += 1
                self.stderr.write(
                    f"Could not publish {unit.source_location_reference}: {exc}"
                )
                continue
            published += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Published {published} approved units from {batch_id}; "
                f"{failed} failed, {already_linked} already linked."
            )
        )
