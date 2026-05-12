from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from shona_api.editorial.models import (
    AuditLog,
    EditorialDecision,
    EditorialDecisionRecord,
    ReviewState,
)
from shona_api.lexicon.models import Form, Lemma, Sense, ToneRecord

from .models import ExtractionUnit


class ExtractionUnitPublishError(ValueError):
    pass


@dataclass(frozen=True)
class PublishedExtractionBundle:
    extraction_unit: ExtractionUnit
    lemma: Lemma
    senses: list[Sense]
    tone_records: list[ToneRecord]
    forms: list[Form]
    editorial_decision: EditorialDecision
    audit_log: AuditLog


def publish_reviewed_extraction_unit(
    extraction_unit: ExtractionUnit,
    *,
    decided_by=None,
) -> PublishedExtractionBundle:
    if extraction_unit.review_state != ReviewState.APPROVED:
        raise ExtractionUnitPublishError(
            "Only approved extraction units can be published."
        )

    parser_output = extraction_unit.parser_output or {}
    if extraction_unit.parser_status == ExtractionUnit.ParserStatus.FAILED:
        raise ExtractionUnitPublishError(
            "Extraction units with parser failures cannot be published."
        )
    if parser_output.get("errors"):
        raise ExtractionUnitPublishError(
            "Extraction units with parser errors cannot be published."
        )
    if extraction_unit.canonical_record_content_type_id or extraction_unit.canonical_record_object_id:
        raise ExtractionUnitPublishError("This extraction unit has already been published.")

    with transaction.atomic():
        extraction_unit = (
            ExtractionUnit.objects.select_for_update()
            .select_related("source")
            .get(pk=extraction_unit.pk)
        )
        if extraction_unit.review_state != ReviewState.APPROVED:
            raise ExtractionUnitPublishError(
                "Only approved extraction units can be published."
            )
        parser_output = extraction_unit.parser_output or {}
        if extraction_unit.parser_status == ExtractionUnit.ParserStatus.FAILED:
            raise ExtractionUnitPublishError(
                "Extraction units with parser failures cannot be published."
            )
        if parser_output.get("errors"):
            raise ExtractionUnitPublishError(
                "Extraction units with parser errors cannot be published."
            )
        if extraction_unit.canonical_record_content_type_id or extraction_unit.canonical_record_object_id:
            raise ExtractionUnitPublishError(
                "This extraction unit has already been published."
            )

        provenance = _build_shared_provenance(extraction_unit)

        lemma = Lemma.objects.create(
            headword=parser_output.get("headword") or extraction_unit.raw_text.strip(),
            headword_kind=_map_headword_kind(parser_output.get("headword_kind")),
            part_of_speech_code=_parser_pos_code(parser_output),
            part_of_speech_label=_parser_pos_label(parser_output),
            dialects=list(parser_output.get("dialects") or []),
            comparative_bantu_marker=bool(
                parser_output.get("comparative_bantu_marker", False)
            ),
            provenance=_record_provenance(
                provenance,
                "lemma",
                headword=parser_output.get("headword"),
                headword_kind=parser_output.get("headword_kind", "unknown"),
                part_of_speech=_parser_part_of_speech(parser_output),
            ),
            review_state=ReviewState.PUBLISHED,
        )

        senses = [
            Sense.objects.create(
                lemma=lemma,
                number=sense_data["number"],
                definition=sense_data["definition"],
                dialects=list(sense_data.get("dialects") or []),
                grammar=list(sense_data.get("grammar") or []),
                examples=list(sense_data.get("examples") or []),
                cross_references=list(sense_data.get("cross_references") or []),
                provenance=_record_provenance(
                    provenance,
                    "sense",
                    sense_number=sense_data["number"],
                    definition=sense_data["definition"],
                    grammar=list(sense_data.get("grammar") or []),
                    dialects=list(sense_data.get("dialects") or []),
                ),
                review_state=ReviewState.PUBLISHED,
            )
            for sense_data in parser_output.get("senses") or []
        ]

        tone_records = []
        tone_pattern = parser_output.get("tone_pattern")
        if tone_pattern:
            tone_records.append(
                ToneRecord.objects.create(
                    lemma=lemma,
                    pattern=tone_pattern,
                    notation_system=ToneRecord.NotationSystem.HANNAN_BRACKET,
                    note="Published from reviewed extraction unit.",
                    provenance=_record_provenance(
                        provenance,
                        "tone_record",
                        tone_pattern=tone_pattern,
                    ),
                    review_state=ReviewState.PUBLISHED,
                )
            )

        forms = []
        for derived_form_group in parser_output.get("derived_forms") or []:
            for form_text in derived_form_group.get("forms", []):
                forms.append(
                    Form.objects.create(
                        lemma=lemma,
                        form_text=form_text,
                        form_kind=Form.FormKind.DERIVED,
                        dialects=list(parser_output.get("dialects") or []),
                        grammar=list(_parser_entry_grammar(parser_output)),
                        provenance=_record_provenance(
                            provenance,
                            "form",
                            form_text=form_text,
                            form_kind=Form.FormKind.DERIVED,
                        ),
                        review_state=ReviewState.PUBLISHED,
                    )
                )

        decision = EditorialDecision.objects.create(
            decision_type=EditorialDecision.DecisionType.PUBLISH,
            decided_by=decided_by,
            summary=f"Publish extraction unit {extraction_unit.source_location_reference}",
            rationale="Reviewed extraction was promoted into canonical lexicon records.",
            metadata={
                "extraction_unit_id": str(extraction_unit.pk),
                "parser_status": extraction_unit.parser_status,
                "parser_uncertainties": parser_output.get("uncertainties", []),
                "canonical_record_public_id": lemma.public_id,
                "canonical_record_type": "lemma",
            },
        )
        decision.record_affected_record(
            lemma,
            relationship=EditorialDecisionRecord.Relationship.PRIMARY,
        )
        for record in [*senses, *tone_records, *forms]:
            decision.record_affected_record(
                record,
                relationship=EditorialDecisionRecord.Relationship.CREATED,
            )

        audit_log = AuditLog.objects.record(
            action=AuditLog.Action.RECORD_STATE_CHANGED,
            actor=decided_by,
            target=extraction_unit,
            metadata={
                "from": extraction_unit.review_state,
                "to": ReviewState.PUBLISHED,
                "decision_id": str(decision.pk),
                "canonical_record_public_id": lemma.public_id,
                "canonical_record_content_type": "lexicon.lemma",
            },
        )

        extraction_unit.canonical_record = lemma
        extraction_unit.review_state = ReviewState.PUBLISHED
        extraction_unit.provenance = {
            **extraction_unit.provenance,
            "publication": {
                "canonical_record_public_id": lemma.public_id,
                "canonical_record_type": "lemma",
                "sense_public_ids": [sense.public_id for sense in senses],
                "tone_record_public_ids": [tone.public_id for tone in tone_records],
                "form_public_ids": [form.public_id for form in forms],
                "decision_id": str(decision.pk),
            },
        }
        extraction_unit.save()

    return PublishedExtractionBundle(
        extraction_unit=extraction_unit,
        lemma=lemma,
        senses=senses,
        tone_records=tone_records,
        forms=forms,
        editorial_decision=decision,
        audit_log=audit_log,
    )


