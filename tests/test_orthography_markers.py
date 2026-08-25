import pytest

from shona_api.editorial.models import ReviewState
from shona_api.lexicon.models import Lemma
from shona_api.lexicon.search import (
    normalize_search_query,
    search_public_records,
)
from shona_api.phonology.orthography import strip_annotation_markers
from shona_api.releases.models import DataRelease


@pytest.fixture
def current_release():
    return DataRelease.objects.create(
        version="2026.05.0",
        label="May 2026 release",
        rule_set_version="morphology-rules-v1",
        is_current=True,
    )


@pytest.mark.django_db
def test_lemma_save_strips_annotation_markers():
    lemma = Lemma.objects.create(
        headword="†-kura",
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        part_of_speech_code="v t",
        part_of_speech_label="v t",
        review_state=ReviewState.PUBLISHED,
    )

    assert lemma.normalized_headword == "kura"
    assert lemma.headword == "†-kura"


@pytest.mark.django_db
def test_lemma_save_strips_asterisk_marker():
    lemma = Lemma.objects.create(
        headword="*-tubwaira",
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        part_of_speech_code="v t",
        part_of_speech_label="v t",
        review_state=ReviewState.PUBLISHED,
    )

    assert lemma.normalized_headword == "tubwaira"


def test_strip_annotation_markers_variants():
    assert strip_annotation_markers("†-kura") == "kura"
    assert strip_annotation_markers("*tubwa tubwa") == "tubwa tubwa"
    assert strip_annotation_markers("-buda") == "buda"
    assert strip_annotation_markers("shumba") == "shumba"
    # mid-word hyphens are meaningful and must survive
    assert strip_annotation_markers("kwaMutare") == "kwaMutare"


def test_normalize_search_query_strips_markers():
    assert normalize_search_query("†-kura") == "kura"
    assert normalize_search_query("*-tubwaira") == "tubwaira"
    assert normalize_search_query("-Buda") == "buda"


@pytest.mark.django_db
def test_marker_lemma_is_searchable_by_clean_headword(current_release):
    Lemma.objects.create(
        headword="†-kura",
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        part_of_speech_code="v t",
        part_of_speech_label="v t",
        review_state=ReviewState.PUBLISHED,
    )

    results = search_public_records(normalize_search_query("†-kura"))
    assert any(result["lemma"].normalized_headword == "kura" for result in results)
