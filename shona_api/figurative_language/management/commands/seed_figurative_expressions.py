import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from shona_api.editorial.models import ReviewState
from shona_api.figurative_language.models import FigurativeExpression
from shona_api.lexicon.models import Lemma
from shona_api.lexicon.search import normalize_search_query


DEFAULT_FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "seed_figurative_expressions.json"
)


class Command(BaseCommand):
    help = "Seed the first reviewed figurative-language records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fixture",
            type=str,
            help="Path to a JSON fixture of reviewed figurative expressions.",
        )

    def handle(self, *args, **options):
        fixture_path = Path(options.get("fixture") or DEFAULT_FIXTURE_PATH)
        if not fixture_path.exists():
            raise CommandError(f"Fixture file not found at: {fixture_path}")

        try:
            records = json.loads(fixture_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CommandError(f"Failed to parse JSON fixture: {exc}") from exc

        if not isinstance(records, list):
            raise CommandError("Figurative expression fixture must contain a list.")

        created_count = 0
        updated_count = 0
        linked_count = 0
        missing_links = []

        with transaction.atomic():
            for data in records:
                expression, was_created = FigurativeExpression.objects.update_or_create(
                    expression_text=data["expression_text"],
                    subtype=data["subtype"],
                    defaults={
                        "subtype_readiness": data.get(
                            "subtype_readiness",
                            FigurativeExpression.SubtypeReadiness.ACTIVE,
                        ),
                        "idiomatic_meaning": data.get("idiomatic_meaning", ""),
                        "english_rendering": data.get("english_rendering", ""),
                        "usage_note": data.get("usage_note", ""),
                        "cultural_themes": data.get("cultural_themes", []),
                        "pedagogy_notes": data.get("pedagogy_notes", []),
                        "source_notes": data.get("source_notes", []),
                        "provenance": data.get("provenance", {}),
                        "review_state": data.get(
                            "review_state",
                            ReviewState.APPROVED,
                        ),
                    },
                )
                if was_created:
                    created_count += 1
                else:
                    updated_count += 1

                linked_lemmas, missing = self._resolve_linked_lemmas(
                    data.get("linked_lemma_headwords", [])
                )
                expression.linked_lemmas.set(linked_lemmas)
                linked_count += len(linked_lemmas)
                missing_links.extend(
                    f"{expression.expression_text}: {headword}" for headword in missing
                )

        if missing_links:
            self.stdout.write(
                self.style.WARNING(
                    "Skipped missing linked lemmas: " + ", ".join(missing_links)
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded figurative expressions: "
                f"{created_count} created, {updated_count} updated, "
                f"{linked_count} lemma links."
            )
        )

    def _resolve_linked_lemmas(self, headwords):
        linked_lemmas = []
        missing = []
        for headword in headwords:
            lemma = (
                Lemma.objects.filter(
                    normalized_headword=normalize_search_query(headword),
                    review_state__in=(ReviewState.APPROVED, ReviewState.PUBLISHED),
                )
                .order_by("public_id")
                .first()
            )
            if lemma is None:
                missing.append(headword)
            else:
                linked_lemmas.append(lemma)
        return linked_lemmas, missing
