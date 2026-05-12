import pytest

from shona_api.releases.models import DataRelease
from shona_api.releases.services import (
    CurrentReleaseNotFound,
    ensure_current_release_available,
    get_current_release,
    get_current_release_metadata,
)


@pytest.mark.django_db
def test_data_release_can_be_created_with_rule_set_version():
    release = DataRelease.objects.create(
        version="2026.05.0",
        label="May 2026 seed release",
        rule_set_version="morphology-rules-v1",
    )

    release.refresh_from_db()

    assert release.version == "2026.05.0"
    assert release.label == "May 2026 seed release"
    assert release.rule_set_version == "morphology-rules-v1"
    assert release.is_current is False


@pytest.mark.django_db
def test_current_release_can_be_marked_and_queried():
    old_release = DataRelease.objects.create(
        version="2026.04.0",
        label="April 2026 release",
        rule_set_version="morphology-rules-v1",
        is_current=True,
    )
    new_release = DataRelease.objects.create(
        version="2026.05.0",
        label="May 2026 release",
        rule_set_version="morphology-rules-v2",
        is_current=True,
    )

    old_release.refresh_from_db()

    assert old_release.is_current is False
    assert get_current_release() == new_release
    assert DataRelease.objects.current() == new_release


@pytest.mark.django_db
def test_current_release_lookup_raises_when_none_exists():
    DataRelease.objects.create(
        version="2026.05.0",
        label="May 2026 release",
        rule_set_version="morphology-rules-v1",
    )

    with pytest.raises(CurrentReleaseNotFound):
        get_current_release()


@pytest.mark.django_db
def test_rule_set_version_metadata_can_be_stored_and_queried():
    DataRelease.objects.create(
        version="2026.04.0",
        label="April 2026 release",
        rule_set_version="morphology-rules-v1",
    )
    release = DataRelease.objects.create(
        version="2026.05.0",
        label="May 2026 release",
        rule_set_version="morphology-rules-v2",
        is_current=True,
        metadata={"phonology_inventory": "standard-v1"},
    )

    assert list(
        DataRelease.objects.filter(rule_set_version="morphology-rules-v2")
    ) == [release]
    assert get_current_release_metadata() == {
        "release_version": "2026.05.0",
        "rule_set_version": "morphology-rules-v2",
    }


@pytest.mark.django_db
def test_publish_guard_skeleton_reports_current_release_readiness():
    missing = ensure_current_release_available()

    DataRelease.objects.create(
        version="2026.05.0",
        label="May 2026 release",
        rule_set_version="morphology-rules-v1",
        is_current=True,
    )

    ready = ensure_current_release_available()

    assert missing.is_ready is False
    assert missing.reason == "current_release_missing"
    assert ready.is_ready is True
    assert ready.reason == ""
