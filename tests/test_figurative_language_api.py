import pytest
from django.core.cache import caches
from django.core.management import call_command
from django.core.management.base import CommandError

from shona_api.api_auth.models import APIKey
from shona_api.editorial.models import ReviewState
from shona_api.figurative_language.models import FigurativeExpression
from shona_api.lexicon.models import Lemma
from shona_api.releases.models import DataRelease


@pytest.fixture(autouse=True)
def figurative_language_api_settings(settings):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "figurative-language-api-tests",
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
        name="Figurative language client",
        plan=APIKey.Plan.DEVELOPER,
        rate_limit_per_minute=20,
    )
    return raw_key


@pytest.fixture
def tsumo_record(current_release):
    lemma = Lemma.objects.create(
        headword="moto",
        headword_kind=Lemma.HeadwordKind.NOUN,
        part_of_speech_code="n",
        part_of_speech_label="noun",
        review_state=ReviewState.APPROVED,
    )
    expression = FigurativeExpression.objects.create(
        expression_text="Kandiro kanoenda kunobva kamwe.",
        subtype=FigurativeExpression.Subtype.TSUMO,
        subtype_readiness=FigurativeExpression.SubtypeReadiness.ACTIVE,
        idiomatic_meaning="Reciprocity sustains relationships.",
        english_rendering="One good turn deserves another.",
        usage_note="Use for mutual help or reciprocal obligation.",
        cultural_themes=["reciprocity", "community"],
        source_notes=[
            {"source_key": "source_tsumo_tsika", "role": "theme_enrichment"}
        ],
        provenance={
            "source_keys": ["source_tsumo_tsika"],
            "review_note": "Reviewed starter proverb fixture.",
        },
        review_state=ReviewState.APPROVED,
    )
    expression.linked_lemmas.add(lemma)
    return expression, lemma


