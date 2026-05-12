from django.contrib import admin

from .models import DataRelease


@admin.register(DataRelease)
class DataReleaseAdmin(admin.ModelAdmin):
    list_display = ("version", "label", "rule_set_version", "is_current", "created_at")
    list_filter = ("is_current", "rule_set_version")
    search_fields = ("version", "label", "rule_set_version")
