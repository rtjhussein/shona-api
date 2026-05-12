# Pedagogy Metadata Design

This design defines the first practical educational metadata layer for Shona API.
It is a label-style enrichment plan, not a curriculum engine, grading system, or
school report generator.

The goal is to make lexical records, examples, grammar notes, and figurative
language easier to organize for learners while keeping core linguistic models
small and source-grounded.

## Source Basis

| Source key | Role in this design |
|---|---|
| `source_fsi` | Backbone learner/example authority for dialogues, teaching examples, common forms, lesson sequencing cues, translations, and beginner-friendly usage contexts. |
| `source_curriculum_notes` | Validation and structured enrichment authority for classroom writing norms, orthography, punctuation, joining and separation, school-facing terminology, and learner guidance. |
| `source_zimsec_syllabus` | Curriculum authority for topic mapping, educational categories, communication contexts, register, style, expressive-language expectations, and curriculum-aware prioritization. |

Pedagogy metadata must not override lexical, grammatical, orthographic, or
figurative-language authority. It can label records for educational use, attach
source-backed learning context, and guide API consumers toward appropriate
examples or explanations.

When source material conflicts, keep the source references and review status on
the candidate metadata. Do not publish a single educational label as canonical
until a reviewer accepts it.

## Design Principles

1. Prefer tags and small value lists over large school-specific models.
2. Keep pedagogy metadata additive; it should enrich canonical records without
   redefining the records themselves.
3. Store provenance for every source-derived label, including source key,
   locator, source note or extracted example, and reviewer decision.
4. Make V1 useful for browsing, filtering, and learner-facing hints before
   attempting sequencing, assessment, or curriculum coverage reports.
5. Allow multiple tags on a record. A word, example, or proverb may belong to
   more than one learning context.
6. Preserve uncertainty. Candidate tags may be suggested by a source or import
   workflow before review, but public API metadata should identify only reviewed
   or explicitly provisional labels.

## Minimal V1 Metadata

V1 should add a compact educational tag envelope to records that need learner or
curriculum context. The envelope can be represented as JSON metadata at first or
as a small related table in a later implementation, but the fields should stay
label-oriented.

| Field | Purpose | Example values |
|---|---|---|
| `learner_level` | Broad learner difficulty or placement cue. | `beginner`, `intermediate`, `advanced`, `unknown` |
| `curriculum_stage` | Coarse school-facing stage when supported by source evidence. | `forms_1_2`, `forms_3_4`, `general_secondary` |
| `curriculum_domains` | Topic areas or assessed language domains from curriculum sources. | `orthography`, `composition`, `comprehension`, `grammar`, `register`, `figurative_language`, `oral_communication` |
| `learning_functions` | How the record may help a learner or teacher. | `vocabulary`, `example_sentence`, `dialogue_practice`, `writing_guidance`, `usage_warning`, `cultural_interpretation` |
| `communication_contexts` | Contexts where the item is useful or assessed. | `conversation`, `narrative`, `description`, `letter_writing`, `school_composition`, `formal_speech` |
| `register_tags` | Register or appropriateness labels when reviewed. | `formal`, `informal`, `respectful`, `school_appropriate`, `avoid_in_school_context` |
| `source_links` | Provenance for the educational label. | `source_key`, `source_locator`, `note`, `review_status` |

These labels are intentionally broad. They make the API useful for education
without requiring a complete model of every lesson, form, unit, exam outcome, or
teacher workflow.

## V1 Tag Taxonomy

### Learner Level

`learner_level` should be a coarse helper, not a promise that a record belongs
to a precise curriculum week.

| Value | Use |
|---|---|
| `beginner` | Common forms, simple examples, FSI early lesson material, or source-reviewed introductory classroom content. |
| `intermediate` | Material that expects basic vocabulary and sentence-pattern familiarity. |
| `advanced` | Figurative, stylistic, formal, literary, or morphologically complex material that likely needs more support. |
| `unknown` | No reviewed learner placement yet. This should be the default rather than guessing. |

