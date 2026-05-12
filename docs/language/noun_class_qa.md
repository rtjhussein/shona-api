# Noun-Class Validation and QA

This note defines the editorial QA lane for assigning and reviewing Shona noun
classes. It is intentionally practical: future import, review, and morphology
issues can reference this workflow instead of restating the same checks.

## Validation Sources

Use these source keys when recording noun-class validation evidence:

| Source key | Role in noun-class QA | Expected evidence |
| --- | --- | --- |
| `source_fortune` | Backbone grammar authority for noun classes, concord behavior, and morphology-facing rule shape. | Page or section locator, rule summary, affected concord or class relationship, extraction confidence, reviewer decision. |
| `source_maumbirwo` | Validation authority for noun formation, nominal prefix logic, singular/plural class relationships, and class membership clarification. | Page or section locator, validated class or rule, reviewed prefix or class-pair note, reviewer decision. |

`source_hannan` may provide entry-level noun-class clues during lexical import,
but it is not the deciding validation source for this QA lane. When Hannan and
the validation sources disagree, preserve both claims and require an editorial
decision before publishing the canonical class assignment.

## Field Mapping

Validate `NounClass` records with this field map:

| Model field | QA question |
| --- | --- |
| `class_number` | Does the class identifier match the grammar source notation used by the project? |
| `label` | Does the human label describe the class without adding unvalidated theory? |
| `nominal_prefix` | Is the primary nominal prefix supported by the validation evidence? |
| `prefix_allomorphs` | Are alternate prefixes explicitly attested or justified by a reviewed note? |
| `default_plural_class` | Is the singular/plural relationship supported, or intentionally left blank? |
| `subject_concord` | Is the subject concord supported by `source_fortune` or a reviewed grammar note? |
| `object_concord` | Is the object concord supported, or intentionally blank where unresolved? |
| `possessive_concord` | Is the possessive concord supported by the validation evidence? |
| `adjectival_concord` | Is the adjectival concord supported by the validation evidence? |
| `relative_concord` | Is the relative concord supported by the validation evidence? |
| `associative_concord` | Is the associative concord supported by the validation evidence? |
| `demonstrative_proximal`, `demonstrative_medial`, `demonstrative_distal` | Are demonstrative forms supported and separated by distance value? |
| `additional_concords` | Are extra concord types named consistently and backed by a source locator? |
| `dialect_overrides` | Are dialect-specific differences keyed by dialect code and limited to fields that differ? |
| `notes` | Does the note explain uncertainty, conflict, or editorial judgment without replacing source evidence? |
| `provenance` | Does it include source key, locator, rule or field summary, confidence where available, and reviewer decision? |
| `review_state` | Does the state reflect the evidence quality and unresolved conflicts? |

Validate `Lemma.noun_class` assignments with this field map:

| Model field | QA question |
| --- | --- |
| `headword_kind` | Is the lemma a noun before assigning `noun_class`? |
| `noun_class` | Does the selected class match the noun's prefix, class clues, and reviewed validation evidence? |
| `forms` | Do plural forms or variants support the class relationship rather than contradict it? |
| `senses.grammar` | Do grammar notes agree with the assigned class, or has a conflict been recorded? |
| `dialects` | Do dialect markers require a `dialect_overrides` note on the class or a scoped lemma note? |
| `provenance` | Does the lemma keep entry-level evidence separate from the noun-class validation evidence? |

## Editorial Checklist

Use this checklist for each noun class or lemma assignment:

1. Confirm the source material is available through the local source registry and cite either `source_fortune` or `source_maumbirwo`.
2. Record the locator before changing canonical data: page, section, entry, or note identifier.
3. Check the nominal prefix and any allomorphs against the validation source.
4. Check the singular/plural class relationship. Leave `default_plural_class` blank if the relationship is uncertain.
5. Check concord fields only where the source evidence is specific. Prefer blank fields over guessed concords.
6. Capture dialect-specific differences in `dialect_overrides`; do not duplicate an entire class record for a dialect-only difference unless a later design issue requires it.
7. Compare imported lexical clues, especially Hannan grammar notes and plural forms, against the validation source.
8. If sources conflict, leave the record in `needs_review` or `in_review`, preserve both evidence trails, and add a note that names the conflict.
9. Approve only when the selected class, source locator, concord evidence, and reviewer decision are all present.
10. Publish only after downstream checks confirm that no linked lemma or form contradicts the approved assignment.

## Review Outcomes

Use consistent outcomes so future tooling can search and filter review notes:

| Outcome | Meaning |
| --- | --- |
| `validated` | The class or assignment is supported by `source_fortune` or `source_maumbirwo` and has no unresolved conflict. |
| `needs_source_locator` | The value may be plausible, but the source page or section has not been recorded. |
| `needs_concord_review` | Class membership is acceptable, but one or more concord fields need grammar review. |
| `conflict_recorded` | Two sources or reviewed notes disagree, and editorial resolution is required. |
| `defer_morphology` | The assignment can be stored, but morphology generation or analysis must wait for a later rule issue. |

## Admin Review Guidance

In Django admin, review `NounClass` before bulk-editing linked lemmas:

1. Search by `class_number`, `label`, `nominal_prefix`, or concord form.
2. Confirm `default_plural_class` points to the reviewed paired class where known.
3. Keep `additional_concords` as a small object keyed by concord type.
4. Keep `dialect_overrides` as a dialect-code object whose values only include overridden fields.
5. Use `notes` for human-readable uncertainty, and `provenance` for source evidence.
6. Move records through `draft`, `needs_review`, `in_review`, and `approved`; do not skip to `published` without a release workflow.

For lemma review, filter lemmas by `headword_kind=noun` and `noun_class`.
Non-noun lemmas must not carry a noun-class assignment.

## Conflict Policy

Do not auto-solve noun-class disputes. If `source_fortune` and
`source_maumbirwo` appear to disagree, or if a lexical import clue disagrees with
the validation sources:

1. Preserve every source claim in provenance, notes, or review records.
2. Keep the canonical value in a non-published review state.
3. Add the smallest useful explanation of the conflict.
4. Defer morphology generation, public morphology endpoints, and bulk derivation
   until a later issue resolves the governing rule.

