from django.db import models

from shona_api.editorial.models import ReviewState
from shona_api.lexicon.models import Lemma, PhonologyFieldsMixin
from shona_api.records.models import CanonicalRecord


class FigurativeExpression(PhonologyFieldsMixin, CanonicalRecord):
    class Subtype(models.TextChoices):
        TSUMO = "tsumo", "Tsumo"
        MADIMIKIRA = "madimikira", "Madimikira"
        MADUNHURIRWA = "madunhurirwa", "Madunhurirwa"
        NYAUDZOSINGWI = "nyaudzosingwi", "Nyaudzosingwi"
        FANANIDZO = "fananidzo", "Fananidzo"
        ENZANISO = "enzaniso", "Enzaniso"
        CHIBHENDE = "chibhende", "Chibhende"

    class SubtypeReadiness(models.TextChoices):
        ACTIVE = "active", "Active"
        RESERVED = "reserved", "Reserved for future support"

    public_id_prefix = "figexpr"

    expression_text = models.CharField(max_length=255)
    normalized_expression = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text="Conservative search/dedupe key for the expression text.",
    )
    subtype = models.CharField(
        max_length=32,
        choices=Subtype.choices,
        db_index=True,
    )
    subtype_readiness = models.CharField(
        max_length=32,
        choices=SubtypeReadiness.choices,
        default=SubtypeReadiness.RESERVED,
        db_index=True,
    )
    idiomatic_meaning = models.TextField(blank=True)
    english_rendering = models.TextField(blank=True)
    usage_note = models.TextField(blank=True)
    cultural_themes = models.JSONField(default=list, blank=True)
    pedagogy_notes = models.JSONField(default=list, blank=True)
    source_notes = models.JSONField(default=list, blank=True)
    linked_lemmas = models.ManyToManyField(
        Lemma,
        blank=True,
        related_name="figurative_expressions",
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
        ordering = ("normalized_expression", "subtype", "expression_text")
        indexes = [
            models.Index(fields=("subtype", "review_state")),
            models.Index(fields=("subtype_readiness", "subtype")),
            models.Index(fields=("normalized_expression", "subtype")),
        ]

    def __str__(self):
        return f"{self.expression_text} ({self.subtype})"

    def save(self, *args, **kwargs):
        self.normalized_expression = " ".join(self.expression_text.split()).casefold()
        self.apply_phonology_fields(self.expression_text)
        self.include_computed_update_fields(kwargs, "normalized_expression")
        super().save(*args, **kwargs)
