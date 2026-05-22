# LEX-PUB-001 - Publish next reviewed lexical tranche

See `docs/backlog/phase2/backlog.md#lex-pub-001---publish-next-reviewed-lexical-tranche` for full context.

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
