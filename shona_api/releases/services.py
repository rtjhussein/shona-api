from dataclasses import dataclass

from .models import DataRelease


class CurrentReleaseNotFound(RuntimeError):
    pass


@dataclass(frozen=True)
class PublishGuardResult:
    is_ready: bool
    reason: str = ""


def get_current_release() -> DataRelease:
    try:
        return DataRelease.objects.current()
    except DataRelease.DoesNotExist as exc:
        raise CurrentReleaseNotFound("No current data release is configured.") from exc


def get_current_release_metadata() -> dict[str, str]:
    release = get_current_release()
    return {
        "release_version": release.version,
        "rule_set_version": release.rule_set_version,
    }


def ensure_current_release_available() -> PublishGuardResult:
    try:
        get_current_release()
    except CurrentReleaseNotFound:
        return PublishGuardResult(
            is_ready=False,
            reason="current_release_missing",
        )
    return PublishGuardResult(is_ready=True)
