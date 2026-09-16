# Source-backed corpus correction record (frozen v1-proposed, hash sha256:f40ed432e7f0c30a)

All later expectation changes require a new entry here. Silent rewrites forbidden.

## Pre-freeze corrections applied (challenger-driven, before first run)

1. Dialect tags: `StSh` -> `St. Sh.`, `K/Ko` -> `KM` (challenger claim 2, Hannan
   p.xii locators). Applies to SRC-009/035/039/068 interpretations.
2. Imperative i-augment scope narrowed to vowelless (C-shape) radicals only;
   bare `pa`/`dya` is not the imperative (challenger claim 4). SRC-033 records this.
3. SRC-059 (-na) and SRC-062 (-ona) frozen as `disputed_unresolved`, flows []
   (challenger claims 5-6). No verb analysis may be grounded on them.
4. Extension scope (challenger claim 7): reciprocal -an- cited via Hannan list +
   Fortune 3.4.2.8 (not 2.10.2.3.3); dz/ts and short -ur-/-or- absent from the
   passage and stay evidence-gated; intensive/perfective/extensive attested but
   unexposed as API types (SRC-049/054 unscored + CT-UNSUP-07 refusal).
5. Object-marked imperatives: all witnesses singular-addressee; plural+object
   unattested on both sides (challenger claim 9). CT-UNSUP-03.
6. Coalescence 3.3.9 nominal-only; no verbal a+a rule (challenger claim 10).
   Finite/infinitive/imperative a|a deferrals stay deferred, never ungrammatical.
7. SRC-022/SRC-042 and SRC-034/SRC-043 and SRC-025/SRC-065 deduplicated by
   endpoint (search-only second surface / distinct concord / finite-vs-infinitive
   lane) so no case is triple-counted.
8. SRC-068/SRC-069 frozen as agreed policy notes with flows [] (no triple-count).

## Review status at freeze

- `agreed`: SRC-068, SRC-069 (challenger explicitly agreed).
- `disputed_unresolved`: SRC-059, SRC-062 (excluded from definitive scoring).
- `proposed`: everything else (challenger verdicts AGREED/CORRECTED incorporated
  above; no open linguistic dispute at freeze).
- Contract cases (`contract` class): API-declared behavior, not grammar claims.
- `previously_tested: true`: SRC-060, CT-UNSUP-*, CT-INV-03..06, CT-VAR-01,
  CT-TERM-*, CT-SEQ-01 (overlapping existing regression shapes); all others are
  new examples. Counts are reported by case, never triple-counted across endpoints.

## Independence limits (carried from protocol)

Source selection delegated to a read-only source author prompted with source
locations + coverage categories only (disclosure: no implementation exposure).
Evidence challenger re-inspected all 14 claim areas from primary passages
(disclosure: no implementation/test/rule-card inspection). True blindness cannot
be guaranteed in one checkout; this is separated-prompt review, not blind review.
`skill://evidence-validation` unavailable; protocol discipline substituted.

## Round-1 corrections (first evaluation run: 11 scored failures, all corpus/harness)

Baseline `sha256:de63...` run: 100 cases, 11 scored failures. Reproduction before
each change; no implementation change resulted:

1. Noun-class object/subject shapes: corpus used `{"noun_class": "8"}`; the API
   requires `{"type": "noun_class", "class_number": "8"}` (existing test shape).
   Fixed 22 feature blocks across SRC-022/038/041/065, CT-UNSUP-01/02/03.
2. Missing class-9 fixture (`i` concord): FSI `Ipe` needs the class-9 object
   concord. Added Class 9 (`i`/`i`); SRC-034 now resolves.
3. SRC-038 transcription error (source-backed): corpus asserted single-i
   `usarise` from OCR (`Usarlis~`); FSI p.340 image
   (`local_batches/fsi_p357_imperative.png`) prints double-i `Usariisa`/`Riise`,
   matching compositional `usa + ri + is + e`. Expected surface corrected to
   `usariise`; implementation output confirmed against the image.
4. Harness matcher ignored nested `lemma` identity: required/prohibited lemma
   checks were vacuous (CT-VIS-01 false alarm on a DRAFT homograph). Matcher now
   enforces `lemma.public_id`; the DRAFT leak was disproven (all stem queries
   filter `SUPPORTED_REVIEW_STATES`), and required-lemma recall is now real.
5. CT-UNSUP-01 design error: subject `va-` alone never touches the stem
   (`-no-` intervenes); the deferral needs object `va` immediately before the
   stem. Added the class-2 object; implementation returns
   `object_before_a_initial_stem` as designed.
6. CT-SEQ-01 design error: `ndinotaurisisa` is LEGAL (`-taurisa` is published, so
   the stack from the resolved lemma is a single causative and generation
   agrees). Replaced with harmony-correct `ndinogonesesa` (`-gona` + `-es-` x2
   after `/o/`, no intermediate lemma), which must 422 on both sides.

## Round-2 corrections (re-run: 2 failures -> 0)

