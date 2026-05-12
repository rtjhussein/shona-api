from django.contrib import admin

from .models import AuditLog, EditorialDecision, EditorialDecisionRecord, ReviewNote


class EditorialDecisionRecordInline(admin.TabularInline):
    model = EditorialDecisionRecord
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(ReviewNote)
class ReviewNoteAdmin(admin.ModelAdmin):
    list_display = (
        "target_content_type",
        "target_object_id",
        "state",
        "author",
        "is_resolved",
        "created_at",
    )
    list_filter = ("state", "is_resolved", "target_content_type")
    search_fields = ("target_object_id", "body", "author__username")
    readonly_fields = ("created_at", "updated_at", "resolved_at")
    ordering = ("-created_at",)


@admin.register(EditorialDecision)
class EditorialDecisionAdmin(admin.ModelAdmin):
    list_display = (
        "decision_type",
        "summary",
        "decided_by",
        "decided_at",
    )
    list_filter = ("decision_type",)
    search_fields = ("summary", "rationale", "decided_by__username")
    readonly_fields = ("decided_at",)
    ordering = ("-decided_at",)
    inlines = (EditorialDecisionRecordInline,)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "action",
        "actor",
        "target_content_type",
        "target_object_id",
        "created_at",
    )
    list_filter = ("action", "target_content_type")
    search_fields = ("target_object_id", "actor__username")
    readonly_fields = (
        "action",
        "actor",
        "target_content_type",
        "target_object_id",
        "metadata",
        "created_at",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
