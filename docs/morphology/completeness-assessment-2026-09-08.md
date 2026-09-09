# Morphology completeness assessment

Assessed on 2026-09-08 against the current checkout, the product requirements, existing API tests, and selected pages of the local Fortune PDF.
This is an implementation and evidence assessment, not independent linguistic certification of the entire engine.
No application source or project data was changed.

## Decision

The next implementation job is to complete and correct the existing verb-extension subsystem, with source-backed expectations and consistent analysis/generation.
Do this before widening tense/aspect support.
Existing extension code is broader than the documentation suggests, but source interpretation, segmentation, validation, and testing are not yet dependable enough to build on.

## Completion target and current coverage

The product already defines a morphology target in `key_documents/prd_v5.md`, sections 8.1-8.5.
Treat this as product intent, not grammatical evidence: its extension terminology and examples must themselves be checked against the grammar sources.

| Capability | Current implementation | Remaining work |
| --- | --- | --- |
| Positive present verbs | Analysis and generation using subject + no + optional object + stem | Validate independently across the promised person/class and lexical coverage; current `present` label is less specific than the PRD's `present_habitual` |
| Negative present verbs | Analysis and generation, final-vowel mutation and class 1/1a handling | Validate exceptions, vowel contact, object combinations and extension interactions |
| Subject/object concords | Hard-coded person markers and reviewed noun-class records | Prove all promised classes and ambiguous readings; stored concord fields alone do not prove coverage |
| Infinitives | Simple ku-prefixed analysis, including extension handling through the common helper | No infinitive generation; no explicit object/reflexive/negative infinitive construction support |
| Verb extensions | Passive, causative (incl. dz/ts styles), applicative, neuter, reciprocal, reversive (vowel-copy long + short) and repetitive labels | Implemented under morphology-rules-v3 (2026-09-08): repetitive split from reversive; reversive vowel copy (-anur-/-enur-/-inur-/-onor-/-unur-) per Vol. 1 section 2.10.2.3.3; strict style/order/combination validation with 422s; lexicon-aware bounded decomposition (exact + homograph + derivational readings); reciprocal/short-reversive/ts retained explicitly pending Volume 2; intensive/extensive/perfective remain unimplemented |
| Past/future and other tense/aspect distinctions | Generator explicitly accepts only `present`; analyzer has present and simple infinitive paths | PRD names simple/recent/hodiernal/remote past, future and subjunctive; confirm distinctions and sources before implementation |
| Mood | No explicit imperative/subjunctive construction support | Implement source-backed mood behaviour rather than accepting ignored feature fields |
| Noun morphology | Class and concord data structures exist | Public generator accepts only `verb_form`; plural pairs, locatives, diminutives and augmentatives are not implemented there |
| Tone | Phonology metadata is returned; morphology explicitly excludes tone | Separate attested lexical tone from future inflectional tone generation |
| Rule evidence/versioning | Rule IDs and supplied release rule-set strings are returned | Only two rule-card files exist; several cited rule IDs lack cards, and a returned version string does not select a historical implementation |
| Accuracy benchmark | Small Hannan-based present corpus and extension examples in tests | No required 100-form, independently annotated FSI benchmark was found in the inspected fixtures; no measured 90% linguistic-accuracy claim is justified |

The absence of a benchmark file in inspected fixtures is not proof that no private annotation work exists elsewhere.
This assessment does not claim that every category missing from the public morphology endpoints is absent from all lexical records.

## Validation performed

Ran `tests/test_morphology_api.py` and `tests/test_morphology_rule_cards.py`: **29 passed in 5.28 seconds**.
Used an isolated in-memory SQLite settings module with migrations and the existing in-memory test cache, avoiding the project's normal database and reusable test database.
Additional reproductions used Django's HTTP test client against `/v1/generate` and `/v1/analyze`, with an API key, current release and published lemma fixtures.
These exercise the routed API, authentication, validation and ORM; they are not external-server or production-stack tests.

## Confirmed gaps

### 1. Generated forms can be rejected by the analyzer

With a published `-ambura` lemma, first-person singular positive present generation and `extensions: ["causative"]` return HTTP 200 and `ndinoamburisa`.
Submitting that returned surface to `/v1/analyze` returns HTTP 422 `ANALYSIS_UNSUPPORTED`.
With a published `-kora` lemma and `extensions: [{"type": "reversive", "style": "long"}]`, generation returns `ndinokororora`, but analysis again returns HTTP 422.
These examples establish API inconsistency, not independent certification that either generated surface is linguistically correct.