`source_fsi` may support beginner and sequencing cues, especially through lesson
or unit location. `source_zimsec_syllabus` and `source_curriculum_notes` may
support school-facing stage labels, but they should not be used to infer a
precise learner level without review.

### Curriculum Stage

V1 should support only broad stages:

| Value | Use |
|---|---|
| `forms_1_2` | Source-reviewed material tied to early secondary curriculum expectations. |
| `forms_3_4` | Source-reviewed material tied to later secondary curriculum expectations. |
| `general_secondary` | Secondary-school relevant material where the source supports curriculum relevance but not a narrower stage. |

Do not model individual terms, weeks, lesson plans, schemes of work, marks, or
report-card outcomes in V1.

### Curriculum Domains

`curriculum_domains` are the main curriculum-aware labels. They should come from
reviewed `source_zimsec_syllabus` topic mapping, `source_curriculum_notes`
writing norms, and later editorial decisions.

Recommended V1 values:

| Value | Use |
|---|---|
| `orthography` | Spelling, punctuation, capitalization, joining, separation, and writing correctness. |
| `grammar` | Parts of speech, agreement, noun classes, verb behavior, and sentence structure. |
| `vocabulary` | General word learning and lexical expansion. |
| `composition` | Extended writing, school essays, letters, descriptions, and narrative work. |
| `comprehension` | Reading, interpretation, and understanding source text. |
| `register` | Formality, appropriateness, audience, style, or school-suitable wording. |
| `oral_communication` | Dialogue, speech, conversation, listening/speaking practice, and recitation contexts. |
| `figurative_language` | `tsumo`, `madimikira`, culturally marked expression, and interpretation work. |
| `culture` | Cultural knowledge, norms, values, and context needed to understand language use. |

The tag list should be allowed to grow by reviewed migration or data policy, not
by arbitrary consumer-supplied strings.

### Learning Functions

`learning_functions` explain why a record is useful in a learner surface.

Recommended V1 values:

| Value | Use |
|---|---|
| `vocabulary` | The item can appear in learner vocabulary lists or flashcards. |
| `example_sentence` | The record has or should surface examples suitable for learners. |
| `dialogue_practice` | The item is useful in conversational practice, especially where `source_fsi` provides dialogue evidence. |
| `writing_guidance` | The item supports learner writing norms from `source_curriculum_notes`. |
| `usage_warning` | The item needs an appropriateness, register, dialect, or school-context caution. |
| `cultural_interpretation` | The item needs cultural or figurative explanation beyond a direct gloss. |
| `assessment_support` | The item helps organize practice around curriculum expectations, without generating grades or reports. |

### Communication Contexts

`communication_contexts` help consumers choose examples for a task.

Recommended V1 values:

| Value | Use |
|---|---|
| `conversation` | Spoken or dialogue use. |
| `narrative` | Storytelling, recounting events, or prose narration. |
| `description` | Describing people, places, objects, or situations. |
| `letter_writing` | School letter-writing and formal/informal correspondence contexts. |
| `school_composition` | Extended classroom writing. |
| `formal_speech` | Polished oral presentation, respectful address, or public speech. |

## Example Metadata Shapes

These examples show the intended shape. They are not migrations or final API
schemas.

### FSI Dialogue Example

```json
{
  "learner_level": "beginner",
  "curriculum_stage": "general_secondary",
  "curriculum_domains": ["vocabulary", "oral_communication"],
  "learning_functions": ["dialogue_practice", "example_sentence"],
  "communication_contexts": ["conversation"],
  "register_tags": ["school_appropriate"],
  "source_links": [
    {
      "source_key": "source_fsi",
      "source_locator": "lesson/unit/page locator",
      "note": "Dialogue or example supports beginner conversational use.",
      "review_status": "reviewed"
    }
  ]
}
```

### Writing Norm From Curriculum Notes

