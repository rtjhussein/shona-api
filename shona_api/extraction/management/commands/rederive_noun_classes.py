"""Re-derive `Lemma.noun_class` from the parser output already on file.

A published noun lemma can be missing its noun class even though its extraction
unit recorded one. That happened at scale: parsers emitted the Hannan class
number as a JSON number (``"classes": [5]``) while the promotion path only
accepted strings, so every such entry was published with a null class. Hannan's
own class inventory is explicit -- ``derere [LLH Z; LLL KM]KMZ n 5, pl: mad-``
-- so the value is recoverable without re-reading the source.

This command re-runs the production resolver (``_parser_noun_class``) against
stored parser output and writes the result with ``bulk_update``.
``bulk_update`` is deliberate: ``Lemma`` has a ``post_save`` receiver that runs
curriculum tagging for published records, and a repair must not rewrite
pedagogical metadata as a side effect.
"""

from django.core.management.base import BaseCommand

from shona_api.extraction.models import ExtractionUnit
from shona_api.extraction.services import _parser_noun_class
from shona_api.lexicon.models import Lemma


class Command(BaseCommand):
    help = (
        "Resolve noun_class for published noun lemmas that lack it, using the "
        "class recorded in their extraction unit's parser output."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Rows written per bulk_update statement (default: 500).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without writing.",
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        dry_run = options["dry_run"]

        candidates = Lemma.objects.filter(
            headword_kind=Lemma.HeadwordKind.NOUN,
            noun_class_id__isnull=True,
        ).only("id", "public_id", "headword", "headword_kind", "noun_class")
        target_ids = {str(lemma.id) for lemma in candidates}
        self.stdout.write(f"{len(target_ids)} noun lemma(s) without a noun class")

        if not target_ids:
            return

        units = (
            ExtractionUnit.objects.exclude(canonical_record_object_id="")
            .only("canonical_record_object_id", "parser_output")
            .iterator(chunk_size=batch_size)
        )

        resolved = 0
        unresolved_no_classes = 0
        unresolved_unmapped: set[str] = set()
        pending = []

        for unit in units:
            # `Lemma.id` is a UUID primary key, so its string form is
            # hyphenated, and that is what the unit stores.
            lemma_id = (unit.canonical_record_object_id or "").strip().lower()
            if lemma_id not in target_ids:
                continue

            parser_output = unit.parser_output if isinstance(unit.parser_output, dict) else {}
            noun_payload = parser_output.get("noun")
            raw_classes = (
                noun_payload.get("classes") if isinstance(noun_payload, dict) else None
            )
            noun_class = _parser_noun_class(parser_output)

            if noun_class is None:
                if isinstance(raw_classes, list) and raw_classes:
                    unresolved_unmapped.update(
                        str(value) for value in raw_classes if str(value).strip()
                    )
                else:
                    unresolved_no_classes += 1
                continue

            lemma = Lemma(id=lemma_id, noun_class=noun_class)
            pending.append(lemma)
            resolved += 1
            if not dry_run and len(pending) >= batch_size:
                Lemma.objects.bulk_update(pending, ["noun_class"])
                pending = []

        if not dry_run and pending:
            Lemma.objects.bulk_update(pending, ["noun_class"])

        verb = "would be resolved" if dry_run else "resolved"
        self.stdout.write(
            self.style.SUCCESS(f"{resolved} noun class(es) {verb}")
        )
        if unresolved_no_classes:
            self.stdout.write(
                f"{unresolved_no_classes} still unresolved: parser output records "
                "no class for the entry"
            )
        if unresolved_unmapped:
            listed = ", ".join(sorted(unresolved_unmapped))
            self.stdout.write(
                f"{len(unresolved_unmapped)} distinct class value(s) have no "
                f"NounClass row and were left unresolved: {listed}"
            )
            self.stdout.write(
                "  review: add the Hannan sub-class to NounClass (with an "
                "evidence-backed concord) before expecting these to resolve"
            )
