from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.contrib.postgres.indexes import GinIndex
from django.db import models

from shona_api.editorial.models import ReviewState
from shona_api.phonology import compute_phonology_fields
from shona_api.phonology.orthography import normalize_orthography
from shona_api.records.models import CanonicalRecord


class PhonologyFieldsMixin(models.Model):
    phonology_field_names = (
        "phonology_inventory_version",
        "graphemes",
        "grapheme_count",
        "syllables",
        "syllable_count",
    )

    phonology_inventory_version = models.CharField(max_length=80, blank=True)
    graphemes = models.JSONField(default=list, blank=True)
    grapheme_count = models.PositiveSmallIntegerField(default=0)
    syllables = models.JSONField(default=list, blank=True)
    syllable_count = models.PositiveSmallIntegerField(default=0)

    class Meta:
        abstract = True

    def apply_phonology_fields(self, text):
        fields = compute_phonology_fields(text)
        for field_name, value in fields.items():
            setattr(self, field_name, value)

    def include_computed_update_fields(self, kwargs, *field_names):
        update_fields = kwargs.get("update_fields")
        if update_fields is None:
            return
        kwargs["update_fields"] = set(update_fields).union(
            self.phonology_field_names,
            field_names,
        )


class NounClass(CanonicalRecord):
    public_id_prefix = "nounclass"

    class_number = models.CharField(
        max_length=16,
        unique=True,
        db_index=True,
        help_text="Readable Shona noun-class identifier such as 1, 1a, 2, or 15.",
    )
    display_order = models.PositiveSmallIntegerField(default=0, db_index=True)
    label = models.CharField(max_length=120, blank=True)
    nominal_prefix = models.CharField(max_length=32, blank=True)
    prefix_allomorphs = models.JSONField(default=list, blank=True)
    default_plural_class = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="singular_classes",
        null=True,
        blank=True,
    )
    subject_concord = models.CharField(max_length=32, blank=True)
    object_concord = models.CharField(max_length=32, blank=True)
    possessive_concord = models.CharField(max_length=32, blank=True)
    adjectival_concord = models.CharField(max_length=32, blank=True)
    relative_concord = models.CharField(max_length=32, blank=True)
    associative_concord = models.CharField(max_length=32, blank=True)
    demonstrative_proximal = models.CharField(max_length=32, blank=True)
    demonstrative_medial = models.CharField(max_length=32, blank=True)
    demonstrative_distal = models.CharField(max_length=32, blank=True)
    additional_concords = models.JSONField(
        default=dict,
        blank=True,
        help_text="Reserved slot for later morphology concord types.",
    )
    dialect_overrides = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Dialect-keyed morphology overrides, for example "
            "{'Z': {'subject_concord': 'u'}}."
        ),
    )
    notes = models.TextField(blank=True)
    review_state = models.CharField(
        max_length=32,
        choices=ReviewState.choices,
        default=ReviewState.DRAFT,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("display_order", "class_number")
        indexes = [
            models.Index(fields=("review_state", "class_number")),
        ]

    def __str__(self):
        label = f" {self.label}" if self.label else ""
        return f"Class {self.class_number}{label}"

    def clean(self):
        errors = {}
        if not isinstance(self.prefix_allomorphs, list):
            errors["prefix_allomorphs"] = "Prefix allomorphs must be a list."
        if not isinstance(self.additional_concords, dict):
            errors["additional_concords"] = "Additional concords must be an object."
        if not isinstance(self.dialect_overrides, dict):
            errors["dialect_overrides"] = "Dialect overrides must be an object."
        if self.pk and self.default_plural_class_id == self.pk:
            errors["default_plural_class"] = "A noun class cannot pluralize to itself."
        if errors:
            raise ValidationError(errors)


class Lemma(PhonologyFieldsMixin, CanonicalRecord):
    class HeadwordKind(models.TextChoices):
        WORD = "word", "Word"
        NOUN = "noun", "Noun"
        VERB_STEM = "verb_stem", "Verb stem"
        IDEOPHONE = "ideophone", "Ideophone"
        UNKNOWN = "unknown", "Unknown"

    class LearnerLevel(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"
        UNKNOWN = "unknown", "Unknown"

    class CurriculumStage(models.TextChoices):
        FORMS_1_2 = "forms_1_2", "Forms 1-2"
        FORMS_3_4 = "forms_3_4", "Forms 3-4"
        GENERAL_SECONDARY = "general_secondary", "General secondary"
        UNKNOWN = "unknown", "Unknown"

    class FrequencyTier(models.TextChoices):
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"
        UNKNOWN = "unknown", "Unknown"

    public_id_prefix = "lemma"

    headword = models.CharField(max_length=160)
    normalized_headword = models.CharField(max_length=160, db_index=True, blank=True)
    headword_kind = models.CharField(
        max_length=32,
        choices=HeadwordKind.choices,
        default=HeadwordKind.UNKNOWN,
        db_index=True,
    )
    part_of_speech_code = models.CharField(max_length=32, blank=True, db_index=True)
    part_of_speech_label = models.CharField(max_length=120, blank=True)
    noun_class = models.ForeignKey(
        NounClass,
        on_delete=models.SET_NULL,
        related_name="lemmas",
        null=True,
        blank=True,
    )
    dialects = models.JSONField(default=list, blank=True)
    comparative_bantu_marker = models.BooleanField(default=False)
    learner_level = models.CharField(
        max_length=32,
        choices=LearnerLevel.choices,
        default=LearnerLevel.UNKNOWN,
        db_index=True,
    )
    curriculum_stage = models.CharField(
        max_length=32,
        choices=CurriculumStage.choices,
        default=CurriculumStage.UNKNOWN,
        db_index=True,
    )
    curriculum_domains = models.JSONField(default=list, blank=True)
    learning_functions = models.JSONField(default=list, blank=True)
    communication_contexts = models.JSONField(default=list, blank=True)
    register_tags = models.JSONField(default=list, blank=True)
    learner_source_links = models.JSONField(default=list, blank=True)
    first_appearance_source_key = models.CharField(
        max_length=80,
        blank=True,
        db_index=True,
    )
    first_appearance_locator = models.CharField(max_length=255, blank=True)
    first_appearance_unit = models.CharField(max_length=120, blank=True, db_index=True)
    first_appearance_lesson = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        db_index=True,
    )
    first_appearance_page = models.CharField(max_length=80, blank=True)
    frequency_tier = models.CharField(
        max_length=32,
        choices=FrequencyTier.choices,
        default=FrequencyTier.UNKNOWN,
        db_index=True,
    )
    frequency_score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Transparent learner-priority score from 0.0 to 1.0.",
    )
    review_state = models.CharField(
        max_length=32,
        choices=ReviewState.choices,
        default=ReviewState.DRAFT,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("normalized_headword", "headword")
        indexes = [
            models.Index(fields=("normalized_headword", "part_of_speech_code")),
            models.Index(fields=("review_state", "headword_kind")),
            models.Index(fields=("learner_level", "frequency_tier")),
            models.Index(fields=("first_appearance_source_key", "first_appearance_lesson")),
            GinIndex(
                fields=["normalized_headword"],
                name="lemma_headword_trgm_idx",
                opclasses=["gin_trgm_ops"],
            ),
        ]

    def __str__(self):
        pos = f" {self.part_of_speech_code}" if self.part_of_speech_code else ""
        return f"{self.headword}{pos}"

    def clean(self):
        errors = {}
        if self.noun_class_id and self.headword_kind != self.HeadwordKind.NOUN:
            errors["noun_class"] = "Only noun lemmas can be linked to a noun class."
        for field_name in (
            "curriculum_domains",
            "learning_functions",
            "communication_contexts",
            "register_tags",
            "learner_source_links",
        ):
            if not isinstance(getattr(self, field_name), list):
                errors[field_name] = "Learner metadata field must be a list."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.normalized_headword = normalize_orthography(self.headword)
        self.apply_phonology_fields(self.normalized_headword)
        self.include_computed_update_fields(kwargs, "normalized_headword")
        super().save(*args, **kwargs)


class Sense(CanonicalRecord):
    public_id_prefix = "sense"

    lemma = models.ForeignKey(
        Lemma,
        on_delete=models.CASCADE,
        related_name="senses",
    )
    number = models.PositiveSmallIntegerField(default=1)
    definition = models.TextField()
    dialects = models.JSONField(default=list, blank=True)
    grammar = models.JSONField(default=list, blank=True)
    examples = models.JSONField(default=list, blank=True)
    cross_references = models.JSONField(default=list, blank=True)
    review_state = models.CharField(
        max_length=32,
        choices=ReviewState.choices,
        default=ReviewState.DRAFT,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("lemma__normalized_headword", "number")
        constraints = [
            models.UniqueConstraint(
                fields=("lemma", "number"),
                name="unique_sense_number_per_lemma",
            )
        ]

    def __str__(self):
        return f"{self.lemma} sense {self.number}"


class ToneRecord(CanonicalRecord):
    class NotationSystem(models.TextChoices):
        HANNAN_BRACKET = "hannan_bracket", "Hannan bracket"
        EDITORIAL = "editorial", "Editorial"

    public_id_prefix = "tone"

    lemma = models.ForeignKey(
        Lemma,
        on_delete=models.CASCADE,
        related_name="tone_records",
    )
    form = models.ForeignKey(
        "Form",
        on_delete=models.CASCADE,
        related_name="tone_records",
        null=True,
        blank=True,
    )
    pattern = models.CharField(max_length=80)
    dialects = models.JSONField(default=list, blank=True)
    notation_system = models.CharField(
        max_length=32,
        choices=NotationSystem.choices,
        default=NotationSystem.HANNAN_BRACKET,
        db_index=True,
    )
    note = models.TextField(blank=True)
    review_state = models.CharField(
        max_length=32,
        choices=ReviewState.choices,
        default=ReviewState.DRAFT,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("lemma__normalized_headword", "notation_system", "pattern")
        indexes = [
            models.Index(fields=("notation_system", "pattern")),
        ]

    def __str__(self):
        return f"{self.lemma} [{self.pattern}]"


class Form(PhonologyFieldsMixin, CanonicalRecord):
    class FormKind(models.TextChoices):
        HEADWORD = "headword", "Headword"
        PLURAL = "plural", "Plural"
        DERIVED = "derived", "Derived"
        INFLECTED = "inflected", "Inflected"
        VARIANT = "variant", "Variant"
        OTHER = "other", "Other"

    public_id_prefix = "form"

    lemma = models.ForeignKey(
        Lemma,
        on_delete=models.CASCADE,
        related_name="forms",
    )
    sense = models.ForeignKey(
        Sense,
        on_delete=models.SET_NULL,
        related_name="forms",
        null=True,
        blank=True,
    )
    form_text = models.CharField(max_length=160)
    normalized_form = models.CharField(max_length=160, db_index=True, blank=True)
    form_kind = models.CharField(
        max_length=32,
        choices=FormKind.choices,
        default=FormKind.OTHER,
        db_index=True,
    )
    dialects = models.JSONField(default=list, blank=True)
    grammar = models.JSONField(default=list, blank=True)
    review_state = models.CharField(
        max_length=32,
        choices=ReviewState.choices,
        default=ReviewState.DRAFT,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("lemma__normalized_headword", "form_kind", "normalized_form")
        indexes = [
            models.Index(fields=("normalized_form", "form_kind")),
            models.Index(fields=("review_state", "form_kind")),
            GinIndex(
                fields=["normalized_form"],
                name="form_text_trgm_idx",
                opclasses=["gin_trgm_ops"],
            ),
        ]

    def __str__(self):
        return f"{self.form_text} ({self.form_kind})"

    def save(self, *args, **kwargs):
        self.normalized_form = normalize_orthography(self.form_text)
        self.apply_phonology_fields(self.normalized_form)
        self.include_computed_update_fields(kwargs, "normalized_form")
        super().save(*args, **kwargs)
