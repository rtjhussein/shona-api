# Shona Lexical API — Implementation Backlog Rewrite
## Execution Spec for Codex / GitHub Issues / GitHub Project

Version: rewritten after source review and scope corrections  
Purpose: turn the PRD into an implementation-ready, source-aware, agent-friendly backlog that can be executed in small vertical slices without overloading model context.

---

# 1. Ultimate Product Goal

Build a source-grounded, developer-friendly, pedagogically useful Shona language platform.

The system is not just a dictionary API. It is a structured Shona language platform with:

- a canonical lexical backbone
- a grammar and morphology layer
- learner-oriented and curriculum-aware metadata
- search and validation features for apps, games, and study tools
- a staged figurative-language subsystem
- a reference web dictionary built on the public API
- editorial review and release management so the data stays trustworthy

The design principle is:

> trustworthy structure, staged delivery, ambition without chaos

---

# 2. Ground Rules for Implementation

## 2.1 Smart-zone rule

Each issue must be small enough for Codex or Claude Code to execute with bounded context.

That means each issue should:

- solve one narrow outcome
- touch only the necessary layers
- include only the source snippets relevant to that task
- have clear acceptance criteria
- produce a testable artifact

Do not hand an agent the entire PRD plus all source books for every issue.

## 2.2 Vertical slices first

Prefer tracer bullets / vertical slices over large horizontal work packages.

Good:
- one small end-to-end slice that adds a model, admin flow, serializer, endpoint, and test for one bounded concept

Bad:
- “build all models”
- “build all API endpoints”
- “build all web pages”

Some foundational work is still necessary, but the board should move into vertical slices as soon as possible.

## 2.3 GitHub Project policy

Use GitHub Issues + GitHub Project as the source of truth.

Create the dependency-shaped backlog up front, but do not flood the board with all repeated throughput issues immediately.

Create up front:

- unique engineering issues
- unique architecture issues
- unique parser issues
- unique docs / release issues
- first few editorial batch issues

Create progressively:

- repeated editorial batch issues
- repeated review tranches
- repeated enrichment batches

---

# 3. Source Key Map

Use stable source keys in all issues so the plan survives filename changes.

| Source Key | Current File |
|---|---|
| `source_prd` | `prd_v5.md` |
| `source_hannan` | `hannan_dictionary.pdf` |
| `source_fortune` | `fortune_grammatical_constructions.pdf` |
| `source_fsi` | `fsi_course.pdf` |
| `source_maumbirwo` | `maumbirwo_emazita.pdf` |
| `source_curriculum_notes` | `curriculum_notes_forms_1_4.pdf` |
| `source_zimsec_syllabus` | `zimsec_syllabus_forms_1_4.pdf` |
| `source_tsumo_tsika` | `tsumo_tsika.pdf` |
| `source_shona_yedu` | `shona_yedu.pdf` |

---

# 4. Source Roles in the System

## 4.1 Core build sources

### `source_hannan`
Role:
- lexical backbone
- lemma candidates
- senses
- dialect markers
- lexical tone
- examples
- cross-references
- ideophone markers
- noun-class clues
- orthographic conventions

System areas affected:
- lemma model
- sense model
- tone model
- form model
- search normalization
- editorial review
- cross-reference graph

Implementation note:
Hannan requires a **dictionary-entry parser for digitized dictionary notation**. This is not an OCR parser. It is a structured parser for compact lexicographic entries.

### `source_fortune`
Role:
- grammar and morphology backbone
- noun classes
- concords
- morphophonemics
- verbal constructions
- ideophonic constructions
- derivational and constructional rules

System areas affected:
- noun-class subsystem
- morphology analyzer
- morphology generator
- grammar metadata
- phonology / morphophonemics rules
- future expressive language expansion

Implementation note:
Fortune is not just reference reading. It is a core implementation source for morphology and grammar.

### `source_fsi`
Role:
- learner corpus
- pedagogical examples
- dialogues
- useful attested forms
- beginner progression / sequencing cues

System areas affected:
- learner metadata
- example bank
- beginner/common vocabulary prioritization
- morphology evaluation corpus
- educational surfaces

---

## 4.2 Validation and structured enrichment sources

### `source_maumbirwo`
Role:
- noun-formation and noun-class validation
- nominal prefix logic
- singular/plural class relationships
- class membership clarification

System areas affected:
- noun-class QA
- nominal morphology QA
- editorial validation

### `source_curriculum_notes`
Role:
- orthography and learner-facing correctness
- punctuation
- joining/separating words
- writing norms
- classroom language expectations
- useful school-facing terminology

System areas affected:
- normalization policy
- validation endpoint behavior
- orthography guidance
- learner-facing documentation
- pedagogical tagging

### `source_zimsec_syllabus`
Role:
- pedagogical structure source
- curriculum topic map
- what categories matter educationally
- what expressive/figurative content is expected in school use
- register/style/communication context

System areas affected:
- pedagogical tags
- learner surfaces
- docs/examples organization
- figurative-language prioritization
- future educational SDK/docs decisions

### `source_tsumo_tsika`
Role:
- proverb-to-culture linkage
- thematic interpretation of proverbs
- cultural taxonomy support
- proverb pedagogy

System areas affected:
- proverb themes
- figurative-language metadata
- educational/cultural browse experiences

---

## 4.3 Candidate enrichment source

### `source_shona_yedu`
Role:
- high-volume proverb enrichment
- madimikira candidates
- future madunhurirwa expansion
- culturally marked lexical terms
- useful compact lexical lists

System areas affected:
- figurative-language enrichment
- cultural vocabulary enrichment
- example browsing
- educational browse surfaces

Implementation note:
`source_shona_yedu` is important, but it is not the highest authority when it conflicts with core lexical or grammatical sources.

---

## 4.4 Out of current main workflow

### External scrape source
A separately scraped source exists for nyaudzosingwi/vocabulary work outside this main implementation path.

Policy:
- do not make that source a blocking dependency in this backlog
- allow future reintegration through a dedicated enrichment issue

---

# 5. High-Level Product Structure

The system is now planned as five major build pillars:

1. **Lexical backbone**
2. **Grammar and morphology**
3. **Pedagogy and learner layer**
4. **Figurative language and expressive forms**
5. **Public product surfaces** (API + reference web dictionary)

This rewrite assumes the figurative-language lane is intentionally broad in design, but staged in delivery.

---

# 6. GitHub Label Conventions

## 6.1 State labels
- `state:backlog`
- `state:ready`
- `state:in_progress`
- `state:review`
- `state:blocked`
- `state:done`

## 6.2 Type labels
- `type:feature`
- `type:infra`
- `type:data`
- `type:research`
- `type:docs`
- `type:ops`

## 6.3 Area labels
- `area:foundation`
- `area:source`
- `area:parser`
- `area:editorial`
- `area:lexicon`
- `area:api`
- `area:search`
- `area:morphology`
- `area:phonology`
- `area:pedagogy`
- `area:figurative_language`
- `area:games`
- `area:web`
- `area:docs`
- `area:release`
- `area:observability`
- `area:security`

## 6.4 Phase labels
- `phase:0`
- `phase:1`
- `phase:2`
- `phase:3`
- `phase:4`
- `phase:5`
- `phase:6`
- `phase:7`

## 6.5 Execution labels
- `exec:agent`
- `exec:hitl`
- `exec:human`

Every issue should usually have:

- one state label
- one type label
- one phase label
- one execution label
- one or more area labels

---

# 7. Phase Goals and What Changes After Each Phase

