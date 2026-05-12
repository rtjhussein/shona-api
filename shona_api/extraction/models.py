from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from shona_api.editorial.models import ReviewState
from shona_api.sources.models import Source


class ExtractionUnitManager(models.Manager):
    def create_from_parser_output(
        self,
        *,
        source,
        source_location_reference,
        raw_text,
        parser_output,
        confidence,
        review_state=ReviewState.NEEDS_REVIEW,
        provenance=None,
    ):
        parse_metadata = parser_output.get("parse_metadata", {})
        parser_name = parse_metadata.get("parser", "unknown-parser")
        parser_status = self.model.status_from_parser_output(parser_output)
        provenance_payload = {
            "source_key": source.source_key,
            "source_location_reference": source_location_reference,
            "parser": parser_name,
        }
        provenance_payload.update(provenance or {})

        return self.create(
            source=source,
            source_location_reference=source_location_reference,
            raw_text=raw_text,
            parser_output=parser_output,
            parser_name=parser_name,
            parser_status=parser_status,
            confidence=confidence,
            review_state=review_state,
            provenance=provenance_payload,
        )


class ExtractionUnit(models.Model):
    class ParserStatus(models.TextChoices):
        PARSED = "parsed", "Parsed"
        PARSED_WITH_UNCERTAINTY = (
            "parsed_with_uncertainty",
            "Parsed with uncertainty",
        )
        FAILED = "failed", "Failed"

    source = models.ForeignKey(
        Source,
        on_delete=models.PROTECT,
        related_name="extraction_units",
    )
    source_location_reference = models.CharField(
        max_length=255,
        help_text="Stable source locator such as filename, page, line, or entry key.",
    )
    raw_text = models.TextField()
    parser_output = models.JSONField(default=dict)
    parser_name = models.CharField(max_length=120, db_index=True)
    parser_status = models.CharField(
        max_length=32,
        choices=ParserStatus.choices,
        db_index=True,
    )
    confidence = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Parser confidence from 0.0 to 1.0 before editorial review.",
    )
    review_state = models.CharField(
        max_length=32,
        choices=ReviewState.choices,
        default=ReviewState.NEEDS_REVIEW,
        db_index=True,
    )
    provenance = models.JSONField(default=dict, blank=True)
    canonical_record_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="extraction_units",
    )
    canonical_record_object_id = models.CharField(max_length=80, blank=True)
    canonical_record = GenericForeignKey(
        "canonical_record_content_type",
        "canonical_record_object_id",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ExtractionUnitManager()

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("source", "review_state")),
            models.Index(fields=("parser_status", "review_state")),
            models.Index(
                fields=(
                    "canonical_record_content_type",
                    "canonical_record_object_id",
                )
            ),
        ]

    @property
    def source_key(self):
        return self.source.source_key

    @classmethod
    def status_from_parser_output(cls, parser_output):
        if parser_output.get("errors"):
            return cls.ParserStatus.FAILED
        if parser_output.get("uncertainties"):
            return cls.ParserStatus.PARSED_WITH_UNCERTAINTY
        return cls.ParserStatus.PARSED

    def __str__(self):
        return f"{self.source_key} {self.source_location_reference}"