```json
{
  "learner_level": "unknown",
  "curriculum_stage": "general_secondary",
  "curriculum_domains": ["orthography", "composition"],
  "learning_functions": ["writing_guidance"],
  "communication_contexts": ["school_composition"],
  "register_tags": ["school_appropriate"],
  "source_links": [
    {
      "source_key": "source_curriculum_notes",
      "source_locator": "page/section locator",
      "note": "Source supports learner-facing joining, separation, punctuation, or spelling guidance.",
      "review_status": "reviewed"
    }
  ]
}
```

### Curriculum-Aware Figurative Language Tag

```json
{
  "learner_level": "advanced",
  "curriculum_stage": "forms_3_4",
  "curriculum_domains": ["figurative_language", "culture", "comprehension"],
  "learning_functions": ["cultural_interpretation", "assessment_support"],
  "communication_contexts": ["narrative", "school_composition"],
  "register_tags": ["school_appropriate"],
  "source_links": [
    {
      "source_key": "source_zimsec_syllabus",
      "source_locator": "syllabus section locator",
      "note": "Syllabus topic mapping supports figurative-language relevance.",
      "review_status": "reviewed"
    }
  ]
}
```

## API Consumer Uses

API consumers should be able to use V1 tags without understanding the whole
source system.

Examples:

1. A flashcard app filters for `learner_level=beginner` and
   `learning_functions=vocabulary` to build a starter word list.
2. A classroom writing helper filters for `curriculum_domains=orthography` and
   `learning_functions=writing_guidance` to show school-facing spelling,
   joining, separation, and punctuation notes.
3. A conversation practice app prefers examples tagged
   `communication_contexts=conversation` and `learning_functions=dialogue_practice`.
4. A reading-comprehension tool groups proverbs and idioms with
   `curriculum_domains=figurative_language` and `learning_functions=cultural_interpretation`.
5. A search UI can badge records with `register_tags=formal` or
   `register_tags=avoid_in_school_context` so learners know when a word or
   expression needs care.
6. An SDK can expose `curriculum_stage=forms_3_4` as a filter while still showing
   source provenance and review status for transparency.

These uses require only labels, provenance, and filtering. They do not require a
curriculum engine.

## Candidate Review Workflow

Future implementation should treat pedagogy labels as reviewable enrichment.

1. Capture a source-backed candidate label from `source_fsi`,
   `source_curriculum_notes`, or `source_zimsec_syllabus`.
2. Store the source key, locator, extracted note or example, proposed tag values,
   extraction method, and confidence.
3. Dedupe against existing tags on the same record.
4. Mark unresolved conflicts for review instead of merging them automatically.
5. Publish only reviewed labels, or explicitly expose provisional labels if a
   future API version supports that distinction.

This mirrors the source strategy: educational metadata should remain traceable
and reversible until editorial review accepts it.

## V1 Scope

V1 includes:

1. A small shared label taxonomy for learner level, broad curriculum stage,
   curriculum domains, learning functions, communication contexts, and register.
2. Provenance for source-derived labels.
3. Review status for pedagogy metadata candidates.
4. API filtering and display use cases that help learners, teachers, and app
   developers choose appropriate records and examples.
5. Compatibility with existing lexical, morphology, orthography, and
   figurative-language records without requiring those models to become school
   curriculum models.

## Deferred Scope

Later issues may add:

1. Mapping from FSI lesson sequence into reviewed beginner practice sets.
2. A richer ZIMSEC topic map with source locators and editorial notes.
3. Admin tools for reviewing proposed pedagogy labels.
4. Curriculum-aware example selection and ordering.
5. Rule identifiers that connect orthography policy to learner guidance.
6. More precise school-stage labels if source review proves they are stable.
7. Analytics about which tags are well-covered or under-covered.

Deferred work must still preserve source provenance and editorial review.

## Out of Scope

This design does not implement:

1. A full curriculum engine.
2. School report generation.
3. Automated grading, marks, rubrics, or pass/fail decisions.
4. Lesson-plan generation or schemes of work.
5. Automatic inference of learner level from word frequency alone.
6. Unreviewed consumer-defined tag strings in public canonical metadata.
7. Changes to core lexical, morphology, parser, or figurative-language models.
