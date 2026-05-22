# Shona API Phase 2 Backlog

## Product Goals

- Grow the public lexical dataset from a promising seed into a useful reviewable corpus.
- Use real published verbs to strengthen morphology correctness instead of adding unsupported grammar breadth too early.
- Improve search and release safety enough that the current API can be shown confidently.
- Seed figurative-language data after lexical/search confidence improves.

## Scope Constraint

The continuous Hannan ingestion workflow already exists. Phase 2 issues must not rebuild it or treat ingestion as a new project deliverable. They may consume its output.

## LEX-PUB-001 - Publish next reviewed lexical tranche

### goal
Publish the next bounded tranche of review-ready lexical records produced by the existing continuous Hannan workflow.

### delivers
- Reviewed extraction units promoted into canonical lemma/sense/tone/form records
- Batch outcome notes with counts and known leftovers
- Searchable examples that prove the tranche is visible through the current API and dictionary UI

### plain_change
Before this issue, continuous ingestion produces candidates but not enough public lexical coverage.
After this issue, the next tranche of approved candidates is published with provenance and can be used for morphology/search validation.

### scope
- Review current `needs_review` extraction units or the next ready continuous-ingestion output tranche
- Approve, reject, or leave uncertain records explicitly
- Publish approved records through existing publication services and commands
- Verify published records in API search and entry UI

### out_of_scope
- Rebuilding or replacing the continuous Hannan ingestion workflow
- Changing parser architecture
- Creating new public API endpoints

### dependencies
- none

### blocks
- MORPH-QA-001
- SEARCH-QUALITY-001

### parallelization
Classification: `parallel-safe-under-shared-goal`
Reason: It mostly consumes existing data and publication paths, but its outputs become fixtures for morphology/search work.
High-Risk Shared Files: `shona_api/extraction/services.py`, `shona_api/lexicon/models.py`, local database state

### implementation_notes
- Prefer using existing admin, review states, and `publish_hannan_batch`/publication service paths.
- Do not alter the ingestion runner unless a blocking defect prevents publication.
- Preserve source locator, parser status, uncertainty notes, and provenance on all canonical records.
- If local `needs_review` rows are stale or unsuitable, document why and use the next ready tranche from the continuous workflow.

### tdd_requirements
- Target Test File Path: `tests/test_extraction_publish.py`
- Failure Condition: approved tranche publication must preserve provenance and expose published records through existing search/read paths
- Test Pattern: Integration

### acceptance_criteria
- At least one bounded tranche is reviewed with explicit outcomes
- Approved records publish without losing provenance
- Failed or uncertain records remain visible for later editorial follow-up
- Published lemmas are searchable through `/v1/search` and visible in the dictionary UI
- Full pytest suite passes

### closeout_requirements
The implementing agent must report:
- Issue completed: yes/no
- Goal satisfied: yes/no
- What changed
- Files changed
- Database changes
- Commands run
- How to test manually
- How to verify automatically
- Known limitations
- Review hotspots

### recommended_agent
Type: `Infra/Data Agent`
Reasoning effort: high
Reason: This is data/editorial-heavy work with provenance and publication correctness requirements.

## MORPH-QA-001 - Build real-data morphology regression corpus

### goal
Create a regression corpus for the existing present-tense morphology rules using real published verb lemmas.

### delivers
- Fixture set of real published verb stems and expected generated/analyzed forms
- Regression tests for positive present, negative present, subject concords, object concords, and vowel coalescence
- Documentation of unsupported but observed forms to guide future morphology issues

### plain_change
Before this issue, morphology tests prove selected examples but do not strongly reflect the growing published corpus.
After this issue, morphology correctness is anchored in real published data and can catch regressions as lexical coverage grows.

### scope
- Select representative published verb-stem lemmas from the current dataset
- Add tests for supported present-tense analyzer/generator behavior
- Add fixture notes for observed unsupported forms without implementing new grammar breadth
- Confirm object concord and coalescence behavior remains stable

### out_of_scope
- Past tense, future tense, passive, causative, applicative, or other verb extension support
- Changing public morphology request/response contracts
- Reworking the morphology service architecture

