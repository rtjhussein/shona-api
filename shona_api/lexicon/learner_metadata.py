from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from .models import Lemma


FSI_MAPPING_METHOD = "fsi_learner_mapping_v1"


@dataclass(frozen=True)
class FSILearnerMappingConfig:
    beginner_max_lesson: int = 10
    intermediate_max_lesson: int = 25
    max_lesson_for_scoring: int = 30
    max_occurrences_for_scoring: int = 5
    lesson_weight: float = 0.7
    occurrence_weight: float = 0.3
    high_frequency_threshold: float = 0.75
    medium_frequency_threshold: float = 0.4


def score_fsi_mapping(
    *,
    lesson_number: int | None,
    occurrence_count: int = 1,
    config: FSILearnerMappingConfig | None = None,
) -> float:
    config = config or FSILearnerMappingConfig()
    lesson_score = _lesson_score(lesson_number, config.max_lesson_for_scoring)
    occurrence_score = min(
        max(occurrence_count, 0) / config.max_occurrences_for_scoring,
        1.0,
    )
    weighted_score = (
        (lesson_score * config.lesson_weight)
        + (occurrence_score * config.occurrence_weight)
    )
    return round(max(0.0, min(weighted_score, 1.0)), 3)


def map_fsi_learner_metadata(
    lemma: Lemma,
    *,
    source_locator: str,
    unit: str = "",
    lesson_number: int | None = None,
    page_reference: str = "",
    extracted_text: str = "",
    note: str = "",
    occurrence_count: int = 1,
    review_status: str = "reviewed",
    config: FSILearnerMappingConfig | None = None,
) -> Lemma:
    config = config or FSILearnerMappingConfig()
    score = score_fsi_mapping(
        lesson_number=lesson_number,
        occurrence_count=occurrence_count,
        config=config,
    )
    source_link = {
        "source_key": "source_fsi",
        "source_locator": source_locator,
        "unit": unit,
        "lesson_number": lesson_number,
        "page_reference": page_reference,
        "extracted_text": extracted_text,
        "note": note,
        "review_status": review_status,
        "mapping_method": FSI_MAPPING_METHOD,
    }

    with transaction.atomic():
        lemma = Lemma.objects.select_for_update().get(pk=lemma.pk)
        lemma.learner_level = _learner_level_for_lesson(lesson_number, config)
        lemma.curriculum_stage = Lemma.CurriculumStage.GENERAL_SECONDARY
        lemma.curriculum_domains = _merge_labels(
            lemma.curriculum_domains,
            ["vocabulary", "oral_communication"],
        )
        lemma.learning_functions = _merge_labels(
            lemma.learning_functions,
            ["vocabulary", "dialogue_practice"],
        )
        lemma.communication_contexts = _merge_labels(
            lemma.communication_contexts,
            ["conversation"],
        )
        lemma.register_tags = _merge_labels(
            lemma.register_tags,
            ["school_appropriate"],
        )
        lemma.learner_source_links = [*lemma.learner_source_links, source_link]
        if _is_earlier_appearance(lemma.first_appearance_lesson, lesson_number):
            lemma.first_appearance_source_key = "source_fsi"
            lemma.first_appearance_locator = source_locator
            lemma.first_appearance_unit = unit
            lemma.first_appearance_lesson = lesson_number
            lemma.first_appearance_page = page_reference
        if score >= lemma.frequency_score:
            lemma.frequency_score = score
            lemma.frequency_tier = _frequency_tier_for_score(score, config)
        lemma.save(
            update_fields=[
                "learner_level",
                "curriculum_stage",
                "curriculum_domains",
                "learning_functions",
                "communication_contexts",
                "register_tags",
                "learner_source_links",
                "first_appearance_source_key",
                "first_appearance_locator",
                "first_appearance_unit",
                "first_appearance_lesson",
                "first_appearance_page",
                "frequency_score",
                "frequency_tier",
                "updated_at",
            ]
        )
    return lemma


def _lesson_score(lesson_number: int | None, max_lesson: int) -> float:
    if lesson_number is None or lesson_number <= 0 or max_lesson <= 1:
        return 0.0
    capped_lesson = min(lesson_number, max_lesson)
    return 1.0 - ((capped_lesson - 1) / (max_lesson - 1))


