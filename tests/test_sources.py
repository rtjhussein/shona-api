import pytest
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError

from shona_api.sources.admin import SourceAdmin
from shona_api.sources.models import Source
from shona_api.sources.registry import SOURCE_REGISTRY


@pytest.mark.django_db
def test_source_key_must_be_unique():
    Source.objects.create(
        source_key="source_hannan",
        title="Hannan Dictionary",
        authority_level="Backbone lexical authority",
        rights_usage_note="Local-only source material; do not upload source file to git.",
        ingestion_style="Digitized dictionary-entry parsing into structured candidates.",
        current_filename="hannan_dictionary.pdf",
    )

    with pytest.raises(IntegrityError):
        Source.objects.create(
            source_key="source_hannan",
            title="Duplicate Hannan Dictionary",
            authority_level="Backbone lexical authority",
            rights_usage_note="Local-only source material; do not upload source file to git.",
            ingestion_style="Digitized dictionary-entry parsing into structured candidates.",
            current_filename="hannan_dictionary.pdf",
        )


def test_source_metadata_fields_are_required():
    source = Source(source_key="source_hannan")

    with pytest.raises(ValidationError) as exc_info:
        source.full_clean(validate_unique=False)

    assert set(exc_info.value.message_dict) == {
        "title",
        "authority_level",
        "rights_usage_note",
        "ingestion_style",
        "current_filename",
    }


@pytest.mark.django_db
def test_seed_sources_creates_all_current_source_keys():
    call_command("seed_sources")

    assert set(Source.objects.values_list("source_key", flat=True)) == {
        source["source_key"] for source in SOURCE_REGISTRY
    }


@pytest.mark.django_db
def test_seed_sources_updates_existing_records_without_changing_source_key():
    Source.objects.create(
        source_key="source_hannan",
        title="Old title",
        authority_level="Old authority",
        rights_usage_note="Old note",
        ingestion_style="Old style",
        current_filename="old.pdf",
    )

    call_command("seed_sources")

    source = Source.objects.get(source_key="source_hannan")
    expected = next(
        source for source in SOURCE_REGISTRY if source["source_key"] == "source_hannan"
    )
    assert source.title == expected["title"]
    assert source.current_filename == expected["current_filename"]


def test_source_admin_has_usable_list_and_search_configuration():
    model_admin = SourceAdmin(Source, admin.site)

    assert model_admin.list_display == (
        "source_key",
        "title",
        "authority_level",
        "current_filename",
    )
    assert model_admin.search_fields == (
        "source_key",
        "title",
        "authority_level",
        "current_filename",
    )