## Phase 0 — Source Readiness and Parsing Strategy
Goal:
turn the source set from “documents we have” into “documents the system knows how to interpret.”

What changes after Phase 0:
before this phase, you have files and assumptions.  
after this phase, you know exactly how each source will be used, and the system has the parsing strategy required to start producing structured candidate data.

## Phase 1 — Foundation and Governance
Goal:
create the durable backend structure, permissions, audit trail, release primitives, and shared model conventions.

What changes after Phase 1:
before this phase, you may understand the sources, but you do not have a system of record.  
after this phase, you have a real backend that can store, review, version, and publish language data.

## Phase 2 — Canonical Lexical Ingestion
Goal:
turn digitized source material into reviewed canonical records.

What changes after Phase 2:
before this phase, the system has machinery but little real content.  
after this phase, it has real lemmas, senses, forms, tone data, and examples that can power product features.

## Phase 3 — Grammar and Morphology
Goal:
turn the platform from a structured dictionary into a linguistic engine.

What changes after Phase 3:
before this phase, the system stores language data.  
after this phase, it can analyze and generate forms and expose grammar-aware functionality.

## Phase 4 — Pedagogy and Learner Layer
Goal:
make the platform explicitly useful for learners, schools, and educational apps.

What changes after Phase 4:
before this phase, the system is linguistically rich but pedagogically thin.  
after this phase, it has learner ordering, curriculum-aware metadata, educational tags, and stronger learner-facing examples.

## Phase 5 — Public API V1
Goal:
make the platform available as a clean, documented public API.

What changes after Phase 5:
before this phase, capabilities exist mostly internally.  
after this phase, outside developers can integrate the platform as a product.

## Phase 6 — Reference Web Dictionary
Goal:
prove the API supports a coherent first-party user experience.

What changes after Phase 6:
before this phase, developers can call endpoints.  
after this phase, real users can browse and validate the platform through a web dictionary.

## Phase 7 — Release, Operations, and Public Beta
Goal:
turn working software into an operational public product.

What changes after Phase 7:
before this phase, the system works.  
after this phase, it is versioned, documented, observable, and ready for beta users.

---

# 8. Core Architectural Decisions for This Rewrite

## 8.0 System Constraints (Non-Functional Requirements)

These are the architectural constraints that should shape implementation decisions from the start.

### Initial scale assumptions
- early development and private beta scale, not internet-scale launch
- low to moderate editorial write volume
- moderate public read volume relative to writes
- bursty reads on search and entry pages are more likely than bursty writes

### Latency expectations
- public lexical reads should feel fast
- public search should feel fast enough for interactive use
- editorial approval/publish flows may tolerate slightly higher latency than public read paths, but should still feel responsive to staff users

### Durability expectations
- canonical lexical data, editorial decisions, provenance, and release metadata must be durable
- once a publish action succeeds, the created canonical data must not be silently lost

### Consistency expectations
- editorial decisions, publish actions, permissions, provenance, and release activation should prefer correctness over availability
- browse/search/cache layers may tolerate bounded staleness if this improves responsiveness

### Availability expectations
- the public API should remain available for reads during routine failures where possible
- temporary degradation of non-critical enrichment freshness is acceptable
- correctness-critical editorial and release actions should not fake success under uncertainty

### Observability expectations
- search latency, cache hit rate, queue depth, publish failures, and zero-result searches should be observable
- operational visibility is required before broad beta exposure

### Security and audit expectations
- authentication and authorization changes must behave strongly and predictably
- editorial and release actions must leave an audit trail
- provenance must remain traceable back to source material and review actions

## 8.5 Consistency Boundaries

Not every part of the system should make the same trade-off.

### Strong-consistency paths
These paths should prioritize correctness:
- editorial approve/reject actions
- publish from extraction unit to canonical records
- release creation and release activation
- permissions and authentication state changes
- provenance and audit-log writes
- canonical lexical record edits

Implementation guidance:
- do these synchronously against the primary database
- do not acknowledge success until the core write is committed
- prefer correctness over aggressive caching here

### Eventually-consistent paths
These paths may tolerate bounded staleness:
- public search ranking freshness
- cached lemma/detail reads
- figurative-language browse pages
- learner metadata derived views
- analytics and dashboards
- enrichment indexes and secondary browse structures

Implementation guidance:
- these may use cache + TTL, background refresh, or queued rebuilds
- do not block user reads waiting for every secondary representation to refresh

## 8.6 Read Path vs Write Path

The system has two very different kinds of work. Treat them differently.

### Write path
Purpose:
take source-grounded or editor-approved changes and create trustworthy canonical data.

Main flow:
- source text
- parser/extraction
- extraction units
- editorial review
- canonical publish
- release tagging

Properties:
- correctness-heavy
- provenance-heavy
- audit-heavy
- lower throughput than reads
- strong consistency preferred

### Read path
Purpose:
serve stable, useful language data to public and internal consumers.

Main flow:
- release-tagged canonical data
- serializers / query layer
- cache / derived read helpers
- API consumers / web dictionary

Properties:
- read-heavy
- latency-sensitive
- cache-friendly
- can tolerate bounded eventual consistency in some layers

Implementation note:
Do not design the read path as if it were the same thing as the editorial write path.

## 8.7 Cache Policy (Initial)

Caching is allowed, but only with explicit boundaries.

### Good cache targets
- lemma detail reads
- stable search results for common queries
- figurative-language list pages
- release metadata
- read-heavy public endpoints over stable released data

### Bad cache targets
- editorial queue views
- approval/reject actions
- publish confirmation paths
- auth / permission decisions
- audit-log creation paths

### Preferred cache style
Start with:
- cache-aside for public reads
- TTL-based expiry for read-heavy content
- explicit invalidation on publish or release events where needed

Avoid for canonical data:
- write-behind caching
- any strategy that can acknowledge success before correctness-critical data is safe

## 8.8 Queue Policy (Initial)

Queues should be used deliberately, not as a default for all work.

### Good queue candidates
- bulk source ingestion
- parser batch jobs
- enrichment imports
- secondary index rebuilds
- cache warming jobs
- analytics aggregation
- release preparation jobs
- long-running morphology backfills or recomputations

### Bad queue candidates
- editorial approve/reject actions that need immediate user certainty
- canonical publish confirmation when the editor expects immediate success/failure
- auth and permission changes
- core read endpoints

Implementation note:
If a user action must be trusted immediately, do it synchronously.
If the work is heavy, repeatable, or rebuildable, it is a strong queue candidate.

## 8.9 Deployment Style

Start as a modular monolith.

### Initial deployment shape
- Django application
- DRF API
- PostgreSQL primary data store
- Redis for cache/broker support
- Celery workers for async jobs
- one codebase, modularized by domain

### Why this is the default
- the domain is already complex
- the team needs fast iteration
- source parsing, editorial workflow, morphology, pedagogy, and figurative language are tightly related
- premature microservices would add failure modes and coordination cost without enough payoff

### Policy
Do not split into separate deployable services for parser, morphology, figurative language, pedagogy, or search at the start.
Keep them as internal modules unless scale or team boundaries later prove separation is necessary.



## 8.1 Digitized-source-first ingestion
Critical path ingestion is based on digitized text.

Do not treat OCR as a prerequisite to begin work.

OCR may exist later as:
- optional fallback
- future source onboarding support

But it is not part of the core start path.

## 8.2 Hannan parser is mandatory
The Hannan parser remains non-negotiable.

Definition:
a parser that reads Hannan’s compact dictionary-entry notation from digitized text and turns it into structured candidate data.

