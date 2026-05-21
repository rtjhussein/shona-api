import json
import os
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from shona_api.editorial.models import ReviewState
from shona_api.lexicon.models import NounClass


class Command(BaseCommand):
    help = "Seed the Shona noun classes with structured concords, demonstratives, and plural relationships."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fixture",
            type=str,
            help="Path to the JSON fixture file containing noun classes.",
        )

    def handle(self, *args, **options):
        fixture_path = options.get("fixture")
        if not fixture_path:
            # Resolve default path relative to this file
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            fixture_path = os.path.join(base_dir, "lexicon", "fixtures", "seed_noun_classes.json")

        if not os.path.exists(fixture_path):
            raise CommandError(f"Fixture file not found at: {fixture_path}")

        self.stdout.write(f"Loading noun classes from: {fixture_path}")
        try:
            with open(fixture_path, "r", encoding="utf-8") as f:
                records = json.load(f)
        except Exception as e:
            raise CommandError(f"Failed to parse JSON fixture: {e}")

        created_count = 0
        updated_count = 0

        # Execute in a transaction-safe atomic block
        with transaction.atomic():
            # Pass 1: Insert or update base records (excluding the default_plural_class ForeignKey)
            for data in records:
                class_number = data["class_number"]
                defaults = {
                    "display_order": data.get("display_order", 0),
                    "label": data.get("label", ""),
                    "nominal_prefix": data.get("nominal_prefix", ""),
                    "prefix_allomorphs": data.get("prefix_allomorphs", []),
                    "subject_concord": data.get("subject_concord", ""),
                    "object_concord": data.get("object_concord", ""),
                    "possessive_concord": data.get("possessive_concord", ""),
                    "adjectival_concord": data.get("adjectival_concord", ""),
                    "relative_concord": data.get("relative_concord", ""),
                    "associative_concord": data.get("associative_concord", ""),
                    "demonstrative_proximal": data.get("demonstrative_proximal", ""),
                    "demonstrative_medial": data.get("demonstrative_medial", ""),
                    "demonstrative_distal": data.get("demonstrative_distal", ""),
                    "additional_concords": data.get("additional_concords", {}),
                    "dialect_overrides": data.get("dialect_overrides", {}),
                    "notes": data.get("notes", ""),
                    "review_state": ReviewState.PUBLISHED,
                    "provenance": data.get("provenance", {}),
                }

                noun_class, created = NounClass.objects.update_or_create(
                    class_number=class_number,
                    defaults=defaults,
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            self.stdout.write(
                f"Pass 1 complete: {created_count} noun classes created, {updated_count} updated."
            )

            # Pass 2: Resolve and set the self-referencing default_plural_class relations
            for data in records:
                class_number = data["class_number"]
                plural_number = data.get("default_plural_class_number")

                noun_class = NounClass.objects.get(class_number=class_number)

                if plural_number:
                    try:
                        plural_class = NounClass.objects.get(class_number=plural_number)
                        noun_class.default_plural_class = plural_class
                    except NounClass.DoesNotExist:
                        raise CommandError(
                            f"Referenced plural class '{plural_number}' for "
                            f"class '{class_number}' does not exist in database."
                        )
                else:
                    noun_class.default_plural_class = None

                noun_class.save()

            self.stdout.write(
                self.style.SUCCESS(
                    "Pass 2 complete: Successfully updated default plural class relationships."
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully seeded {len(records)} Shona noun classes."
                )
            )
