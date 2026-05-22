# SEARCH-QUALITY-001 - Harden inflected-form search and zero-result feedback

See `docs/backlog/phase2/backlog.md#search-quality-001---harden-inflected-form-search-and-zero-result-feedback` for full context.

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