def _learner_level_for_lesson(
    lesson_number: int | None,
    config: FSILearnerMappingConfig,
) -> str:
    if lesson_number is None:
        return Lemma.LearnerLevel.UNKNOWN
    if lesson_number <= config.beginner_max_lesson:
        return Lemma.LearnerLevel.BEGINNER
    if lesson_number <= config.intermediate_max_lesson:
        return Lemma.LearnerLevel.INTERMEDIATE
    return Lemma.LearnerLevel.UNKNOWN


def _frequency_tier_for_score(score: float, config: FSILearnerMappingConfig) -> str:
    if score >= config.high_frequency_threshold:
        return Lemma.FrequencyTier.HIGH
    if score >= config.medium_frequency_threshold:
        return Lemma.FrequencyTier.MEDIUM
    if score > 0:
        return Lemma.FrequencyTier.LOW
    return Lemma.FrequencyTier.UNKNOWN


def _merge_labels(existing: list[str], additions: list[str]) -> list[str]:
    labels = list(existing)
    for label in additions:
        if label not in labels:
            labels.append(label)
    return labels


def _is_earlier_appearance(
    current_lesson: int | None,
    candidate_lesson: int | None,
) -> bool:
    if current_lesson is None:
        return True
    if candidate_lesson is None:
        return False
    return candidate_lesson < current_lesson


def apply_rule_based_curriculum_tags(lemma) -> bool:
    """
    Apply rule-based curriculum stage, contexts, domains, and register tags to a Lemma 
    based on its headword and sense definitions. Returns True if any updates were applied.
    """
    import re
    from django.db import transaction
    from .models import Lemma

    keywords = {
        "greetings": re.compile(r"\b(?:mhoro|kwaziwai|greet|welcome|say hello|hello|greeting)\b", re.I),
        "family": re.compile(r"\b(?:amai|baba|hanzvadzi|child|son|daughter|mother|father|brother|sister|aunt|uncle|family)\b", re.I),
        "environment": re.compile(r"\b(?:musha|gomo|rwizi|mhuka|sango|river|mountain|animal|forest|tree|rain|sun|weather|nature)\b", re.I),
        "time": re.compile(r"\b(?:nguva|zuva|mwaka|nhasi|mangwana|time|hour|day|year|yesterday|tomorrow|month)\b", re.I)
    }

    matched_contexts = []
    definitions_text = " ".join([sense.definition for sense in lemma.senses.all()])
    text_to_match = f"{lemma.headword} {lemma.normalized_headword} {definitions_text}"

    for context_key, regex in keywords.items():
        if regex.search(text_to_match):
            matched_contexts.append(context_key)

    if not matched_contexts:
        return False

    stage = Lemma.CurriculumStage.FORMS_1_2 if any(c in ("greetings", "family", "time") for c in matched_contexts) else Lemma.CurriculumStage.GENERAL_SECONDARY
    domains = ["vocabulary"]
    if "greetings" in matched_contexts or "family" in matched_contexts:
        domains.append("oral_communication")

    # Merge labels helper from this module
    lemma.curriculum_stage = stage
    lemma.curriculum_domains = _merge_labels(lemma.curriculum_domains, domains)
    lemma.learning_functions = _merge_labels(lemma.learning_functions, ["vocabulary"])
    lemma.communication_contexts = _merge_labels(lemma.communication_contexts, matched_contexts)
    lemma.register_tags = _merge_labels(lemma.register_tags, ["school_appropriate"])

    # Avoid duplicate rule match source links
    source_locator = "curriculum_notes_forms_1_4.pdf:rule_match"
    existing_link = any(link.get("source_locator") == source_locator for link in lemma.learner_source_links)
    
    if not existing_link:
        source_link = {
            "source_key": "source_curriculum_notes",
            "source_locator": source_locator,
            "review_status": "reviewed",
            "mapping_method": "rule_curriculum_mapping_v1",
            "note": "Automatically matched based on keyword lexicons (Post-Publish Signal)."
        }
        lemma.learner_source_links = [*lemma.learner_source_links, source_link]

    lemma.save(
        update_fields=[
            "curriculum_stage",
            "curriculum_domains",
            "learning_functions",
            "communication_contexts",
            "register_tags",
            "learner_source_links",
            "updated_at",
        ]
    )
    return True
