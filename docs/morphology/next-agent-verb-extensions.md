# Fresh-agent assignment: complete and correct verb extensions

You are implementing the next language-product milestone for Shona API.
The user wants the API's linguistic capabilities completed before deployment, billing or infrastructure work.
The supervising agent has already assessed morphology and selected this implementation job.
Read `docs/morphology/completeness-assessment-2026-09-08.md` first, then verify its findings against your checkout.
Deliver working code and evidence, not another general assessment.

## Goal

Make the existing verb-extension functionality source-grounded, internally consistent and accurately documented.
Complete the already-exposed extension families with explicit supported boundaries, correcting grammatical classification and rejecting unsupported styles/combinations.
Do not implement new finite tenses, noun generation, deployment, billing or bulk data publication in this job.

## Project context

Repository: `C:/Users/user/Documents/Projects/shona-api`.
Stack: Django, Django REST Framework and Python 3.12+.
Read applicable `AGENTS.md`, `CONTEXT.md`, and the user's durable engineering preferences before implementation.
Use CodeGraph first only if a `.codegraph` directory exists in your checkout.
The original assessment checkout was clean; check current status and preserve unrelated work.
Use a `codex/` branch for this task.
The direction is approved for implementation by this assignment; resolve ordinary implementation choices yourself.
Follow source-review requirements honestly and never label your own extraction as independent human review.

The public morphology endpoints are `POST /v1/analyze` and `POST /v1/generate`.
They require API-key authentication and a current `DataRelease`.
Generation currently supports only `generation_type: verb_form`, `tense_aspect: present`, positive/negative polarity, person or noun-class subjects, optional object concords, and extensions.
Analysis supports the present constructions plus simple ku-infinitives.
Person and noun-class markers are combined with reviewed lexical verb stems.
The generator and analyzer share `shona_api/morphology/services.py`, but extension application and decomposition are separate functions.

## Read these files

- `shona_api/morphology/services.py` and `views.py`
- `tests/test_morphology_api.py` and `tests/test_morphology_rule_cards.py`
- `tests/fixtures/morphology/real_data_present_verbs.json`
- `docs/morphology/rules/README.md` and `rules/cards/*.json`
- `docs/morphology/generate_endpoint.md` and `real_data_regression_corpus.md`
- `shona_api/api_docs/spec.py` and relevant API-doc tests
- `shona_api/lexicon/search.py`, the morphology enrichment in `lexicon/views.py`, and relevant search/corpus tests
- `key_documents/prd_v5.md`, especially sections 8.1-8.5, for product intent
- The local grammar PDF described below for linguistic evidence

The PRD and previous test expectations are not substitutes for source evidence.

## Source evidence already verified

`key_documents/fortune_grammatical_constructions.pdf` is *Shona Grammatical Constructions, Volume 1*, not the 1955 *Analytical Grammar* cited by the current extension card.
Read and visually inspect PDF page 33, printed page 21, section 2.10.2.3.3, and adjacent pages as needed.
This section distinguishes repetitive `-urur-/-oror-` from reversive and supplies reversive allomorphs `-anur-/-enur-/-inur-/-onor-/-unur-` with examples.
It also distinguishes causative classes and describes radical-specific changes.
PDF pages 90-91, printed 78-79, provide class-15 infinitive context, but fuller infinitive construction support is a later job.
Do not invent locators in a missing volume, upload copyrighted source PDFs, or bulk-copy source prose into committed artifacts.

## Reproduce before fixing

Use isolated test data and routed API requests, with authentication and a current release.
The assessment's existing morphology/card suite passed all 29 tests in an isolated in-memory SQLite database, yet these additional requests exposed gaps:

1. Create a published `-ambura` verb-stem lemma; generate first-person singular positive present with `["causative"]`.
   Generation returns `ndinoamburisa` with HTTP 200; analyzing that surface returns HTTP 422.
   `_decompose_stem` strips beyond the intended lexical root because its ending resembles another extension.
2. Create `-kora`; generate with `[{"type":"reversive","style":"long"}]`.
   Generation returns `ndinokororora`, but analysis returns HTTP 422.
   This also implicates grammatical classification; do not preserve an incorrect meaning solely to satisfy round-trip tests.
