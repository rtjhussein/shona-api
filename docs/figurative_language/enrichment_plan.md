# Figurative Language Enrichment Plan

This plan defines how `source_shona_yedu` and `source_tsumo_tsika` should feed future figurative-language enrichment without treating high-volume material as automatically canonical. It is an operational guide for later import and review work; it does not implement ingestion.

## Goals

- Ingest proverb and idiom material as reviewable candidates.
- Preserve source provenance, extraction uncertainty, and editorial decisions.
- Use `source_tsumo_tsika` for structured cultural and thematic enrichment where it applies.
- Use `source_shona_yedu` as high-volume candidate material, not as final authority.
- Leave an explicit lane for later `madunhurirwa` work.

## Source Roles

| Source key | Role in this lane | Default authority |
|---|---|---|
| `source_tsumo_tsika` | Structured enrichment for proverb meaning, proverb-to-culture linkage, cultural themes, and pedagogy | Trusted for reviewed cultural/theme enrichment, especially for `tsumo` |
| `source_shona_yedu` | High-volume candidates for `tsumo`, `madimikira`, future `madunhurirwa`, culturally marked lexical terms, and compact lists | Candidate source only until deduped, conflict-checked, and reviewed |

Both sources remain enrichment sources. They do not override core lexical or grammatical authorities for lemma facts, morphology, orthography, or grammar.

## Candidate Import Strategy

Future import work should create candidate rows before canonical figurative-language records. A batch from either source should be traceable, repeatable, and safe to reject without losing the raw observation.

Each imported candidate should capture:

| Field | Purpose |
|---|---|
| `source_key` | One of `source_shona_yedu` or `source_tsumo_tsika` |
| `source_locator` | Page, section, heading, or other stable location available from the local source |
| `raw_text` | The expression exactly as captured before normalization |
| `normalized_text` | Search/dedupe form after conservative whitespace, punctuation, and casing cleanup |
| `candidate_type` | `tsumo`, `madimikira`, uncertain, or a reserved future type such as `madunhurirwa` |
| `meaning_or_note` | Source-provided meaning, explanation, translation, or interpretation when present |
| `theme_suggestions` | Candidate cultural, educational, moral, or social themes |
| `linked_lemma_suggestions` | Lemmas that may be linked after review |
| `extraction_method` | Manual entry, digitized text extraction, table extraction, or other method |
| `confidence` | Import confidence before editorial review |
| `review_status` | Pending, dedupe-needed, conflict, promoted, rejected, or deferred |

Recommended batch flow:

1. Capture a bounded source batch with provenance.
2. Normalize text only enough for search and duplicate detection.
3. Classify the candidate as `tsumo`, `madimikira`, uncertain, or reserved future subtype.
4. Run dedupe and conflict checks against existing canonical records and pending candidates.
5. Attach theme suggestions from `source_tsumo_tsika` where applicable.
6. Send the candidate to editorial review before promotion.

High-volume material from `source_shona_yedu` must stop at candidate status until a reviewer promotes it. No import job should publish those candidates directly as canonical records.

## Authority Policy

For figurative-language enrichment, use this authority order:

1. Existing reviewed canonical figurative-language records.
2. Reviewed `source_tsumo_tsika` enrichment for proverb interpretation, cultural linkage, theme validation, and pedagogy.
3. `source_shona_yedu` candidates after dedupe, conflict checks, and editorial review.
4. Unreviewed imported candidates, which must remain unpublished.

When a candidate makes lexical, morphological, orthographic, or grammatical claims, defer to the relevant backbone source policy in `docs/sources/source_strategy.md`. Figurative enrichment may suggest links to lemmas, but it should not redefine lemma forms, noun classes, tone, or grammatical behavior.

If two enrichment sources disagree, keep both source references on the candidate, mark the conflict, and require editorial resolution before promotion. A reviewer may approve one interpretation, merge compatible notes, or publish with an uncertainty note if the future model supports that.

## Dedupe Guidance

Dedupe should compare candidates before editorial review and again before promotion.

Use at least these matching passes:

- Exact normalized text match.
- Punctuation-insensitive and spacing-insensitive match.
- Common variant match where word order, particles, or orthographic variants are known to be equivalent.
- Meaning/theme proximity check for expressions that differ in text but appear to carry the same proverb or idiom.
- Source-collision check, where the same expression appears in both `source_shona_yedu` and `source_tsumo_tsika`.

Dedupe output should not automatically merge records. It should present a reviewer with candidate links such as duplicate-of, variant-of, related-to, or conflict-with. When promoted, the canonical record should preserve all supporting provenance rather than discarding the duplicate source trail.

## Theme Enrichment Guidance

Themes should help browsing, pedagogy, and cultural explanation without flattening a figurative expression into one rigid moral.

Preferred theme inputs:

- Structured theme or interpretation notes from reviewed `source_tsumo_tsika` material.
- Reviewer-confirmed themes derived from `source_shona_yedu` candidates.
- Curriculum-aware tags from the source strategy where later issues connect figurative language to educational surfaces.

Theme review should distinguish:

- Source-stated themes: directly supported by a source note.
- Reviewer-derived themes: inferred during review and traceable to the reviewer decision.
- Browse tags: product-facing grouping labels that may be broader than a source phrase.

Theme enrichment should allow multiple themes per expression and should keep culturally specific notes separate from generic English glosses. If a theme is uncertain, keep it as a suggestion rather than publishing it as canonical metadata.

## Tsumo And Madimikira Handling

`tsumo` candidates should prioritize proverb text, source meaning, cultural interpretation, and theme linkage. `source_tsumo_tsika` is especially useful here because it is structured around proverb culture and pedagogy.

`madimikira` candidates should prioritize idiomatic expression text, idiomatic meaning, usage note, and linked lemma suggestions. `source_shona_yedu` may provide useful volume, but each idiom still needs subtype confirmation and editorial review before promotion.

For both subtypes, candidate import should preserve uncertainty rather than forcing a record into the wrong bucket. Ambiguous material may stay in an uncertain review queue until the figurative-language model and editorial policy can classify it responsibly.

## Future Madunhurirwa Lane

`madunhurirwa` is not part of this issue's implementation scope, but candidate handling should reserve it as a future subtype. If `source_shona_yedu` contains material that appears to belong in this lane, import it only as a reserved future candidate with no public canonical promotion.

Future `madunhurirwa` work should define:

- subtype-specific fields and presentation needs
- review criteria for separating it from `tsumo` and `madimikira`
- whether `source_tsumo_tsika` contributes any useful themes or cultural notes
- migration or promotion rules for candidates collected before the subtype is active

Until that lane exists, `madunhurirwa` candidates should remain deferred, source-linked, and excluded from public figurative-language endpoints.

## Out Of Scope

- Building import commands, parsers, admin actions, API endpoints, or migrations.
- Automatically trusting all enrichment content from either source.
- Uploading local-only source documents to git.
- Making `source_shona_yedu` a canonical authority for high-volume proverb or idiom content.
