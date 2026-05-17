import json
import re
from dataclasses import dataclass
from pathlib import Path

from django.core.management.base import CommandError

from shona_api.editorial.models import ReviewState
from shona_api.parsers.hannan import parse_hannan_entry
from shona_api.sources.models import Source

from .models import ExtractionUnit


IMPORT_FORMAT_VERSION = "hannan-local-batch-v1"
HANNAN_SOURCE_KEY = "source_hannan"
RAW_EXTRACTION_METHOD = "local pdftotext -raw Hannan full-entry assembly"
ENTRY_HEADER_RE = re.compile(
    r"^\s*(?:\u2020)?[A-Za-z-][^\[]*?\s+\[[A-Z ;]+\]\s*"
    r"(?:K|Ko|M|Z|\(|\))*\s*"
    r"(?:adv|conj|demons|ideo|inter|near|n|oc|poss|pron|sfx|v|vi|vt|weak)\b"
)
NO_TONE_ENTRY_HEADER_RE = re.compile(
    r"^\s*(?:\u2020)?-?[A-Za-z][A-Za-z'’.-]*\s+"
    r"(?:K|Ko|M|Z|\(|\))+\s+"
    r"(?:adv|conj|demons|ideo|inter|near|n|oc|poss|pron|sfx|v|vi|vt|weak)\b"
)


@dataclass(frozen=True)
class HannanBatchImportResult:
    batch_id: str
    imported_count: int
    skipped_count: int
    dry_run: bool


@dataclass(frozen=True)
class HannanRawEntry:
    raw_entry_text: str
    start_line: int
    end_line: int

    @property
    def headword(self) -> str:
        return self.raw_entry_text.split(maxsplit=1)[0]


def import_hannan_batch_file(path, *, dry_run=False) -> HannanBatchImportResult:
    payload = _load_payload(path)
    batch_id = _required_string(payload, "batch_id")
    entries = payload.get("entries")
    if not isinstance(entries, list) or not entries:
        raise CommandError("Hannan batch must include a non-empty 'entries' list.")

    seen_locators = set()
    normalized_entries = []
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise CommandError(f"Entry {index} must be an object.")
        locator = _entry_locator(entry, index)
        if locator in seen_locators:
            raise CommandError(f"Duplicate locator in batch: {locator}")
        seen_locators.add(locator)
        raw_text = _entry_raw_text(entry, index)
        normalized_entries.append((index, locator, raw_text, entry))

    try:
        source = Source.objects.get(source_key=HANNAN_SOURCE_KEY)
    except Source.DoesNotExist as exc:
        raise CommandError(
            "source_hannan is missing. Run 'python manage.py seed_sources' first."
        ) from exc

    imported_count = 0
    skipped_count = 0
    for index, locator, raw_text, entry in normalized_entries:
        exists = ExtractionUnit.objects.filter(
            source=source,
            source_location_reference=locator,
        ).exists()
        if exists:
            skipped_count += 1
            continue

        parsed = parse_hannan_entry(raw_text)
        confidence = _entry_confidence(entry, parsed)
        provenance = {
            "batch_id": batch_id,
            "batch_entry_index": index,
            "import_format_version": IMPORT_FORMAT_VERSION,
            "source_filename": "hannan_dictionary.pdf",
            "extraction_method": payload.get(
                "extraction_method",
                "local pdftotext-backed Hannan batch",
            ),
        }
        provenance.update(entry.get("provenance") or {})

        if not dry_run:
            ExtractionUnit.objects.create_from_parser_output(
                source=source,
                source_location_reference=locator,
                raw_text=raw_text,
                parser_output=parsed,
                confidence=confidence,
                review_state=ReviewState.NEEDS_REVIEW,
                provenance=provenance,
            )
        imported_count += 1

    return HannanBatchImportResult(
        batch_id=batch_id,
        imported_count=imported_count,
        skipped_count=skipped_count,
        dry_run=dry_run,
    )


