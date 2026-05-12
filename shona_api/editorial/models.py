from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone


class ReviewState(models.TextChoices):
    DRAFT = "draft", "Draft"
    NEEDS_REVIEW = "needs_review", "Needs review"
    IN_REVIEW = "in_review", "In review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    PUBLISHED = "published", "Published"
    DEPRECATED = "deprecated", "Deprecated"


class ReviewNote(models.Model):
    target_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="editorial_review_notes",
    )
    target_object_id = models.CharField(max_length=80)
    target = GenericForeignKey("target_content_type", "target_object_id")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="editorial_review_notes",
    )
    state = models.CharField(
        max_length=32,
        choices=ReviewState.choices,
        default=ReviewState.NEEDS_REVIEW,
        db_index=True,
    )
    body = models.TextField()
    is_resolved = models.BooleanField(default=False, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("target_content_type", "target_object_id")),
            models.Index(fields=("state", "is_resolved")),
        ]

    def __str__(self):
        return f"{self.state} note for {self.target_content_type}:{self.target_object_id}"

    def mark_resolved(self, when=None):
        self.is_resolved = True
        self.resolved_at = when or timezone.now()
        self.save(update_fields=("is_resolved", "resolved_at", "updated_at"))


class EditorialDecision(models.Model):
    class DecisionType(models.TextChoices):
        APPROVE = "approve", "Approve"
        REJECT = "reject", "Reject"
        REQUEST_CHANGES = "request_changes", "Request changes"
        DEPRECATE = "deprecate", "Deprecate"
        PUBLISH = "publish", "Publish"

    decision_type = models.CharField(
        max_length=32,
        choices=DecisionType.choices,
        db_index=True,
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="editorial_decisions",
    )
    summary = models.CharField(max_length=255)
    rationale = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    decided_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-decided_at",)

    def __str__(self):
        return f"{self.get_decision_type_display()}: {self.summary}"

    def record_affected_record(self, target, relationship):
        return self.affected_records.create(target=target, relationship=relationship)


class EditorialDecisionRecord(models.Model):
    class Relationship(models.TextChoices):
        PRIMARY = "primary", "Primary"
        RELATED = "related", "Related"
        SUPERSEDED = "superseded", "Superseded"
        CREATED = "created", "Created"

    decision = models.ForeignKey(
        EditorialDecision,
        on_delete=models.CASCADE,
        related_name="affected_records",
    )
    target_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="editorial_decision_records",
    )
    target_object_id = models.CharField(max_length=80)
    target = GenericForeignKey("target_content_type", "target_object_id")
    relationship = models.CharField(
        max_length=32,
        choices=Relationship.choices,
        default=Relationship.PRIMARY,
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)
        indexes = [
            models.Index(fields=("target_content_type", "target_object_id")),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=(
                    "decision",
                    "target_content_type",
                    "target_object_id",
                    "relationship",
                ),
                name="unique_editorial_decision_record_relationship",
            )
        ]

    def __str__(self):
        return (
            f"{self.relationship} record for decision {self.decision_id}: "
            f"{self.target_content_type}:{self.target_object_id}"
        )


class AuditLogManager(models.Manager):
    def record(self, *, action, actor=None, target=None, metadata=None):
        entry = self.model(action=action, actor=actor, metadata=metadata or {})
        if target is not None:
            entry.target = target
        entry.save()
        return entry


class AuditLog(models.Model):
    class Action(models.TextChoices):
        REVIEW_NOTE_CREATED = "review_note_created", "Review note created"
        REVIEW_NOTE_RESOLVED = "review_note_resolved", "Review note resolved"
        EDITORIAL_DECISION_RECORDED = (
            "editorial_decision_recorded",
            "Editorial decision recorded",
        )
        RECORD_STATE_CHANGED = "record_state_changed", "Record state changed"

    action = models.CharField(max_length=64, choices=Action.choices, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="editorial_audit_logs",
    )
    target_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="editorial_audit_logs",
    )
    target_object_id = models.CharField(max_length=80, blank=True)
    target = GenericForeignKey("target_content_type", "target_object_id")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = AuditLogManager()

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("target_content_type", "target_object_id")),
        ]

    def __str__(self):
        return f"{self.action} at {self.created_at:%Y-%m-%d %H:%M:%S}"