This parser must understand, at minimum:
- headwords
- tone bracket notation
- dialect abbreviations
- POS markers
- sense boundaries
- cross-reference notation
- ideophone markers
- noun-class clues
- special symbols and abbreviations

## 8.3 Figurative language is broad in design, narrow in first delivery
The figurative-language subsystem is designed for expansion, but initial delivery only fully implements:

- `tsumo`
- `madimikira`

The data model and backlog must leave explicit room for:
- `madunhurirwa`
- `nyaudzosingwi`
- `fananidzo`
- `enzaniso`
- `chibhende`

## 8.4 Curriculum docs affect product design
Curriculum-related sources are not just optional reading.

They materially shape:
- pedagogical tagging
- orthography and correctness policy
- expressive-language prioritization
- register and style metadata
- learner-facing documentation and examples

---

# 9. Issue Template

Use this exact field shape for every issue.

## Issue Fields

### goal
One-sentence statement of what this issue exists to achieve.

### delivers
The concrete artifact(s) or system capability produced by the issue.

### plain_change
What becomes true after this issue that was not true before.

### scope
Bounded implementation work included in the issue.

### instruction_to_codex
Direct implementation guidance for Codex.  
Be explicit about files, architecture, tests, migrations, serializers, admin, docs, and constraints.

### acceptance_criteria
Clear, testable completion conditions.

### out_of_scope
What this issue must not expand into.

### blockers
Issues that must be complete first.

### labels
The GitHub labels to assign.

---

# 10. Backlog

Execution rule:
Use this backlog one issue at a time. An issue is ready for a fresh agent/chat only when its `blockers` value is `none` or every listed blocker has already been completed and merged. Issues marked `state:blocked` should be created on the board for visibility, but should not be assigned to an implementation chat until their blockers clear.

## ISSUE-000 — Define source role map and ingestion rules

**goal**  
Define, in code-adjacent documentation, how each source is used, what authority level it has, and how it enters the system.

**delivers**  
A source-role map, authority policy, ingestion-style matrix, and conflict-resolution policy document checked into the repo.

**plain_change**  
Before this issue, the system has documents but no explicit contract for how they affect the build. After this issue, every source has a defined role and Codex can implement later issues without guessing which source governs which subsystem.

**scope**
- create a source registry document in the repo
- define source keys and current filenames
- define authority levels: backbone, validation, enrichment
- define ingestion style per source
- define conflict-handling rules
- define how provenance must be stored
- define which sources are critical path

**instruction_to_codex**
- Create a markdown document under `docs/sources/source_strategy.md`.
- Include the stable source keys from this spec.
- Add sections for source role, authority level, ingestion style, affected subsystems, and conflict policy.
- Record that `source_hannan`, `source_fortune`, and `source_fsi` are core build sources.
- Record that `source_maumbirwo`, `source_curriculum_notes`, `source_zimsec_syllabus`, and `source_tsumo_tsika` are validation/structured enrichment sources.
- Record that `source_shona_yedu` is candidate enrichment.
- Record that OCR is not on the critical path.
- Record that Hannan requires a dictionary-entry parser for digitized text.
- Keep the document implementation-oriented, not academic.

**acceptance_criteria**
- `docs/sources/source_strategy.md` exists
- stable source keys are documented
- every current key has a mapped current filename
- each source has authority level and ingestion style documented
- conflict policy is explicit
- OCR is explicitly marked non-critical-path
- the document is short enough to be usable in agent context

**out_of_scope**
- building models
- parsing any source
- writing migrations

**blockers**
- none

**labels**
- `state:ready`
- `type:docs`
- `area:source`
- `area:foundation`
- `phase:0`
- `exec:agent`

## ISSUE-001 — Bootstrap Django/DRF/Postgres project with health endpoint and CI smoke test

**goal**  
Create the base project so all later slices have a stable runtime, test, and deployment foundation.

**delivers**  
Running Django project, DRF installed, Postgres configuration, environment management, health endpoint, CI smoke test.

**plain_change**  
Before this issue, there is no running product shell. After this issue, the repo boots, tests run, and future slices have a safe base to build on.

**scope**
- Django project bootstrap
- DRF install and config
- Postgres settings
- local env config
- health endpoint
- test runner
- CI smoke workflow

**instruction_to_codex**
- Create Django project structure using Python 3.12.
- Add DRF and Postgres support.
- Split settings into a maintainable module layout.
- Add `.env`-driven config.
- Create a simple `/health` endpoint returning status and app version.
- Add pytest or Django test config.
- Add a CI workflow that installs dependencies, runs migrations, and executes a minimal test suite.
- Do not build business models yet.

**acceptance_criteria**
- app boots locally
- Postgres config is wired
- `/health` returns 200
- CI passes on a fresh checkout
- test command runs successfully

**out_of_scope**
- domain models
- auth
- admin customization

**blockers**
- none

**labels**
- `state:ready`
- `type:infra`
- `area:foundation`
- `area:api`
- `phase:1`
- `exec:agent`

## ISSUE-002 — Implement source registry model and admin CRUD

**goal**  
Represent all sources explicitly in the database.

**delivers**  
`Source` model, migration, admin CRUD, seeded starting source records.

**plain_change**  
Before this issue, sources are only files on disk or documents in a folder. After this issue, sources exist as first-class records the system can reference in provenance and workflows.

**scope**
- `Source` model
- admin registration
- seed data for current source keys
- validation on source ID uniqueness

**instruction_to_codex**
- Implement `Source` model in the lexicon/editorial app.
- Include source key, title, authority level, rights/usage note, ingestion style, and current filename.
- Add admin CRUD.
- Seed all current source keys from this spec.
- Make the source key unique and stable.
- Keep the model simple and extensible.

**acceptance_criteria**
- migration exists
- source records can be created/edited in admin
- seed command or fixture creates all key source records
- source keys are unique
- admin list view is usable

**out_of_scope**
- provenance JSON on every other model
- extraction logic

**blockers**
- ISSUE-001
- ISSUE-000

**labels**
- `state:blocked`
- `type:feature`
- `area:source`
- `area:editorial`
- `phase:1`
- `exec:agent`

## ISSUE-003 — Implement shared record primitives

**goal**  
Create the reusable conventions all canonical records depend on.

**delivers**  
Patterns/utilities for UUID primary keys, public IDs, provenance support, revisions, and deprecation markers.

**plain_change**  
Before this issue, each model would invent its own identity and metadata conventions. After this issue, later records can be built consistently.

**scope**
- UUID pattern
- public ID generation strategy
- provenance field convention
- revision field convention
- deprecation field convention

**instruction_to_codex**
- Create reusable utilities/mixins for canonical record identity and metadata.
- Standardize on UUID primary keys.
- Provide a path for human-readable `public_id` generation.
- Provide base-field patterns for provenance, revision, and deprecation markers.
- Keep this thin; do not over-abstract.

**acceptance_criteria**
- shared base pattern exists
- future models can consume it cleanly
- public ID generation approach is documented in code comments or docs
- no premature inheritance maze

**out_of_scope**
- full domain model set
- business-specific validators

**blockers**
- ISSUE-001

**labels**
- `state:blocked`
- `type:feature`
- `area:foundation`
- `area:lexicon`
- `phase:1`
- `exec:agent`

## ISSUE-004 — Implement editorial governance primitives

**goal**  
Provide the review, audit, and decision structures that make the dataset trustworthy.

**delivers**  
Review-note model, editorial-decision model, audit-log model, basic review-state conventions, role-aware permissions scaffold.

