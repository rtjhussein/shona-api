# Shona API Phase 2 Execution Notes

## How To Use This Backlog

- Work one issue per branch unless a batch is explicitly marked parallel-safe.
- Keep Hannan ingestion workflow changes out of scope unless an issue explicitly says otherwise.
- Every implementation issue starts with tests or fixture assertions.
- Closeout must include commands run, files changed, database changes, and known limitations.

## Branch Convention

Use `codex/<issue-id-kebab-title>`, for example:

```text
codex/lex-pub-001-publication-tranche
```

## Review Rules

- Do not merge an issue until the full test suite passes.
- Preserve provenance and uncertainty rather than smoothing it away.
- Public API wire shapes should remain backwards-compatible unless an issue explicitly permits a breaking change.

## Parallel Agent Guidance

- `LEX-PUB-001` and `RELEASE-SAFETY-001` can run in parallel.
- `MORPH-QA-001` should wait for enough newly published verb examples from `LEX-PUB-001`.
- `SEARCH-QUALITY-001` should wait for `MORPH-QA-001` if search changes depend on new morphology fixtures.
- `FIG-SEED-001` can run independently if a human has selected candidate source material.
