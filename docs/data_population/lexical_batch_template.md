# Lexical Batch Issue Template

Use this template for `LEX-BATCH-001`, `LEX-BATCH-002`, and later Hannan lexical
population batches.

## What to build

Import, review, and publish the next bounded Hannan lexical batch into canonical
lemma, sense, tone, and form records while preserving provenance and uncertainty.

Default batch size:

- 25 records until the workflow is stable.
- 100 records after import, review, dashboard, and report quality are predictable.
- 250 records only after repeated batches show low parser failure and review rework.

## Acceptance criteria

- [ ] Local batch file uses `hannan-local-batch-v1` and is not committed.
- [ ] Import dry-run succeeds before any database writes.
- [ ] Candidate `ExtractionUnit` rows include `batch_id`, locator, parser output,
      confidence, parser status, and source provenance.
- [ ] Reviewer decisions leave failed or uncertain entries visible for follow-up.
- [ ] Approved entries publish through the existing publish service.
- [ ] Approved batch entries publish through `publish_hannan_batch --batch-id`.
- [ ] Published canonical records include source locator, parser status,
      uncertainty notes, and revision metadata.
- [ ] `/ops/progress/` reflects queue movement and canonical record growth.
- [ ] `report_hannan_batch --batch-id <BATCH_ID>` reports parser, review, and
      publish outcomes.

## Blocked by

None once the data population pilot tooling is merged.

## Labels

`type:data`, `area:source`, `area:parser`, `area:editorial`, `area:lexicon`,
`state:ready`, `exec:hitl`
