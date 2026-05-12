from django.core.validators import RegexValidator
from django.db import models


class Source(models.Model):
    source_key = models.CharField(
        max_length=80,
        unique=True,
        validators=[
            RegexValidator(
                regex=r"^source_[a-z0-9_]+$",
                message="Source keys must be stable lowercase identifiers prefixed with source_.",
            )
        ],
        help_text="Stable unique key used by provenance and ingestion workflows.",
    )
    title = models.CharField(max_length=255)
    authority_level = models.CharField(max_length=120)
    rights_usage_note = models.TextField()
    ingestion_style = models.TextField()
    current_filename = models.CharField(max_length=255)

    class Meta:
        ordering = ("source_key",)

    def __str__(self):
        return f"{self.source_key} - {self.title}"
