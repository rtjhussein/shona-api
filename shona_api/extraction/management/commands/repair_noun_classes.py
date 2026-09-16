"""Correct `Lemma.noun_class` where it disagrees with the source line.

The published corpus was produced by parsers that dropped Hannan's sub-class
letter: a line reading ``Chikumi [LHH]KMZ n 1a June.`` reached the database as
class ``1``, and ``gufu [LH]MZ n 1a (M), 5 (Z), ...`` lost its class entirely.
Hannan's class 1a is not class 1 -- it takes a different concord -- so these
records carry a wrong grammatical category.

`rederive_noun_classes` fixes records from their *parser output*, which cannot
help here: the parser never recorded the sub-class. The source line is the
authority for what class an entry belongs to, so this command reads it directly
and corrects the record when the two disagree. It also fills a class where the
parser recorded none but the line attests one.

Writes use ``bulk_update``: ``Lemma`` has a ``post_save`` receiver that runs
curriculum tagging for published records, and a repair must not rewrite
pedagogical metadata as a side effect.
"""

from collections import Counter

from django.core.management.base import BaseCommand

from shona_api.extraction.models import ExtractionUnit
from shona_api.lexicon.models import Lemma, NounClass
from shona_api.parsers.hannan import read_attested_noun_classes


class Command(BaseCommand):
    help = (
        "Set noun_class from the attested source line wherever the published "
        "class disagrees with it or is missing."
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

        class_by_number = {noun_class.class_number: noun_class for noun_class in NounClass.objects.all()}
        lemma_state = {
            str(lemma.id): (
                lemma.noun_class.class_number if lemma.noun_class_id else None,
                lemma.headword_kind,
            )
            for lemma in Lemma.objects.select_related("noun_class").only(
                "id", "headword", "headword_kind", "noun_class"
            )
        }
        self.stdout.write(f"{len(lemma_state):,} published lemmas to check")

        corrections: Counter[tuple[str, str]] = Counter()
        by_kind: Counter[str] = Counter()
        recovered = 0
        unmapped: Counter[str] = Counter()
        agreements = 0
        no_evidence = 0
        pending: list[Lemma] = []

        units = (
            ExtractionUnit.objects.exclude(canonical_record_object_id="")
            .only("canonical_record_object_id", "raw_text")
            .iterator(chunk_size=batch_size)
        )
        for unit in units:
            lemma_id = (unit.canonical_record_object_id or "").strip().lower()
            state = lemma_state.get(lemma_id)
            if state is None:
                continue
            current_class, headword_kind = state

            attested = read_attested_noun_classes(unit.raw_text)
            if not attested:
                no_evidence += 1
                continue

            expected = attested[0]
            if current_class == expected:
                agreements += 1
                continue

            noun_class = class_by_number.get(expected)
            if noun_class is None:
                unmapped[expected] += 1
                continue

            corrections[(str(current_class), expected)] += 1
            by_kind[headword_kind] += 1
            if current_class is None:
                recovered += 1
            pending.append(Lemma(id=lemma_id, noun_class=noun_class))
            if not dry_run and len(pending) >= batch_size:
                Lemma.objects.bulk_update(pending, ["noun_class"])
                pending = []

        if not dry_run and pending:
            Lemma.objects.bulk_update(pending, ["noun_class"])

        verb = "would change" if dry_run else "changed"
        for (was, now), count in corrections.most_common():
            self.stdout.write(f"  class {was} -> {now}: {count} record(s) {verb}")
        total = sum(corrections.values())
        self.stdout.write(
            self.style.SUCCESS(
                f"{total:,} record(s) {verb} ({recovered:,} had no class at all); "
                f"{agreements:,} already agreed with the source line"
            )
        )
        if by_kind:
            breakdown = ", ".join(
                f"{kind}={count}" for kind, count in by_kind.most_common()
            )
            self.stdout.write(
                f"  by the record's current headword_kind: {breakdown} "
                "(a line that reads 'n 9' is a noun whatever the parser called it)"
            )
        if no_evidence:
            self.stdout.write(f"{no_evidence:,} line(s) attest no noun class")
        if unmapped:
            listed = ", ".join(f"{value} ({count})" for value, count in unmapped.most_common())
            self.stdout.write(
                self.style.WARNING(
                    f"{len(unmapped)} attested class value(s) have no NounClass row and "
                    f"were left unchanged: {listed}"
                )
            )
