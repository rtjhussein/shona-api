# Orthography and Normalization Policy

This policy defines how Shona API should treat written forms when storing canonical
records, building search keys, and explaining learner-facing correctness. It is a
policy slice, not a spelling-correction engine or a full normalization
implementation.

## Source Basis

| Source key | Role in this policy |
|---|---|
| `source_hannan` | Backbone lexical authority for Standard Shona spelling, dictionary headword conventions, dialect markers, lexical tone notation, and word-division principles. |
| `source_curriculum_notes` | Validation authority for learner-facing writing norms: spelling, punctuation, capitalization, joining, and separation in school use. |
| `source_zimsec_syllabus` | Curriculum authority confirming that writing, spelling, punctuation, suitable language use, and composition correctness are assessed learner outcomes. |

When sources disagree, preserve the conflict and send it to editorial review. Do
not silently rewrite one source into another source's convention.

## Terms

**Canonical form** means the reviewed written form stored as language data. It is
the form the API presents as the trusted headword, form, example text, or
learner-facing correction target.

**Normalized form** means a derived key used for lookup, matching, sorting, and
duplicate detection. It may remove dictionary notation or presentation-only
differences, but it must not replace the canonical form as the displayed source
of truth.

**Variant** means a reviewed form that is valid in a dialect, source tradition,
historical layer, or usage context but is not the preferred canonical display for
the current record.

**Advisory guidance** means learner-facing feedback that helps a user write more
standard or school-appropriate Shona without rejecting the form as impossible
language.

## Policy Summary

| Area | Canonical storage | Search normalization | Validation behavior |
|---|---|---|---|
| Letter case | Store reviewed casing where casing is meaningful; ordinary lexical forms should usually be lowercase unless they are proper names or fixed title forms. | Casefold for lookup. | Enforce capitalization rules in learner validation where the context is known, such as sentence starts and proper names. |
| Dictionary stem hyphen | Preserve Hannan-style leading, trailing, or surrounding hyphens only as dictionary notation or parser evidence. Canonical lexical display should distinguish notation from written running text. | Remove notation hyphens used only to mark stripped prefixal, suffixal, or infixal formatives. | Advisory unless the user is explicitly editing dictionary-style entries. |
| Reduplication hyphen | Store reviewed hyphenation when standard writing requires it, especially reduplicated verb stems and longer reduplicated substantive stems. | Match with and without hyphen only where the policy marks the hyphen as orthographic punctuation, not as a different lexical form. | Enforce in learner validation for clear school-taught cases; otherwise warn and explain. |
| Word joining and separation | Store the reviewed word division, because joining can change meaning and learner correctness. | Do not collapse all spaces. Add targeted alternate keys only for known join/separate patterns. | Enforce clear auxiliary, conjunction, interjection, compound, and reduplication patterns; warn on ambiguous cases. |
| Punctuation | Preserve punctuation in examples, quotations, and learner text. It is not part of bare lemma identity unless a form is inherently punctuated. | Strip or ignore punctuation for simple lexical lookup, except apostrophes or hyphens marked as meaningful by a rule. | Enforce in learner writing contexts; advisory for dictionary search. |
| Diacritics and tone notation | Store tone in tone records or structured metadata, not by decorating the main headword unless the source itself requires display. | Search should normally ignore tone marks and Hannan tone brackets unless a future advanced mode asks for tone-sensitive lookup. | Advisory: tone helps correctness and disambiguation, but missing tone should not make ordinary text invalid in v1. |
| Dialect variants | Store each reviewed dialectal form with source and dialect metadata. Do not erase dialect evidence to force one spelling. | A search for one reviewed variant may return related variants when the relation is explicit. | Advisory unless the user selected a target dialect or school standard. |
| Historical or older spellings | Store as variants with source and time/context notes when reviewed. Do not promote older forms to the current canonical display without editorial decision. | Search may map older reviewed variants to the current canonical record. | Advisory: explain that a form is historical, source-specific, or non-preferred rather than simply wrong. |
| Borrowed words | Store the reviewed Shona spelling and provenance. Keep original-language evidence in metadata, not in the canonical headword unless it is part of the attested form. | Casefold and normalize ordinary spacing/punctuation. Do not automatically translate or respell. | Advisory when the learner mixes English spelling or register into Shona prose. |

## Canonical Storage Rules

Canonical storage must protect source-grounded written forms.

1. Store the reviewed display form exactly as accepted by editorial review.
2. Keep source evidence in provenance, including `source_key`, locator, extracted
   text or note, parser version when relevant, and reviewer decision.
3. Distinguish a written form from source notation. Hannan verb stems such as
   dictionary entries with leading hyphens are parser or lexicographic notation;
   the canonical record may keep both the notation evidence and the normalized
   searchable stem.
4. Keep word division in canonical text. Joining and separation are correctness
   concerns, not cosmetic whitespace.
5. Keep dialect metadata on forms and senses. A dialect form may be valid without
   being the default display form.
6. Keep tone as structured data. Hannan bracket tone notation should become a
   tone record or parser evidence, not a string decoration mixed into ordinary
   headword search keys.
