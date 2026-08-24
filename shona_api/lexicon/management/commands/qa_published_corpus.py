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
            help="Exit nonzero when the QA report contains issues.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        if limit is not None and limit < 1:
            raise CommandError("--limit must be a positive integer.")

        report = run_published_corpus_qa(limit=limit)
        self.stdout.write(json.dumps(report, indent=2, sort_keys=True))

        if options["fail_on_issues"] and report["summary"]["issues"]:
            raise CommandError(
                f"Published corpus QA found {report['summary']['issues']} issue(s)."
            )
