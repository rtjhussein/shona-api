# Morphology Rule Cards

Rule cards are source-backed morphology review artifacts. They translate a
small Fortune grammar observation into a testable implementation contract
without making the public API claim support before review is complete.

The canonical card files live in:

```text
docs/morphology/rules/cards/
```

Cards are JSON so the test suite can validate the same documents that future
reviewers and import tools will consume.

## Required Fields

Every card must include:

- `rule_card_schema_version`
- `rule_id`
- `title`
- `source_key`
- `source_locator`
- `rule_domain`
- `rule_type`
- `rule_summary`
- `affected_rule_set`
- `inputs`
- `conditions`
- `outputs`
- `evidence.examples`
- `qa.extraction_confidence`
- `qa.review_state`
- `qa.review_decision`
- `api_safety.analyzer_consumes`
- `api_safety.generator_consumes`
- `api_safety.public_endpoint_safe`
- `api_safety.requires_review_before_public`
- `api_safety.backward_compatibility`

`source_key` must be `source_fortune` for Fortune cards. `source_locator` must
be a page, section, or named local-PDF locator before a rule can move beyond
`draft`. A draft card may use a `PENDING_FORTUNE_LOCATOR: ...` marker only when
all public API safety flags remain false.

## Review States

- `draft`: extraction target exists, but source locator or review decision is
  incomplete.
- `extracted`: source locator and summary are filled, but reviewer decision is
  pending.
- `approved`: reviewer has accepted the rule for internal implementation.
- `published`: public API behavior may cite or consume the rule.
- `rejected`: retained only as a conflict or non-support note.

Analyzer and generator work may consume only `approved` or `published` cards
whose API safety flags permit that behavior. Draft cards exist to prevent
future issues from inventing rule IDs or silently widening support.

## API Safety Gate

Cards must keep `public_endpoint_safe: false` until:

1. A real Fortune locator is present.
2. `qa.review_state` is `approved` or `published`.
3. Positive examples are reviewed.
4. Unsupported or ambiguous cases are documented.
5. Backward-compatibility notes explain the public behavior.

If a card is still `draft`, `analyzer_consumes`, `generator_consumes`, and
`public_endpoint_safe` must all be false.

