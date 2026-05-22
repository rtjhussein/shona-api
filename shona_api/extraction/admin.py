from django import forms
from django.contrib import admin, messages

from shona_api.editorial.models import ReviewState

from .models import ExtractionUnit, IngestionRun
from .services import ExtractionUnitPublishError, publish_reviewed_extraction_unit


class ExtractionUnitAdminForm(forms.ModelForm):
    class Meta:
        model = ExtractionUnit
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        review_state = cleaned_data.get("review_state")
        canonical_record_object_id = cleaned_data.get("canonical_record_object_id")
        if review_state == ReviewState.PUBLISHED and not canonical_record_object_id:
            raise forms.ValidationError(
                "Use the publish action to create a dictionary record. "
                "Extraction units cannot be manually marked published without a "
                "canonical record link."
            )
        return cleaned_data


@admin.register(ExtractionUnit)
class ExtractionUnitAdmin(admin.ModelAdmin):
    form = ExtractionUnitAdminForm
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
    actions = ("publish_selected_units",)

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
            return "Published to dictionary"
        if obj.review_state == ReviewState.APPROVED:
            return "Needs publication"
        if obj.review_state == ReviewState.PUBLISHED:
            return "Invalid published state"
        return "Not published"

    @admin.action(description="Publish selected units to dictionary")
    def publish_selected_units(self, request, queryset):
        published = 0
        skipped = 0
        failed = 0

        for unit in queryset.order_by("source_location_reference", "pk"):
            if unit.canonical_record_object_id:
                skipped += 1
                continue
            if unit.review_state == ReviewState.PUBLISHED:
                unit.review_state = ReviewState.APPROVED
                unit.save(update_fields=("review_state", "updated_at"))
            elif unit.review_state != ReviewState.APPROVED:
                skipped += 1
                continue

            try:
                publish_reviewed_extraction_unit(unit, decided_by=request.user)
            except ExtractionUnitPublishError as exc:
                failed += 1
                self.message_user(
                    request,
                    f"Could not publish {unit.source_location_reference}: {exc}",
                    level=messages.WARNING,
                )
                continue
            published += 1

        self.message_user(
            request,
            (
                f"Published {published} extraction unit(s); "
                f"skipped {skipped}; failed {failed}."
            ),
            level=messages.SUCCESS if failed == 0 else messages.WARNING,
        )


@admin.register(IngestionRun)
class IngestionRunAdmin(admin.ModelAdmin):
    list_display = (
        "batch_id",
        "run_kind",
        "status",
        "page_label",
        "import_parser_name",
        "auto_approve",
        "auto_publish",
        "dry_run",
        "imported_count",
        "duplicate_count",
        "published_count",
        "created_at",
    )
    list_filter = (
        "run_kind",
        "status",
        "auto_approve",
        "auto_publish",
        "dry_run",
        "created_at",
    )
    search_fields = (
        "batch_id",
        "source_jsonl_path",
        "jsonl_path",
        "import_parser_name",
        "log_text",
        "error_message",
    )
    readonly_fields = (
        "run_kind",
        "batch_id",
        "source_jsonl_path",
        "jsonl_path",
        "import_parser_name",
        "status",
        "imported_count",
        "duplicate_count",
        "publishable_count",
        "published_count",
        "failed_publish_count",
        "created_at",
        "started_at",
        "finished_at",
        "log_text",
        "error_message",
    )
    ordering = ("-created_at",)
