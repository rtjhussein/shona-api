"""Collapse part-of-speech code spellings onto the canonical vocabulary.

Parsers record Hannan's abbreviations as written, so ``vt``, ``v t``, ``vt&i``,
and ``v t & i`` all appear as distinct codes for the same word class, and a
client filtering on ``vt`` silently misses most transitive verbs. This command
applies ``canonical_pos_code`` to stored records.

Only re-spellings of the same category are rewritten. Codes the vocabulary does
not recognise are reported and left untouched: an unfamiliar code must stay
visible in the data rather than be relabelled as something it may not be.

The command also reports part-of-speech *labels* that absorbed their entry text
(for example ``oMZ n 9 Eland R 305.``). Those are not rewritten -- recovering
the real category needs the source line, not a string rule -- so they are
listed as an editorial review queue.

Records are updated with ``bulk_update``: ``Lemma`` has a ``post_save`` receiver
that runs curriculum tagging for published records, and a repair must not
rewrite pedagogical metadata as a side effect.
"""

from collections import Counter

from django.core.management.base import BaseCommand

from shona_api.extraction.gpt_jsonl import (
    MAX_POS_LABEL_LENGTH,
    POS_LABEL_RESIDUE_RE,
)
from shona_api.lexicon.models import Lemma
from shona_api.lexicon.part_of_speech import (
    CANONICAL_POS_CODES,
    canonical_pos_code,
)


class Command(BaseCommand):
    help = (
        "Rewrite stored part-of-speech codes onto the canonical vocabulary and "
        "report labels that still carry entry text."
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
            help="Report what would change without writing.",
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        dry_run = options["dry_run"]

        pending = []
        renames: Counter[tuple[str, str]] = Counter()
        unrecognised: Counter[str] = Counter()
        residue = 0

        for lemma in Lemma.objects.only(
            "id", "part_of_speech_code", "part_of_speech_label"
        ).iterator(chunk_size=batch_size):
            stored = lemma.part_of_speech_code or ""
            canonical = canonical_pos_code(stored)
            if canonical != stored:
                renames[(stored, canonical)] += 1
                lemma.part_of_speech_code = canonical
                pending.append(lemma)
                if not dry_run and len(pending) >= batch_size:
                    Lemma.objects.bulk_update(pending, ["part_of_speech_code"])
                    pending = []

            label = lemma.part_of_speech_label or ""
            if POS_LABEL_RESIDUE_RE.search(label) or len(label) > MAX_POS_LABEL_LENGTH:
                residue += 1

            if canonical and canonical not in CANONICAL_POS_CODES:
                unrecognised[canonical] += 1

        if not dry_run and pending:
            Lemma.objects.bulk_update(pending, ["part_of_speech_code"])

        total = sum(renames.values())
        verb = "would be rewritten" if dry_run else "rewritten"
        for (stored, canonical), count in renames.most_common():
            self.stdout.write(f"  {stored!r} -> {canonical!r}: {count} record(s)")
        self.stdout.write(
            self.style.SUCCESS(
                f"{total} part-of-speech code(s) {verb}; "
                f"{len(CANONICAL_POS_CODES)} canonical codes in the vocabulary."
            )
        )

        if unrecognised:
            listed = ", ".join(
                f"{code} ({count})" for code, count in unrecognised.most_common()
            )
            self.stdout.write(
                f"{len(unrecognised)} code(s) are outside the canonical vocabulary "
                f"and were left as stored: {listed}"
            )

        if residue:
            self.stdout.write(
                self.style.WARNING(
                    f"{residue} record(s) carry entry text in the part-of-speech "
                    "label; these need the source line to reclassify and are not "
                    "rewritten automatically"
                )
            )
