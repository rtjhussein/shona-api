# Ox Vision Sweep — Hannan Dictionary Population

How the Shona-English section of the Hannan dictionary was fully populated
(2026-08-25) using vision-based extraction, and how to re-run any part of it.

## Result

- Scope: Shona-English main section (book pages 1-757 = PDF 25-781) plus the
  Shona ADDENDUM (book 997-1014 = PDF 1021-1038). The English-Shona index
  (PDF 783-1020) is out of scope by design.
- Coverage: 775/775 scope pages extracted; zero gaps.
- Sources: pre-existing GPT-5.5 batch JSONL (101 files, ~15k entries, book
  1-292 + 389-390) plus ~28k entries extracted by parallel vision agents
  (parser tag `ox-alpha-vision`) for the remaining pages.
- 188 units remain `needs_review` by design: entries extracted at confidence
  < 1.0 (faint print, scan-cropped edges, reconstructed glyphs) are held for
  editorial review instead of auto-published.

## Pipeline

1. **Render** page images at 220 dpi:
   `python tools/ox_sweep/render_range.py <pdf_start> <pdf_end>`
   -> `local_batches/render_pages/hannan-pdf-page-XXXX.png`
2. **Extract** one chunk (5-10 pages) per agent against the chunk brief
   (image = source of truth, two-column OCR layer `local_source_cache/`
   `hannan_dictionary.txt` as cross-check, honest provenance tags). Each
   chunk writes `local_batches/ox-sweep/out/oxv1_book_<SSSS>-<EEEE>.jsonl`
   in the `hannan-gpt-jsonl-v3` schema and MUST pass:
   `python tools/ox_sweep/validate.py <out.jsonl> <book_start> <book_end>`
3. **Land** chunks (merge boundary continuation sidecars -> import via
   `import_gpt_5_5_parsed` -> auto-approve confidence-1.0 parsed units ->
   publish -> assert published == approved):
   `python tools/ox_sweep/land_wave.py oxv1`
   The lander skips chunks whose `<BATCH-ID>: landed` line is already in
   `local_batches/ox-sweep/land_oxv1.log`, so it is safe to relaunch after a
   timeout.
4. **Gate** the corpus: `python manage.py qa_published_corpus --format json`
   replays published records through search and morphology.
5. **Ledger**: `python tools/ox_sweep/coverage.py` prints covered page
   ranges, gaps, and unit states.

## Conventions that matter

- `book_page = pdf_page - 24`; locators are `hannan:page_<BOOK>:entry_<NNN>:<slug>`
  with per-page sequence restart at 001.
- Tone brackets: single pattern -> `tone_pattern` + one record; dialect-scoped
  (`[H KM; LHLH Z]`) -> `tone_pattern: null` + one record per alternative;
  patterns are bare H/L runs (space-separated groups allowed for multi-word
  headwords).
- Cross-page entries: a fragment at the top of a chunk's first page is written
  to a sidecar JSON (merged centrally by the lander); cut-offs at a chunk's
  last page are completed using the next page's image.
- No headword-level dedupe anywhere (Hannan legitimately repeats headwords on
  one page, e.g. two distinct `bvambu` entries on book page 33).

## Key incident handled during the sweep

The original May-June GPT batches were never imported and mixed two locator
conventions (1,676 rows used PDF pages in locators). `normalize_batches.py`
rebuilt those locators from each row's `actual_page_number`, re-sequenced
per-page entry numbers for fresh pages, and resolved the two multi-covered
pages by file supersession — WITHOUT headword-level dedupe.
