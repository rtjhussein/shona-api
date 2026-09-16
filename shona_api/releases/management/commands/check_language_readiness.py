"""Fail loudly when a deployment's data cannot be served by its code.

Two independent axes are checked, because both silently disable or corrupt
public behaviour when they drift:

1. The current ``DataRelease.rule_set_version`` must equal the rule set this
   checkout implements. A mismatch makes ``/v1/analyze`` and ``/v1/generate``
   return ``503 MORPHOLOGY_RULES_VERSION_UNSUPPORTED`` and degrades search
   enrichment to ``unavailable`` -- the endpoints are up but the language
   engine is switched off.
2. Stored phonology fields must come from the active grapheme inventory. After
   an inventory version bump, records still carrying the previous version
   served ``grapheme_count``/``syllables`` values computed by superseded rules.

Exit status is non-zero when either axis is unready, so the command is usable
as a deployment or CI gate.
"""

from django.core.management.base import BaseCommand

from shona_api.figurative_language.models import FigurativeExpression
from shona_api.lexicon.models import Form, Lemma
from shona_api.morphology.services import MORPHOLOGY_RULES_VERSION
from shona_api.phonology import DEFAULT_GRAPHEME_INVENTORY
from shona_api.releases.models import DataRelease


class Command(BaseCommand):
    help = (
        "Report whether the current release and stored phonology fields match "
        "the language rules this checkout implements."
    )

    def handle(self, *args, **options):
        failures: list[str] = []

        try:
            release = DataRelease.objects.current()
        except DataRelease.DoesNotExist:
            self.stderr.write(
                self.style.ERROR(
                    "No current data release is configured; protected language "
                    "endpoints return 503 CURRENT_RELEASE_NOT_CONFIGURED."
                )
            )
            self.stderr.write(
                "  fix: python manage.py ensure_current_release "
                '--version <version> --label "<label>"'
            )
            raise SystemExit(1)

        implemented = MORPHOLOGY_RULES_VERSION
        if release.rule_set_version == implemented:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Release {release.version} declares {release.rule_set_version}."
                )
            )
        else:
            failures.append(
                f"release {release.version} declares "
                f"rule_set_version={release.rule_set_version!r} but this checkout "
                f"implements {implemented!r}; /v1/analyze and /v1/generate "
                f"return 503 and search enrichment is unavailable"
            )
            self.stderr.write(
                "  fix: python manage.py ensure_current_release "
                f"--version {release.version} --label {release.label!r}"
            )

        inventory_version = DEFAULT_GRAPHEME_INVENTORY.version
        stale = {
            "lemma": Lemma.objects.exclude(
                phonology_inventory_version=inventory_version
            ).count(),
            "form": Form.objects.exclude(
                phonology_inventory_version=inventory_version
            ).count(),
            "figurative_expression": FigurativeExpression.objects.exclude(
                phonology_inventory_version=inventory_version
            ).count(),
        }
        stale_total = sum(stale.values())
        if stale_total == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Stored phonology fields use {inventory_version}."
                )
            )
        else:
            breakdown = ", ".join(
                f"{name}={count}" for name, count in stale.items() if count
            )
            failures.append(
                f"{stale_total} records still carry a superseded phonology "
                f"inventory ({breakdown}); their grapheme_count and syllables "
                f"were computed by older rules"
            )
            self.stderr.write("  fix: python manage.py recompute_phonology")

        if failures:
            self.stderr.write(
                self.style.ERROR(f"Language readiness: NOT READY ({len(failures)} issue(s))")
            )
            for failure in failures:
                self.stderr.write(f"  - {failure}")
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS("Language readiness: READY"))
