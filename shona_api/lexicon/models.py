from django.db import models

from shona_api.editorial.models import ReviewState
from shona_api.phonology import compute_phonology_fields
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


class Lemma(PhonologyFieldsMixin, CanonicalRecord):
    class HeadwordKind(models.TextChoices):
        WORD = "word", "Word"
        NOUN = "noun", "Noun"
        VERB_STEM = "verb_stem", "Verb stem"
        IDEOPHONE = "ideophone", "Ideophone"
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
    dialects = models.JSONField(default=list, blank=True)
    comparative_bantu_marker = models.BooleanField(default=False)
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
        ]

    def __str__(self):
        pos = f" {self.part_of_speech_code}" if self.part_of_speech_code else ""
        return f"{self.headword}{pos}"

    def save(self, *args, **kwargs):
        self.normalized_headword = self.headword.removeprefix("-").strip()
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
        ]

    def __str__(self):
        return f"{self.form_text} ({self.form_kind})"

    def save(self, *args, **kwargs):
        self.normalized_form = self.form_text.removeprefix("-").strip()
        self.apply_phonology_fields(self.normalized_form)
        self.include_computed_update_fields(kwargs, "normalized_form")
        super().save(*args, **kwargs)
