import pytest
from django.core.cache import caches

from shona_api.api_auth.models import APIKey
from shona_api.editorial.models import ReviewState
from shona_api.figurative_language.models import FigurativeExpression
from shona_api.lexicon.models import Lemma
from shona_api.releases.models import DataRelease


@pytest.fixture(autouse=True)
def madimikira_api_settings(settings):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "madimikira-api-tests",
        }
    }
    caches["default"].clear()


@pytest.fixture
def current_release():
    return DataRelease.objects.create(
        version="2026.05.0",
        label="May 2026 release",
        rule_set_version="figurative-language-v1",
        is_current=True,
    )


@pytest.fixture
def api_key():
    _, raw_key = APIKey.objects.create_key(
        name="Madimikira client",
        plan=APIKey.Plan.DEVELOPER,
        rate_limit_per_minute=20,
    )
    return raw_key


@pytest.fixture
def madimikira_record(current_release):
    lemma = Lemma.objects.create(
        headword="ruoko",
        headword_kind=Lemma.HeadwordKind.NOUN,
        part_of_speech_code="n",
        part_of_speech_label="noun",
        review_state=ReviewState.APPROVED,
    )
    expression = FigurativeExpression.objects.create(
        expression_text="kupa ruoko",
        subtype=FigurativeExpression.Subtype.MADIMIKIRA,
        subtype_readiness=FigurativeExpression.SubtypeReadiness.ACTIVE,
        idiomatic_meaning="To help or assist someone.",
        english_rendering="Give a hand.",
        usage_note="Use for practical help, not only literal hand movement.",
        cultural_themes=["helpfulness", "community"],
        source_notes=[
            {"source_key": "source_shona_yedu", "role": "candidate_enrichment"}
        ],
        provenance={
            "source_keys": ["source_shona_yedu"],
            "review_note": "Reviewed starter idiom fixture.",
        },
        review_state=ReviewState.APPROVED,
    )
    expression.linked_lemmas.add(lemma)
    return expression, lemma


@pytest.mark.django_db
def test_madimikira_list_endpoint_returns_public_active_idioms(
    client, api_key, current_release, madimikira_record
):
    expression, lemma = madimikira_record
    FigurativeExpression.objects.create(
        expression_text="Draft idiom",
        subtype=FigurativeExpression.Subtype.MADIMIKIRA,
        subtype_readiness=FigurativeExpression.SubtypeReadiness.ACTIVE,
        review_state=ReviewState.DRAFT,
    )
    FigurativeExpression.objects.create(
        expression_text="Reserved nickname",
        subtype=FigurativeExpression.Subtype.MADUNHURIRWA,
        subtype_readiness=FigurativeExpression.SubtypeReadiness.RESERVED,
        review_state=ReviewState.APPROVED,
    )

    response = client.get(
        "/v1/figurative-expressions/madimikira",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["api_version"] == "v1"
    assert body["data_release"] == current_release.version
    assert body["rule_set_version"] == current_release.rule_set_version
    assert body["data"]["subtype"] == FigurativeExpression.Subtype.MADIMIKIRA
    assert body["data"]["count"] == 1
    result = body["data"]["results"][0]
    assert result["public_id"] == expression.public_id
    assert result["text"] == "kupa ruoko"
    assert result["meaning"] == "To help or assist someone."
    assert result["english_rendering"] == "Give a hand."
    assert result["cultural_themes"] == ["helpfulness", "community"]
    assert result["linked_lemmas"][0]["public_id"] == lemma.public_id
    assert result["source_notes"] == [
        {"source_key": "source_shona_yedu", "role": "candidate_enrichment"}
    ]
    assert result["provenance"] == {
        "source_keys": ["source_shona_yedu"],
        "review_note": "Reviewed starter idiom fixture.",
    }
    assert result["review_status"] == ReviewState.APPROVED


@pytest.mark.django_db
def test_madimikira_detail_endpoint_returns_one_idiom(
    client, api_key, current_release, madimikira_record
):
    expression, _ = madimikira_record

    response = client.get(
        f"/v1/figurative-expressions/madimikira/{expression.public_id}",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["public_id"] == expression.public_id
    assert body["data"]["subtype"] == FigurativeExpression.Subtype.MADIMIKIRA
    assert body["data"]["subtype_readiness"] == (
        FigurativeExpression.SubtypeReadiness.ACTIVE
    )
    assert body["data"]["review_status"] == ReviewState.APPROVED


@pytest.mark.django_db
def test_madimikira_detail_endpoint_hides_other_subtypes(
    client, api_key, current_release
):
    tsumo = FigurativeExpression.objects.create(
        expression_text="Kandiro kanoenda kunobva kamwe.",
        subtype=FigurativeExpression.Subtype.TSUMO,
        subtype_readiness=FigurativeExpression.SubtypeReadiness.ACTIVE,
        review_state=ReviewState.APPROVED,
    )

    response = client.get(
        f"/v1/figurative-expressions/madimikira/{tsumo.public_id}",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert response.status_code == 404
    assert response.json() == {
        "api_version": "v1",
        "error": {
            "code": "MADIMIKIRA_NOT_FOUND",
            "message": f"No madimikira found for public_id '{tsumo.public_id}'",
            "detail": None,
        },
    }


@pytest.mark.django_db
def test_tsumo_endpoint_stays_scoped_after_madimikira_expansion(
    client, api_key, current_release, madimikira_record
):
    response = client.get(
        "/v1/figurative-expressions/tsumo",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["subtype"] == FigurativeExpression.Subtype.TSUMO
    assert body["data"]["count"] == 0
    assert body["data"]["results"] == []
