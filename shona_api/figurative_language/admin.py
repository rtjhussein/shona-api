from django.contrib import admin

from .models import FigurativeExpression


@admin.register(FigurativeExpression)
class FigurativeExpressionAdmin(admin.ModelAdmin):
    list_display = (
        "expression_text",
        "subtype",
        "subtype_readiness",
        "review_state",
        "updated_at",
    )
    list_filter = ("subtype", "subtype_readiness", "review_state")
    search_fields = (
        "expression_text",
        "normalized_expression",
        "idiomatic_meaning",
        "english_rendering",
        "public_id",
    )
    filter_horizontal = ("linked_lemmas",)
    readonly_fields = (
        "id",
        "public_id",
        "normalized_expression",
        "phonology_inventory_version",
        "graphemes",
        "grapheme_count",
        "syllables",
        "syllable_count",
        "created_at",
        "updated_at",
    )