In `shona_api/morphology/services.py`, `_decompose_stem` strips every suffix-looking ending before attempting a lexical lookup.
For example, after removing `is` from `amburisa`, it also removes `ur` from the actual fixture stem `ambura`.
The algorithm needs bounded candidate exploration at valid stem boundaries, with grammar constraints and lexical evidence.
Exact derived lemmas and homographs also need explicit ambiguity treatment: `_get_reviewed_verb_stem` currently selects `.first()`, and exact lookup bypasses derivational alternatives.

### 2. Source and implementation disagree about extension meaning and form

The available `key_documents/fortune_grammatical_constructions.pdf` identifies itself as *Shona Grammatical Constructions, Volume 1*, with a third edition dated 1985, and has 205 PDF pages.
The extension card instead cites *An Analytical Grammar of Shona* (1955), Chapter VII, section 453, pp. 201-222.
That is not a verified locator in the available source.

I extracted and visually checked PDF page 33, printed page 21, section 2.10.2.3.3, “Extended radicals”.
It distinguishes repetitive `-urur-/-oror-` from reversive extensions.
The code labels both as reversive styles.
The source lists reversive forms conditioned by the radical vowel, including `-anur-`, `-enur-`, `-inur-`, `-onor-` and `-unur-`.
The current generator's corresponding long-unur branch chooses only u or o.

With a published `-pfeka` fixture and long-unur reversive request, the API returned `ndinopfekunura`.
The cited source gives the radical relationship `pfek` to `pfekenur`, so the implemented extension surface conflicts with that source example.
Do not generalize this one page into a complete rule for every dialect, root or extension sequence.

The source also describes causative (1) with radical-specific sound changes and an alternative `-idz-/-edz-` distribution.
The implementation exposes `dz` and `ts` as broadly selectable styles without demonstrating those lexical restrictions.
This requires evidence-backed correction, not a claim that all existing examples are necessarily wrong.

### 3. Invalid extension styles silently succeed

For a published `-buda` fixture, `extensions: [{"type": "causative", "style": "nonsense"}]` returns HTTP 200 and `ndinobudisa`.
The style falls through to the default suffix instead of producing a structured unsupported-feature error.
Extension ordering, repeats and combinations also have no explicit grammar-validation gate in the inspected validation path.

### 4. Public descriptions contradict implemented behaviour

The generate documentation says extensions are unsupported despite six accepted extension types.
Response warnings say extensions are not generated even when `slots.extensions` contains applied extensions.
The rule card covers passive, causative and applicative but does not document all the implemented families and styles.
The real-data regression document still describes infinitives as future work although simple infinitive analysis exists.
Passing card tests check structure and non-empty locators, not whether the cited text supports the actual rule.

## Next job and acceptance boundary

Deliver a source-grounded extension implementation covering the already-exposed families, correcting classification where necessary and refusing combinations or styles that lack evidence.
Preserve valid existing behaviour and the v1 response envelope, while documenting corrections to incorrect or unsupported behaviour.
Use real source examples for linguistic expectations and generated-to-analyzed consistency as an additional engineering check.
Do not pass the assignment merely by disabling all extensions or rewriting test expectations to match the implementation.

The implementation must include valid stem-boundary handling, source-backed allomorphs, strict feature validation, explicit ambiguity behaviour, truthful rule metadata and documentation, and endpoint-level regression evidence.
Correcting this subsystem is a bounded product-completion milestone, not a claim that morphology as a whole is complete.

## Subsequent implementation sequence

1. Complete simple infinitive generation and source-supported negative/object/reflexive infinitive analysis and generation.
2. Add source-backed tense/aspect and mood slices, validating terminology and evidence availability first.
3. Implement nominal generation and its concord/morphophonemic constraints.
4. Complete the independently annotated FSI benchmark and publish coverage and accuracy by capability; build relevant portions during each earlier slice rather than postponing all validation.

The local Fortune volume contains useful verb morphophonemics but references later verbal sections; verify source availability before assigning comprehensive tense/mood coverage.
Tsumo, madimikira, lexical quality and search still require their own completion assessments.
Deployment remains outside this workstream.

---

## Status update: 2026-09-09 verb-extension correction pass

The historical sections above are preserved as written; the original
assessment was not updated after the first implementation pass and its
reproduction examples describe pre-correction behaviour. This section records
what the correction pass (supervisor findings 1-5) changed. It is an
implementation and evidence report, not independent linguistic certification.

