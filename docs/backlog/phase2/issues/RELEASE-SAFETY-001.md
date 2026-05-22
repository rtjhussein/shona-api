# RELEASE-SAFETY-001 - Make current release setup safe and obvious

See `docs/backlog/phase2/backlog.md#release-safety-001---make-current-release-setup-safe-and-obvious` for full context.

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
