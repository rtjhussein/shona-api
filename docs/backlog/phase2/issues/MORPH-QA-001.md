# MORPH-QA-001 - Build real-data morphology regression corpus

See `docs/backlog/phase2/backlog.md#morph-qa-001---build-real-data-morphology-regression-corpus` for full context.

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