@pytest.mark.django_db
def test_tsumo_list_endpoint_returns_public_active_proverbs(
    client, api_key, current_release, tsumo_record
):
    expression, lemma = tsumo_record
    FigurativeExpression.objects.create(
        expression_text="Draft proverb",
        subtype=FigurativeExpression.Subtype.TSUMO,
        subtype_readiness=FigurativeExpression.SubtypeReadiness.ACTIVE,
        review_state=ReviewState.DRAFT,
    )
    FigurativeExpression.objects.create(
        expression_text="Reserved idiom",
        subtype=FigurativeExpression.Subtype.MADIMIKIRA,
        subtype_readiness=FigurativeExpression.SubtypeReadiness.RESERVED,
        review_state=ReviewState.APPROVED,
    )

    response = client.get(
        "/v1/figurative-expressions/tsumo",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["api_version"] == "v1"
    assert body["data_release"] == current_release.version
    assert body["rule_set_version"] == current_release.rule_set_version
    assert body["data"]["subtype"] == FigurativeExpression.Subtype.TSUMO
    assert body["data"]["count"] == 1
    result = body["data"]["results"][0]
    assert result["public_id"] == expression.public_id
    assert result["text"] == "Kandiro kanoenda kunobva kamwe."
    assert result["meaning"] == "Reciprocity sustains relationships."
    assert result["english_rendering"] == "One good turn deserves another."
    assert result["cultural_themes"] == ["reciprocity", "community"]
    assert result["linked_lemmas"][0]["public_id"] == lemma.public_id
    assert result["provenance"] == {
        "source_keys": ["source_tsumo_tsika"],
        "review_note": "Reviewed starter proverb fixture.",
    }
    assert result["review_status"] == ReviewState.APPROVED


@pytest.mark.django_db
def test_tsumo_detail_endpoint_returns_one_proverb(
    client, api_key, current_release, tsumo_record
):
    expression, _ = tsumo_record

    response = client.get(
        f"/v1/figurative-expressions/tsumo/{expression.public_id}",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["public_id"] == expression.public_id
    assert body["data"]["subtype"] == FigurativeExpression.Subtype.TSUMO
    assert body["data"]["subtype_readiness"] == (
        FigurativeExpression.SubtypeReadiness.ACTIVE
    )
    assert body["data"]["review_status"] == ReviewState.APPROVED


@pytest.mark.django_db
def test_tsumo_detail_endpoint_hides_non_public_records(
    client, api_key, current_release
):
    draft = FigurativeExpression.objects.create(
        expression_text="Draft proverb",
        subtype=FigurativeExpression.Subtype.TSUMO,
        subtype_readiness=FigurativeExpression.SubtypeReadiness.ACTIVE,
        review_state=ReviewState.DRAFT,
    )

    response = client.get(
        f"/v1/figurative-expressions/tsumo/{draft.public_id}",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert response.status_code == 404
    assert response.json() == {
        "api_version": "v1",
        "error": {
            "code": "TSUMO_NOT_FOUND",
            "message": f"No tsumo found for public_id '{draft.public_id}'",
            "detail": None,
        },
    }


@pytest.mark.django_db
def test_tsumo_endpoints_use_existing_api_key_auth(client, current_release):
    response = client.get("/v1/figurative-expressions/tsumo")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication credentials were not provided."


@pytest.mark.django_db
def test_seed_figurative_expressions_command_exposes_reviewed_public_records(
    client, api_key, current_release
):
    linked_lemma = Lemma.objects.create(
        headword="ruoko",
        headword_kind=Lemma.HeadwordKind.NOUN,
        part_of_speech_code="n",
        part_of_speech_label="noun",
        review_state=ReviewState.APPROVED,
    )

    call_command("seed_figurative_expressions")

    tsumo_response = client.get(
        "/v1/figurative-expressions/tsumo",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    madimikira_response = client.get(
        "/v1/figurative-expressions/madimikira",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )

    assert tsumo_response.status_code == 200
    tsumo_body = tsumo_response.json()
    assert tsumo_body["data"]["count"] == 1
    tsumo = tsumo_body["data"]["results"][0]
    assert tsumo["text"] == "Kandiro kanoenda kunobva kamwe."
    assert tsumo["subtype"] == FigurativeExpression.Subtype.TSUMO
    assert tsumo["subtype_readiness"] == FigurativeExpression.SubtypeReadiness.ACTIVE
    assert tsumo["review_status"] == ReviewState.APPROVED
    assert tsumo["source_notes"] == [
        {
            "source_key": "source_tsumo_tsika",
            "role": "reviewed_theme_enrichment",
            "locator": "local_review:fig-seed-001",
        }
    ]
    assert tsumo["provenance"] == {
        "source_keys": ["source_tsumo_tsika"],
        "review_note": "Reviewed starter proverb seed for FIG-SEED-001.",
        "confidence": "reviewed",
    }

    assert madimikira_response.status_code == 200
    madimikira_body = madimikira_response.json()
    assert madimikira_body["data"]["count"] == 1
    madimikira = madimikira_body["data"]["results"][0]
    assert madimikira["text"] == "kupa ruoko"
    assert madimikira["subtype"] == FigurativeExpression.Subtype.MADIMIKIRA
    assert madimikira["linked_lemmas"][0]["public_id"] == linked_lemma.public_id
    assert madimikira["source_notes"] == [
        {
            "source_key": "source_shona_yedu",
            "role": "reviewed_candidate",
            "locator": "local_review:fig-seed-001",
        }
    ]


@pytest.mark.django_db
def test_seed_figurative_expressions_command_is_idempotent():
    call_command("seed_figurative_expressions")
    call_command("seed_figurative_expressions")

    assert FigurativeExpression.objects.count() == 2


@pytest.mark.django_db
def test_seed_figurative_expressions_missing_fixture_raises_error():
    with pytest.raises(CommandError) as exc_info:
        call_command(
            "seed_figurative_expressions",
            fixture="missing_figurative_fixture.json",
        )

    assert "Fixture file not found at:" in str(exc_info.value)
