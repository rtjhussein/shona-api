from django.core.management.base import BaseCommand, CommandError

from shona_api.extraction.ingestion import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PARSER_REPO_PATH,
    DEFAULT_PDF_PATH,
    execute_ingestion_run,
)
from shona_api.extraction.models import IngestionRun


class Command(BaseCommand):
    help = "Run the local Hannan Gemini extraction/import pipeline."

    def add_arguments(self, parser):
        parser.add_argument("--run-id", type=int)
        parser.add_argument("--batch-id")
        parser.add_argument("--start-page", type=int, required=False)
        parser.add_argument("--end-page", type=int)
        parser.add_argument("--parser-repo-path", default=str(DEFAULT_PARSER_REPO_PATH))
        parser.add_argument("--pdf-path", default=str(DEFAULT_PDF_PATH))
        parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--overwrite-pages", action="store_true")
        parser.add_argument("--auto-publish", action="store_true")

    def handle(self, *args, **options):
        if options["run_id"]:
            try:
                run = IngestionRun.objects.get(pk=options["run_id"])
            except IngestionRun.DoesNotExist as exc:
                raise CommandError(f"Ingestion run not found: {options['run_id']}") from exc
        else:
            if not options["batch_id"]:
                raise CommandError("--batch-id is required when --run-id is not provided.")
            if not options["start_page"]:
                raise CommandError("--start-page is required when --run-id is not provided.")
            start_page = options["start_page"]
            end_page = options["end_page"] or start_page
            run = IngestionRun.objects.create(
                batch_id=options["batch_id"],
                start_page=start_page,
                end_page=end_page,
                parser_repo_path=options["parser_repo_path"],
                pdf_path=options["pdf_path"],
                output_dir=options["output_dir"],
                dry_run=options["dry_run"],
                overwrite_pages=options["overwrite_pages"],
                auto_publish=options["auto_publish"],
            )

        run = execute_ingestion_run(run)
        self.stdout.write(run.log_text)
        if run.status == IngestionRun.Status.FAILED:
            raise CommandError(run.error_message or "Pipeline failed.")
        self.stdout.write(
            self.style.SUCCESS(
                f"Run {run.pk} {run.status}: imported {run.imported_count}, "
                f"published {run.published_count}."
            )
        )
        return run.pk
