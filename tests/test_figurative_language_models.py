import pytest
from django.contrib import admin

from shona_api.editorial.models import ReviewState
from shona_api.figurative_language.admin import FigurativeExpressionAdmin
from shona_api.figurative_language.models import FigurativeExpression
from shona_api.lexicon.models import Lemma


@pytest.mark.django_db
def test_figurative_expression_foundation_supports_shared_metadata_and_lemmas():
    lemma = Lemma.objects.create(
        headword="moto",
        headword_kind=Lemma.HeadwordKind.NOUN,
        part_of_speech_code="n",
    )
    expression = FigurativeExpression.objects.create(
        expression_text="Kandiro kanoenda kunobva kamwe.",
        subtype=FigurativeExpression.Subtype.TSUMO,
        subtype_readiness=FigurativeExpression.SubtypeReadiness.ACTIVE,
        idiomatic_meaning="Reciprocity sustains relationships.",
        english_rendering="One good turn deserves another.",
        usage_note="Use for mutual help or reciprocal obligation.",
        cultural_themes=["reciprocity", "community"],
        pedagogy_notes=[{"level": "secondary", "topic": "tsumo"}],
        source_notes=[
            {"source_key": "source_tsumo_tsika", "role": "theme_enrichment"}
        ],
        provenance={
            "source_keys": ["source_tsumo_tsika"],
            "review_note": "Starter canonical proverb shape.",
        },
        review_state=ReviewState.APPROVED,
    )
    expression.linked_lemmas.add(lemma)

    assert expression.public_id.startswith("figexpr_")
    assert expression.normalized_expression == "kandiro kanoenda kunobva kamwe."
    assert expression.subtype == FigurativeExpression.Subtype.TSUMO
    assert expression.cultural_themes == ["reciprocity", "community"]
    assert expression.pedagogy_notes[0]["topic"] == "tsumo"
    assert expression.provenance["source_keys"] == ["source_tsumo_tsika"]
    assert list(expression.linked_lemmas.all()) == [lemma]
    assert list(lemma.figurative_expressions.all()) == [expression]


def test_figurative_expression_subtypes_include_active_and_reserved_lanes():
    subtype_values = {choice.value for choice in FigurativeExpression.Subtype}

    assert {
        "tsumo",
        "madimikira",
        "madunhurirwa",
        "nyaudzosingwi",
        "fananidzo",
        "enzaniso",
        "chibhende",
    }.issubset(subtype_values)
    assert FigurativeExpression.SubtypeReadiness.ACTIVE == "active"
    assert FigurativeExpression.SubtypeReadiness.RESERVED == "reserved"


def test_figurative_expression_admin_exposes_review_and_linked_lemma_controls():
    expression_admin = FigurativeExpressionAdmin(FigurativeExpression, admin.site)

    assert expression_admin.list_display == (
        "expression_text",
        "subtype",
        "subtype_readiness",
        "review_state",
        "updated_at",
    )
    assert expression_admin.filter_horizontal == ("linked_lemmas",)
