from django.core.management.base import BaseCommand

from shona_api.releases.models import DataRelease


class Command(BaseCommand):
    help = "Create or update a DataRelease and make it the current release."

    def create_parser(self, prog_name, subcommand, **kwargs):
        kwargs.setdefault("conflict_handler", "resolve")
        return super().create_parser(prog_name, subcommand, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument(
            "--version",
            required=True,
            help="Stable release identifier exposed in public API envelopes.",
        )
        parser.add_argument(
            "--label",
            required=True,
            help="Human-readable release label.",
        )
        parser.add_argument(
            "--rule-set-version",
            dest="rule_set_version",
            required=True,
            help="Morphology/phonology rule-set version exposed by this release.",
        )

    def handle(self, *args, **options):
        release, created = DataRelease.objects.update_or_create(
            version=options["version"],
            defaults={
                "label": options["label"],
                "rule_set_version": options["rule_set_version"],
                "is_current": True,
            },
        )

        action = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} current data release {release.version} "
                f"({release.rule_set_version})."
            )
        )
