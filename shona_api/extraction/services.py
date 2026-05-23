from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.db.models import Q

from shona_api.editorial.models import (
    AuditLog,
    EditorialDecision,
    EditorialDecisionRecord,
    ReviewState,
)
from shona_api.figurative_language.models import FigurativeExpression
from shona_api.lexicon.examples import (
    EXAMPLE_SCHEMA_VERSION,
    normalize_example_pairs,
)
from shona_api.lexicon.models import Form, Lemma, NounClass, Sense, ToneRecord

from .gpt_jsonl import build_tone_record_payloads, validate_publishable_parser_output
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
    figurative_expressions: list[FigurativeExpression]
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
    publish_validation_errors = validate_publishable_parser_output(parser_output)
    if publish_validation_errors:
        raise ExtractionUnitPublishError(publish_validation_errors[0])
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
        publish_validation_errors = validate_publishable_parser_output(parser_output)
        if publish_validation_errors:
            raise ExtractionUnitPublishError(publish_validation_errors[0])
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
            noun_class=_parser_noun_class(parser_output),
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

        senses = []
        for sense_data in parser_output.get("senses") or []:
            examples = normalize_example_pairs(sense_data.get("examples"))
            sense_provenance = _record_provenance(
                provenance,
                "sense",
                sense_number=sense_data["number"],
                definition=sense_data["definition"],
                grammar=list(sense_data.get("grammar") or []),
                dialects=list(sense_data.get("dialects") or []),
                examples=examples,
                example_schema_version=EXAMPLE_SCHEMA_VERSION,
            )
            raw_examples = sense_data.get("examples")
            if isinstance(raw_examples, list):
                sense_provenance["raw_examples"] = list(raw_examples)
            senses.append(
                Sense.objects.create(
                    lemma=lemma,
                    number=sense_data["number"],
                    definition=sense_data["definition"],
                    dialects=list(sense_data.get("dialects") or []),
                    grammar=list(sense_data.get("grammar") or []),
                    examples=examples,
                    cross_references=list(sense_data.get("cross_references") or []),
                    provenance=sense_provenance,
                    review_state=ReviewState.PUBLISHED,
                )
            )

        tone_records = [
            ToneRecord.objects.create(
                lemma=lemma,
                pattern=tone_data["pattern"],
                dialects=list(tone_data.get("dialects") or []),
                notation_system=ToneRecord.NotationSystem.HANNAN_BRACKET,
                note="Published from reviewed extraction unit.",
                provenance=_record_provenance(
                    provenance,
                    "tone_record",
                    tone_pattern=tone_data["pattern"],
                    dialects=list(tone_data.get("dialects") or []),
                ),
                review_state=ReviewState.PUBLISHED,
            )
            for tone_data in build_tone_record_payloads(parser_output)
        ]
        if not tone_records and parser_output.get("tone_pattern"):
            tone_pattern = parser_output["tone_pattern"]
            tone_records.append(
                ToneRecord.objects.create(
                    lemma=lemma,
                    pattern=tone_pattern,
                    dialects=list(parser_output.get("dialects") or []),
                    notation_system=ToneRecord.NotationSystem.HANNAN_BRACKET,
                    note="Published from reviewed extraction unit.",
                    provenance=_record_provenance(
                        provenance,
                        "tone_record",
                        tone_pattern=tone_pattern,
                        dialects=list(parser_output.get("dialects") or []),
                    ),
                    review_state=ReviewState.PUBLISHED,
                )
            )

        forms = []
        for form_payload in _iter_derived_form_payloads(parser_output):
            form_text = form_payload["form_text"]
            form_provenance = _record_provenance(
                provenance,
                "form",
                form_text=form_text,
                form_kind=Form.FormKind.DERIVED,
            )
            if form_payload["evidence"]:
                form_provenance["derived_form_evidence"] = form_payload["evidence"]
            forms.append(
                Form.objects.create(
                    lemma=lemma,
                    form_text=form_text,
                    form_kind=Form.FormKind.DERIVED,
                    dialects=list(parser_output.get("dialects") or []),
                    grammar=list(_parser_entry_grammar(parser_output)),
                    provenance=form_provenance,
                    review_state=ReviewState.PUBLISHED,
                )
            )

        figurative_expressions = _publish_idiomatic_expressions(
            extraction_unit=extraction_unit,
            lemma=lemma,
            parser_output=parser_output,
            provenance=provenance,
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
        for record in [*senses, *tone_records, *forms, *figurative_expressions]:
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
                "figurative_expression_public_ids": [
                    expression.public_id for expression in figurative_expressions
                ],
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
        figurative_expressions=figurative_expressions,
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


def _parser_noun_class(parser_output: dict[str, object]) -> NounClass | None:
    if _map_headword_kind(parser_output.get("headword_kind")) != Lemma.HeadwordKind.NOUN:
        return None
    noun_payload = parser_output.get("noun")
    if not isinstance(noun_payload, dict):
        return None
    classes = noun_payload.get("classes")
    if not isinstance(classes, list):
        return None
    for class_number in classes:
        if isinstance(class_number, str) and class_number.strip():
            return NounClass.objects.filter(class_number=class_number.strip()).first()
    return None


DERIVED_FORM_RELATIONS = {
    ">": "headword_to_derived_form",
    "<-": "derived_form_to_headword",
}


def _iter_derived_form_payloads(
    parser_output: dict[str, object],
) -> list[dict[str, object]]:
    form_payloads: list[dict[str, object]] = []
    for index, item in enumerate(parser_output.get("derived_forms") or []):
        if isinstance(item, str):
            if item.strip():
                form_payloads.append({"form_text": item.strip(), "evidence": {}})
            continue
        if not isinstance(item, dict):
            continue
        evidence = _build_derived_form_evidence(item, source_index=index)
        for form_text in _derived_form_texts_from_item(item):
            form_payloads.append({"form_text": form_text, "evidence": evidence})
    return form_payloads


def _derived_form_texts_from_item(item: dict[str, object]) -> list[str]:
    raw_forms = item.get("forms")
    candidates: list[object]
    if isinstance(raw_forms, list):
        candidates = raw_forms
    else:
        candidates = [
            item.get("form_text"),
            item.get("form"),
            item.get("text"),
        ]

    form_texts: list[str] = []
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            form_texts.append(candidate.strip())
        elif isinstance(candidate, dict):
            nested_text = (
                candidate.get("form_text")
                or candidate.get("form")
                or candidate.get("text")
            )
            if isinstance(nested_text, str) and nested_text.strip():
                form_texts.append(nested_text.strip())
    return form_texts


def _build_derived_form_evidence(
    item: dict[str, object],
    *,
    source_index: int,
) -> dict[str, object]:
    marker = _clean_parser_string(
        item.get("marker") or item.get("relation_marker")
    )
    source_note = _clean_parser_string(
        item.get("source_note")
        or item.get("raw_source_note")
        or item.get("note")
    )
    raw_source = _clean_parser_string(
        item.get("raw_source")
        or item.get("source_text")
        or item.get("raw_text")
    )
    relation = _clean_parser_string(item.get("relation"))
    if not relation and marker:
        relation = DERIVED_FORM_RELATIONS.get(marker, "source_marker_relation")
    if not source_note and raw_source:
        source_note = raw_source

    evidence: dict[str, object] = {}
    if marker:
        evidence["marker"] = marker
    if relation:
        evidence["relation"] = relation
    if source_note:
        evidence["source_note"] = source_note
    if raw_source and raw_source != source_note:
        evidence["raw_source"] = raw_source
    if evidence:
        evidence["source_path"] = f"derived_forms[{source_index}]"
    return evidence


def _publish_idiomatic_expressions(
    *,
    extraction_unit: ExtractionUnit,
    lemma: Lemma,
    parser_output: dict[str, object],
    provenance: dict[str, object],
) -> list[FigurativeExpression]:
    expressions: list[FigurativeExpression] = []
    for expression_data in parser_output.get("idiomatic_expressions") or []:
        if not isinstance(expression_data, dict):
            continue
        expression_text = _clean_parser_string(expression_data.get("expression_text"))
        meaning = _clean_parser_string(expression_data.get("idiomatic_meaning"))
        english_rendering = _clean_parser_string(expression_data.get("english_rendering"))
        if not expression_text or not (meaning or english_rendering):
            continue

        expression = FigurativeExpression.objects.create(
            expression_text=expression_text,
            subtype=FigurativeExpression.Subtype.MADIMIKIRA,
            subtype_readiness=FigurativeExpression.SubtypeReadiness.ACTIVE,
            idiomatic_meaning=meaning,
            english_rendering=english_rendering,
            usage_note=_clean_parser_string(expression_data.get("usage_note")),
            source_notes=[
                {
                    "source_key": extraction_unit.source_key,
                    "role": "embedded_hannan_idiom",
                }
            ],
            provenance=_record_provenance(
                provenance,
                "figurative_expression",
                subtype=FigurativeExpression.Subtype.MADIMIKIRA,
                source_sense_number=expression_data.get("source_sense_number"),
                dialects=list(expression_data.get("dialects") or []),
                raw_idiom_payload=expression_data,
            ),
            review_state=ReviewState.NEEDS_REVIEW,
        )
        expression.linked_lemmas.add(lemma, *_resolve_linked_lemmas(expression_data))
        expressions.append(expression)
    return expressions


def _resolve_linked_lemmas(expression_data: dict[str, object]) -> list[Lemma]:
    linked_headwords = expression_data.get("linked_headwords")
    if not isinstance(linked_headwords, list):
        return []
    normalized_headwords = {
        headword.removeprefix("-").strip()
        for headword in linked_headwords
        if isinstance(headword, str) and headword.strip()
    }
    if not normalized_headwords:
        return []
    query = Q()
    for headword in normalized_headwords:
        query |= Q(normalized_headword__iexact=headword)
    return list(Lemma.objects.filter(query))


def _clean_parser_string(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())


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