**plain_change**  
Before this issue, records can exist but not be governed. After this issue, human review and change history become real system concepts.

**scope**
- review note
- editorial decision
- audit log
- role scaffolding
- review-state enum conventions

**instruction_to_codex**
- Implement `ReviewNote`, `EditorialDecision`, and `AuditLog`.
- Add basic role-aware permission structure for viewer/editor/admin style separation.
- Add admin visibility for these objects.
- Keep the first version simple and queryable.
- Do not implement a full custom workflow engine.

**acceptance_criteria**
- migrations exist
- review notes can attach to records
- editorial decisions can record affected records
- audit log structure exists
- basic permissions scaffolding is present

**out_of_scope**
- polished review UI
- full queue experience

**blockers**
- ISSUE-001
- ISSUE-003

**labels**
- `state:blocked`
- `type:feature`
- `area:editorial`
- `area:security`
- `phase:1`
- `exec:agent`

## ISSUE-005 — Implement release/version primitives

**goal**  
Create the versioning objects the API and publishing workflow depend on.

**delivers**  
`DataRelease` model, rule-set version convention, current release lookup utilities, publish guard skeleton.

**plain_change**  
Before this issue, data has no durable release identity. After this issue, records and API responses can be tied to releases and rule versions.

**scope**
- release model
- current release lookup
- rule-set version config
- publish guard skeleton

**instruction_to_codex**
- Implement `DataRelease`.
- Add a service/helper for getting current release.
- Establish `rule_set_version` storage convention.
- Keep the publishing logic minimal for now.
- Make later serializers able to use current release metadata.

**acceptance_criteria**
- migration exists
- current release can be created and queried
- rule-set version convention exists
- later code can depend on a current release API

**out_of_scope**
- full release workflow
- changelog rendering

**blockers**
- ISSUE-001
- ISSUE-003

**labels**
- `state:blocked`
- `type:feature`
- `area:release`
- `area:foundation`
- `phase:1`
- `exec:agent`

## ISSUE-006 — Configure database search extensions, Redis, Celery, and observability scaffold

**goal**  
Set up the infrastructure later slices need for search, caching, and async jobs.

**delivers**  
Postgres extensions, Redis wiring, Celery app, metrics/logging scaffold.

**plain_change**  
Before this issue, later features would need to improvise infra. After this issue, search and async paths can be built on known primitives.

**scope**
- `pg_trgm`
- `unaccent`
- Redis
- Celery
- baseline logging/metrics setup

**instruction_to_codex**
- Add Postgres extension migration or setup path for `pg_trgm` and `unaccent`.
- Wire Redis config.
- Create Celery application scaffold.
- Add logging format and a minimal metrics hook or placeholder.
- Do not build caching policies yet.

**acceptance_criteria**
- app can connect to Redis
- Celery app initializes
- Postgres extensions are documented and installable
- no feature code depends on ad hoc infra later

**out_of_scope**
- concrete cache logic
- dashboard UI

**blockers**
- ISSUE-001

**labels**
- `state:blocked`
- `type:infra`
- `area:foundation`
- `area:observability`
- `phase:1`
- `exec:agent`

## ISSUE-007 — Build phonology primitives: grapheme segmentation and syllabification

**goal**  
Implement reusable phonology primitives required by search, validation, games, and later language features.

**delivers**  
Grapheme segmentation utility, syllabification utility, unit tests, shared compute hooks.

**plain_change**  
Before this issue, the system cannot compute grapheme length or syllables consistently. After this issue, later lexical and game features can rely on stored phonological fields.

**scope**
- grapheme inventory table
- segmentation utility
- syllabification utility
- tests
- save-time compute hooks design

**instruction_to_codex**
- Implement a greedy longest-match grapheme segmenter.
- Keep grapheme inventory configurable/versioned.
- Implement syllabification suitable for stored lexical fields.
- Add robust tests from representative Shona forms.
- Prepare helper functions for model save hooks, but do not wire every model yet.

**acceptance_criteria**
- segmentation utility returns ordered grapheme units
- syllabification returns stable output
- tests cover multi-letter graphemes
- functions are reusable by future models

**out_of_scope**
- pattern search endpoint
- game endpoints
- full phonology theory layer

**blockers**
- ISSUE-001

**labels**
- `state:blocked`
- `type:feature`
- `area:phonology`
- `area:lexicon`
- `phase:3`
- `exec:agent`

## ISSUE-008 — Create Hannan parser fixture corpus

**goal**  
Create the annotated examples needed to build the Hannan parser safely.

**delivers**  
A hand-verified fixture corpus of Hannan entry samples covering major notation patterns.

**plain_change**  
Before this issue, Codex would be coding the parser blind. After this issue, parser work is anchored in known-good examples.

**scope**
- fixture format
- representative sample selection
- manual annotation guidelines
- starter annotated set

**instruction_to_codex**
- Create a fixture format under `tests/fixtures/hannan/`.
- Define JSON or YAML structure for raw entry text and expected parse fields.
- Add documentation for how humans should annotate future entries.
- Seed the fixture corpus with a meaningful initial set of varied entries.
- Do not overfit to one narrow entry style.

**acceptance_criteria**
- fixture format exists
- at least an initial representative sample is checked in
- annotation docs exist
- later parser tests can load fixtures directly

**out_of_scope**
- parser implementation
- full corpus parsing

**blockers**
- ISSUE-000
- ISSUE-002

**labels**
- `state:blocked`
- `type:data`
- `area:parser`
- `area:source`
- `phase:0`
- `exec:human`

## ISSUE-009 — Implement Hannan parser v1

**goal**  
Parse digitized Hannan entry text into structured candidate data.

**delivers**  
First working Hannan parser with structured output and fixture-driven tests.

**plain_change**  
Before this issue, Hannan is still mostly compact text. After this issue, the system can mechanically extract candidate lexical structure from digitized Hannan entries.

**scope**
- headword parsing
- tone bracket parsing
- dialect marker parsing
- POS parsing
- sense boundary parsing
- cross-reference parsing
- ideophone marker detection
- confidence scoring skeleton

**instruction_to_codex**
- Build parser code in a dedicated module, not inside models.
- Input is digitized entry text, not OCR image output.
- Return a structured parse object that preserves uncertain fields.
- Include confidence or parse completeness markers.
- Fail soft: partial parse is acceptable if uncertainty is preserved.
- Test against the annotated fixture corpus.

**acceptance_criteria**
- parser reads fixture inputs and returns structured output
- partial parses are represented explicitly
- tests cover multiple entry shapes
- code is modular and not embedded in admin or view logic

**out_of_scope**
- full editorial queue
- canonical record creation
- UI polish

**blockers**
- ISSUE-008

**labels**
- `state:blocked`
- `type:feature`
- `area:parser`
- `area:lexicon`
- `phase:0`
- `exec:agent`

## ISSUE-010 — Implement extraction-unit model and digitized source review queue

**goal**  
Store parsed source fragments as reviewable candidate units.

**delivers**  
`ExtractionUnit` model, admin/review list basics, parser-output persistence.

**plain_change**  
Before this issue, parse output is ephemeral. After this issue, candidate source extracts become trackable review objects.

**scope**
- extraction unit model
- source linkage
- raw text storage
- parser output storage
- confidence storage
- review status field
- basic admin list

**instruction_to_codex**
- Implement `ExtractionUnit` model.
- Store source key, source location reference, raw text, parser output, parser status, confidence, and review status.
- Add admin registration and useful list filters.
- Keep the first review experience in admin if needed.
- Make sure extraction units can link to future canonical records.

