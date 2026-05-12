from dataclasses import dataclass

from shona_api.editorial.models import ReviewState
from shona_api.lexicon.models import Lemma, NounClass
from shona_api.lexicon.search import SEARCH_NORMALIZER_VERSION, normalize_search_query
from shona_api.phonology import compute_phonology_fields


ANALYZER_VERSION = "shona-morphology-analyzer-v1"
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
