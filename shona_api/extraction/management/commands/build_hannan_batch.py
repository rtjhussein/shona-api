import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from shona_api.extraction.hannan_import import build_hannan_batch_payload


class Command(BaseCommand):
    help = (
        "LEGACY: build a small local Hannan batch JSON file from pdftotext "
        "-raw output. Prefer import_hannan_segments for dashboard JSONL."
    )

    def add_arguments(self, parser):
        parser.add_argument("raw_text_path")
        parser.add_argument("output_path")
        parser.add_argument("--batch-id", required=True)
        parser.add_argument("--limit", type=int, default=25)
        parser.add_argument("--start-line", type=int, default=1)

    def handle(self, *args, **options):
        raw_path = Path(options["raw_text_path"])
        output_path = Path(options["output_path"])

        if options["limit"] < 1:
            raise CommandError("--limit must be at least 1.")
        if options["start_line"] < 1:
            raise CommandError("--start-line must be at least 1.")

        try:
            raw_text = raw_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raw_text = raw_path.read_text(encoding="cp1252", errors="replace")
        except OSError as exc:
            raise CommandError(f"Could not read raw text file: {raw_path}") from exc

        payload = build_hannan_batch_payload(
            raw_text,
            batch_id=options["batch_id"],
            limit=options["limit"],
            start_line=options["start_line"],
            source_cache_name=raw_path.name,
        )
        if not payload["entries"]:
            raise CommandError("No parseable full entries were assembled.")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Wrote {len(payload['entries'])} entries to {output_path}."
            )
        )
