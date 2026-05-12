from django.contrib import admin

from .models import APIKey


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "prefix",
        "plan",
        "rate_limit_per_minute",
        "is_active",
        "last_used_at",
        "created_at",
    )
    list_filter = ("plan", "is_active")
    search_fields = ("name", "prefix")
    readonly_fields = (
        "prefix",
        "key_hash",
        "last_used_at",
        "revoked_at",
        "created_at",
        "updated_at",
    )
    actions = ("revoke_keys",)

    def has_add_permission(self, request):
        return False

    @admin.action(description="Revoke selected API keys")
    def revoke_keys(self, request, queryset):
        for api_key in queryset.filter(is_active=True):
            api_key.revoke()
