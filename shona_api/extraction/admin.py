from django.contrib import admin

from shona_api.editorial.models import ReviewState

from .models import ExtractionUnit, IngestionRun


@admin.register(ExtractionUnit)
class ExtractionUnitAdmin(admin.ModelAdmin):
    list_display = (
        "display_headword",
        "source_location_reference",
        "batch_id",
        "parser_name",
        "parser_status",
        "review_state",
        "publication_state",
        "confidence",
        "created_at",
    )
    list_display_links = ("display_headword",)
    list_filter = (
        "review_state",
        "parser_status",
        "source",
        "parser_name",
        "batch_id",
        "created_at",
    )
    search_fields = (
        "parser_output__headword",
        "source__source_key",
        "source_location_reference",
        "batch_id",
        "raw_text",
        "parser_output",
    )
    readonly_fields = ("created_at", "updated_at")
    ordering = ("review_state", "-created_at")

    @admin.display(description="Word", ordering="source_location_reference")
    def display_headword(self, obj):
        parser_output = obj.parser_output or {}
        headword = parser_output.get("headword")
        if headword:
            return headword
        raw_text = (obj.raw_text or "").strip()
        if raw_text:
            return raw_text.split(maxsplit=1)[0]
        return obj.source_location_reference

    @admin.display(description="Publication")
    def publication_state(self, obj):
        if obj.canonical_record_object_id:
            return "published link"
        if obj.review_state == ReviewState.PUBLISHED:
            return "published"
        return "not published"


@admin.register(IngestionRun)
class IngestionRunAdmin(admin.ModelAdmin):
    list_display = (
        "batch_id",
        "status",
        "page_label",
        "auto_publish",
        "dry_run",
        "imported_count",
        "published_count",
        "created_at",
    )
    list_filter = ("status", "auto_publish", "dry_run", "created_at")
    search_fields = ("batch_id", "log_text", "error_message")
    readonly_fields = (
        "created_at",
        "started_at",
        "finished_at",
        "log_text",
        "error_message",
    )
    ordering = ("-created_at",)
