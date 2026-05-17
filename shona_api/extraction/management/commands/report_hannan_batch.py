import json

from django.core.management.base import BaseCommand

from shona_api.extraction.reports import build_batch_quality_report


class Command(BaseCommand):
    help = "Report parser/review/publish quality metrics for a Hannan import batch."

    def add_arguments(self, parser):
        parser.add_argument("--batch-id", required=True)
        parser.add_argument(
            "--json",
            action="store_true",
            help="Print the full report as JSON.",
        )

    def handle(self, *args, **options):
        report = build_batch_quality_report(options["batch_id"])
        if options["json"]:
            self.stdout.write(json.dumps(report, indent=2, sort_keys=True))
            return

        self.stdout.write(f"Batch: {report['batch_id']}")
        self.stdout.write(f"Imported: {report['imported_count']}")
        self.stdout.write(f"Parseable rate: {report['parseable_rate']}")
        self.stdout.write(f"Published: {report['published_count']}")
        self.stdout.write(f"Failed parses: {report['failed_count']}")
        self.stdout.write(f"Uncertain parses: {report['uncertain_count']}")
        self.stdout.write(f"Parser states: {report['parser_status_counts']}")
        self.stdout.write(f"Review states: {report['review_state_counts']}")
        if report["common_error_codes"]:
            self.stdout.write(f"Common errors: {report['common_error_codes']}")
        if report["common_uncertainty_codes"]:
            self.stdout.write(
                f"Common uncertainties: {report['common_uncertainty_codes']}"
            )