def _load_payload(path):
    try:
        content = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise CommandError(f"Could not read Hannan batch file: {path}") from exc

    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise CommandError(f"Hannan batch file is not valid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise CommandError("Hannan batch file must contain a JSON object.")
    version = payload.get("format_version")
    if version != IMPORT_FORMAT_VERSION:
        raise CommandError(
            f"Hannan batch format_version must be '{IMPORT_FORMAT_VERSION}'."
        )
    return payload


def _required_string(payload, field_name):
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise CommandError(f"Hannan batch requires a non-empty '{field_name}'.")
    return value.strip()


def _entry_locator(entry, index):
    locator = entry.get("locator") or entry.get("source_location_reference")
    if not isinstance(locator, str) or not locator.strip():
        raise CommandError(f"Entry {index} requires a non-empty locator.")
    return locator.strip()


def _entry_raw_text(entry, index):
    raw_text = entry.get("raw_entry_text")
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise CommandError(f"Entry {index} requires non-empty raw_entry_text.")
    return raw_text.strip()


def _entry_confidence(entry, parsed):
    if "confidence" in entry:
        confidence = entry["confidence"]
        if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            raise CommandError("Entry confidence must be a number from 0.0 to 1.0.")
        return float(confidence)
    if parsed.get("errors"):
        return 0.2
    if parsed.get("uncertainties"):
        return 0.75
    return 0.95


def assemble_hannan_raw_entries(
    raw_text: str,
    *,
    limit: int | None = None,
    start_line: int = 1,
):
    entries: list[HannanRawEntry] = []
    current_lines: list[str] = []
    current_start_line: int | None = None
    end_line = 0

    for line_number, line in enumerate(raw_text.splitlines(), start=1):
        if line_number < start_line:
            continue
        clean_line = _clean_raw_text_line(line)
        if not clean_line:
            continue

        if _is_raw_entry_header(clean_line):
            if current_lines and current_start_line is not None:
                entries.append(
                    HannanRawEntry(
                        raw_entry_text=_join_raw_entry_lines(current_lines),
                        start_line=current_start_line,
                        end_line=end_line,
                    )
                )
                if limit is not None and len(entries) >= limit:
                    return entries
            current_lines = [clean_line]
            current_start_line = line_number
        elif current_lines:
            current_lines.append(clean_line)

        if current_lines:
            end_line = line_number

    if current_lines and current_start_line is not None and (
        limit is None or len(entries) < limit
    ):
        entries.append(
            HannanRawEntry(
                raw_entry_text=_join_raw_entry_lines(current_lines),
                start_line=current_start_line,
                end_line=end_line,
            )
        )

    return entries


def build_hannan_batch_payload(
    raw_text: str,
    *,
    batch_id: str,
    limit: int = 25,
    start_line: int = 1,
    source_cache_name: str = "hannan_dictionary.raw.txt",
) -> dict[str, object]:
    entries: list[dict[str, object]] = []
    for raw_entry in assemble_hannan_raw_entries(raw_text, start_line=start_line):
        if _looks_like_truncated_species_entry(raw_entry.raw_entry_text):
            continue
        parsed = parse_hannan_entry(raw_entry.raw_entry_text)
        if parsed.get("errors"):
            continue
        entries.append(
            {
                "locator": _raw_entry_locator(source_cache_name, raw_entry),
                "raw_entry_text": raw_entry.raw_entry_text,
                "confidence": _entry_confidence({}, parsed),
                "provenance": {
                    "raw_start_line": raw_entry.start_line,
                    "raw_end_line": raw_entry.end_line,
                    "source_cache_name": source_cache_name,
                    "source_text_format": "pdftotext -raw",
                    "headword": parsed.get("headword", raw_entry.headword),
                },
            }
        )
        if len(entries) >= limit:
            break

    return {
        "format_version": IMPORT_FORMAT_VERSION,
        "batch_id": batch_id,
        "extraction_method": RAW_EXTRACTION_METHOD,
        "entries": entries,
    }


def _clean_raw_text_line(line: str) -> str:
    return (
        line.replace("â€ ", "\u2020")
        .replace("\u00ad", "")
        .replace("\u2010", "-")
        .replace("\u2011", "-")
        .strip()
    )


def _is_raw_entry_header(line: str) -> bool:
    return bool(ENTRY_HEADER_RE.match(line) or NO_TONE_ENTRY_HEADER_RE.match(line))


def _join_raw_entry_lines(lines: list[str]) -> str:
    return " ".join(" ".join(lines).split())


def _looks_like_truncated_species_entry(raw_entry_text: str) -> bool:
    return bool(re.search(r"\bsp\s*$", raw_entry_text.strip()))


def _raw_entry_locator(source_cache_name: str, raw_entry: HannanRawEntry) -> str:
    safe_headword = re.sub(r"[^A-Za-z0-9-]+", "-", raw_entry.headword).strip("-")
    return (
        f"{source_cache_name}:lines-{raw_entry.start_line}-{raw_entry.end_line}:"
        f"entry:{safe_headword}"
    )
