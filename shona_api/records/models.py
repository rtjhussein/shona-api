import uuid

from django.core.exceptions import ImproperlyConfigured
from django.db import models

from .public_ids import make_public_id


class CanonicalRecord(models.Model):
    """Thin abstract base for canonical records shared across future domains."""

    public_id_prefix = ""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    public_id = models.CharField(
        max_length=80,
        unique=True,
        editable=False,
        db_index=True,
        help_text="Stable API-facing identifier derived from the UUID primary key.",
    )
    provenance = models.JSONField(
        default=dict,
        blank=True,
        help_text="Source and evidence metadata for tracing canonical record origins.",
    )
    revision = models.PositiveIntegerField(
        default=1,
        help_text="Monotonic editorial/data revision for this canonical record.",
    )
    deprecated_at = models.DateTimeField(null=True, blank=True)
    deprecation_note = models.TextField(blank=True)

    class Meta:
        abstract = True

    @property
    def is_deprecated(self) -> bool:
        return self.deprecated_at is not None

    def save(self, *args, **kwargs):
        if not self.public_id:
            self.public_id = self.build_public_id()
        super().save(*args, **kwargs)

    def build_public_id(self) -> str:
        if not self.public_id_prefix:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} must define public_id_prefix."
            )
        return make_public_id(self.public_id_prefix, self.id)