### dependencies
- LEX-PUB-001

### blocks
- SEARCH-QUALITY-001

### parallelization
Classification: `serial`
Reason: It should consume the tranche published by `LEX-PUB-001` and becomes a safety net for search improvements.
High-Risk Shared Files: `shona_api/morphology/services.py`, `tests/test_morphology_api.py`

### implementation_notes
- Keep current supported shape: present positive and present negative with optional object concord.
- Prefer fixture-driven tests over hard-coding many one-off assertions.
- Unsupported observed patterns should be recorded as future candidates, not silently accepted.

### tdd_requirements
- Target Test File Path: `tests/test_morphology_api.py`
- Failure Condition: real published verb stems must analyze/generate supported present forms with expected slots and rule IDs
- Test Pattern: Integration

### acceptance_criteria
- Regression corpus includes multiple published verb stems
- Tests cover positive, negative, object concord, and coalescence cases
- Unsupported observed forms are documented as future scope
- Full pytest suite passes

### closeout_requirements
The implementing agent must report:
- Issue completed: yes/no
- Goal satisfied: yes/no
- What changed
- Files changed
- Database changes
- Commands run
- How to test manually
- How to verify automatically
- Known limitations
- Review hotspots

### recommended_agent
Type: `Backend Core Agent`
Reasoning effort: high
Reason: Rule-based morphology needs careful fixture design and regression protection.

## SEARCH-QUALITY-001 - Harden inflected-form search and zero-result feedback

### goal
Make search behavior clearer and more useful for inflected forms without changing the public API contract.

### delivers
- More reliable morphology enrichment behavior in search
- Structured handling/logging for morphology enrichment failures
- Tests for inflected-form search and zero-result cases

### plain_change
Before this issue, search supports exact matches and opportunistic morphology enrichment, but enrichment failures are silent.
After this issue, supported inflected forms produce clearer results and unsupported/failed enrichment is observable.

### scope
- Keep `/v1/search` response shape backwards-compatible
- Preserve exact lemma/form search behavior
- Add tests around inflected forms that resolve through morphology
- Replace broad silent failure with controlled fallback and observable diagnostics
- Improve zero-result feedback where it can be done without breaking clients

### out_of_scope
- Full fuzzy search or ranking overhaul
- New search endpoint
- Large Postgres full-text/trigram implementation

### dependencies
- LEX-PUB-001
- MORPH-QA-001
- RELEASE-SAFETY-001

### blocks
- none

### parallelization
Classification: `serial`
Reason: It touches shared public API behavior and should be protected by the morphology regression corpus first.
High-Risk Shared Files: `shona_api/lexicon/views.py`, `shona_api/lexicon/serializers.py`, `tests/test_lexicon_api.py`

### implementation_notes
- Do not introduce a breaking response shape.
- If morphology enrichment fails internally, return search results normally and record diagnostics through existing logging/metrics hooks.
- Keep exact search deterministic before adding broader matching.

### tdd_requirements
- Target Test File Path: `tests/test_lexicon_api.py`
- Failure Condition: supported inflected search queries must expose morphology enrichment while unsupported forms produce stable zero-result behavior
- Test Pattern: Integration

### acceptance_criteria
- Existing exact-match search tests still pass
- Inflected supported forms return useful morphology enrichment
- Unsupported forms do not crash search
- Enrichment failures are observable in logs or metrics
- Full pytest suite passes

### closeout_requirements
The implementing agent must report:
- Issue completed: yes/no
- Goal satisfied: yes/no
- What changed
- Files changed
- Database changes
- Commands run
- How to test manually
- How to verify automatically
- Known limitations
- Review hotspots

### recommended_agent
Type: `Backend Core Agent`
Reasoning effort: high
Reason: This touches public API behavior, morphology integration, and observability.

## RELEASE-SAFETY-001 - Make current release setup safe and obvious

### goal
Prevent missing current-release configuration from causing confusing protected API failures.