3. Create `-pfeka`; generate with `[{"type":"reversive","style":"long_unur"}]`.
   The output is `ndinopfekunura`, whereas the verified source gives the radical relationship `pfek` to `pfekenur`.
4. Create `-buda`; request `[{"type":"causative","style":"nonsense"}]`.
   The API returns HTTP 200 and the default causative rather than a structured error.

All generation examples above use `generation_type: verb_form`, subject `{type: person, person: first, number: singular}`, `tense_aspect: present` and `polarity: positive`.
Treat these as reproduction fixtures; independently justify linguistic expected outputs from sources.

## Required implementation

1. Reconcile extension taxonomy and evidence.
   Provide accurate cards/fixtures for every extension family and style that remains supported, including restrictions and counterexamples.
   Separate repetitive and reversive behaviour rather than silently treating them as synonyms.
   Document how corrected names or legacy styles behave; do not silently preserve a wrong semantic label.
   Preserve useful existing support where evidence allows it, and make genuinely unverified cases explicit.
2. Correct extension allomorph selection and lexical restrictions.
   Cover the source-supported vowel conditions, short roots and relevant causative changes.
   Do not treat all suffix choices as freely productive for every lemma.
   Validate extension order, repetition and combinations within the supported source-backed boundary.
3. Replace greedy terminal stripping with bounded, lexicon-aware candidate handling.
   Recognize a valid lexical stem at intermediate boundaries instead of stripping it away.
   Account for exact derived lemmas, homographs and genuinely ambiguous derivations without arbitrary first-row selection.
   Retain the existing analyses-list contract, deterministic ordering and sensible resource bounds.
4. Make request validation strict for extension types, styles and combinations.
   Invalid styles must return a documented structured 422 error, not silently choose a default.
   Do not accept unexplained feature values or combinations that the engine cannot faithfully implement.
5. Make analyzer and generator behaviour consistent across the existing positive/negative present constructions, object-concord variants and supported infinitive analysis.
   A supported generated form should recover the originating lemma and compatible features among its analyses, allowing legitimate ambiguity.
   Round-trip agreement alone is insufficient: both sides must also satisfy independently sourced expectations.
6. Align response warnings, limitations, rule attribution, documentation and OpenAPI with actual support.
   Preserve existing valid clients and the v1 envelope; document deliberate correctness changes.
   Apply the project's rule-set versioning convention to changed behaviour and explain activation without mutating the user's live data.
   Regenerate `docs/openapi.json` through its owning command if its source changes.

Prefer a simple shared rule representation where it prevents analyzer/generator drift.
Do not turn this task into a generic grammar-engine rewrite.

## Acceptance evidence

- API-level regression tests reproduce the confirmed failures before changes and prove their resolution afterwards.
- Fixture expectations cite the actual local source and distinguish source-attested examples from constructed combinations.
- Tests exercise the supported families and allomorph conditions, extension-looking root endings, malformed styles, unsupported chains, and lexical ambiguity.
- Positive/negative present and object-concord paths have relevant extension regression coverage.
- Search morphology enrichment still works with corrected derivations.
- Existing valid morphology behaviour remains covered; changed incorrect expectations have explicit source-backed explanations.
- Run the full suite using safe isolated settings and report failures honestly, including unrelated or backend-specific limitations.
- Use the evidence-validation skill for closeout and risk-rate the changes.
- Do not modify the live corpus, approve extraction batches, or alter live release records as a testing shortcut.

## Deliverable

Return the implementation, updated fixtures/cards/docs and a concise closeout explaining what customers can now analyze/generate reliably.
List files changed, commands and results, representative before/after API examples, grammar-source locators, remaining unsupported cases, compatibility decisions and review hotspots.
Update the assessment's relevant coverage notes to reflect the final implementation.
The supervisor should be able to verify the result without redoing your exploration.
Do not claim morphology as a whole is finished: tense/aspect, broader infinitives, nominal generation and the full independently annotated benchmark remain subsequent milestones.
