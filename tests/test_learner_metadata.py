import pytest

from shona_api.lexicon.learner_metadata import (
    FSILearnerMappingConfig,
    map_fsi_learner_metadata,
    score_fsi_mapping,
)
from shona_api.lexicon.models import Lemma


def test_fsi_mapping_score_is_transparent_and_threshold_based():
    config = FSILearnerMappingConfig(
        max_lesson_for_scoring=20,
        lesson_weight=0.75,
        occurrence_weight=0.25,
        high_frequency_threshold=0.8,
        medium_frequency_threshold=0.45,
    )

    early_score = score_fsi_mapping(
        lesson_number=1,
        occurrence_count=5,
        config=config,
    )
    later_score = score_fsi_mapping(
        lesson_number=20,
        occurrence_count=1,
        config=config,
    )

    assert early_score == 1.0
    assert later_score == 0.05
    assert early_score > later_score


@pytest.mark.django_db
def test_fsi_mapping_updates_lemma_learner_metadata_and_first_appearance():
    lemma = Lemma.objects.create(headword="mhoro")

    map_fsi_learner_metadata(
        lemma,
        source_locator="fsi_course.pdf:unit:1:dialogue:1",
        unit="Unit 1",
        lesson_number=1,
        page_reference="p. 3",
        extracted_text="Mhoro.",
        note="Greeting appears in an opening FSI dialogue.",
        occurrence_count=4,
    )

    lemma.refresh_from_db()
    assert lemma.learner_level == Lemma.LearnerLevel.BEGINNER
    assert lemma.curriculum_stage == Lemma.CurriculumStage.GENERAL_SECONDARY
    assert lemma.curriculum_domains == ["vocabulary", "oral_communication"]
    assert lemma.learning_functions == ["vocabulary", "dialogue_practice"]
    assert lemma.communication_contexts == ["conversation"]
    assert lemma.register_tags == ["school_appropriate"]
    assert lemma.first_appearance_source_key == "source_fsi"
    assert lemma.first_appearance_locator == "fsi_course.pdf:unit:1:dialogue:1"
    assert lemma.first_appearance_unit == "Unit 1"
    assert lemma.first_appearance_lesson == 1
    assert lemma.first_appearance_page == "p. 3"
    assert lemma.frequency_tier == Lemma.FrequencyTier.HIGH
    assert lemma.frequency_score > 0.8
    assert lemma.learner_source_links == [
        {
            "source_key": "source_fsi",
            "source_locator": "fsi_course.pdf:unit:1:dialogue:1",
            "unit": "Unit 1",
            "lesson_number": 1,
            "page_reference": "p. 3",
            "extracted_text": "Mhoro.",
            "note": "Greeting appears in an opening FSI dialogue.",
            "review_status": "reviewed",
            "mapping_method": "fsi_learner_mapping_v1",
        }
    ]


@pytest.mark.django_db
def test_fsi_mapping_keeps_earliest_appearance_and_appends_source_links():
    lemma = Lemma.objects.create(
        headword="ndinoda",
        first_appearance_source_key="source_fsi",
        first_appearance_locator="fsi_course.pdf:unit:2:dialogue:1",
        first_appearance_unit="Unit 2",
        first_appearance_lesson=2,
        first_appearance_page="p. 8",
        learner_source_links=[
            {
                "source_key": "source_fsi",
                "source_locator": "fsi_course.pdf:unit:2:dialogue:1",
                "review_status": "reviewed",
            }
        ],
    )

    map_fsi_learner_metadata(
        lemma,
        source_locator="fsi_course.pdf:unit:5:dialogue:2",
        unit="Unit 5",
        lesson_number=5,
        occurrence_count=1,
    )

    lemma.refresh_from_db()
    assert lemma.first_appearance_locator == "fsi_course.pdf:unit:2:dialogue:1"
    assert lemma.first_appearance_lesson == 2
    assert len(lemma.learner_source_links) == 2