### delivers
- Clear current-release readiness behavior
- Admin or command path for creating/activating a local current release
- Tests documenting protected endpoint behavior when release metadata is missing

### plain_change
Before this issue, most protected API endpoints assume a current `DataRelease` exists.
After this issue, setup is explicit and failure mode is clear, test-covered, and easy to fix.

### scope
- Add or document a lightweight command/admin workflow for current release setup
- Improve failure clarity when no current release exists
- Add tests for missing-release behavior on protected public endpoints
- Update developer docs with the setup command/path

### out_of_scope
- Full release management product
- Versioned data snapshots
- Public launch process

### dependencies
- none

### blocks
- SEARCH-QUALITY-001

### parallelization
Classification: `parallel-safe-under-shared-goal`
Reason: It can run beside lexical publication but should land before search/release-facing work.
High-Risk Shared Files: `shona_api/releases/services.py`, `docs/developer_quickstart.md`, endpoint tests

### implementation_notes
- Keep the solution small and operationally useful.
- Prefer a management command or clear admin path over hidden auto-creation.
- Public API errors should remain client-understandable and testable.

### tdd_requirements
- Target Test File Path: `tests/test_releases.py`
- Failure Condition: missing current release must produce a documented readiness/failure behavior instead of surprising endpoint crashes
- Test Pattern: Integration

### acceptance_criteria
- Local setup docs explain how to create/activate a current release
- Tests cover missing and present current-release states
- Protected endpoints have a clear behavior when release metadata is absent
- Full pytest suite passes

### closeout_requirements
The implementing agent must report:
- Issue completed: yes/no
- Goal satisfied: yes/no
- What changed
- Files changed
- Database changes
- Commands run
- How to test manually
- How to verify automatically
- Known limitations
- Review hotspots

### recommended_agent
Type: `Infra/Data Agent`
Reasoning effort: medium
Reason: This is release/data setup hardening with API contract implications.

## FIG-SEED-001 - Seed first reviewed figurative-language records

### goal
Publish the first bounded set of reviewed figurative-language records for tsumo and/or madimikira.

### delivers
- Initial active reviewed figurative-expression records
- Source/provenance notes for each record
- API/UI verification that public figurative endpoints return real data

### plain_change
Before this issue, figurative-language endpoints exist but local data count is zero.
After this issue, the endpoints demonstrate real reviewed content and can support product demos.

### scope
- Select a small human-reviewed candidate set from approved local source material
- Create active reviewed `tsumo` and/or `madimikira` records
- Link records to lemmas where obvious and safe
- Verify list/detail APIs and entry page related-content behavior

### out_of_scope
- New figurative subtypes such as `madunhurirwa`
- Bulk scraping or automated high-volume enrichment
- Schema redesign

### dependencies
- none

### blocks
- none

### parallelization
Classification: `parallel-safe`
Reason: It uses existing figurative-language model/API paths and does not overlap much with morphology implementation.
High-Risk Shared Files: `shona_api/figurative_language/models.py`, `shona_api/figurative_language/views.py`, local source data

### implementation_notes
- Keep the first set small and reviewable.
- Use existing `subtype_readiness=active` and reviewed/public review states.
- Preserve source notes and uncertainty rather than overclaiming interpretation.

### tdd_requirements
- Target Test File Path: `tests/test_figurative_language_api.py`
- Failure Condition: public figurative endpoints must return seeded reviewed records and hide non-active/non-reviewed records
- Test Pattern: Integration

### acceptance_criteria
- At least one reviewed active record exists for a first figurative subtype
- Public list/detail endpoints return the record
- Non-reviewed or reserved records remain hidden
- Source/provenance notes are present
- Full pytest suite passes

### closeout_requirements
The implementing agent must report:
- Issue completed: yes/no
- Goal satisfied: yes/no
- What changed
- Files changed
- Database changes
- Commands run
- How to test manually
- How to verify automatically
- Known limitations
- Review hotspots

### recommended_agent
Type: `Infra/Data Agent`
Reasoning effort: medium
Reason: This is a small data/editorial slice using existing models and endpoints.
