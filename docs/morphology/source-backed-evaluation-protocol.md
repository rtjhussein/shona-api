# Source-backed morphology evaluation â€” protocol (predeclared 2026-09-10)

Branch: `codex/source-backed-evaluation`. Base: `01e8ce7` (PR #113, morphology-rules-v6).
No commits, pushes, PRs, merges, deploys, or Actions runs (actions disabled).

This is an engineering evaluation and correction milestone, not linguistic certification.
No paid linguist. No claim of expert certification or population accuracy.

Independence limits (declared up front): coordinator has full knowledge of
implementation code, existing fixtures, and prior bug history. Source selection
is delegated to a read-only source-author subagent prompted with source
locations + coverage categories only (no implementation code, no existing
expected outputs, no bug history), with prior-exposure disclosure requested.
A separate evidence-challenger subagent re-inspects primary passages and
attempts to disprove expectations. This is separated-prompt review, not a
blind evaluation, because true blindness cannot be guaranteed in one checkout.
The `skill://evidence-validation` skill is unavailable in this environment
(only `bmad-orchestrator`, `gnhf` exist); evidence discipline below substitutes
for it. If subagents are unavailable, coordinator performs explicitly separated
passes and reports reduced independence.

## 1. Coverage categories and sampling

Linguistic cases (~70 target, distinct surfaces/lemmas; no padding with trivial
variations; no triple-counting one case across three endpoints):
- FIN-POS: positive present finite (`ndi-no-â€¦-a`), person + noun-class subjects.
- FIN-NEG: negative present finite (`ha-â€¦-i` Standard / `-e` Zezuru variant).
- INF-POS / INF-NEG: `ku-` infinitives, `sa-` negative, object, reflexive `zvi`.
- IMP-SG-POS / IMP-PL-POS: bare stem, `-i` plural, prothetic `i-` monosyllabic,
  Manyika `-nyi` analyzed variant.
- IMP-NEG: `usa-/musa-` + radical + `-e` (generated) / `-a` (analyzed variant),
  with/without object.
- OBJ: person + noun-class object concords in finite/infinitive/imperative lanes.
- EXT: passive, causative (default only), applicative, neuter, reciprocal,
  reversive (vowel-copy long), repetitive; shared sequence convention;
  evidence-gated `dz/ts/short` excluded.
- STEM: short/vowelless radicals, divergent `-ti/-nzi`, defective `-na`,
  vowel-initial `-ambura/-enda/-ona` type with boundary discipline.
- AMB: ambiguous surfaces (object vs no-object, extension vs stem, `zvi`
  reflexive vs class-8 object, `kudai`-type infinitive vs imperative).
- DEF: deferred boundaries (`a|a` contacts, `sa-|a-`, plural+object imperative,
  reflexive imperative, `chi-` exclusive out of scope).

Contract cases (~30 target, classified separately from grammar):
- CT-LEX: lexical alternatives (exact derived lemma vs inferred derivation).
- CT-AMB: multi-reading responses preserved, not collapsed to `.first()`.
- CT-SEARCH: enrichment follows analyzer policy (no matched enrichment for
  excluded/deferred lanes; exact lexical hits unaffected).
- CT-UNSUP: deferred constructions return structured 422 with stable
  boundary/reason, never presented as ungrammatical; invalid inputs
  (bad features shape, unknown fields, unknown extension type/style,
  malformed style values, `generation_type` mismatches) return documented
  400/422 codes; version mismatch returns 503 / `unavailable`.
- CT-VIS: public visibility (published vs unpublished lemma) where the flow needs it.

Sampling: source-author selects verbatim source forms first, then minimal
constructed combinations only where an explicit general rule justifies them.
New vs previously-tested examples distinguished by `previously_tested: true/false`
in the corpus. Shortfalls reported, never padded.

## 2. Corpus size and stopping condition

Target ~100 distinct cases (70 linguistic + 30 contract). Stopping condition:
declared corpus frozen with hash before first evaluation run; initial run +
up to two focused correction/re-evaluation rounds. Remaining failures reported,
not iterated to zero. Later expectation changes require a source-backed
correction record; silent rewrites to match implementation output are forbidden.

## 3. Evidence classifications

- `source_attested`: source contains the form AND relevant interpretation.
- `rule_supported`: explicit applicable rule justifies the constructed combination
  (cite rule passage, not absence of counterexample).
- `unresolved`: evidence does not establish the expectation â€” excluded from
  definitive accuracy scoring, counted separately.
- Contract cases: `contract` (API-declared deferral = contract expectation, not
  grammatical invalidity). Nominal rules never transferred to verbal
  constructions; commands / finite negation / infinitives / subjunctives never
  conflated; morpheme boundaries require more than substring match; PDF images
  inspected where OCR/tone/layout matters.

## 4. Expected-output representation (per linguistic case)

`case_id, category, source_file, source_locator (exact PDF/printed page or entry),
source_form_verbatim, source_interpretation, normalized_input (+normalization notes),
language_dialect_construction, lemma, morpheme_boundaries (+justification),
expected_interpretations[], acceptable_variants[], exhaustive: bool,
evidence_class, review_status (proposed|challenged|agreed|disputed),
previously_tested, notes`. Contract cases use a shorter schema
(`case_id, category, flow, request, expected_status/code, evidence_class=contract`).

## 5. Metrics (raw numerators + denominators, by capability; no single blended %)

Units are part of the contract (amendment 2026-09-12 binds them):
- Generation: requests — correct / declared supported generate requests.
- Analysis required recall: readings — recovered / declared required readings,
  where declared = analyze-200 required_readings + search-200 required_readings
  + 1 per round_trip. A supported request returning 4xx/5xx or an unreadable
  body emits no (or failing) per-reading checks, so missing readings count as
  unrecovered. Denominators derive from declared expectations only, never from
  emitted checks or response shape. The search empty-aggregate diagnostic is
  excluded from both counts.
- Prohibited: readings produced (count, must be 0).
- Unadjudicated extras: readings (count; flagged, not failed).
- Supported-request refusals: requests — 4xx refusals / declared supported
  generate+analyze requests. Only explicit 4xx counts as a refusal; 5xx or
  unreadable bodies stay in the denominator but not the numerator, keeping
  refusals distinguishable from server failures while neither disappears.
  Multi-flow cases contribute each supported flow independently.
- Deferred/invalid handling: requests — correctly handled / declared deferred
  generate/analyze/search requests (correct 422/400/503 with stable reason).
- Cross-endpoint consistency: generate→analyze round-trip agreement (cases);
  analyze→search enrichment agreement (cases with search morphology).
- Unresolved count + coverage gaps listed separately.
An API refusing everything fails supported-coverage checks by construction.

## 6. Failure categories

`linguistic_rule_defect | lexical_data_gap | generation_analysis_disagreement |
search_propagation_defect | appropriate_contract_refusal |
unnecessary_refusal_of_supported | invalid_input_handling_failure |
unresolved_evidence`. Each mismatch labeled with one category + evidence.

## 7. Challenged-expectation resolution

Challenger inspects primary passages (not author summaries). Outcomes:
`agreed` (stays scored), `corrected` (author revises with new locator +
correction record), `disputed` (disagreement preserved, case excluded from
definitive scoring, counted as unresolved). No majority vote, no confidence
scores. Model agreement is not evidence.

## 8. Reproducibility and safety

- Isolated SQLite via `config.settings.eval` (`EVAL_DB_PATH` temp file, never
  `DATABASE_URL` — the project `.env` overwrites it; see INCIDENT.md) with a
  pre-migration live-path assertion; never touches `db/shona.sqlite3`; no
  fixtures in dev DB; no secrets in artifacts. Nothing under the output
  directory is deleted; prior runs archive to `history/`.
- One command runs the evaluation; output = machine-readable JSON + concise
  human report naming code revision + corpus version/hash.
- Reference expectations never generated with morphology implementation helpers.
- Harness self-tests prove wrong readings, unexpected refusals, and leaked
  deferred interpretations are detected.
- Full suite + targeted regressions + direct API checks + `git diff --check`.
- Rule-set versioning policy followed; no release-record rewrites.
- Existing capabilities preserved unless evidence supports correction; no score
  gains by disabling broadly supported functionality; no global spelling
  blacklists; no broadening support from round-trip success alone.

## Amendment 2026-09-11 (harness repair; supervisor findings 1-6)

Predeclared protocol stands; the following bindings were tightened after
adversarial probes demonstrated false passes. No linguistic expectation was
weakened to obtain a clean result; annotation corrections carry evidence in
`evaluation/source_backed/v1/CORRECTIONS.md`.

- Semantic readings: scored linguistic cases assert lemma, construction,
  polarity, subject/object/addressee, number, and extension type/order/style
  where the claim needs them. Partial-match semantics: maps assert subsets,
  lists assert ordered exact-length sequences, null asserts a present null
  (missing fails), unknown expectation keys fail. Schema rejects unknown keys.
- Exhaustive references (`exhaustive: true`, explicit) reject every unmatched
  returned analysis; non-exhaustive references verify required readings,
  reject prohibited readings, and count actual unmatched readings once each
  as unadjudicated (never `len - required`).
- Round trips submit the ACTUAL generated form to `/v1/analyze` and recover
  the originating reading; fixed-input analysis stays a separate check.
  Search cases compare returned morphology readings and parsed lexical hits,
  preserving the lexical-vs-enrichment distinction.
- Metrics (raw, by capability, linguistic vs contract, no blended score):
  generation correctness, required recall, prohibited produced, unadjudicated
  extras, supported refusals, deferred/invalid handling, both agreements,
  unresolved + not_evaluated counts. No-flow cases report `not_evaluated`
  (never pass); scored cases without assertions are rejected at load.
- Corpus integrity: builder-owned construction from parts+fixtures, full
  SHA-256 over canonical `{version, fixtures, cases}` (hash field excluded),
  verified with schema validation in both runners before any request.
- Reports identify code revision + dirty flag, evaluator hash, corpus
  version + hash. Evidence audit: constructed full words are `rule_supported`
  unless the full form and interpretation are attested.

## Amendment 2026-09-12 (adversarial probes 7–8; response-independent denominators + nested validation)

No linguistic expectation weakened; no API change to make the evaluator green.
- Response-independent denominators: every denominator derives from declared
  executable expectations (supported/deferred requests, required readings),
  never from emitted checks, HTTP status, or body shape. Missing expected
  readings on 4xx/5xx/unreadable count as unrecovered; 4xx refusals and 5xx
  failures stay distinguishable (only 4xx counts as a refusal) while both stay
  in every relevant denominator. Multi-flow cases contribute each flow
  independently. The search empty-aggregate diagnostic
  (`search_morphology_empty`) fails the case but is excluded from
  required-recall counts. Units bound in §5; report lines state them.
- Nested expectation validation: the builder owns a maintained slot/field
  schema (slot names, per-slot fields, extension entry keys; values
  unrestricted, partial/null/ordered-list semantics preserved) applied to
  required/prohibited/also_allowed, search, and round-trip expectations with a
  corpus locator. The evaluator validates resolved expectations before
  matching and fails via `*_expectation` checks, so a malformed prohibited
  pattern can never pass as a non-match. The schema is hand-maintained, never
  imported from the morphology implementation, and linguistic values are never
  derived from it.

### Amendment 2026-09-13 (malformed-response robustness)

No linguistic expectation weakened; no API change. Valid JSON with malformed
response structures (non-object `data`, missing/non-list `analyses`,
non-object list entries, non-object `morphology`/`generated`/result `lemma`)
is a response failure, never a crash and never a silent empty pass: the flow
emits a field-specific `*_body` diagnostic, fails the case, counts declared
readings as unrecovered under the existing response-independent denominators,
and evaluation continues with later cases. Absent search enrichment, empty
analysis lists, and nullable slots stay legitimate. A small shared
parse/validate layer (`_extract_data`, `_reading_list`) covers
analyze/search/round-trip/generate without a blanket handler around the run;
the standalone runner still exits non-zero on any scored failure with
machine-readable results and the report produced.


## Amendment 2026-09-16 (search retrieval tier; no expectation changed)

Search gained a retrieval tier and no corpus expectation moved. Recorded so the
search contract's scope is not inferred from the corpus alone.

`/v1/search` now resolves an inflected form to its lemma as a *result*, per
product requirements section 7.1 tier 3 ("Morphological analysis: parse
inflected form to lemma"). Previously the resolution appeared only as an
enrichment object beside `count: 0`. Tiers run in order -- exact lemma, exact
form, morphological resolution (`match_type: "morphology_lemma"`), fuzzy
similarity -- and a later tier is consulted only when the earlier ones matched
nothing, so a lexical hit is never displaced.

Why no expectation changed: the search checks assert *membership*
(`expected_lexical_hits` among returned headwords, required/prohibited readings
among `morphology.analyses`, `expected_absent` over the raw body). None asserts
that `results` is empty, so a newly populated result list satisfies every
existing case. The evaluator was re-run after the change and reports 0 scored
failures on the frozen corpus.

What the tier must never do, and the cases that already bind it:

- surface an evidence-gated derivation: CT-SEARCH-03 (`ndinotauridza`) must
  still expose the `unverified_extension_derivation` lane and no reading;
- surface a deferred boundary: CT-SEARCH-04 (`vanovambura`) must still return no
  matched enrichment;
- displace a lexical hit: CT-AMB-01 (`taurisa`) must still return the exact
  hit;
- reach an unpublished lemma: the tier re-queries through the public
  (published-only) queryset rather than trusting the analyzer's reviewed set.
