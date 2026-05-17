import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from shona_api.editorial.models import ReviewState
from shona_api.extraction.models import ExtractionUnit
from shona_api.figurative_language.models import FigurativeExpression
from shona_api.lexicon.models import Lemma, Sense
from shona_api.parsers.hannan import parse_hannan_entry
from shona_api.sources.models import Source
from shona_api.web.progress import build_data_progress_snapshot


@pytest.fixture
def hannan_source():
    return Source.objects.create(
        source_key="source_hannan",
        title="Hannan Dictionary",
        authority_level="Backbone lexical authority",
        rights_usage_note="Local-only source material; do not upload source file to git.",
        ingestion_style="Digitized dictionary-entry parsing into structured candidates.",
        current_filename="hannan_dictionary.pdf",
    )


@pytest.mark.django_db
def test_data_progress_dashboard_requires_staff_user():
    response = Client().get(reverse("data-progress"))

    assert response.status_code == 302
    assert "/admin/login/" in response["Location"]


@pytest.mark.django_db
def test_data_progress_dashboard_shows_population_counts(hannan_source):
    user = get_user_model().objects.create_user(
        username="staff",
        password="pass",
        is_staff=True,
    )
    lemma = Lemma.objects.create(
        headword="-buda",
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        part_of_speech_code="vi",
        review_state=ReviewState.PUBLISHED,
    )
    Sense.objects.create(
        lemma=lemma,
        number=1,
        definition="Come out.",
        review_state=ReviewState.PUBLISHED,
    )
    ExtractionUnit.objects.create_from_parser_output(
        source=hannan_source,
        source_location_reference="hannan_dictionary.pdf:p.42:entry:-buda",
        raw_text="-buda [H] vi Come out.",
        parser_output=parse_hannan_entry("-buda [H] vi Come out."),
        confidence=0.95,
        provenance={"batch_id": "HANNAN-PILOT-001"},
    )
    FigurativeExpression.objects.create(
        expression_text="Kandiro kanoenda kunobva kamwe.",
        subtype=FigurativeExpression.Subtype.TSUMO,
        subtype_readiness=FigurativeExpression.SubtypeReadiness.ACTIVE,
        idiomatic_meaning="Reciprocity sustains relationships.",
        review_state=ReviewState.APPROVED,
    )

    client = Client()
    client.force_login(user)
    response = client.get(reverse("data-progress"))

    assert response.status_code == 200
    assert b"Shona API Progress" in response.content
    assert b'data-theme="dark"' in response.content
    assert b"data-progress.js" in response.content
    assert b"data-theme-toggle" in response.content
    assert b"Current batch" in response.content
    assert b"Needs human attention" in response.content
    assert b"1 / 3000" in response.content
    assert b"1 / 150" in response.content
    assert b"source_hannan" in response.content
    assert b"HANNAN-PILOT-001" in response.content
    assert b"Review candidates" in response.content


@pytest.mark.django_db
def test_data_progress_snapshot_exposes_active_batch_pipeline(hannan_source):
    ExtractionUnit.objects.create_from_parser_output(
        source=hannan_source,
        source_location_reference="hannan_dictionary.pdf:p.42:entry:-buda",
        raw_text="-buda [H] vi Come out.",
        parser_output=parse_hannan_entry("-buda [H] vi Come out."),
        confidence=0.95,
        provenance={"batch_id": "HANNAN-PILOT-001"},
    )
    ExtractionUnit.objects.create_from_parser_output(
        source=hannan_source,
        source_location_reference="hannan_dictionary.pdf:p.43:entry:-bata",
        raw_text="-bata [H] vt Hold.",
        parser_output=parse_hannan_entry("-bata [H] vt Hold."),
        confidence=0.95,
        review_state=ReviewState.APPROVED,
        provenance={"batch_id": "HANNAN-PILOT-001"},
    )

    snapshot = build_data_progress_snapshot()

    assert snapshot["batches"]["active"] == "HANNAN-PILOT-001"
    assert snapshot["active_batch"]["total"] == 2
    assert snapshot["active_batch"]["needs_review_count"] == 1
    assert snapshot["active_batch"]["approved_unpublished_count"] == 1
    assert [step["key"] for step in snapshot["active_batch"]["pipeline"]] == [
        "imported",
        "parsed",
        "needs_review",
        "approved",
        "published",
    ]
