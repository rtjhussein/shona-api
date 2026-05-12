# Hannan Parser Fixtures

This directory contains the starter corpus for `source_hannan` parser tests.

## Files

- `entries.json` is the canonical fixture corpus.
- `schema.json` documents the intended JSON shape.
- `loader.py` exposes `load_hannan_fixtures()` and `iter_hannan_fixture_entries()` for future parser tests.

## Entry Contract

Each fixture entry stores:

- `raw_entry_text`: the compact dictionary entry text the parser should receive.
- `expected_parse`: manually annotated target fields for headword, tone, dialects, POS, noun or verb metadata, etymology/derivation markers, senses, examples, and cross-references.
- `coverage_tags`: notation features exercised by the entry.
- `provenance`: source key, source filename, entry locator, page reference, and extraction method.
- `annotation`: annotator, date, confidence, notes, and uncertainty records.

Keep the raw excerpts short and focused. The source PDF stays in `key_documents/` and must remain local-only.