**acceptance_criteria**
- migration exists
- extraction units can be created from parser output
- admin shows queue with useful filters
- parser output persists as structured data

**out_of_scope**
- polished review app
- batch import of all sources

**blockers**
- ISSUE-002
- ISSUE-009
- ISSUE-004

**labels**
- `state:blocked`
- `type:feature`
- `area:parser`
- `area:editorial`
- `phase:2`
- `exec:agent`

## ISSUE-011 — Build canonical lexical core slice: Lemma + Sense + Tone + Form

**goal**  
Create the smallest end-to-end canonical lexical slice that can represent real dictionary content.

**delivers**  
`Lemma`, `Sense`, `ToneRecord`, and `Form` models with admin CRUD and basic validations.

**plain_change**  
Before this issue, the system can parse candidates but cannot hold real reviewed dictionary content. After this issue, a reviewed lexical record can exist canonically.

**scope**
- lexical core models
- admin CRUD
- provenance fields
- phonology field wiring
- basic validators

**instruction_to_codex**
- Implement `Lemma`, `Sense`, `ToneRecord`, and `Form`.
- Use shared record primitives from earlier issues.
- Add save-time phonology field computation for lemma/form display strings where applicable.
- Include admin CRUD with useful inline or linked relationships.
- Keep model constraints practical, not over-constrained.

**acceptance_criteria**
- migrations exist
- admin can create and inspect linked lexical records
- phonology fields compute on save
- provenance structure is available
- lexical core is test-covered

**out_of_scope**
- public endpoints
- full ingestion automation

**blockers**
- ISSUE-003
- ISSUE-004
- ISSUE-007

**labels**
- `state:blocked`
- `type:feature`
- `area:lexicon`
- `area:editorial`
- `phase:2`
- `exec:agent`

## ISSUE-012 — Implement publish path from reviewed extraction unit into canonical lexical records

**goal**  
Turn one reviewed candidate extraction into canonical data.

**delivers**  
Service or workflow that creates canonical lexical records from approved extraction units.

**plain_change**  
Before this issue, candidates stay trapped in the queue. After this issue, reviewed source data can become real product data.

**scope**
- extraction-to-canonical mapping service
- review status transition
- provenance propagation
- linking extraction unit to created records

**instruction_to_codex**
- Create a service layer for publishing an approved extraction unit.
- Map parsed fields into `Lemma`, `Sense`, `ToneRecord`, and `Form`.
- Preserve provenance and uncertainty markers where needed.
- Record the linkage so editors can trace canonical records back to extraction units.
- Keep the first path narrow and reliable.

**acceptance_criteria**
- one approved extraction unit can be published into canonical records
- provenance is preserved
- created records link back to origin
- tests cover success and partial-data cases

**out_of_scope**
- full batch publish
- advanced merge/split logic

**blockers**
- ISSUE-010
- ISSUE-011

**labels**
- `state:blocked`
- `type:feature`
- `area:editorial`
- `area:lexicon`
- `phase:2`
- `exec:hitl`

## ISSUE-013 — Build noun-class subsystem

**goal**  
Implement noun classes as first-class infrastructure.

**delivers**  
`NounClass` model, admin CRUD, concord fields, lemma linkage, serializer-ready structure.

**plain_change**  
Before this issue, noun-class information is ad hoc. After this issue, it becomes explicit infrastructure the API and morphology can depend on.

**scope**
- noun class model
- concord fields
- admin CRUD
- linkage from lemmas
- validation rules

**instruction_to_codex**
- Implement `NounClass` with full concord-related fields needed for later morphology.
- Keep model names and field names readable.
- Support dialect overrides in a future-ready way.
- Add admin CRUD and tests.
- Do not build morphology endpoints yet.

**acceptance_criteria**
- migration exists
- noun classes can be managed in admin
- lemmas can link to noun class
- data shape supports future morphology work

**out_of_scope**
- full morphology analysis
- noun derivation generation

**blockers**
- ISSUE-011

**labels**
- `state:blocked`
- `type:feature`
- `area:morphology`
- `area:lexicon`
- `phase:3`
- `exec:agent`

## ISSUE-014 — Build noun-class validation and QA lane using Fortune + Maumbirwo

**goal**  
Create a validation workflow for noun-class data using the grammar and noun-formation sources.

**delivers**  
Validation rules, QA checklist, and editorial guidance for noun-class assignment.

**plain_change**  
Before this issue, noun classes may be stored but not systematically verified. After this issue, noun-class assignment has explicit validation support.

**scope**
- validation notes
- QA checklist
- reference mapping to source fields
- editorial workflow guidance

**instruction_to_codex**
- Create a documentation artifact and optional admin guidance for validating noun-class assignments.
- Use `source_fortune` and `source_maumbirwo` as validation sources.
- Focus on practical editorial use, not theoretical exhaustiveness.
- Keep the output lightweight enough to be used inside future review issues.

**acceptance_criteria**
- noun-class QA document exists
- validation sources are explicitly named
- editors can follow the checklist for assignments
- future issues can reference this instead of re-explaining

**out_of_scope**
- auto-solving every noun-class dispute
- mass data import

**blockers**
- ISSUE-000

**labels**
- `state:blocked`
- `type:docs`
- `area:morphology`
- `area:pedagogy`
- `phase:3`
- `exec:human`

## ISSUE-015 — Confirm and structure Fortune extraction for morphology rules

**goal**  
Make Fortune directly usable for implementing morphology rules, rather than just citing it abstractly.

**delivers**  
A practical extraction plan for rule-relevant sections of Fortune and a starter structured rule reference.

**plain_change**  
Before this issue, Fortune is present but not operationalized. After this issue, morphology work can point to concrete structured rule inputs.

**scope**
- identify relevant sections
- structure rule extraction plan
- record starter rule reference
- define what later analyzer/generator issues should consume

**instruction_to_codex**
- Create a doc or structured artifact under `docs/morphology/fortune_rule_plan.md`.
- Identify the Fortune sections most relevant to noun classes, concords, morphophonemics, and verbal constructions.
- Define the extraction/output shape later morphology issues should expect.
- Keep it implementation-facing.

**acceptance_criteria**
- Fortune extraction plan exists
- relevant rule domains are identified
- later analyzer/generator issues can reference the plan

**out_of_scope**
- fully implemented morphology engine
- rule parser automation

**blockers**
- ISSUE-000

**labels**
- `state:blocked`
- `type:research`
- `area:morphology`
- `area:source`
- `phase:3`
- `exec:human`

## ISSUE-016 — Implement morphology analyze endpoint v1

**goal**  
Provide first public grammar-aware analysis for bounded verb forms.

**delivers**  
`POST /v1/analyze` with structured output for supported verb forms.

**plain_change**  
Before this issue, the platform stores lexical data but cannot analyze user input morphologically. After this issue, it can decompose bounded forms into useful grammatical structure.

**scope**
- analyze endpoint
- request/response schema
- supported feature set
- confidence output
- rule-set version output

**instruction_to_codex**
- Implement a bounded first version of `/v1/analyze`.
- Use a service layer, not view-level logic.
- Return clear structured output including supported slots.
- Include `rule_set_version` and `confidence`.
- Be honest about unsupported cases; return structured failure where necessary.

**acceptance_criteria**
- endpoint exists
- tests cover successful analyses and failures
- response includes confidence and rule-set version
- unsupported inputs fail clearly

**out_of_scope**
- full language coverage
- batch analysis
- speculative advanced tone modeling

