"""Turn the source-conflict register into ReviewNote rows on affected records.

The register (`evaluation/conflicts/open.json`) records what the sources
disagree about and what would settle it. This carries each open conflict onto
the records it affects, as a `ReviewNote` in `needs_review`, so it appears in
the editorial queue rather than living only in a file nobody opens -- the
product requirements' conflict policy, which had never been exercised.

Idempotent: a record already carrying a note for a conflict id is skipped, so
the command can be re-run as new records appear. Notes are never deleted here;
closing a conflict is an editorial act performed on the note.

Usage::

    python manage.py sync_source_conflicts --dry-run
    python manage.py sync_source_conflicts
"""

import json
import re
from pathlib import Path

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from shona_api.editorial.models import ReviewNote, ReviewState
from shona_api.extraction.models import ExtractionUnit
from shona_api.lexicon.models import Lemma

REGISTER_PATH = Path("evaluation/conflicts/open.json")
SYNCABLE_STATUSES = {"open"}

# A note records where to read the full argument, not a copy of it that can
# drift from the register.
NOTE_TEMPLATE = (
    "Source conflict '{conflict_id}': {title}\n\n"
    "{summary}\n\n"
    "What would settle it: {resolution_needed}\n\n"
    "Register entry: evaluation/conflicts/open.json, id '{conflict_id}'."
)


class Command(BaseCommand):
    help = "Create ReviewNote rows for records affected by open source conflicts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--register",
            type=Path,
            default=REGISTER_PATH,
            help=f"Conflict register to read (default: {REGISTER_PATH}).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be created without writing.",
        )
        parser.add_argument(
            "--include-mitigated",
            action="store_true",
            help="Also sync conflicts whose status is 'mitigated'.",
        )

    def handle(self, *args, **options):
        register_path = options["register"]
        if not register_path.exists():
            self.stderr.write(self.style.ERROR(f"register not found: {register_path}"))
            raise SystemExit(1)
        register = json.loads(register_path.read_text(encoding="utf-8"))

        statuses = set(SYNCABLE_STATUSES)
        if options["include_mitigated"]:
            statuses.add("mitigated")

        dry_run = options["dry_run"]
        lemma_type = ContentType.objects.get_for_model(Lemma)
        created_total = 0

        for conflict in register.get("conflicts", []):
            conflict_id = conflict["id"]
            if conflict.get("status") not in statuses:
                self.stdout.write(f"{conflict_id}: skipped (status {conflict.get('status')!r})")
                continue

            locators = self._affected_locators(conflict)
            lemmas = (
                list(self._lemmas_for(locators))
                + list(self._lemmas_for_parser_classes(conflict.get("affected_parser_class_values")))
                + list(self._lemmas_for_headwords(conflict.get("affected_headwords")))
            )
            if not lemmas:
                self.stdout.write(
                    f"{conflict_id}: no affected rows found for its selector"
                )
                continue

            body = NOTE_TEMPLATE.format(
                conflict_id=conflict_id,
                title=conflict["title"],
                summary=conflict["summary"],
                resolution_needed=conflict["resolution_needed"],
            )
            created = 0
            skipped = 0
            seen: set[str] = set()
            for lemma in lemmas:
                if str(lemma.pk) in seen:
                    continue
                seen.add(str(lemma.pk))
                # Checked even on a dry run: reporting rows that already exist
                # as "would create" makes --dry-run predict a write that will
                # not happen.
                if ReviewNote.objects.filter(
                    target_content_type=lemma_type,
                    target_object_id=str(lemma.pk),
                    body__contains=f"'{conflict_id}'",
                ).exists():
                    skipped += 1
                    continue
                created += 1
                if not dry_run:
                    ReviewNote.objects.create(
                        target=lemma,
                        state=ReviewState.NEEDS_REVIEW,
                        body=body,
                    )
            created_total += created
            verb = "would create" if dry_run else "created"
            self.stdout.write(
                f"{conflict_id}: {verb} {created} note(s)"
                + (f", {skipped} already noted" if skipped else "")
            )

        summary = "would create" if dry_run else "created"
        self.stdout.write(
            self.style.SUCCESS(f"{created_total} ReviewNote(s) {summary} across the register")
        )

    def _affected_locators(self, conflict):
        """The extraction-unit locators a conflict affects, from its worklist."""
        worklist = conflict.get("affected_worklist")
        pattern = conflict.get("affected_filter")
        if not worklist or not pattern:
            return []
        path = Path(worklist)
        if not path.exists():
            return []
        selector = re.compile(pattern)
        locators = []
        for index, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
            if index == 0 or not line.strip():
                continue
            columns = line.split("\t")
            if len(columns) < 5:
                continue
            if columns[1] == "unit_recorded_prefix" or not selector.search(columns[3]):
                continue
            locators.append(columns[4].strip())
        return locators

    def _lemmas_for_headwords(self, headwords):
        """Named lemmas, for a conflict that affects specific entries rather than a pattern."""
        if not headwords:
            return []
        return Lemma.objects.filter(headword__in=headwords)

    def _lemmas_for_parser_classes(self, class_values):
        """Lemmas whose parser output recorded one of these class values.

        Used where the affected rows have no work list: the parser's class value
        survives in the unit even when no NounClass row exists to resolve it.
        """
        if not class_values:
            return []
        wanted = {f'"{value}"' for value in class_values}
        object_ids = []
        units = ExtractionUnit.objects.exclude(canonical_record_object_id="").only(
            "canonical_record_object_id", "parser_output"
        )
        for unit in units.iterator(chunk_size=500):
            noun = (unit.parser_output or {}).get("noun")
            classes = noun.get("classes") if isinstance(noun, dict) else None
            if not isinstance(classes, list):
                continue
            if wanted & {f'"{value}"' for value in classes}:
                object_ids.append(str(unit.canonical_record_object_id).replace("-", "").lower())
        if not object_ids:
            return []
        return Lemma.objects.filter(pk__in=object_ids)

    def _lemmas_for(self, locators):
        """The canonical lemmas behind those units, published or not."""
        units = (
            ExtractionUnit.objects.exclude(canonical_record_object_id="")
            .filter(source_location_reference__in=locators)
            .values_list("canonical_record_object_id", flat=True)
        )
        ids = {str(value).replace("-", "").lower() for value in units}
        if not ids:
            return []
        return Lemma.objects.filter(pk__in=ids)
