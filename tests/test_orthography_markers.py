import pytest

from shona_api.editorial.models import ReviewState
from shona_api.lexicon.models import Form, Lemma, Sense
from shona_api.lexicon.search import (
    normalize_search_query,
    search_public_records,
)
from shona_api.phonology.orthography import normalize_orthography, strip_annotation_markers
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

def test_normalize_orthography_casefolds_and_collapses():
    assert normalize_orthography("Agasiti") == "agasiti"
    assert normalize_orthography("Bhaibheri") == "bhaibheri"
    assert normalize_orthography("†Bhaibheri") == "bhaibheri"
    assert normalize_orthography("  Agasiti  ") == "agasiti"
    assert normalize_orthography("mowa  danga") == "mowa danga"
    assert normalize_orthography("kwaMutare") == "kwamutare"
    # dagger + hyphen + capital is the published-corpus failure mode
    assert normalize_orthography("†-Buda") == "buda"


@pytest.mark.django_db
def test_lemma_save_casefolds_capitalized_headword():
    lemma = Lemma.objects.create(
        headword="Bhaibheri",
        headword_kind=Lemma.HeadwordKind.WORD,
        part_of_speech_code="n",
        part_of_speech_label="n",
        review_state=ReviewState.PUBLISHED,
    )
    assert lemma.normalized_headword == "bhaibheri"
    assert lemma.headword == "Bhaibheri"


@pytest.mark.django_db
def test_lemma_save_casefolds_with_annotation_marker():
    lemma = Lemma.objects.create(
        headword="†Bhaibheri",
        headword_kind=Lemma.HeadwordKind.WORD,
        part_of_speech_code="n",
        part_of_speech_label="n",
        review_state=ReviewState.PUBLISHED,
    )
    assert lemma.normalized_headword == "bhaibheri"


@pytest.mark.django_db
def test_form_save_casefolds_normalized_form():
    lemma = Lemma.objects.create(
        headword="buda",
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        part_of_speech_code="vi",
        part_of_speech_label="vi",
        review_state=ReviewState.PUBLISHED,
    )
    sense = Sense.objects.create(
        lemma=lemma,
        number=1,
        definition="Come out.",
        review_state=ReviewState.PUBLISHED,
    )
    form = Form.objects.create(
        lemma=lemma,
        sense=sense,
        form_text="Bude",
        form_kind=Form.FormKind.DERIVED,
        review_state=ReviewState.PUBLISHED,
    )
    assert form.normalized_form == "bude"


@pytest.mark.django_db
def test_search_is_case_insensitive_for_capitalized_headword(current_release):
    lemma = Lemma.objects.create(
        headword="Bhaibheri",
        headword_kind=Lemma.HeadwordKind.WORD,
        part_of_speech_code="n",
        part_of_speech_label="n",
        review_state=ReviewState.PUBLISHED,
    )
    # query lowercases — exact lemma match must be case-insensitive
    results = search_public_records(normalize_search_query("bhaibheri"))
    assert any(r["lemma"].public_id == lemma.public_id for r in results)
    # query with original capital must also match (search normalizes too)
    results_cap = search_public_records(normalize_search_query("Bhaibheri"))
    assert any(r["lemma"].public_id == lemma.public_id for r in results_cap)
    # mixed dagger + capital
    results_dagger = search_public_records(normalize_search_query("†Bhaibheri"))
    assert any(r["lemma"].public_id == lemma.public_id for r in results_dagger)


@pytest.mark.django_db
def test_capitalized_forms_are_searchable_via_exact_form(current_release):
    lemma = Lemma.objects.create(
        headword="buda",
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        part_of_speech_code="vi",
        part_of_speech_label="vi",
        review_state=ReviewState.PUBLISHED,
    )
    sense = Sense.objects.create(
        lemma=lemma,
        number=1,
        definition="Come out.",
        review_state=ReviewState.PUBLISHED,
    )
    form = Form.objects.create(
        lemma=lemma,
        sense=sense,
        form_text="Bude",
        form_kind=Form.FormKind.DERIVED,
        review_state=ReviewState.PUBLISHED,
    )
    results = search_public_records(normalize_search_query("bude"))
    assert any(r["form"] and r["form"].public_id == form.public_id for r in results)