**blockers**
- ISSUE-013
- ISSUE-015
- ISSUE-007
- ISSUE-005

**labels**
- `state:blocked`
- `type:feature`
- `area:morphology`
- `area:api`
- `phase:3`
- `exec:agent`

## ISSUE-017 — Implement morphology generate endpoint v1

**goal**  
Generate bounded Shona forms from supported lexical and feature inputs.

**delivers**  
`POST /v1/generate`, generation metadata, warnings, rule-set versioning.

**plain_change**  
Before this issue, the platform can maybe analyze some forms but cannot generate them. After this issue, it becomes a two-way morphology service for supported cases.

**scope**
- generate endpoint
- feature schema
- generation metadata
- warnings array
- confidence output

**instruction_to_codex**
- Implement `/v1/generate` as a service-driven endpoint.
- Require structured feature input.
- Return generated form plus metadata, warnings, and rule-set version.
- Keep unsupported combinations explicit rather than silently guessing.
- Reuse morphology rule services where possible.

**acceptance_criteria**
- endpoint exists
- tests cover supported generation cases
- warnings appear where rules are partial
- response is consistent and documented

**out_of_scope**
- total language coverage
- async batch generation

**blockers**
- ISSUE-016

**labels**
- `state:blocked`
- `type:feature`
- `area:morphology`
- `area:api`
- `phase:3`
- `exec:agent`

## ISSUE-018 — Build pedagogy and curriculum metadata design

**goal**  
Define what educational metadata belongs in the system and how it should be represented.

**delivers**  
Pedagogy metadata design document and initial label/value taxonomy.

**plain_change**  
Before this issue, learner support is generic. After this issue, the platform has a concrete educational metadata plan tied to real curriculum sources.

**scope**
- pedagogical tags
- curriculum-domain tags
- learner-surface decisions
- relation to existing label taxonomy

**instruction_to_codex**
- Create a document under `docs/pedagogy/pedagogy_metadata.md`.
- Use `source_curriculum_notes`, `source_zimsec_syllabus`, and `source_fsi`.
- Define practical, minimal pedagogical metadata for V1 and what is deferred.
- Prefer label-style enrichment over bloated core models.
- Include examples of how tags might be used by API consumers.

**acceptance_criteria**
- pedagogy metadata doc exists
- curriculum sources are reflected
- V1 vs later scope is explicit
- future issues can implement against it

**out_of_scope**
- full curriculum engine
- school report generation

**blockers**
- ISSUE-000

**labels**
- `state:blocked`
- `type:docs`
- `area:pedagogy`
- `area:source`
- `phase:4`
- `exec:human`

## ISSUE-019 — Implement learner metadata fields and FSI mapping slice

**goal**  
Add the first real learner-oriented metadata to lexical records.

**delivers**  
Learner fields on canonical records plus first mapping workflow from FSI.

**plain_change**  
Before this issue, records are linguistically rich but not learner-aware. After this issue, records can be ranked and filtered for educational use.

**scope**
- learner fields
- first appearance/unit fields
- frequency tier/score path
- mapping workflow

**instruction_to_codex**
- Add or finalize learner-related fields needed by the PRD.
- Build a first mapping workflow from `source_fsi`.
- Keep scoring logic transparent and adjustable.
- Do not pretend to solve all ranking science in v1.

**acceptance_criteria**
- learner metadata fields exist
- records can store first-appearance / learner metadata
- initial mapping path from FSI exists
- tests cover field behavior

**out_of_scope**
- full corpus ingestion
- advanced recommendation logic

**blockers**
- ISSUE-011
- ISSUE-018

**labels**
- `state:blocked`
- `type:feature`
- `area:pedagogy`
- `area:lexicon`
- `phase:4`
- `exec:hitl`

## ISSUE-020 — Build orthography and normalization policy slice

**goal**  
Define how canonical forms, variants, joining/separation rules, and learner-facing correctness will behave.

**delivers**  
Normalization policy doc plus implementation notes for search and validation.

**plain_change**  
Before this issue, orthographic behavior is implicit and inconsistent. After this issue, search, validation, and docs can follow a single policy.

**scope**
- joining/separation rules
- punctuation/correctness relevance
- canonical vs variant handling
- modernization/historical form policy
- normalization notes

**instruction_to_codex**
- Create `docs/language/orthography_policy.md`.
- Use `source_hannan`, `source_curriculum_notes`, and `source_zimsec_syllabus`.
- Focus on practical rules that affect canonical storage, search normalization, and validation behavior.
- Document what is enforced, what is normalized, and what is merely advisory.

**acceptance_criteria**
- policy doc exists
- canonical vs normalized distinctions are clear
- search and validation issues can depend on it
- learner-facing correctness implications are noted

**out_of_scope**
- implementing all normalization code
- spelling correction engine

**blockers**
- ISSUE-000

**labels**
- `state:blocked`
- `type:docs`
- `area:search`
- `area:pedagogy`
- `phase:4`
- `exec:human`

## ISSUE-021 — Implement lexical read endpoint slice

**goal**  
Expose the first canonical lexical records through the public API.

**delivers**  
`GET /v1/lemmas/{public_id}` with standard response envelope and core depth.

**plain_change**  
Before this issue, canonical records exist only internally. After this issue, external clients can retrieve a real lexical record from the API.

**scope**
- read endpoint
- core serializer
- standard envelope
- error schema
- tests

**instruction_to_codex**
- Implement a core lemma read endpoint first.
- Include standard response envelope with release and rule-set metadata.
- Keep depth handling minimal at first if necessary.
- Implement clean not-found behavior.

**acceptance_criteria**
- endpoint exists
- serializer returns stable shape
- envelope includes release metadata
- tests cover success and not-found

**out_of_scope**
- full search
- advanced depth tiers

**blockers**
- ISSUE-011
- ISSUE-005

**labels**
- `state:blocked`
- `type:feature`
- `area:api`
- `area:lexicon`
- `phase:5`
- `exec:agent`

## ISSUE-022 — Implement API key auth and rate limiting

**goal**  
Protect the public API with plan-aware authentication and rate limiting.

**delivers**  
API key model path, auth middleware/path, hashed keys, rate limit handling.

**plain_change**  
Before this issue, the API is only locally callable. After this issue, it behaves like a real controlled product.

**scope**
- API key storage
- hashing
- auth integration
- rate headers
- plan tiers

**instruction_to_codex**
- Implement API key support with hashed key storage.
- Add DRF-compatible auth integration.
- Add rate limiting and rate limit headers.
- Keep key creation/admin mechanics practical.
- Do not store raw keys beyond first display paths.

**acceptance_criteria**
- authenticated requests work
- invalid keys fail correctly
- rate limit headers appear
- tests cover valid and invalid paths

**out_of_scope**
- billing
- self-service portal

**blockers**
- ISSUE-001

**labels**
- `state:blocked`
- `type:feature`
- `area:api`
- `area:security`
- `phase:5`
- `exec:agent`

## ISSUE-023 — Implement search v1 slice

**goal**  
Provide the first useful public search path over canonical lexical data.

**delivers**  
`GET /v1/search` with exact match, lemma match, normalization hook, zero-result structure.

**plain_change**  
Before this issue, users must know exact IDs. After this issue, they can search the language data in a practical way.

**scope**
- query endpoint
- exact form match
- lemma match
- normalization hook
- structured zero results

**instruction_to_codex**
- Implement a bounded first search version.
- Support exact form and direct lemma matching first.
- Use normalization policy hooks where available.
- Return structured zero-result responses, not empty ad hoc responses.
- Keep ranking logic simple in v1.

