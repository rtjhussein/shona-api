from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from shona_api.editorial.models import AuditLog, ReviewState
from shona_api.extraction.gpt_jsonl import (
    build_tone_record_payloads,
    normalize_gpt_parser_output,
)
from shona_api.extraction.models import ExtractionUnit
from shona_api.lexicon.models import Sense, ToneRecord


class Command(BaseCommand):
    help = (
        "Repair GPT-5.5 Hannan extraction units and published canonical children "
        "after parser-output structuring improvements."
    )

    def add_arguments(self, parser):
        parser.add_argument("--batch-id", default="")
        parser.add_argument("--locator", default="")
        parser.add_argument("--parser-name", default="gpt-5.5-thinking")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report records that would be repaired without writing changes.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        qs = ExtractionUnit.objects.filter(parser_name=options["parser_name"])
        if options["batch_id"]:
            qs = qs.filter(batch_id=options["batch_id"])
        if options["locator"]:
            qs = qs.filter(source_location_reference=options["locator"])

        inspected = 0
        changed = 0
        skipped = 0
        failed = 0

        for unit in qs.order_by("source_location_reference", "pk"):
            inspected += 1
            try:
                would_change = _unit_needs_repair(unit)
                if not would_change:
                    skipped += 1
                    continue
                changed += 1
                self.stdout.write(
                    f"{'Would repair' if dry_run else 'Repairing'} "
                    f"{unit.source_location_reference}"
                )
                if not dry_run:
                    _repair_unit(unit)
            except Exception as exc:
                failed += 1
                self.stderr.write(
                    f"Could not repair {unit.source_location_reference}: {exc}"
                )

        verb = "Would repair" if dry_run else "Repaired"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb} {changed} of {inspected} GPT extraction unit(s); "
                f"{skipped} skipped; {failed} failed."
            )
        )


def _unit_needs_repair(unit: ExtractionUnit) -> bool:
    current = unit.parser_output or {}
    normalized = normalize_gpt_parser_output(current, raw_text=unit.raw_text)
    if normalized != current:
        return True
    if unit.canonical_record_object_id and unit.canonical_record:
        lemma = unit.canonical_record
        expected_tones = build_tone_record_payloads(normalized)
        current_tones = [
            {"pattern": tone.pattern, "dialects": list(tone.dialects or [])}
            for tone in lemma.tone_records.all().order_by("created_at", "pk")
        ]
        if expected_tones != current_tones:
            return True
        expected_senses = [
            {
                "number": sense["number"],
                "definition": sense["definition"],
                "dialects": list(sense.get("dialects") or []),
                "grammar": list(sense.get("grammar") or []),
                "examples": list(sense.get("examples") or []),
                "cross_references": list(sense.get("cross_references") or []),
            }
            for sense in normalized.get("senses") or []
        ]
        current_senses = [
            {
                "number": sense.number,
                "definition": sense.definition,
                "dialects": list(sense.dialects or []),
                "grammar": list(sense.grammar or []),
                "examples": list(sense.examples or []),
                "cross_references": list(sense.cross_references or []),
            }
            for sense in lemma.senses.all().order_by("number", "pk")
        ]
        return expected_senses != current_senses
    return False


@transaction.atomic
def _repair_unit(unit: ExtractionUnit) -> None:
    unit = ExtractionUnit.objects.select_for_update().get(pk=unit.pk)
    normalized = normalize_gpt_parser_output(unit.parser_output or {}, raw_text=unit.raw_text)
    unit.parser_output = normalized
    unit.parser_status = ExtractionUnit.status_from_parser_output(normalized)
    unit.save(update_fields=("parser_output", "parser_status", "updated_at"))

    if not unit.canonical_record_object_id or unit.canonical_record is None:
        return

    lemma = unit.canonical_record
    if unit.parser_status == ExtractionUnit.ParserStatus.FAILED:
        raise ValueError("normalized parser output still contains parser errors")

    _repair_senses(unit, lemma, normalized)
    _repair_tones(unit, lemma, normalized)
    AuditLog.objects.record(
        action=AuditLog.Action.RECORD_STATE_CHANGED,
        target=unit,
        metadata={
            "repair": "repair_gpt_hannan_structuring",
            "canonical_record_public_id": lemma.public_id,
        },
    )


def _repair_senses(unit: ExtractionUnit, lemma, parser_output: dict) -> None:
    expected_numbers = set()
    existing_by_number = {sense.number: sense for sense in lemma.senses.all()}
    for sense_data in parser_output.get("senses") or []:
        number = int(sense_data["number"])
        expected_numbers.add(number)
        sense = existing_by_number.get(number)
        if sense is None:
            sense = Sense(lemma=lemma, number=number)
        sense.definition = sense_data["definition"]
        sense.dialects = list(sense_data.get("dialects") or [])
        sense.grammar = list(sense_data.get("grammar") or [])
        sense.examples = list(sense_data.get("examples") or [])
        sense.cross_references = list(sense_data.get("cross_references") or [])
        sense.review_state = ReviewState.PUBLISHED
        sense.provenance = {
            **(sense.provenance or {}),
            "source_key": unit.source_key,
            "source_location_reference": unit.source_location_reference,
            "parser": unit.parser_name,
            "record_type": "sense",
            "sense_number": number,
            "repair": "repair_gpt_hannan_structuring",
        }
        sense.save()

    lemma.senses.exclude(number__in=expected_numbers).delete()


def _repair_tones(unit: ExtractionUnit, lemma, parser_output: dict) -> None:
    expected_tones = build_tone_record_payloads(parser_output)
    existing = list(lemma.tone_records.all().order_by("created_at", "pk"))

    for index, tone_data in enumerate(expected_tones):
        tone = existing[index] if index < len(existing) else ToneRecord(lemma=lemma)
        tone.pattern = tone_data["pattern"]
        tone.dialects = list(tone_data.get("dialects") or [])
        tone.notation_system = ToneRecord.NotationSystem.HANNAN_BRACKET
        tone.note = "Repaired from GPT-5.5 parser output."
        tone.review_state = ReviewState.PUBLISHED
        tone.provenance = {
            **(tone.provenance or {}),
            "source_key": unit.source_key,
            "source_location_reference": unit.source_location_reference,
            "parser": unit.parser_name,
            "record_type": "tone_record",
            "tone_pattern": tone.pattern,
            "dialects": tone.dialects,
            "repair": "repair_gpt_hannan_structuring",
        }
        tone.save()

    for stale in existing[len(expected_tones):]:
        stale.delete()
