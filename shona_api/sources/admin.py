from django.contrib import admin

from .models import Source


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = (
        "source_key",
        "title",
        "authority_level",
        "current_filename",
    )
    search_fields = (
        "source_key",
        "title",
        "authority_level",
        "current_filename",
    )
    list_filter = ("authority_level",)
    ordering = ("source_key",)

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return ()
        return ("source_key",)