**acceptance_criteria**
- endpoint exists
- exact and lemma matches work
- zero-result response shape is stable
- tests cover common cases

**out_of_scope**
- fuzzy search
- pattern search
- reverse English lookup

**blockers**
- ISSUE-021
- ISSUE-020
- ISSUE-011

**labels**
- `state:blocked`
- `type:feature`
- `area:search`
- `area:api`
- `phase:5`
- `exec:agent`

## ISSUE-024 — Implement figurative language data model foundation

**goal**  
Create a unified model foundation for figurative and expressive forms without forcing all subtypes to be complete immediately.

**delivers**  
A broad figurative-expression schema or parent model design with subtype support, fully prepared for staged rollout.

**plain_change**  
Before this issue, proverb work would hard-code the system into one narrow path. After this issue, figurative-language growth has a clean architectural home.

**scope**
- parent concept/model design
- subtype field
- shared metadata fields
- link to lemmas
- pedagogy/culture-ready metadata fields

**instruction_to_codex**
- Implement a broad `FigurativeExpression` style foundation, or equivalent clean schema.
- Support subtype storage for at least:
  - `tsumo`
  - `madimikira`
  - reserved future types:
    - `madunhurirwa`
    - `nyaudzosingwi`
    - `fananidzo`
    - `enzaniso`
    - `chibhende`
- Include shared fields such as expression text, idiomatic meaning, English rendering, usage note, cultural themes, provenance, review status, and linked lemmas.
- Keep the first implementation broad in design but narrow in active use.

**acceptance_criteria**
- migration exists
- model/schema supports subtype-based expansion
- shared metadata fields are present
- future subtypes can be added without redesign

**out_of_scope**
- implementing all subtypes fully
- public endpoints for every subtype

**blockers**
- ISSUE-003
- ISSUE-004

**labels**
- `state:blocked`
- `type:feature`
- `area:figurative_language`
- `area:lexicon`
- `phase:4`
- `exec:agent`

## ISSUE-025 — Implement tsumo slice

**goal**  
Deliver first-class proverb support on the new figurative-language foundation.

**delivers**  
Tsumo records, review/admin flow, API read/list path, cultural theme support.

**plain_change**  
Before this issue, figurative-language foundation exists but no real user-facing proverb product does. After this issue, the platform has first-class proverb functionality.

**scope**
- tsumo subtype usage
- admin CRUD/review
- API list/read
- theme metadata
- linked lemmas

**instruction_to_codex**
- Use the figurative-language foundation from ISSUE-024.
- Implement the first active subtype: `tsumo`.
- Support text, meaning, English rendering, cultural themes, linked lemmas, provenance, and review status.
- Build list and detail endpoints.
- Keep endpoint naming flexible enough not to block future broader expressions endpoints.

**acceptance_criteria**
- tsumo records can be created and reviewed
- API can list and retrieve tsumo
- themes and lemma links are present
- tests cover basic flows

**out_of_scope**
- all figurative subtypes
- advanced recommendation/browse UI

**blockers**
- ISSUE-024

**labels**
- `state:blocked`
- `type:feature`
- `area:figurative_language`
- `area:api`
- `phase:4`
- `exec:hitl`

## ISSUE-026 — Implement madimikira slice

**goal**  
Deliver first-class idiom support on the same figurative-language foundation.

**delivers**  
Madimikira records, review/admin flow, API list/read path, idiomatic meaning fields.

**plain_change**  
Before this issue, the figurative-language subsystem only supports tsumo. After this issue, it supports both tsumo and madimikira without redesign.

**scope**
- madimikira subtype usage
- admin CRUD/review
- API list/read
- meaning/rendering metadata
- linked lemmas

**instruction_to_codex**
- Reuse the figurative-language foundation and subtype machinery from ISSUE-024.
- Add first active support for `madimikira`.
- Preserve room for later `madunhurirwa`.
- Keep implementation symmetric with tsumo where possible but allow subtype-specific presentation differences.

**acceptance_criteria**
- madimikira can be stored and reviewed
- API can list and retrieve madimikira
- tests cover subtype behavior
- tsumo implementation is not broken by subtype expansion

**out_of_scope**
- madunhurirwa implementation
- all future figurative types

**blockers**
- ISSUE-024

**labels**
- `state:blocked`
- `type:feature`
- `area:figurative_language`
- `area:api`
- `phase:4`
- `exec:hitl`

## ISSUE-027 — Build figurative language enrichment plan using Shona Yedu + Tsumo Tsika

**goal**  
Operationalize the enrichment sources for tsumo and madimikira without overpromoting them above core sources.

**delivers**  
Enrichment strategy doc, import candidate shape, authority guidance for figurative-language enrichment.

**plain_change**  
Before this issue, the system knows these sources exist but not how to consume them safely. After this issue, future ingestion batches can use them consistently.

**scope**
- candidate import strategy
- authority policy
- dedupe guidance
- theme enrichment guidance

**instruction_to_codex**
- Create `docs/figurative_language/enrichment_plan.md`.
- Use `source_shona_yedu` and `source_tsumo_tsika`.
- Define how high-volume proverb material is ingested as candidates rather than blindly canonical.
- Define how cultural themes may be added or validated.
- Include guidance for future `madunhurirwa` support.

**acceptance_criteria**
- enrichment plan exists
- source authority guidance is explicit
- tsumo/madimikira enrichment strategy is documented
- future `madunhurirwa` lane is acknowledged

**out_of_scope**
- full import implementation
- automatic trust of all enrichment content

**blockers**
- ISSUE-000

**labels**
- `state:blocked`
- `type:docs`
- `area:figurative_language`
- `area:source`
- `phase:4`
- `exec:human`

## ISSUE-028 — Build reference web dictionary search page

**goal**  
Create the first public-facing dictionary UI using only API data.

**delivers**  
Search page for lemma/form lookup backed by public API.

**plain_change**  
Before this issue, only API clients can consume the system. After this issue, normal users can start interacting with it directly.

**scope**
- search UI
- query input
- result list
- API integration
- basic states

**instruction_to_codex**
- Build the web page against the public API, not internal DB shortcuts.
- Support search query entry and result rendering.
- Handle loading, empty, and error states.
- Keep the design functional first.

**acceptance_criteria**
- page loads
- search calls public API
- results display coherently
- empty state is informative

**out_of_scope**
- advanced design polish
- full entry display

**blockers**
- ISSUE-023
- ISSUE-022

**labels**
- `state:blocked`
- `type:feature`
- `area:web`
- `area:search`
- `phase:6`
- `exec:agent`

## ISSUE-029 — Build entry page slice

**goal**  
Create the first full entry page showing lexical data from the API.

**delivers**  
Entry page with core lexical display, examples, noun class or tone where available, and linked figurative-language content where supported.

**plain_change**  
Before this issue, the web app can search but not show a proper entry. After this issue, it behaves like a real dictionary.

**scope**
- entry UI
- API integration
- lexical fields
- examples
- linked figurative-language section
- developer proof JSON view

**instruction_to_codex**
- Build an entry page that consumes the public API only.
- Show headword, POS, gloss/definitions, examples, and other available metadata.
- Where linked tsumo/madimikira exist, display them in a related section.
- Add an optional raw JSON developer panel.

**acceptance_criteria**
- entry page renders from public API data
- core lexical metadata is displayed
- related figurative-language content appears when available
- raw JSON view works

**out_of_scope**
- final design system polish
- advanced personalization

**blockers**
- ISSUE-021
- ISSUE-025
- ISSUE-026

