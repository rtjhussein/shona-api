# Hannan Fixture Annotation Guide

The Hannan fixture corpus lives in `tests/fixtures/hannan/entries.json`. It is a hand-verified starter set for parser development, not the parser implementation and not a full transcription of the source.

## Goals

- Preserve the exact compact entry text future parser tests should parse.
- Record manually expected fields without hiding uncertainty.
- Cover notation patterns before parser code exists: tone brackets, dialect markers, POS abbreviations, noun class and plural notation, transitivity, sense boundaries, cross-references, examples, etymology, derivation markers, comparative markers, and homographs.

## Annotation Rules

- Use `fixture_format_version: hannan-fixture-v1` until a deliberate migration is needed.
- Keep each `raw_entry_text` to one dictionary entry or one intentionally selected homograph.
- Normalize only obvious extraction artifacts such as line-wrap hyphenation; record that in `annotation.uncertainties` or `annotation.notes`.
- Preserve stem hyphens in `expected_parse.headword`; put the searchable form in `normalized_headword`.
- Split compact dialect strings into ordered dialect codes: `K`, `Ko`, `M`, `Z`, and any qualified form such as `Ko(B)` when it appears.
- Put broad entry dialect markers in `expected_parse.dialects`; put narrower sense markers in each sense's `dialects`.
- Record tone brackets without square brackets in `tone_pattern`, for example `L`, `HH`, or `HHHL`.
- For nouns, record class numbers in `noun.classes` and plural notation in `noun.plural_prefixes`.
- For verbs, record transitivity/POS shorthand in `verb.entry_grammar` and, where the source narrows it, in `verb.transitivity_by_sense`.
- Record `cp` references as `cross_references` with `type: cp`, a `target`, and any dialect marker attached to the reference.
- Record `<` source markers in `etymology`; record `>` target forms in `derived_forms`.
- Attach examples to the nearest clear sense. If the source position is ambiguous, keep the attachment useful for parser tests and add an uncertainty note.
- Never silently promote a guess to a high-confidence annotation.

## Provenance Requirements

Every entry must include:

- `source_key: source_hannan`
- `source_filename: hannan_dictionary.pdf`
- `entry_locator`, usually the headword plus a qualifier for homographs
- `page_reference`, preferably both PDF page and printed page when known
- `extraction_method`, such as `manual annotation from pdftotext -layout output`

## Extending The Corpus

When adding entries, prefer samples that increase parser coverage rather than many near-duplicates. Useful next additions include irregular dialect qualifiers, coarse/deprecatory usage labels, variants introduced by `see`, more homographs with distinct tone patterns, proverb markers, species markers, and entries split across columns.

After editing fixtures or docs, run:

```bash
python -m pytest tests/test_hannan_fixtures.py
```
