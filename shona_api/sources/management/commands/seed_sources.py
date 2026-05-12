from django.core.management.base import BaseCommand

from shona_api.sources.models import Source
from shona_api.sources.registry import SOURCE_REGISTRY


class Command(BaseCommand):
    help = "Seed the current source registry records."

    def handle(self, *args, **options):
        created = 0
        updated = 0

        for source_data in SOURCE_REGISTRY:
            source_key = source_data["source_key"]
            defaults = {
                key: value for key, value in source_data.items() if key != "source_key"
            }
            _, was_created = Source.objects.update_or_create(
                source_key=source_key,
                defaults=defaults,
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded source registry: {created} created, {updated} updated."
            )
        )
