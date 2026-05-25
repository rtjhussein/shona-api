import pytest
from django.core.management import call_command
from django.core.cache import caches
from rest_framework.test import APIClient

from shona_api.api_auth.models import APIKey
from shona_api.editorial.models import ReviewState
from shona_api.lexicon.models import Form, Lemma, Sense
from shona_api.releases.models import DataRelease

@pytest.fixture(autouse=True)
def pedagogy_api_settings(settings):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "pedagogy-api-tests",
        }
    }
    caches["default"].clear()

@pytest.fixture
def current_release():
    return DataRelease.objects.create(
        version="2026.05.0",
        label="May 2026 release",
        rule_set_version="fortune.verbal.slots.001",
        is_current=True,
    )

@pytest.fixture
def api_key():
    _, raw_key = APIKey.objects.create_key(
        name="Pedagogy client",
        plan=APIKey.Plan.DEVELOPER,
        rate_limit_per_minute=20,
    )
    return raw_key

@pytest.fixture
def canonical_lemmas(current_release):
    provenance = {"source_key": "source_hannan", "entry_locator": "fixture:pedagogy"}
    
    # 1. 'mhoro' (greeting)
    l1 = Lemma.objects.create(
        headword="mhoro",
        headword_kind=Lemma.HeadwordKind.WORD,
        part_of_speech_code="interj",
        dialects=["Z"],
        review_state=ReviewState.PUBLISHED,
        provenance=provenance,
    )
    Sense.objects.create(
        lemma=l1,
        number=1,
        definition="Greeting, hello.",
        review_state=ReviewState.PUBLISHED,
        provenance=provenance,
    )

    # 2. 'baba' (family)
    l2 = Lemma.objects.create(
        headword="baba",
        headword_kind=Lemma.HeadwordKind.NOUN,
        part_of_speech_code="n",
        dialects=["Z"],
        review_state=ReviewState.PUBLISHED,
        provenance=provenance,
    )
    Sense.objects.create(
        lemma=l2,
        number=1,
        definition="Father, paternal uncle.",
        review_state=ReviewState.PUBLISHED,
        provenance=provenance,
    )

    # 3. 'sango' (environment)
    l3 = Lemma.objects.create(
        headword="sango",
        headword_kind=Lemma.HeadwordKind.NOUN,
        part_of_speech_code="n",
        dialects=["Z"],
        review_state=ReviewState.PUBLISHED,
        provenance=provenance,
    )
    Sense.objects.create(
        lemma=l3,
        number=1,
        definition="Forest, veld, wilderness.",
        review_state=ReviewState.PUBLISHED,
        provenance=provenance,
    )

    return l1, l2, l3


@pytest.mark.django_db
def test_tag_curriculum_syllabus_rule_based(canonical_lemmas):
    l1, l2, l3 = canonical_lemmas
    
    # Run the rule-based curriculum tagging command
    call_command("tag_curriculum_syllabus")
    
    # Refresh and assert updates
    l1.refresh_from_db()
    l2.refresh_from_db()
    l3.refresh_from_db()
    
    assert l1.curriculum_stage == Lemma.CurriculumStage.FORMS_1_2
    assert "greetings" in l1.communication_contexts
    assert "vocabulary" in l1.curriculum_domains
    assert "school_appropriate" in l1.register_tags
    
    assert l2.curriculum_stage == Lemma.CurriculumStage.FORMS_1_2
    assert "family" in l2.communication_contexts
    
    assert l3.curriculum_stage == Lemma.CurriculumStage.GENERAL_SECONDARY
    assert "environment" in l3.communication_contexts


@pytest.mark.django_db
def test_lemma_list_view_filters_and_random_shuffling(client, api_key, current_release, canonical_lemmas):
    l1, l2, l3 = canonical_lemmas
    
    # Run the rule-based curriculum tagging command to populate data
    call_command("tag_curriculum_syllabus")
    
    # Query lemmas listing with greetings context
    response = client.get(
        "/v1/lemmas/",
        {"communication_context": "greetings"},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["count"] == 1
    assert body["data"]["results"][0]["public_id"] == l1.public_id
    
    # Query with family context
    response = client.get(
        "/v1/lemmas/",
        {"communication_context": "family"},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["count"] == 1
    assert body["data"]["results"][0]["public_id"] == l2.public_id

    # Query with stage filter
    response = client.get(
        "/v1/lemmas/",
        {"curriculum_stage": "forms_1_2"},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["count"] == 2
    
    # Query with invalid list filter
    response = client.get(
        "/v1/lemmas/",
        {"learner_level": "bad_level"},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "LEMMA_LIST_FILTER_INVALID"

    # Query with random ordering
    response = client.get(
        "/v1/lemmas/",
        {"random": "true"},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    assert len(response.json()["data"]["results"]) == 3


@pytest.mark.django_db
def test_search_view_pedagogical_filters(client, api_key, current_release, canonical_lemmas):
    l1, l2, l3 = canonical_lemmas
    call_command("tag_curriculum_syllabus")
    
    # Search with q and pedagogy filter
    response = client.get(
        "/v1/search",
        {"q": "baba", "curriculum_stage": "forms_1_2"},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["count"] == 1
    assert body["data"]["results"][0]["lemma"]["public_id"] == l2.public_id

    # Search with q and incompatible pedagogy filter (should return 0 results)
    response = client.get(
        "/v1/search",
        {"q": "baba", "curriculum_stage": "forms_3_4"},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    assert response.json()["data"]["count"] == 0

    # Search with random shuffle
    response = client.get(
        "/v1/search",
        {"q": "baba", "random": "true"},
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    assert response.json()["data"]["count"] == 1


@pytest.mark.django_db
def test_post_publish_signal_triggers_on_lemma_publish(current_release):
    provenance = {"source_key": "source_hannan", "entry_locator": "fixture:signal_test"}
    # Create as draft
    lemma = Lemma.objects.create(
        headword="mhoro",
        headword_kind=Lemma.HeadwordKind.WORD,
        part_of_speech_code="interj",
        review_state=ReviewState.DRAFT,
        provenance=provenance,
    )
    Sense.objects.create(
        lemma=lemma,
        number=1,
        definition="Greeting, hello.",
        review_state=ReviewState.DRAFT,
        provenance=provenance,
    )
    
    # Assert initially unmapped
    assert lemma.curriculum_stage == Lemma.CurriculumStage.UNKNOWN
    assert not lemma.communication_contexts

    # Publish the lemma
    lemma.review_state = ReviewState.PUBLISHED
    lemma.save()
    
    # Assert signal triggered rule-based matching
    lemma.refresh_from_db()
    assert lemma.curriculum_stage == Lemma.CurriculumStage.FORMS_1_2
    assert "greetings" in lemma.communication_contexts
    assert any("Post-Publish Signal" in link.get("note", "") for link in lemma.learner_source_links)
