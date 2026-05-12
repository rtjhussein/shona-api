import uuid

import pytest
from django.db import connection, models
from django.test.utils import isolate_apps
from django.utils import timezone

from shona_api.records.models import CanonicalRecord
from shona_api.records.public_ids import make_public_id


def test_public_id_helper_builds_stable_human_readable_ids():
    record_id = uuid.UUID("12345678-1234-5678-1234-567812345678")

    assert make_public_id("lemma", record_id) == (
        "lemma_ci2fm6asgrlhqerukz4bencwpa"
    )
    assert make_public_id("sense", record_id) == (
        "sense_ci2fm6asgrlhqerukz4bencwpa"
    )


@pytest.mark.django_db(transaction=True)
@isolate_apps("tests")
def test_canonical_record_uses_uuid_primary_key_and_generates_public_id():
    class ExampleRecord(CanonicalRecord):
        public_id_prefix = "lemma"
        label = models.CharField(max_length=80)

        class Meta:
            app_label = "tests"

    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(ExampleRecord)
    try:
        record = ExampleRecord.objects.create(label="mhoro")

        assert isinstance(record.id, uuid.UUID)
        assert record.public_id == make_public_id("lemma", record.id)
    finally:
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(ExampleRecord)


@pytest.mark.django_db(transaction=True)
@isolate_apps("tests")
def test_canonical_record_metadata_conventions_are_reusable_defaults():
    class ExampleRecord(CanonicalRecord):
        public_id_prefix = "sense"
        label = models.CharField(max_length=80)

        class Meta:
            app_label = "tests"

    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(ExampleRecord)
    try:
        first = ExampleRecord.objects.create(label="first")
        second = ExampleRecord.objects.create(label="second")

        first.provenance["source_keys"] = ["source_hannan"]
        deprecated_at = timezone.now()
        first.revision = 2
        first.deprecated_at = deprecated_at
        first.deprecation_note = "Superseded by reviewed evidence."
        first.save()

        second.refresh_from_db()
        first.refresh_from_db()

        assert first.provenance == {"source_keys": ["source_hannan"]}
        assert first.revision == 2
        assert first.deprecated_at == deprecated_at
        assert first.deprecation_note == "Superseded by reviewed evidence."
        assert first.is_deprecated is True

        assert second.provenance == {}
        assert second.revision == 1
        assert second.deprecated_at is None
        assert second.deprecation_note == ""
        assert second.is_deprecated is False
    finally:
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(ExampleRecord)