def _build_shared_provenance(extraction_unit: ExtractionUnit) -> dict[str, object]:
    parser_output = extraction_unit.parser_output or {}
    return {
        "source_key": extraction_unit.source_key,
        "source_location_reference": extraction_unit.source_location_reference,
        "parser": extraction_unit.parser_name,
        "parser_status": extraction_unit.parser_status,
        "parser_errors": list(parser_output.get("errors", [])),
        "parser_uncertainties": list(parser_output.get("uncertainties", [])),
        "extraction_unit_id": str(extraction_unit.pk),
        "extraction_unit_review_state": extraction_unit.review_state,
    }


def _record_provenance(
    shared_provenance: dict[str, object],
    record_type: str,
    **extra: object,
) -> dict[str, object]:
    return {
        **shared_provenance,
        "record_type": record_type,
        **extra,
    }


def _parser_part_of_speech(parser_output: dict[str, object]) -> dict[str, str] | None:
    part_of_speech = parser_output.get("part_of_speech")
    return part_of_speech if isinstance(part_of_speech, dict) else None


def _parser_pos_code(parser_output: dict[str, object]) -> str:
    part_of_speech = _parser_part_of_speech(parser_output)
    if part_of_speech:
        code = part_of_speech.get("code")
        if isinstance(code, str):
            return code
    return ""


def _parser_pos_label(parser_output: dict[str, object]) -> str:
    part_of_speech = _parser_part_of_speech(parser_output)
    if part_of_speech:
        label = part_of_speech.get("label")
        if isinstance(label, str):
            return label
    return ""


def _parser_entry_grammar(parser_output: dict[str, object]) -> list[str]:
    verb_payload = parser_output.get("verb")
    if isinstance(verb_payload, dict):
        entry_grammar = verb_payload.get("entry_grammar")
        if isinstance(entry_grammar, list):
            return [grammar for grammar in entry_grammar if isinstance(grammar, str)]
    return []


def _map_headword_kind(parser_headword_kind: object) -> str:
    mapping = {
        "word": Lemma.HeadwordKind.WORD,
        "noun": Lemma.HeadwordKind.NOUN,
        "verb_stem": Lemma.HeadwordKind.VERB_STEM,
        "ideophone": Lemma.HeadwordKind.IDEOPHONE,
    }
    if isinstance(parser_headword_kind, str):
        return mapping.get(parser_headword_kind, Lemma.HeadwordKind.UNKNOWN)
    return Lemma.HeadwordKind.UNKNOWN
