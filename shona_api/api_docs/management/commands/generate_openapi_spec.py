import json

from django.core.management.base import BaseCommand

from config.settings.base import BASE_DIR
from shona_api.api_docs.spec import build_openapi_spec


class Command(BaseCommand):
    help = "Generate the public OpenAPI specification."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default=str(BASE_DIR / "docs" / "openapi.json"),
            help="Path to write the generated OpenAPI JSON file.",
        )

    def handle(self, *args, **options):
        output_path = BASE_DIR / options["output"]
        if (BASE_DIR / options["output"]).is_absolute():
            output_path = BASE_DIR / options["output"]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(build_openapi_spec(), indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
        self.stdout.write(self.style.SUCCESS(f"Wrote {output_path}"))
