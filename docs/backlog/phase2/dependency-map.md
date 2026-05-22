# Shona API Phase 2 Dependency Map

## Graph

```text
LEX-PUB-001
  -> MORPH-QA-001
  -> SEARCH-QUALITY-001

RELEASE-SAFETY-001
  -> SEARCH-QUALITY-001

FIG-SEED-001
  independent after current figurative-language model/API foundation
```

## Parallel-Safe Batches

- Batch 1: `LEX-PUB-001` and `RELEASE-SAFETY-001`.
- Batch 2: `MORPH-QA-001`, `SEARCH-QUALITY-001`, and `FIG-SEED-001` after their local blockers clear.

## Blocking Issues

- `LEX-PUB-001` blocks real-data morphology QA and better search examples.
- `RELEASE-SAFETY-001` blocks reliable public/API beta behavior.

## Recommended First Execution Path

1. Finish `LEX-PUB-001`.
2. Run `MORPH-QA-001` against the newly published verb data.
3. Use failures and zero-result patterns to drive `SEARCH-QUALITY-001`.
4. Complete `RELEASE-SAFETY-001` before sharing the API with any external beta user.
5. Start `FIG-SEED-001` once lexical/search flow is stable enough for demo use.

## Human Review Hotspots

- `LEX-PUB-001`: editorial approval and source-traceability decisions.
- `FIG-SEED-001`: subtype classification and cultural interpretation.
