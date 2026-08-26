import json

from django.core.management.base import BaseCommand, CommandError

from shona_api.lexicon.qa import run_published_corpus_qa


class Command(BaseCommand):
    help = "Run corpus-level QA checks against published canonical lexicon data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--format",
            choices=("json",),
            default="json",
            help="Output format. Defaults to machine-readable JSON.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit each checked record type for bounded local runs.",
        )
        parser.add_argument(
            "--fail-on-issues",
            action="store_true",
            help=(
                "Exit nonzero when the QA report contains error-severity "
                "issues (info-level notes do not fail the run)."
            ),
        )
        parser.add_argument(
            "--exact-only",
            "--skip-morphology",
            dest="skip_morphology",
            action="store_true",
            help=(
                "Run exact-search and visibility checks only; skip morphology "
                "analysis replays for fast CI-scale passes."
            ),
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        if limit is not None and limit < 1:
            raise CommandError("--limit must be a positive integer.")

        report = run_published_corpus_qa(
            limit=limit,
            include_morphology=not options["skip_morphology"],
        )
        self.stdout.write(json.dumps(report, indent=2, sort_keys=True))

        if options["fail_on_issues"] and report["summary"]["errors"]:
            raise CommandError(
                f"Published corpus QA found {report['summary']['errors']} "
                f"error-severity issue(s)."
            )
