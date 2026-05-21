from django.core.management.base import BaseCommand
from django.db import transaction

from shona_api.editorial.models import ReviewState
from shona_api.extraction.ingestion import TRUSTED_GEMINI_PARSER
from shona_api.extraction.models import ExtractionUnit
from shona_api.lexicon.models import Form, Lemma, Sense, ToneRecord


class Command(BaseCommand):
    help = (
        "Remove local non-Gemini fixture extraction/canonical records. "
        "Dry-run by default; pass --execute to delete."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Actually delete the targeted records.",
        )

    def handle(self, *args, **options):
        execute = options["execute"]
        extraction_qs = ExtractionUnit.objects.exclude(parser_name=TRUSTED_GEMINI_PARSER)
        lemma_qs = Lemma.objects.exclude(
            review_state=ReviewState.PUBLISHED,
            provenance__parser=TRUSTED_GEMINI_PARSER,
            provenance__source_key="source_hannan",
        ).exclude(review_state=ReviewState.PUBLISHED)
        sense_qs = Sense.objects.filter(lemma__in=lemma_qs)
        tone_qs = ToneRecord.objects.filter(lemma__in=lemma_qs)
        form_qs = Form.objects.filter(lemma__in=lemma_qs)

        summary = {
            "non_gemini_extraction_units": extraction_qs.count(),
            "non_gemini_unpublished_lemmas": lemma_qs.count(),
            "dependent_senses": sense_qs.count(),
            "dependent_tone_records": tone_qs.count(),
            "dependent_forms": form_qs.count(),
        }

        action = "Deleting" if execute else "Would delete"
        for label, count in summary.items():
            self.stdout.write(f"{action} {count} {label.replace('_', ' ')}.")

        if not execute:
            self.stdout.write(self.style.WARNING("Dry run only. Re-run with --execute to delete."))
            return

        with transaction.atomic():
            extraction_deleted, _ = extraction_qs.delete()
            lemma_deleted, _ = lemma_qs.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {extraction_deleted} extraction rows and "
                f"{lemma_deleted} canonical lexical rows/dependents."
            )
        )