7. Mark historical, deprecated, coarse, classroom-inappropriate, or register
   restricted forms in metadata when the source or reviewer supports that label.

## Normalization Rules for Search

Search normalization is a matching aid. It must be reversible in the sense that
every search result still points back to a reviewed canonical or variant form.

Initial normalization keys may:

1. Trim leading and trailing whitespace.
2. Casefold.
3. Remove dictionary notation hyphens used only to show removed formatives, such
   as leading hyphens on verb stems.
4. Ignore Hannan tone bracket notation in ordinary lookup.
5. Collapse repeated internal whitespace in user queries.
6. Strip punctuation for broad lexical lookup, while retaining rule-specific keys
   for meaningful hyphenation.
7. Add explicit alias keys for reviewed variants, historical forms, or dialect
   forms.

Initial normalization keys must not:

1. Rewrite an unreviewed spelling into a canonical form.
2. Collapse all joined and separated forms into the same key.
3. Treat every hyphen as disposable.
4. Remove dialect, register, or provenance evidence from the result.
5. Generate speculative corrections for misspellings.
6. Turn English glosses or translations into Shona lexical matches without a
   separate reverse-lookup design.

## Validation Rules

Validation behavior should be stricter than search, because validation is often
learner-facing and can affect confidence, grading, or classroom feedback.

### Enforced

Enforce only rules that are clear from the policy, source evidence, and target
context:

1. Required capitalization in known contexts, such as sentence starts, proper
   names, place names, and respectful name forms.
2. Required punctuation in learner-writing contexts, including sentence-ending
   marks, question marks, commas in lists, quotation marks for direct speech, and
   other school-taught punctuation where the prompt requires prose.
3. Standard joining for reviewed compounds, relationship terms, and contracted
   constructions where the source or editorial rule is explicit.
4. Standard separation for auxiliaries, defective verbs, conjunctions, repeated
   full words, and ideophones where the source or editorial rule is explicit.
5. Hyphen use for clear reduplicated verb stems and other reviewed hyphenated
   patterns.

### Normalized

Normalize only for matching or feedback grouping:

1. Case in search and duplicate checks.
2. Leading dictionary hyphens on stems.
3. Extra user whitespace.
4. Tone bracket notation in ordinary lexical lookup.
5. Non-semantic punctuation in broad search.

### Advisory

Use advisory feedback when a form is understandable but not the preferred school
or canonical presentation:

1. Dialectal spellings that are valid but outside the selected target dialect or
   school standard.
2. Historical or older source forms.
3. Missing tone information in contexts where tone is helpful but not required.
4. Register or style mismatches in learner writing.
5. Ambiguous joining/separation where the system lacks enough grammatical
   analysis to enforce a correction.
6. Possible misspellings. The system may say it found no reviewed match or offer
   exact known alternatives, but it must not invent corrections in this issue.

## Learner-Facing Correctness

Learner-facing responses should separate "not found", "non-standard", and
"wrong in this writing context".

Use these categories:

| Category | Meaning | Example behavior |
|---|---|---|
| `accepted` | The submitted form matches a reviewed canonical or variant form for the target context. | Return the canonical record and any relevant dialect/register notes. |
| `accepted_variant` | The form is reviewed and valid, but another form is preferred for the selected canonical, dialect, or classroom context. | Return the preferred form plus the variant label. |
| `needs_correction` | A clear school-taught or editorial rule is violated in the current context. | Explain the specific joining, separation, punctuation, capitalization, or hyphen rule. |
| `advisory` | The form is understandable or source-attested, but the system cannot or should not reject it. | Give a note about dialect, register, historical status, tone, or ambiguity. |
| `not_reviewed` | The system has no reviewed evidence for the form. | Say that it is not in reviewed data; do not guess a spelling correction. |

The response should avoid treating all search misses as learner errors. A user may
have entered a valid form not yet reviewed, a dialect form, an inflected form that
needs morphology support, or a misspelling outside the current engine.

## Implementation Notes for Future Issues

1. Add a named normalizer version before search v1 depends on this policy, for
   example `shona-orthography-normalizer-v1`.
2. Store both display and normalized fields for lookup, as current lexical models
   already do with `headword`/`normalized_headword` and
   `form_text`/`normalized_form`.
3. Treat normalization as a pipeline with named steps so later changes can be
   versioned and explained in API metadata.
4. Keep rule decisions data-driven where possible. A future validation endpoint
   should return rule identifiers, severity, evidence source, and learner-facing
   explanation.
5. Add fixture-based tests when normalization code is implemented. Fixtures
   should cover Hannan stem notation, reduplication hyphens, auxiliary separation,
   conjunction separation, compound joining, punctuation, dialect variants, and
   historical variants.

## Out of Scope

This policy does not implement:

1. A spelling correction engine.
2. Full morphological analysis.
3. Fuzzy search ranking.
4. Automatic dialect inference.
5. Automatic conversion between historical and modern spellings.
6. A complete punctuation checker.

