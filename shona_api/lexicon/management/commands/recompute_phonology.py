"""Recompute stored phonology fields onto the active grapheme inventory.

The `phonology_inventory_version` field records which grapheme inventory
produced a record's `graphemes`, `grapheme_count`, `syllables`, and
`syllable_count`. When the inventory version changes, previously stored values
were computed by superseded rules -- for example `mbwa` (dog) was once counted
as three graphemes instead of two -- and this command brings them forward.

Records are updated with `bulk_update`, never `save()`: `Lemma` has a
`post_save` receiver that runs curriculum tagging for published records, and a
backfill must not rewrite pedagogical metadata as a side effect. `bulk_update`
also keeps the run to a bounded number of statements per batch.
"""

from django.core.management.base import BaseCommand

from shona_api.figurative_language.models import FigurativeExpression
from shona_api.lexicon.models import Form, Lemma
from shona_api.phonology import DEFAULT_GRAPHEME_INVENTORY

# (model, field holding the surface text, human name)
TARGETS = (
    (Lemma, "headword", "lemma"),
    (Form, "form_text", "form"),
    (FigurativeExpression, "expression_text", "figurative expression"),
)


class Command(BaseCommand):
    help = (
        "Recompute graphemes, grapheme_count, syllables, syllable_count, and "
        "phonology_inventory_version for records stored under a superseded "
        "grapheme inventory."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="Rows written per bulk_update statement (default: 1000).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report the records that would change without writing.",
        )

    def handle(self, *args, **options):
        inventory = DEFAULT_GRAPHEME_INVENTORY
        batch_size = options["batch_size"]
        dry_run = options["dry_run"]
        if batch_size < 1:
            self.stderr.write(self.style.ERROR("--batch-size must be at least 1."))
            raise SystemExit(1)

        total = 0
        for model, text_field, name in TARGETS:
            queryset = model.objects.exclude(
                phonology_inventory_version=inventory.version
            )
            count = queryset.count()
            total += count
            if dry_run or count == 0:
                self.stdout.write(f"{name}: {count} record(s) to recompute")
                continue

            pending = []
            for obj in queryset.only("pk", text_field).iterator(chunk_size=batch_size):
                obj.apply_phonology_fields(getattr(obj, text_field))
                pending.append(obj)
                if len(pending) >= batch_size:
                    model.objects.bulk_update(pending, obj.phonology_field_names)
                    pending = []
            if pending:
                model.objects.bulk_update(pending, pending[0].phonology_field_names)
            self.stdout.write(
                f"{name}: recomputed {count} record(s) onto {inventory.version}"
            )

        verb = "would be recomputed" if dry_run else "recomputed"
        self.stdout.write(
            self.style.SUCCESS(
                f"{total} record(s) {verb} onto grapheme inventory "
                f"{inventory.version}."
            )
        )
