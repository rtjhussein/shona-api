from dataclasses import dataclass

from shona_api.editorial.models import ReviewState
from shona_api.lexicon.models import Lemma, NounClass
from shona_api.lexicon.search import SEARCH_NORMALIZER_VERSION, normalize_search_query
from shona_api.phonology import compute_phonology_fields


ANALYZER_VERSION = "shona-morphology-analyzer-v1"
GENERATOR_VERSION = "shona-morphology-generator-v1"
SUPPORTED_RULE_ID = "fortune.verbal.slots.001"
SUPPORTED_TENSE_ASPECT_MARKER = "no"
SUPPORTED_REVIEW_STATES = (
    ReviewState.APPROVED,
    ReviewState.PUBLISHED,
)


@dataclass(frozen=True)
class AnalysisFailure(Exception):
    code: str
    message: str
    detail: dict[str, object] | None = None


@dataclass(frozen=True)
class GenerationFailure(Exception):
    code: str
    message: str
    detail: dict[str, object] | None = None


PERSON_SUBJECT_CONCORDS = (
    {
        "surface": "ndi",
        "slot_type": "person",
        "person": "first",
        "number": "singular",
        "label": "1st person singular subject concord",
        "confidence": 0.86,
    },
    {
        "surface": "u",
        "slot_type": "person",
        "person": "second",
        "number": "singular",
        "label": "2nd person singular subject concord",
        "confidence": 0.84,
    },
    {
        "surface": "ti",
        "slot_type": "person",
        "person": "first",
        "number": "plural",
        "label": "1st person plural subject concord",
        "confidence": 0.84,
    },
    {
        "surface": "mu",
        "slot_type": "person",
        "person": "second",
        "number": "plural",
        "label": "2nd person plural subject concord",
        "confidence": 0.82,
    },
)


def analyze_text(raw_text: str, *, rule_set_version: str) -> dict[str, object]:
    normalized = normalize_search_query(raw_text)
    if not normalized:
        raise AnalysisFailure(
            code="ANALYSIS_TEXT_REQUIRED",
            message="Analysis requires a non-empty 'text' string.",
        )
    if " " in normalized:
        raise AnalysisFailure(
            code="ANALYSIS_UNSUPPORTED",
            message="Only single-token verb forms are supported by analyze v1.",
            detail={"normalized": normalized},
        )

    candidates = _candidate_subject_concords()
    analyses = [
        analysis
        for candidate in candidates
        if (analysis := _analyze_present_positive(normalized, candidate)) is not None
    ]
    if not analyses:
        raise AnalysisFailure(
            code="ANALYSIS_UNSUPPORTED",
            message=(
                "No supported v1 analysis matched the input. Supported v1 forms "
                "are positive present verb forms using subject concord + 'no' + "
                "a reviewed verb-stem lemma."
            ),
            detail={
                "normalized": normalized,
                "supported_shape": "subject_concord + no + verb_stem",
                "supported_rule_ids": [SUPPORTED_RULE_ID],
            },
        )

    analyses.sort(key=lambda item: item["confidence"], reverse=True)
    return {
        "query": {
            "raw": raw_text,
            "normalized": normalized,
            "normalizer": SEARCH_NORMALIZER_VERSION,
        },
        "analyzer_version": ANALYZER_VERSION,
        "rule_set_version": rule_set_version,
        "count": len(analyses),
        "analyses": analyses,
    }


def generate_form(
    *,
    lemma_public_id: str,
    features: dict[str, object],
    rule_set_version: str,
) -> dict[str, object]:
    lemma = _get_generation_verb_stem(lemma_public_id)
    _validate_supported_generation_features(features)
    subject_candidate = _resolve_generation_subject(features["subject"])

    form = (
        f"{subject_candidate['surface']}"
        f"{SUPPORTED_TENSE_ASPECT_MARKER}"
        f"{lemma.normalized_headword}"
    )
    generated = {
        "generation_type": "verb_form",
        "form": form,
        "normalized": normalize_search_query(form),
        "confidence": subject_candidate["confidence"],
        "rule_id": SUPPORTED_RULE_ID,
        "lemma": _lemma_payload(lemma),
        "slots": {
            "subject": _subject_slot(subject_candidate),
            "tense_aspect": {
                "surface": SUPPORTED_TENSE_ASPECT_MARKER,
                "value": "present",
                "label": "positive present marker",
            },
            "polarity": {
                "surface": "",
                "value": "positive",
                "label": "No negative marker generated in supported v1 pattern.",
            },
            "object": None,
            "verb_stem": {
                "surface": lemma.normalized_headword,
                "lemma_public_id": lemma.public_id,
            },
            "final_vowel": {
                "surface": lemma.normalized_headword[-1],
                "value": lemma.normalized_headword[-1],
            },
        },
        "phonology": compute_phonology_fields(form),
    }
    return {
        "input": {
            "lemma_public_id": lemma_public_id,
            "features": features,
        },
        "generator_version": GENERATOR_VERSION,
        "rule_set_version": rule_set_version,
        "confidence": generated["confidence"],
        "generated": generated,
        "warnings": [
            {
                "code": "GENERATION_PARTIAL_RULE_SET",
                "message": (
                    "v1 generation supports only single-token positive present verb forms."
                ),
            },
            {
                "code": "TONE_NOT_GENERATED",
                "message": (
                    "Tone, object markers, negative forms, and extensions are not generated."
                ),
            },
        ],
        "metadata": {
            "supported_shape": "subject_concord + no + verb_stem",
            "supported_rule_ids": [SUPPORTED_RULE_ID],
            "normalizer": SEARCH_NORMALIZER_VERSION,
        },
    }


