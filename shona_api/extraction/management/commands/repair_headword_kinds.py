"""Correct `Lemma.headword_kind` where it disagrees with the source line.

Parsers published entries the source marks as a verb, noun, or ideophone under
the generic ``word`` kind: ``†-ti [L]KKoMZ defective v Say.`` and
``-nga- [L]KMZ defective v Be.`` are core defective verbs, and
``piku [LL]KMZ ideo of Taking up.`` is an ideophone. This is not only a label
problem -- the morphology engine resolves verb stems by ``headword_kind``, so
every misclassified stem is unreachable by ``/v1/analyze``.

The source line is the authority, in the same way it is for the noun class. A
line that names no modelled category (``adj``, ``inter``, ``conj``, ``sc``, ...)
yields no reading and the record is left alone, rather than being forced into a
class the model does not have.

Writes use ``bulk_update``: ``Lemma`` has a ``post_save`` receiver that runs
curriculum tagging for published records, and a repair must not rewrite
pedagogical metadata as a side effect.
"""

from collections import Counter

from django.core.management.base import BaseCommand

from shona_api.extraction.models import ExtractionUnit
from shona_api.lexicon.models import Lemma
from shona_api.parsers.hannan import read_attested_headword_kind


class Command(BaseCommand):
    help = (
        "Set headword_kind from the attested source line wherever the published "
        "kind disagrees with it."
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

        # Lemma's primary key is a UUID, so its string form is hyphenated and
        # lowercase; that is what the extraction unit stores.
        published_kind = {
            str(lemma_id): headword_kind
            for lemma_id, headword_kind in Lemma.objects.only(
                "id", "headword_kind"
            ).values_list("id", "headword_kind")
        }
        self.stdout.write(f"{len(published_kind):,} published lemmas to check")

        corrections: Counter[tuple[str, str]] = Counter()
        agreements = 0
        no_reading = 0
        examined = 0
        pending: list[Lemma] = []

        units = (
            ExtractionUnit.objects.exclude(canonical_record_object_id="")
            .only("canonical_record_object_id", "raw_text")
            .iterator(chunk_size=batch_size)
        )
        for unit in units:
            lemma_id = (unit.canonical_record_object_id or "").strip().lower()
            current_kind = published_kind.get(lemma_id)
            if current_kind is None:
                continue
            examined += 1

            attested = read_attested_headword_kind(unit.raw_text)
            if attested is None:
                no_reading += 1
                continue
            if attested == current_kind:
                agreements += 1
                continue

            corrections[(current_kind, attested)] += 1
            pending.append(Lemma(id=lemma_id, headword_kind=attested))
            if not dry_run and len(pending) >= batch_size:
                Lemma.objects.bulk_update(pending, ["headword_kind"])
                pending = []

        if not dry_run and pending:
            Lemma.objects.bulk_update(pending, ["headword_kind"])

        verb = "would change" if dry_run else "changed"
        for (was, now), count in corrections.most_common():
            self.stdout.write(f"  {was} -> {now}: {count} record(s) {verb}")
        total = sum(corrections.values())
        self.stdout.write(
            self.style.SUCCESS(
                f"{total:,} record(s) {verb} after checking {examined:,} linked "
                f"record(s); {agreements:,} already agreed with the source line"
            )
        )
        if no_reading:
            self.stdout.write(
                f"{no_reading:,} line(s) name no modelled category (adjective, "
                "interjection, concord, ...) and were left unchanged"
            )