**labels**
- `state:blocked`
- `type:feature`
- `area:web`
- `area:lexicon`
- `phase:6`
- `exec:agent`

## ISSUE-030 — Publish OpenAPI spec and developer quickstart

**goal**  
Provide the docs needed for external developers to start integrating quickly.

**delivers**  
OpenAPI publication, quickstart, endpoint docs, auth docs, example requests.

**plain_change**  
Before this issue, the API may work but is hard to adopt. After this issue, external developers can start integrating with confidence.

**scope**
- OpenAPI generation
- quickstart
- auth docs
- endpoint docs
- example payloads

**instruction_to_codex**
- Generate OpenAPI from DRF where possible.
- Create a concise quickstart that gets a developer to a first successful request fast.
- Document auth, search, lexical reads, and any available figurative-language endpoints.
- Keep docs accurate to current implementation only.

**acceptance_criteria**
- OpenAPI spec is published
- quickstart exists
- example requests work against current code
- docs do not describe nonexistent features

**out_of_scope**
- SDK generation
- full developer portal

**blockers**
- ISSUE-021
- ISSUE-022
- ISSUE-023

**labels**
- `state:blocked`
- `type:docs`
- `area:docs`
- `area:api`
- `phase:5`
- `exec:agent`

## ISSUE-031 — Add sandbox environment and release-ready API packaging

**goal**  
Prepare the product for bounded external beta use.

**delivers**  
Sandbox mode, subset publishing support, release metadata exposure, beta-ready packaging.

**plain_change**  
Before this issue, the API is technically public-capable but not safely packaged for beta use. After this issue, it can be exposed in a controlled public-beta shape.

**scope**
- sandbox subset concept
- sandbox key behavior
- release metadata exposure
- bounded packaging

**instruction_to_codex**
- Implement minimal sandbox-aware behavior.
- Support a limited published subset mode without requiring the full production dataset.
- Ensure release metadata is present in responses.
- Keep implementation simple and transparent.

**acceptance_criteria**
- sandbox mode exists
- a subset dataset can be served
- sandbox auth path works
- release metadata is present

**out_of_scope**
- billing
- full provisioning portal

**blockers**
- ISSUE-022
- ISSUE-030
- ISSUE-005

**labels**
- `state:blocked`
- `type:ops`
- `area:release`
- `area:api`
- `phase:7`
- `exec:agent`

## ISSUE-032 — Add caching and observability to hot paths

**goal**  
Make core product flows operationally sane for beta.

**delivers**  
Caching on key read/search paths, request metrics, zero-result logging, latency tracking.

**plain_change**  
Before this issue, the product may work but without good operational visibility. After this issue, you can observe and improve real usage.

**scope**
- cache lemma reads
- cache common search paths
- zero-result logging
- latency metrics
- basic alert-friendly instrumentation

**instruction_to_codex**
- Add cache hooks to stable hot paths only.
- Instrument search and read endpoints.
- Log zero-result searches in a structured way.
- Keep observability practical, not overengineered.

**acceptance_criteria**
- hot paths are cached
- search metrics/logs exist
- zero-result logging exists
- code remains readable

**out_of_scope**
- full BI platform
- advanced ranking system

**blockers**
- ISSUE-006
- ISSUE-021
- ISSUE-023

**labels**
- `state:blocked`
- `type:ops`
- `area:observability`
- `area:search`
- `phase:7`
- `exec:agent`

## ISSUE-033 — Launch preparation issue

**goal**  
Prepare the first public beta release.

**delivers**  
Release checklist, final dependency review, beta partner checklist, launch readiness artifact.

**plain_change**  
Before this issue, the product exists but is not formally prepared for beta. After this issue, the team has a concrete release readiness decision.

**scope**
- release checklist
- dependency verification
- docs readiness
- beta-readiness summary
- launch decision artifact

**instruction_to_codex**
- Create a release readiness document under `docs/release/beta_release_checklist.md`.
- Summarize what must be true for beta.
- Include API, data, docs, sandbox, observability, and review status considerations.
- Keep it practical and check-box based.

**acceptance_criteria**
- checklist exists
- major readiness dimensions are covered
- doc is short and operationally useful

**out_of_scope**
- actual marketing launch
- commercial pricing strategy

**blockers**
- ISSUE-028
- ISSUE-029
- ISSUE-030
- ISSUE-031
- ISSUE-032

**labels**
- `state:blocked`
- `type:ops`
- `area:release`
- `area:docs`
- `phase:7`
- `exec:human`

---

# 11. Repeated Work Lanes to Create Progressively

These should not all be created at once.

## 11.1 Editorial lexical tranches
Template:
- review and publish next 250 lemma candidates from approved extraction units

Use repeated issues:
- `LEX-BATCH-001`
- `LEX-BATCH-002`
- etc.

## 11.2 Tsumo enrichment batches
Template:
- review and promote next bounded proverb candidate set into canonical figurative-language records

## 11.3 Madimikira enrichment batches
Template:
- review and promote next bounded idiom candidate set into canonical figurative-language records

## 11.4 Future madunhurirwa lane
Not first delivery, but architecture should leave room.

Create later when:
- tsumo and madimikira flows are stable
- subtype expansion can happen without schema redesign

---

# 12. Recommended Critical Path

This is the dependency-complete path for a first public-beta shape. Items outside this list can still run when their own blockers clear, but this path should not skip prerequisite foundation work.

1. ISSUE-000  
2. ISSUE-001  
3. ISSUE-002  
4. ISSUE-003  
5. ISSUE-004  
6. ISSUE-005  
7. ISSUE-006  
8. ISSUE-007  
9. ISSUE-008  
10. ISSUE-009  
11. ISSUE-010  
12. ISSUE-011  
13. ISSUE-012  
14. ISSUE-021  
15. ISSUE-022  
16. ISSUE-023  
17. ISSUE-024  
18. ISSUE-025  
19. ISSUE-026  
20. ISSUE-030  
21. ISSUE-028  
22. ISSUE-029  
23. ISSUE-031  
24. ISSUE-032  
25. ISSUE-033  

Morphology and pedagogy work can run in parallel once the lexical backbone is stable.

---

# 13. Final Guidance for Codex

When implementing from this backlog:

- do not read all source documents for every issue
- read only the source fragments relevant to the issue’s `instruction_to_codex`
- keep each issue implementation narrow
- preserve provenance and uncertainty rather than silently collapsing ambiguity
- prefer clean extensible schema over one-off hacks
- do not prematurely implement every future subtype or every endpoint named in the PRD
- remember the current figurative-language first delivery is:
  - `tsumo`
  - `madimikira`

The next planned expansions are:
- `madunhurirwa`
- `nyaudzosingwi`
- `fananidzo`
- `enzaniso`
- `chibhende`

The backbone of the product remains:
- lexical trustworthiness
- grammar/morphology correctness
- pedagogical usefulness
- staged delivery
- operational clarity

---

# 14. Summary of Main Changes from the Earlier Rewrite

This rewrite intentionally changes the earlier direction in these ways:

- OCR is removed from the critical path
- Hannan parser is clarified as a digitized dictionary-notation parser
- source roles are explicitly structured
- curriculum docs are upgraded in product importance
- pedagogical metadata is now an intentional subsystem
- figurative language is designed broadly but delivered narrowly at first
- the proverb-only lane is replaced by a broader figurative-language foundation
- `tsumo` and `madimikira` are now explicit first-delivery subtypes
- `madunhurirwa` is left as a deliberate next extension
- source keys are used so the plan survives filename changes
