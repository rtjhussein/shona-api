from django.db import models, transaction
from django.db.models import Q


class DataReleaseManager(models.Manager):
    def current(self):
        return self.get_queryset().get(is_current=True)


class DataRelease(models.Model):
    version = models.CharField(
        max_length=40,
        unique=True,
        db_index=True,
        help_text="Stable release identifier exposed through API metadata.",
    )
    label = models.CharField(max_length=120)
    rule_set_version = models.CharField(
        max_length=80,
        db_index=True,
        help_text="Version string for morphology/phonology rules used by this release.",
    )
    is_current = models.BooleanField(default=False, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = DataReleaseManager()

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("is_current",),
                condition=Q(is_current=True),
                name="unique_current_data_release",
            )
        ]

    def __str__(self):
        current_marker = " current" if self.is_current else ""
        return f"{self.version}{current_marker}"

    def save(self, *args, **kwargs):
        if not self.is_current:
            return super().save(*args, **kwargs)

        with transaction.atomic():
            type(self).objects.filter(is_current=True).exclude(pk=self.pk).update(
                is_current=False
            )
            return super().save(*args, **kwargs)