7. CT-UNSUP-01 stale boundary string (`subject_...` -> `object_before_a_initial_stem`).
8. CT-SEARCH-04 overreach (no code change): the reviewed search contract
   (`test_search_never_reports_deferred_imperative_as_matched`) surfaces deferred
   lanes under `zero_result` only and stays silent beside fuzzy hits. The case
   now asserts that parity for the finite lane (never `matched`, no
   `morphology_enrichment` beside hits) instead of demanding lanes. Deliberately
   not "fixed" in code: overturning a reviewed contract needs supervisor approval.
9. SRC-038 analyze surface switched to verbatim FSI `usariisa` (-a, KM/FSI
   practice); generation keeps constructed Zezuru `usariise`. Both pass.
10. New CT-IMP-SCOPE-01: bare `ti` -> 422 with `excluded_divergent_stem_imperative`
    lane (shared stem scope on the bare-surface path). SRC-057 gains a prohibited
    imperative reading for `kuti`.

## Deliberately not changed

- Search `unsupported` enrichment stays absent beside fuzzy hits (reviewed
  contract, see 8). A finite-lane parity regression now guards it.
- `ndinotaurisisa` analyzes 200 via published `-taurisa` + single causative:
  correct under the published-derived-lemma doctrine, with generation agreement.
- No implementation file was modified by this milestone; all green behavior was
  verified, not assumed. Corpus hash after round 2: `sha256:f40ed432e7f0c30a`.

## Repair task (2026-09-11): evaluator overhaul, no implementation change

Supervisor adversarial probes demonstrated six false passes in the v1-proposed
harness. All six are now caught; the repairs below are verified by 18 gate
tests, including direct reproductions of each probe. Corpus re-versioned to
`source-backed-eval-v1` (full 64-hex hash); the v1-proposed baseline run
(`sha256:f40ed432e7f0c30a`, old format, 0 fails) is preserved under
`results/history/run-1789076957/`, as is the first repaired-harness run
(`run-1789077046`, 2 fails, both annotation errors since fixed).

### Evaluator changes (tools/evaluate_source_backed.py)

1. Semantic reading checks: required readings now assert lemma identity,
   construction (analysis_type/rule_id), polarity values, subject/object/
   addressee surfaces (+person/number/class where the claim needs it),
   imperative number, and extension type/order/style lists. Partial-match
   semantics are explicit (maps assert subsets, lists assert ordered
   exact-length, null asserts present-null so missing fails, unknown
   expectation keys fail loudly). Missing-vs-null-vs-empty-list is tested.
2. Exhaustive references reject every unmatched returned analysis
   (`analyze_exhaustive`); non-exhaustive references count actual unmatched
   readings (required first, then prohibited, remainder unadjudicated once
   each) instead of `len - required`.
3. Round trips analyze the ACTUAL generated form and recover the originating
   reading (`round_trip_recovered`); fixed-input analysis stays separate.
   Search cases compare returned morphology readings (required/prohibited) and
   parsed lexical hits, preserving the lexical-vs-enrichment distinction.
4. Metrics engine with explicit denominators, split linguistic vs contract:
   generation correctness, required recall, prohibited produced, unadjudicated
   extras, supported refusals, deferred/invalid handling, both agreements,
   unresolved + not_evaluated lists. No blended score. No-flow cases report
   `not_evaluated`, never pass. Failures carry candidate triage classes from
   the declared categories (heuristic, labeled as such).
5. Isolation: `config/settings/eval.py` (ignores `DATABASE_URL` by
   construction) + temp database + pre-migration live-path assertion. Nothing
   under `--out` is deleted; prior results archive to `history/`.

### Corpus changes (builder-owned; annotations, not behavior)

6. All scored linguistic analyze-200 cases carry full semantic readings;
   analyze-200 requires an explicit `exhaustive` boolean; generate-200
   requires `expected_surface` (+`round_trip.required_reading`); search needs
   a real assertion; scored cases without assertions are rejected by schema.
7. Evidence audit: nine constructed full words relabeled
   `source_attested` -> `rule_supported` (SRC-046/047/048/050/051/052/056/063/
   070): their radicals/extensions are attested, the full ku-forms are built
   by the general ku- rule. Attested-form cases are unchanged.
8. CT-LEX-01 corrected to the exact-vs-derived surface `ndinotaurisa`
   (exact `-taurisa` ext [] + derived `-taura` + causative); the earlier
   `ndinotaurisisa` text made both required readings unmatchable (a legal
   single-causative-on-`-taurisa` reading, with generation agreement).
   SRC-034 now asserts the class-9 object surface (`ipe` = i- + p + e).
   SRC-057 gains teeth via enforced exhaustiveness (was already prohibited).
   New CT-IMP-SCOPE-01 (bare `ti` 422 + lane).
9. Version `source-backed-eval-v1`, hash
   `sha256:b519698a7dd6d2491fb67cae6e5c7d6c816d74ddac665542433974bd14059bb1`
   (full SHA-256 over canonical {version, fixtures, cases}; definition in
   tools/build_source_backed_corpus.py, verified by both runners).

### Deliberately unchanged after adjudication

- Search `unsupported` enrichment stays absent beside fuzzy hits (reviewed
  contract `test_search_never_reports_deferred_imperative_as_matched`);
  finite-lane parity is regression-tested, not recoded.
- `ndinotaurisisa` analyzing 200 via published `-taurisa` + single causative
  is correct under the published-derived-lemma doctrine (generation agrees).
