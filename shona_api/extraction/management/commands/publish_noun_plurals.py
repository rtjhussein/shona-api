"""Publish derived noun plurals as `Form` records.

The published lexicon held **zero** plural forms while 2,060 nouns carried a
plural prefix in their parser output. This turns the recorded prefix into a
surface form (see `shona_api.morphology.plurals` for the rule and its source
locators) and writes it as a `Form` with `form_kind=plural`, so the plural
appears on the lemma read endpoint and resolves in search through the existing
exact-form tier -- neither of which needed a change.

Every published plural traces to a recorded prefix and an allomorph pair the
source states or that follows from the change it states. A noun whose class or
allomorph is not yet verified is skipped with a stable code rather than given a
derived form: a wrong plural is worse than a missing one.

Idempotent: a plural already published for a lemma is left alone.

Usage::

    python manage.py publish_noun_plurals --dry-run
    python manage.py publish_noun_plurals
"""

from collections import Counter

from django.core.management.base import BaseCommand

from shona_api.editorial.models import ReviewState
from shona_api.extraction.models import ExtractionUnit
from shona_api.lexicon.models import Form, Lemma
from shona_api.morphology.plurals import PluralDerivationError, derive_plural
from shona_api.parsers.hannan import read_attested_plural_forms


class Command(BaseCommand):
    help = "Create plural Form records from the plural each source line records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be published without writing.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Stop after this many new forms (for a staged rollout).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        limit = options["limit"]

        lemmas = {
            str(lemma.id).replace("-", "").lower(): lemma
            for lemma in Lemma.objects.filter(
                headword_kind=Lemma.HeadwordKind.NOUN
            )
            .select_related("noun_class")
            .only("id", "headword", "headword_kind", "noun_class")
            .iterator(chunk_size=500)
        }
        self.stdout.write(f"{len(lemmas):,} published noun lemmas to consider")

        already = Counter(
            Form.objects.filter(form_kind=Form.FormKind.PLURAL).values_list(
                "lemma_id", flat=True
            )
        )

        published: Counter[str] = Counter()
        skipped: Counter[str] = Counter()
        bases: Counter[str] = Counter()
        samples: list[str] = []
        created = 0

        units = (
            ExtractionUnit.objects.exclude(canonical_record_object_id="")
            .only("canonical_record_object_id", "parser_output", "raw_text")
            .iterator(chunk_size=500)
        )
        for unit in units:
            key = (unit.canonical_record_object_id or "").replace("-", "").strip().lower()
            lemma = lemmas.get(key)
            if lemma is None:
                continue

            parser_output = unit.parser_output
            if not isinstance(parser_output, dict):
                continue
            noun = parser_output.get("noun")
            recorded = noun.get("plural_forms") if isinstance(noun, dict) else None
            if not isinstance(recorded, list) or not recorded:
                # Parsers dropped this field on entries whose line carries it
                # (`bino [LL]KM n 5, pl: map-, Big nose.`), so fall back to the
                # line, which is the authority in the same way it is for class.
                recorded = read_attested_plural_forms(unit.raw_text)
            if not recorded:
                skipped["no recorded plural"] += 1
                continue

            noun_class = lemma.noun_class.class_number if lemma.noun_class_id else None
            try:
                derivation = derive_plural(
                    lemma.headword, recorded, noun_class=noun_class
                )
            except PluralDerivationError as exc:
                skipped[exc.code] += 1
                continue

            if already.get(lemma.id):
                skipped["plural already published"] += 1
                continue
            if limit is not None and created >= limit:
                skipped["limit reached"] += 1
                continue

            published[derivation.surface] += 1
            bases[derivation.basis] += 1
            if len(samples) < 8:
                samples.append(
                    f"{lemma.headword} ({noun_class}) {derivation.recorded} "
                    f"-> {derivation.surface}"
                )
            if not dry_run:
                Form.objects.create(
                    lemma=lemma,
                    form_text=derivation.surface,
                    form_kind=Form.FormKind.PLURAL,
                    review_state=ReviewState.PUBLISHED,
                    dialects=list(parser_output.get("dialects") or []),
                    grammar=[f"class {noun_class} plural"],
                    provenance={
                        "source_key": unit.source_key,
                        "source_location_reference": unit.source_location_reference,
                        "derivation": derivation.as_payload(),
                    },
                )
            created += 1

        verb = "would be published" if dry_run else "published"
        for label, count in bases.most_common():
            self.stdout.write(f"  {count:>5}  {label} {verb}")
        self.stdout.write(
            self.style.SUCCESS(f"{created:,} plural form(s) {verb}")
        )
        for label, count in skipped.most_common():
            self.stdout.write(f"  skipped {count:>5}  {label}")
        for sample in samples:
            self.stdout.write(f"  e.g. {sample}")
