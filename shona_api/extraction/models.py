from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
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
    batch_id = models.CharField(
        max_length=120,
        blank=True,
        db_index=True,
        help_text="Identifier for the import batch that created this unit.",
    )
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


class IngestionRun(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    batch_id = models.CharField(max_length=120, db_index=True)
    start_page = models.PositiveIntegerField()
    end_page = models.PositiveIntegerField()
    parser_repo_path = models.CharField(max_length=500)
    pdf_path = models.CharField(max_length=500)
    output_dir = models.CharField(max_length=500)
    jsonl_path = models.CharField(max_length=500, blank=True)
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    dry_run = models.BooleanField(default=False)
    overwrite_pages = models.BooleanField(default=False)
    auto_publish = models.BooleanField(default=False)
    imported_count = models.PositiveIntegerField(default=0)
    duplicate_count = models.PositiveIntegerField(default=0)
    publishable_count = models.PositiveIntegerField(default=0)
    published_count = models.PositiveIntegerField(default=0)
    failed_publish_count = models.PositiveIntegerField(default=0)
    log_text = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hannan_ingestion_runs",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(
                fields=("status", "created_at"),
                name="ingrun_status_created_idx",
            ),
            models.Index(
                fields=("batch_id", "created_at"),
                name="ingrun_batch_created_idx",
            ),
        ]

    @property
    def page_label(self):
        if self.start_page == self.end_page:
            return f"PDF page {self.start_page}"
        return f"PDF pages {self.start_page}-{self.end_page}"

    def append_log(self, message):
        self.log_text = f"{self.log_text}{message.rstrip()}\n"

    def __str__(self):
        return f"{self.batch_id} ({self.status})"
