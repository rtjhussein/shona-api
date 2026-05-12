from django.contrib import admin

from .models import ExtractionUnit


@admin.register(ExtractionUnit)
class ExtractionUnitAdmin(admin.ModelAdmin):
    list_display = (
        "source",
        "source_location_reference",
        "parser_name",
        "parser_status",
        "review_state",
        "confidence",
        "created_at",
    )
    list_filter = (
        "review_state",
        "parser_status",
        "source",
        "parser_name",
        "created_at",
    )
    search_fields = (
        "source__source_key",
        "source_location_reference",
        "raw_text",
        "parser_output",
    )
    readonly_fields = ("created_at", "updated_at")
    ordering = ("review_state", "-created_at")
