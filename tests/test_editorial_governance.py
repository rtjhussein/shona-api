import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from shona_api.editorial.admin import (
    AuditLogAdmin,
    EditorialDecisionAdmin,
    ReviewNoteAdmin,
)
from shona_api.editorial.models import (
    AuditLog,
    EditorialDecision,
    EditorialDecisionRecord,
    ReviewNote,
    ReviewState,
)
from shona_api.editorial.permissions import (
    EDITORIAL_ROLE_PERMISSIONS,
    EditorialRole,
    user_has_editorial_permission,
)
from shona_api.sources.models import Source


def test_review_state_conventions_are_stable():
    assert ReviewState.values == [
        "draft",
        "needs_review",
        "in_review",
        "approved",
        "rejected",
        "published",
        "deprecated",
    ]


@pytest.fixture
def source_record():
    return Source.objects.create(
        source_key="source_hannan",
        title="Hannan Dictionary",
        authority_level="Backbone lexical authority",
        rights_usage_note="Local-only source material; do not upload source file to git.",
        ingestion_style="Digitized dictionary-entry parsing into structured candidates.",
        current_filename="hannan_dictionary.pdf",
    )


@pytest.mark.django_db
def test_review_notes_attach_to_records(source_record):
    user = get_user_model().objects.create_user(username="reviewer")

    note = ReviewNote.objects.create(
        target=source_record,
        author=user,
        state=ReviewState.NEEDS_REVIEW,
        body="Check dialect marker before approval.",
    )

    note.refresh_from_db()
    assert note.target == source_record
    assert note.author == user
    assert note.state == ReviewState.NEEDS_REVIEW
    assert note.is_resolved is False


@pytest.mark.django_db
def test_editorial_decisions_record_affected_records(source_record):
    user = get_user_model().objects.create_user(username="editor")
    decision = EditorialDecision.objects.create(
        decision_type=EditorialDecision.DecisionType.APPROVE,
        decided_by=user,
        summary="Approve source metadata",
        rationale="Required fields are present and traceable.",
    )

    affected_record = decision.record_affected_record(
        source_record,
        relationship=EditorialDecisionRecord.Relationship.PRIMARY,
    )

    affected_record.refresh_from_db()
    assert affected_record.decision == decision
    assert affected_record.target == source_record
    assert affected_record.relationship == EditorialDecisionRecord.Relationship.PRIMARY
    assert list(decision.affected_records.all()) == [affected_record]


@pytest.mark.django_db
def test_audit_log_captures_actor_target_and_metadata(source_record):
    user = get_user_model().objects.create_user(username="auditor")

    entry = AuditLog.objects.record(
        action=AuditLog.Action.REVIEW_NOTE_CREATED,
        actor=user,
        target=source_record,
        metadata={"field": "authority_level"},
    )

    entry.refresh_from_db()
    assert entry.actor == user
    assert entry.target == source_record
    assert entry.action == AuditLog.Action.REVIEW_NOTE_CREATED
    assert entry.metadata == {"field": "authority_level"}


@pytest.mark.django_db
def test_editorial_permission_scaffold_supports_role_aware_checks():
    user = get_user_model().objects.create_user(username="viewer")
    view_permission = Permission.objects.get(
        content_type=ContentType.objects.get_for_model(ReviewNote),
        codename="view_reviewnote",
    )

    user.user_permissions.add(view_permission)

    assert "editorial.view_reviewnote" in EDITORIAL_ROLE_PERMISSIONS[
        EditorialRole.VIEWER
    ]
    assert "editorial.add_editorialdecision" in EDITORIAL_ROLE_PERMISSIONS[
        EditorialRole.EDITOR
    ]
    assert "editorial.delete_reviewnote" in EDITORIAL_ROLE_PERMISSIONS[
        EditorialRole.ADMIN
    ]
    assert user_has_editorial_permission(user, "editorial.view_reviewnote") is True
    assert user_has_editorial_permission(user, "editorial.add_reviewnote") is False


def test_editorial_admin_has_queryable_list_configuration():
    review_note_admin = ReviewNoteAdmin(ReviewNote, admin.site)
    decision_admin = EditorialDecisionAdmin(EditorialDecision, admin.site)
    audit_log_admin = AuditLogAdmin(AuditLog, admin.site)

    assert review_note_admin.list_display == (
        "target_content_type",
        "target_object_id",
        "state",
        "author",
        "is_resolved",
        "created_at",
    )
    assert decision_admin.list_display == (
        "decision_type",
        "summary",
        "decided_by",
        "decided_at",
    )
    assert audit_log_admin.list_display == (
        "action",
        "actor",
        "target_content_type",
        "target_object_id",
        "created_at",
    )
