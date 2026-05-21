import json
import os
import tempfile
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from shona_api.editorial.models import ReviewState
from shona_api.lexicon.models import NounClass


@pytest.mark.django_db
def test_noun_class_seeding_command_creates_and_pairs_all_classes():
    # Verify DB is empty (or has no seeded noun classes initially in a fresh test database)
    NounClass.objects.all().delete()
    assert NounClass.objects.count() == 0

    # Call the management command to seed the classes
    call_command("seed_noun_classes")

    # Verify all 21 Shona noun classes are successfully created
    assert NounClass.objects.count() == 21

    # Verify Class 1 properties
    class_1 = NounClass.objects.get(class_number="1")
    assert class_1.display_order == 1
    assert class_1.label == "mu- (personal singular)"
    assert class_1.nominal_prefix == "mu"
    assert class_1.prefix_allomorphs == ["mu", "m"]
    assert class_1.subject_concord == "u"
    assert class_1.object_concord == "mu"
    assert class_1.possessive_concord == "wa"
    assert class_1.adjectival_concord == "mu"
    assert class_1.relative_concord == "u"
    assert class_1.associative_concord == "wa"
    assert class_1.demonstrative_proximal == "uyu"
    assert class_1.demonstrative_medial == "uwo"
    assert class_1.demonstrative_distal == "uya"
    assert class_1.notes == "Standard personal singular class for human beings."
    assert class_1.review_state == ReviewState.PUBLISHED
    assert class_1.provenance == {
        "source_key": "source_fortune",
        "locator": "page_48",
        "rule_id": "fortune.noun_class.inventory.001",
        "confidence": "verified",
    }

    # Verify Class 2 properties and connection
    class_2 = NounClass.objects.get(class_number="2")
    assert class_2.display_order == 3
    assert class_2.label == "va- (personal plural)"
    assert class_2.nominal_prefix == "va"
    assert class_2.default_plural_class is None
    assert class_2.review_state == ReviewState.PUBLISHED

    # Verify relationship: Class 1 default plural should point to Class 2
    assert class_1.default_plural_class == class_2

    # Verify Class 21 points to Class 6
    class_21 = NounClass.objects.get(class_number="21")
    class_6 = NounClass.objects.get(class_number="6")
    assert class_21.default_plural_class == class_6
    assert class_21.subject_concord == "ri"  # Augmentatives concord as Class 5/6 (ri-)
    assert class_21.adjectival_concord == "zi"


@pytest.mark.django_db
def test_noun_class_seeding_is_idempotent_and_updates_correctly():
    # Run the command to seed the initial classes
    call_command("seed_noun_classes")
    initial_count = NounClass.objects.count()
    assert initial_count == 21

    # Fetch Class 1 and store its ID/UUID to verify it remains the same
    class_1_before = NounClass.objects.get(class_number="1")
    class_1_id = class_1_before.id

    # Run the command again to verify idempotency (no duplicate entries)
    call_command("seed_noun_classes")
    assert NounClass.objects.count() == 21

    class_1_after = NounClass.objects.get(class_number="1")
    assert class_1_after.id == class_1_id


@pytest.mark.django_db
def test_noun_class_seeding_with_custom_fixture():
    # Create a temporary custom fixture JSON
    custom_records = [
        {
            "class_number": "99",
            "display_order": 99,
            "label": "custom-class",
            "nominal_prefix": "cust",
            "prefix_allomorphs": ["cust"],
            "default_plural_class_number": None,
            "subject_concord": "c",
            "object_concord": "c",
            "possessive_concord": "ca",
            "adjectival_concord": "cust",
            "relative_concord": "c",
            "associative_concord": "ca",
            "demonstrative_proximal": "cc",
            "demonstrative_medial": "co",
            "demonstrative_distal": "ca",
            "additional_concords": {},
            "dialect_overrides": {},
            "notes": "Custom test class.",
            "provenance": {
                "source_key": "source_fortune",
                "locator": "page_999",
                "rule_id": "fortune.test.999",
                "confidence": "verified",
            },
        }
    ]

    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False, encoding="utf-8") as temp_file:
        json.dump(custom_records, temp_file)
        temp_file_path = temp_file.name

    try:
        # Call command with custom fixture path
        call_command("seed_noun_classes", fixture=temp_file_path)

        # Verify our custom class is seeded
        custom_class = NounClass.objects.get(class_number="99")
        assert custom_class.label == "custom-class"
        assert custom_class.nominal_prefix == "cust"
    finally:
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@pytest.mark.django_db
def test_seeding_missing_fixture_raises_error():
    with pytest.raises(CommandError) as exc_info:
        call_command("seed_noun_classes", fixture="nonexistent_file_path_12345.json")
    assert "Fixture file not found at:" in str(exc_info.value)