def _candidate_subject_concords() -> list[dict[str, object]]:
    candidates = [dict(candidate) for candidate in PERSON_SUBJECT_CONCORDS]
    candidates.extend(_noun_class_subject_concords())
    return sorted(candidates, key=lambda candidate: len(candidate["surface"]), reverse=True)


def _noun_class_subject_concords() -> list[dict[str, object]]:
    return [
        {
            "surface": noun_class.subject_concord.casefold(),
            "slot_type": "noun_class",
            "class_number": noun_class.class_number,
            "noun_class_public_id": noun_class.public_id,
            "label": noun_class.label,
            "confidence": 0.78,
        }
        for noun_class in NounClass.objects.filter(
            review_state__in=SUPPORTED_REVIEW_STATES,
        )
        .exclude(subject_concord="")
        .order_by("display_order", "class_number")
    ]


def _analyze_present_positive(
    normalized: str, subject_candidate: dict[str, object]
) -> dict[str, object] | None:
    subject_surface = subject_candidate["surface"]
    prefix = f"{subject_surface}{SUPPORTED_TENSE_ASPECT_MARKER}"
    if not normalized.startswith(prefix):
        return None

    verb_stem = normalized.removeprefix(prefix)
    if not verb_stem:
        return None

    lemma = _get_reviewed_verb_stem(verb_stem)
    if lemma is None:
        return None

    phonology = compute_phonology_fields(normalized)
    return {
        "analysis_type": "verb_form",
        "confidence": subject_candidate["confidence"],
        "rule_id": SUPPORTED_RULE_ID,
        "lemma": {
            "public_id": lemma.public_id,
            "headword": lemma.headword,
            "normalized_headword": lemma.normalized_headword,
            "part_of_speech_code": lemma.part_of_speech_code,
        },
        "slots": {
            "subject": _subject_slot(subject_candidate),
            "tense_aspect": {
                "surface": SUPPORTED_TENSE_ASPECT_MARKER,
                "value": "present",
                "label": "positive present marker",
            },
            "polarity": {
                "surface": "",
                "value": "positive",
                "label": "No negative marker detected in supported v1 pattern.",
            },
            "object": None,
            "verb_stem": {
                "surface": verb_stem,
                "lemma_public_id": lemma.public_id,
            },
            "final_vowel": {
                "surface": verb_stem[-1],
                "value": verb_stem[-1],
            },
        },
        "phonology": phonology,
        "limitations": [
            "v1 supports only single-token positive present verb forms.",
            "Object markers, negative forms, extensions, and tone are not analyzed.",
        ],
    }


def _get_reviewed_verb_stem(normalized_stem: str) -> Lemma | None:
    return (
        Lemma.objects.filter(
            review_state__in=SUPPORTED_REVIEW_STATES,
            headword_kind=Lemma.HeadwordKind.VERB_STEM,
            normalized_headword=normalized_stem,
        )
        .order_by("normalized_headword", "public_id")
        .first()
    )


