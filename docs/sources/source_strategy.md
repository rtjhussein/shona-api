# Source Strategy

This document defines how the current source set is used during Shona API build work. Source files live in `key_documents/`, which is local-only source material and must not be uploaded to git.

## Global Rules

- Critical-path ingestion starts from digitized text. OCR is not on the critical path; it may be used later only as an optional fallback or source-onboarding aid.
- `source_hannan` requires a dictionary-entry parser for digitized text. That parser must read compact lexicographic notation, not OCR output.
- Later implementation should preserve uncertainty instead of silently promoting ambiguous source material into canonical data.

## Source Map

| Source key | Current filename | Source role | Authority level | Ingestion style | Affected subsystems | Provenance expectations | Critical path |
|---|---|---|---|---|---|---|---|
| `source_prd` | `prd_v5.md` | Product scope and requirements reference | Planning authority | Manual reference only | Backlog, architecture, acceptance criteria | Cite PRD section or decision note when it shapes implementation | Yes, for product direction |
| `source_hannan` | `hannan_dictionary.pdf` | Core build source for lemmas, senses, dialect markers, tone, examples, cross-references, ideophones, noun-class clues, and orthographic conventions | Backbone lexical authority | Digitized dictionary-entry parsing into structured candidates, followed by editorial review | Lemmas, senses, forms, tone, search normalization, editorial review, cross-reference graph | Store source key, entry/headword locator, page or section locator where available, parsed field, parser version, extraction confidence, and reviewer decision | Yes |
| `source_fortune` | `fortune_grammatical_constructions.pdf` | Core build source for grammar, morphology, noun classes, concords, morphophonemics, verbal constructions, ideophonic constructions, and derivational rules | Backbone grammar authority | Rule extraction and structured grammar notes, then tests/fixtures before implementation | Noun classes, morphology analyzer/generator, grammar metadata, phonology and morphophonemics rules | Store source key, page/section locator, rule summary, affected rule set, extraction confidence, and review decision | Yes |
| `source_fsi` | `fsi_course.pdf` | Core build source for learner corpus, dialogues, pedagogical examples, common forms, and beginner sequencing cues | Backbone learner/example authority | Example and form extraction as reviewed learner-facing candidates | Learner metadata, example bank, beginner/common vocabulary priority, morphology evaluation corpus, educational surfaces | Store source key, lesson/unit/page locator, extracted example, translation or gloss when present, and review decision | Yes |
| `source_maumbirwo` | `maumbirwo_emazita.pdf` | Validation and structured enrichment source for noun formation, nominal prefix logic, singular/plural class relationships, and class membership clarification | Validation authority | Targeted structured notes and QA fixtures | Noun-class QA, nominal morphology QA, editorial validation | Store source key, page/section locator, validated class or rule, and review decision | Yes, for noun-class validation |
| `source_curriculum_notes` | `curriculum_notes_forms_1_4.pdf` | Validation and structured enrichment source for orthography, punctuation, joining/separating words, writing norms, classroom expectations, and school-facing terminology | Validation authority | Manual policy extraction into normalization and learner-guidance notes | Normalization policy, validation behavior, orthography guidance, learner docs, pedagogical tagging | Store source key, page/section locator, policy note, affected behavior, and review decision | Yes, for learner/orthography policy |
| `source_zimsec_syllabus` | `zimsec_syllabus_forms_1_4.pdf` | Validation and structured enrichment source for curriculum topic mapping, educational categories, expressive-language expectations, register, style, and communication context | Curriculum authority | Manual topic/tag extraction into curriculum metadata | Pedagogical tags, learner surfaces, examples organization, figurative-language priority, educational SDK/docs | Store source key, syllabus section locator, topic/tag mapping, and review decision | Yes, for curriculum-aware metadata |
| `source_tsumo_tsika` | `tsumo_tsika.pdf` | Validation and structured enrichment source for proverb-to-culture linkage, thematic interpretation, cultural taxonomy, and proverb pedagogy | Structured enrichment authority | Theme and interpretation extraction as reviewed enrichment | Proverb themes, figurative-language metadata, educational/cultural browse experiences | Store source key, page/section locator, proverb or theme locator, interpretation note, and review decision | No for lexical backbone; yes for proverb enrichment |
| `source_shona_yedu` | `shona_yedu.pdf` | Candidate enrichment source for high-volume proverbs, madimikira candidates, future madunhurirwa expansion, culturally marked lexical terms, and compact lexical lists | Candidate enrichment authority | Candidate extraction only; promote after dedupe, conflict checks, and review | Figurative-language enrichment, cultural vocabulary enrichment, example browsing, educational browse surfaces | Store source key, page/section locator, candidate text, candidate type, confidence, dedupe links, and review decision | No |

## Conflict Policy

Use the most authoritative source for the affected subsystem, and record conflicts rather than erasing them.

- Lexical facts: prefer `source_hannan`; use `source_fsi` for learner examples and attested teaching forms, not to override core lexical structure.
- Grammar and morphology: prefer `source_fortune`; use `source_maumbirwo` to validate and clarify noun-class and nominal formation details.
- Orthography and school-facing correctness: prefer `source_curriculum_notes`; use `source_zimsec_syllabus` to shape curriculum tags and educational priority.
- Figurative language and cultural themes: prefer reviewed structured enrichment from `source_tsumo_tsika`; treat `source_shona_yedu` as candidate material until reviewed.
- Product scope: use `source_prd` for product intent, but do not let it override source-grounded linguistic evidence.

When two authorities conflict, keep both source references on the candidate record, mark the conflict for editorial review, and do not publish a canonical value until a reviewer chooses the governing interpretation or explicitly records uncertainty.