| Finding | Status | Evidence |
| --- | --- | --- |
| 1. Malformed extension styles returned HTTP 500 (`TypeError` on unhashable style values) | Resolved | `style`/`type` are validated as strings before any membership or dict lookup (`_normalize_generation_extensions`); lists, objects, booleans, numbers return structured `422 GENERATION_UNSUPPORTED`; explicit `style: null` matches the omitted-style contract. Regression: `test_malformed_extension_type_and_style_values_are_structured_422`. |
| 2. Object-marker parsing discarded the originating lemma (first object segmentation returned early) | Resolved | `_analyze_segmentations` collects no-object, every prefixing object concord, and coalescence readings for both polarities, deduplicates by full features, ranks by confidence, and bounds per-subject work (`_MAX_ANALYSES_PER_SUBJECT`). `ndinokurisa` now analyzes as `-kura` + causative (no object, first) and `-ra` + `ku` (second). Regression: `test_ambiguity_keeps_originating_lemma_across_object_readings`, `test_competing_object_concords_stay_distinct`, `test_coalesced_object_reading_survives_competition`. |
| 3. Analyzer accepted sequences the generator refuses (`passive`+`causative`, repeated causative) | Resolved with an explicit policy | One shared sequence convention (`_extension_types_violation`: at most 3, each type once, canonical order) now gates both the generator's request validation and the analyzer's decompositions. Fortune 2.10.2.3.3 states "R + extension(s)" with no ordering rule, so the convention is documented as a product limit, not a grammar rule; attested combination radicals (Fortune 3.4.2.8, e.g. -pamhidz-ir-an-, PDF p. 110 / printed p. 98) conform to it. `ndinobudwisa` and `ndinobudisisa` are now structured 422s on both sides. Regression: `test_sequence_policy_shared_between_generator_and_analyzer`. |
| 4. Lexically restricted styles (dz/ts) generated with only a warning; reciprocal/short-reversive enabled without locators | Resolved with an explicit policy | Generation of causative `dz`/`ts` and reversive `short` returns structured `422 EXTENSION_UNVERIFIED`, and the same evidence gate excludes those derivations from inferred analyzer readings (supervisor-blocker follow-up): a reviewed base lemma is not evidence for an arbitrary derivation, so base-only surfaces such as `ndinobuditsa` return structured `422 ANALYSIS_UNSUPPORTED` with an `unverified_extension_derivation` lane, and search cannot report matched enrichment for an excluded derivation. Independently published derived lemmas (e.g. `-buditsa`) still analyze and search as exact lexical entries with no derivation claim. Reciprocal gained real locators (Fortune 3.3.18 ku-tarisan-a; Fortune 3.4.2.8 -pamhidz-ir-an-; Hannan printed p. 2, kuda > kudana) and moved to its own evidence-backed card with generation preserved. Hannan locators for -idz-/-edz- (pp. 158, 240) and the listed-but-unlocated -ura are recorded in the retained card. Regressions: `test_unverified_allomorphs_refused_on_both_sides_of_the_api`, `test_published_derived_lemma_resolves_as_own_entry_without_derivation_claim`, `test_search_never_reports_matched_for_excluded_derivations`. |
| 5. Release rule-set version was echoed without selecting executed rules | Resolved with the validate-policy | `MORPHOLOGY_RULES_VERSION = "morphology-rules-v3"` names the executed rules; analyze and generate return structured `503 MORPHOLOGY_RULES_VERSION_UNSUPPORTED` when the current release declares anything else, and search returns results with `morphology_enrichment.status = "unavailable"`. No version rewriting, no duplicated historical engines; `data_release` identity stays separate. Regression: `tests/test_morphology_rules_version.py`. |

Corrections also landed in the OpenAPI description (`docs/openapi.json`,
regenerated through `python manage.py generate_openapi_spec`) and the
generate-endpoint documentation. The first-pass improvements (greedy-strip
fixes, reversive vowel copy, repetitive/reversive separation, lexical
candidates, strict validation, source-labelled regression examples) are
preserved and still covered.

Remaining limits, stated honestly: per-lemma extension distribution is not
certified by the available sources (Fortune defers causative distribution to
an unavailable volume 2 section; Hannan lists a `-ura` suffix whose entry could
not be located), so dz/ts and short-reversive derivations are excluded from
both generation and inferred analysis until reviewed evidence exists; no
independent linguistic review of the enabled patterns has occurred; sequence
conventions remain a product policy. This correction pass does not claim the
whole morphology milestone is complete.