def _get_generation_verb_stem(lemma_public_id: str) -> Lemma:
    if not lemma_public_id:
        raise GenerationFailure(
            code="GENERATION_LEMMA_REQUIRED",
            message="Generation requires a non-empty 'lemma_public_id' string.",
            detail={"field": "lemma_public_id", "expected_type": "string"},
        )
    lemma = (
        Lemma.objects.filter(
            public_id=lemma_public_id,
            review_state__in=SUPPORTED_REVIEW_STATES,
            headword_kind=Lemma.HeadwordKind.VERB_STEM,
        )
        .order_by("public_id")
        .first()
    )
    if lemma is None:
        raise GenerationFailure(
            code="GENERATION_UNSUPPORTED",
            message=(
                "No supported v1 generation rule matched the lemma. Supported v1 "
                "generation requires a reviewed verb-stem lemma."
            ),
            detail={
                "field": "lemma_public_id",
                "received": lemma_public_id,
                "supported_lemma_kind": Lemma.HeadwordKind.VERB_STEM,
                "supported_review_states": list(SUPPORTED_REVIEW_STATES),
                "supported_shape": "subject_concord + no + verb_stem",
                "supported_rule_ids": [SUPPORTED_RULE_ID],
            },
        )
    if not lemma.normalized_headword:
        raise GenerationFailure(
            code="GENERATION_UNSUPPORTED",
            message="The lemma cannot be generated because it has no normalized stem.",
            detail={
                "field": "lemma_public_id",
                "received": lemma_public_id,
                "supported_shape": "subject_concord + no + verb_stem",
                "supported_rule_ids": [SUPPORTED_RULE_ID],
            },
        )
    return lemma


def _validate_supported_generation_features(features: dict[str, object]) -> None:
    if features.get("generation_type") != "verb_form":
        raise _unsupported_generation(
            field="generation_type",
            received=features.get("generation_type"),
            supported=["verb_form"],
        )
    if features.get("tense_aspect") != "present":
        raise _unsupported_generation(
            field="tense_aspect",
            received=features.get("tense_aspect"),
            supported=["present"],
        )
    if features.get("polarity") != "positive":
        raise _unsupported_generation(
            field="polarity",
            received=features.get("polarity"),
            supported=["positive"],
        )
    if features.get("object") not in (None, ""):
        raise _unsupported_generation(
            field="object",
            received=features.get("object"),
            supported=[None],
        )
    if not isinstance(features.get("subject"), dict):
        raise _unsupported_generation(
            field="subject",
            received=features.get("subject"),
            supported=["structured subject object"],
        )


def _resolve_generation_subject(subject: dict[str, object]) -> dict[str, object]:
    subject_type = subject.get("type")
    if subject_type == "person":
        for candidate in PERSON_SUBJECT_CONCORDS:
            if (
                candidate["person"] == subject.get("person")
                and candidate["number"] == subject.get("number")
            ):
                return dict(candidate)
        raise _unsupported_generation(
            field="subject",
            received=subject,
            supported=[
                {
                    "type": "person",
                    "person": candidate["person"],
                    "number": candidate["number"],
                }
                for candidate in PERSON_SUBJECT_CONCORDS
            ],
        )
    if subject_type == "noun_class":
        noun_class = (
            NounClass.objects.filter(
                class_number=subject.get("class_number"),
                review_state__in=SUPPORTED_REVIEW_STATES,
            )
            .exclude(subject_concord="")
            .order_by("display_order", "class_number")
            .first()
        )
        if noun_class is not None:
            return {
                "surface": noun_class.subject_concord.casefold(),
                "slot_type": "noun_class",
                "class_number": noun_class.class_number,
                "noun_class_public_id": noun_class.public_id,
                "label": noun_class.label,
                "confidence": 0.78,
            }
    raise _unsupported_generation(
        field="subject",
        received=subject,
        supported=[
            "person subject with person and number",
            "reviewed noun_class subject with class_number and subject_concord",
        ],
    )


def _unsupported_generation(*, field: str, received, supported) -> GenerationFailure:
    return GenerationFailure(
        code="GENERATION_UNSUPPORTED",
        message=f"Unsupported v1 generation feature: {field}.",
        detail={
            "field": field,
            "received": received,
            "supported": supported,
            "supported_shape": "subject_concord + no + verb_stem",
            "supported_rule_ids": [SUPPORTED_RULE_ID],
        },
    )


def _lemma_payload(lemma: Lemma) -> dict[str, object]:
    return {
        "public_id": lemma.public_id,
        "headword": lemma.headword,
        "normalized_headword": lemma.normalized_headword,
        "part_of_speech_code": lemma.part_of_speech_code,
    }


def _subject_slot(subject_candidate: dict[str, object]) -> dict[str, object]:
    slot = {
        "surface": subject_candidate["surface"],
        "type": subject_candidate["slot_type"],
        "label": subject_candidate["label"],
    }
    for field_name in (
        "person",
        "number",
        "class_number",
        "noun_class_public_id",
    ):
        if field_name in subject_candidate:
            slot[field_name] = subject_candidate[field_name]
    return slot
