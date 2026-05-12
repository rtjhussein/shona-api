from rest_framework import serializers

from shona_api.lexicon.serializers import LemmaCoreSerializer

from .models import FigurativeExpression


class FigurativeExpressionSerializer(serializers.ModelSerializer):
    text = serializers.CharField(source="expression_text")
    normalized_text = serializers.CharField(source="normalized_expression")
    meaning = serializers.CharField(source="idiomatic_meaning")
    review_status = serializers.CharField(source="review_state")
    linked_lemmas = LemmaCoreSerializer(many=True, read_only=True)

    class Meta:
        model = FigurativeExpression
        fields = (
            "public_id",
            "subtype",
            "subtype_readiness",
            "text",
            "normalized_text",
            "meaning",
            "english_rendering",
            "usage_note",
            "cultural_themes",
            "linked_lemmas",
            "source_notes",
            "provenance",
            "phonology_inventory_version",
            "graphemes",
            "grapheme_count",
            "syllables",
            "syllable_count",
            "revision",
            "review_status",
        )
