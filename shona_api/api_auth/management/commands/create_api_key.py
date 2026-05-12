from django.core.management.base import BaseCommand

from shona_api.api_auth.models import APIKey


class Command(BaseCommand):
    help = "Create an API key and print the raw key once."

    def add_arguments(self, parser):
        parser.add_argument("name")
        parser.add_argument(
            "--plan",
            choices=[choice.value for choice in APIKey.Plan],
            default=APIKey.Plan.DEVELOPER,
        )
        parser.add_argument("--rate-limit-per-minute", type=int)

    def handle(self, *args, **options):
        api_key, raw_key = APIKey.objects.create_key(
            name=options["name"],
            plan=options["plan"],
            rate_limit_per_minute=options["rate_limit_per_minute"],
        )

        self.stdout.write(self.style.SUCCESS(f"Created API key {api_key.prefix}"))
        self.stdout.write(f"Name: {api_key.name}")
        self.stdout.write(f"Plan: {api_key.plan}")
        self.stdout.write(f"Rate limit per minute: {api_key.rate_limit_per_minute}")
        self.stdout.write(f"Raw key: {raw_key}")
        self.stdout.write("Store this raw key now; only its hash is saved.")
