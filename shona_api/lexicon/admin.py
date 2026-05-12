from django.contrib import admin

from .models import Form, Lemma, NounClass, Sense, ToneRecord


class SenseInline(admin.TabularInline):
    model = Sense
    extra = 0
    fields = ("number", "definition", "review_state")
    show_change_link = True


class ToneRecordInline(admin.TabularInline):
    model = ToneRecord
    extra = 0
    fields = ("pattern", "notation_system", "form", "review_state")
    show_change_link = True


class FormInline(admin.TabularInline):
    model = Form
    extra = 0
    fields = ("form_text", "form_kind", "sense", "review_state")
    show_change_link = True


@admin.register(NounClass)
class NounClassAdmin(admin.ModelAdmin):
    list_display = (
        "class_number",
        "label",
        "nominal_prefix",
        "subject_concord",
        "default_plural_class",
        "review_state",
        "updated_at",
    )
    list_filter = ("review_state", "default_plural_class")
    search_fields = (
        "class_number",
        "label",
        "nominal_prefix",
        "subject_concord",
        "object_concord",
        "public_id",
    )
    readonly_fields = ("id", "public_id", "created_at", "updated_at")


@admin.register(Lemma)
class LemmaAdmin(admin.ModelAdmin):
    list_display = (
        "headword",
        "headword_kind",
        "noun_class",
        "part_of_speech_code",
        "learner_level",
        "frequency_tier",
        "review_state",
        "updated_at",
    )
    list_filter = (
        "headword_kind",
        "noun_class",
        "part_of_speech_code",
        "learner_level",
        "curriculum_stage",
        "frequency_tier",
        "first_appearance_source_key",
        "review_state",
    )
    search_fields = (
        "headword",
        "normalized_headword",
        "part_of_speech_code",
        "part_of_speech_label",
        "public_id",
    )
    readonly_fields = (
        "id",
        "public_id",
        "normalized_headword",
        "phonology_inventory_version",
        "graphemes",
        "grapheme_count",
        "syllables",
        "syllable_count",
        "created_at",
        "updated_at",
    )
    inlines = (SenseInline, ToneRecordInline, FormInline)


@admin.register(Sense)
class SenseAdmin(admin.ModelAdmin):
    list_display = ("lemma", "number", "review_state", "updated_at")
    list_filter = ("review_state",)
    search_fields = ("lemma__headword", "definition", "public_id")
    readonly_fields = ("id", "public_id", "created_at", "updated_at")


@admin.register(ToneRecord)
class ToneRecordAdmin(admin.ModelAdmin):
    list_display = ("lemma", "pattern", "notation_system", "review_state", "updated_at")
    list_filter = ("notation_system", "review_state")
    search_fields = ("lemma__headword", "pattern", "public_id")
    readonly_fields = ("id", "public_id", "created_at", "updated_at")


@admin.register(Form)
class FormAdmin(admin.ModelAdmin):
    list_display = ("form_text", "lemma", "form_kind", "review_state", "updated_at")
    list_filter = ("form_kind", "review_state")
    search_fields = ("form_text", "normalized_form", "lemma__headword", "public_id")
    readonly_fields = (
        "id",
        "public_id",
        "normalized_form",
        "phonology_inventory_version",
        "graphemes",
        "grapheme_count",
        "syllables",
        "syllable_count",
        "created_at",
        "updated_at",
    )
