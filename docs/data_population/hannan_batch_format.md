# Hannan Local Batch Format

> Legacy pilot format. The current Hannan extraction path is dashboard JSONL
> from `hannan-parser-dashboard` imported with `import_hannan_segments`.
> Keep this format only for historical pilot batches.

Hannan source PDFs and generated text caches are local-only. Do not commit them.

Use `local_source_cache/` for generated `pdftotext` output and `local_batches/`
for working batch JSON files. Both paths are ignored by git.

## Format

```json
{
  "format_version": "hannan-local-batch-v1",
  "batch_id": "HANNAN-PILOT-001",
  "extraction_method": "local pdftotext-backed Hannan batch",
  "entries": [
    {
      "locator": "hannan_dictionary.pdf:p.50:entry:-bonya",
      "raw_entry_text": "-bonya [L] K v i Water; discharge (of eyes).",
      "confidence": 0.9,
      "provenance": {
        "page_reference": "PDF page 50, printed page 26"
      }
    }
  ]
}
```

## Commands

Prefer dashboard segment JSONL for current work:

```powershell
python manage.py import_hannan_segments path\to\approved_segments.jsonl --batch-id SEG-2026-001 --dry-run
python manage.py import_hannan_segments path\to\approved_segments.jsonl --batch-id SEG-2026-001
```

For the Gemini visual-OCR workflow and staff UI, see
`docs/data_population/hannan_ingestion_dashboard.md`.

Only after API review approves imported segments should structural conversion run:

```powershell
python manage.py structure_extraction_units --batch-id SEG-2026-001
```

Build a local batch from full entries assembled out of `pdftotext -raw` output:

```powershell
python manage.py build_hannan_batch local_source_cache\hannan_dictionary.raw.txt local_batches\HANNAN-PILOT-001.hannan-batch.json --batch-id HANNAN-PILOT-001 --limit 25 --start-line 1168
```

Validate without writing records:

```powershell
python manage.py import_hannan_batch local_batches\HANNAN-PILOT-001.hannan-batch.json --dry-run
```

Import candidates as `ExtractionUnit` rows:

```powershell
python manage.py import_hannan_batch local_batches\HANNAN-PILOT-001.hannan-batch.json
```

Report batch quality:

```powershell
python manage.py report_hannan_batch --batch-id HANNAN-PILOT-001
```

After editorial review marks candidates as `approved`, publish the approved
records:

```powershell
python manage.py publish_hannan_batch --batch-id HANNAN-PILOT-001
```

## Rules

- Keep each entry to one compact Hannan dictionary entry.
- Build batches from full raw entries, not physical PDF text lines.
- Preserve source punctuation and stem hyphens in `raw_entry_text`.
- Use stable locators that can be traced back to the PDF/text cache.
- Duplicate locators inside one batch fail validation.
- Existing database records with the same source locator are skipped safely.
- Imports create review candidates only; they do not publish canonical records.
