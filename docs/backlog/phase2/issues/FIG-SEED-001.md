# FIG-SEED-001 - Seed first reviewed figurative-language records

See `docs/backlog/phase2/backlog.md#fig-seed-001---seed-first-reviewed-figurative-language-records` for full context.

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
