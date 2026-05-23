# Fortune Morphology Rule Extraction Plan

This document turns `source_fortune` from a general grammar citation into an
implementation-facing rule extraction plan. It does not implement morphology,
parse the source automatically, or invent page-level claims. Human extraction
must fill exact Fortune page or section locators before any rule becomes
canonical.

## Source Contract

Primary source:

- `source_fortune`
- Current filename: `fortune_grammatical_constructions.pdf`
- Source role: backbone grammar authority for morphology rule shape

Supporting source for nominal QA:

- `source_maumbirwo`
- Use only to validate and clarify noun-class and nominal formation details
- See `docs/language/noun_class_qa.md`

Every extracted rule must preserve:

- `source_key`
- `source_locator`
- `rule_summary`
- `rule_domain`
- `affected_rule_set`
- `extraction_confidence`
- `review_state`
- `review_decision`

## Rule Domains

These are the Fortune section families most relevant to morphology work. Exact
locators are deliberately blank until a reviewer extracts them from the local
source file.

| Domain | Fortune section target | Why it matters | First consumers |
| --- | --- | --- | --- |
| `noun_class_inventory` | Sections describing noun classes, nominal prefixes, and class membership. | Seeds `NounClass`, validates `Lemma.noun_class`, and anchors plural class pairing. | Noun-class QA, analyze endpoint, generate endpoint. |
| `concords` | Sections describing subject, object, possessive, adjectival, relative, associative, demonstrative, and related concords. | Fills class-level concord fields and future agreement checks. | Noun-class admin review, analyze endpoint, generator agreement rules. |
| `nominal_morphology` | Sections describing noun formation, prefix behavior, singular/plural relationships, and nominal derivation. | Explains how noun forms relate to lemmas and when generation is allowed. | Form validation, noun generation fixtures, QA lanes. |
| `morphophonemics` | Sections describing sound alternations triggered by prefix/stem contact, vowel interaction, assimilation, elision, or other form changes. | Prevents analyzers and generators from treating surface strings as simple concatenation. | Phonology services, analyzer normalization, generator output tests. |
| `verbal_constructions` | Sections describing verb-stem structure, subject/object marking, tense/aspect/mood slots, extensions, negation, and final vowels. | Provides the first rule boundary for verb analysis and generation. | Analyze endpoint v1, generate endpoint v1, release rule-set versioning. |
| `ideophonic_constructions` | Sections describing ideophone grammar and constructions. | Keeps ideophones out of ordinary noun/verb rule paths while preserving future support. | Lexicon display, analyzer exclusions, future ideophone rules. |
| `derivational_rules` | Sections describing derivation between lexical categories, including nominalization or verb extensions where present. | Supports future derived forms without hard-coding one-off parser behavior. | Form records, generator scope decisions, editorial QA. |

## Extraction Order

1. Extract noun-class inventory and nominal prefix rules.
2. Extract concord tables or prose rules that map class to agreement forms.
3. Extract nominal morphology and plural relationship rules.
4. Extract morphophonemic rules that affect noun and concord surfaces.
5. Extract verbal construction slot rules for analyze endpoint v1.
6. Extract generator-safe verbal rules only after analyzer fixtures exist.
7. Extract ideophonic and derivational rules into reserved lanes unless they are needed by a scheduled issue.

This order keeps future implementation honest: data structures first, analysis
fixtures second, generation last.

## Rule Card Shape

Concrete rule cards live under:

```text
docs/morphology/rules/cards/
```

Each card is a small JSON document so tests and future import tooling can read
the same artifact that reviewers edit. `docs/morphology/rules/README.md`
defines the required field contract, review states, and API safety gate.

Later morphology issues should consume reviewed rule cards with this shape:

```yaml
rule_id: fortune.noun_class.inventory.001
source_key: source_fortune
source_locator: "REQUIRED: page or section locator from local PDF"
rule_domain: noun_class_inventory
rule_type: inventory | concord | morphophonemic_change | construction_slot | derivation | exclusion
rule_summary: "Short human-readable statement of the extracted rule."
affected_rule_set: morphology-rules-v1
inputs:
  lexical_category: noun
  headword_kind: noun
  noun_class: "1"
conditions:
  dialects: []
  source_scope: "standard unless source says otherwise"
outputs:
  model_fields:
    - NounClass.class_number
    - NounClass.nominal_prefix
evidence:
  examples: []
  counterexamples: []
  notes: []
qa:
  extraction_confidence: 0.0
  review_state: draft
  review_decision: ""
  reviewer_notes: ""
implementation:
  analyzer_consumes: true
  generator_consumes: false
  public_endpoint_safe: false
api_safety:
  analyzer_consumes: true
  generator_consumes: false
  public_endpoint_safe: false
  requires_review_before_public: true
  backward_compatibility: "No breaking public behavior."
```

Rules can be stored as markdown tables, YAML fixtures, or future database
records, but the field names above should remain stable enough for tests and
import scripts to target.

## Starter Rule Reference

These starter IDs define the first extraction queue. They are not canonical
grammar claims until a `source_locator` and review decision are added.

| Rule ID | Domain | Rule type | Extraction target | Expected outputs |
| --- | --- | --- | --- | --- |
| `fortune.noun_class.inventory.001` | `noun_class_inventory` | `inventory` | Noun class list and class labels. | `NounClass.class_number`, `NounClass.label`, `NounClass.nominal_prefix`. |
| `fortune.noun_class.plural_pairing.001` | `nominal_morphology` | `inventory` | Singular/plural class relationships. | `NounClass.default_plural_class`, QA notes for uncertain pairings. |
| `fortune.concord.subject.001` | `concords` | `concord` | Subject concords by noun class. | `NounClass.subject_concord`, class agreement fixtures. |
| `fortune.concord.object.001` | `concords` | `concord` | Object concords by noun class or construction. | `NounClass.object_concord`, analyzer agreement notes. |
| `fortune.concord.possessive.001` | `concords` | `concord` | Possessive concords by noun class. | `NounClass.possessive_concord`, generator agreement notes. |
| `fortune.concord.adjectival.001` | `concords` | `concord` | Adjectival concords by noun class. | `NounClass.adjectival_concord`, phrase-level QA fixtures. |
| `fortune.concord.relative.001` | `concords` | `concord` | Relative concords by noun class. | `NounClass.relative_concord`, construction notes. |
| `fortune.concord.associative.001` | `concords` | `concord` | Associative concords by noun class. | `NounClass.associative_concord`, phrase-level QA fixtures. |
| `fortune.concord.demonstrative.001` | `concords` | `concord` | Demonstratives by class and distance. | `NounClass.demonstrative_proximal`, `NounClass.demonstrative_medial`, `NounClass.demonstrative_distal`. |
| `fortune.morphophonemics.prefix_stem.001` | `morphophonemics` | `morphophonemic_change` | Prefix/stem contact changes. | Normalization notes, analyzer surface-to-underlying fixtures. |
| `fortune.verbal.slots.001` | `verbal_constructions` | `construction_slot` | Verb construction slot order. | Analyzer token slots, generator ordering constraints. |
| `fortune.verbal.negation.001` | `verbal_constructions` | `construction_slot` | Negation patterns in verbal constructions. | Analyzer polarity field, generator safety rules. |
| `fortune.verbal.extensions.001` | `verbal_constructions` | `derivation` | Verb extension forms and meanings. | Stem segmentation notes, derivational rule candidates. |
| `fortune.ideophone.scope.001` | `ideophonic_constructions` | `exclusion` | Ideophone-specific construction behavior. | Analyzer exclusion notes, future reserved rule lane. |
| `fortune.derivation.nominalization.001` | `derivational_rules` | `derivation` | Nominalization or category-changing derivation. | `Form` derivation notes, generator scope gates. |

## Analyzer and Generator Consumption

Analyzer issues should consume only reviewed rule cards with:

- `review_state` of `approved` or `published`
- `analyzer_consumes: true`
- source locators present
- at least one positive example or fixture expectation
- conflict notes resolved or explicitly scoped

Generator issues have a stricter threshold:

- `generator_consumes: true`
- analyzer behavior already tested
- morphophonemic effects represented in fixtures
- public endpoint safety reviewed
- unsupported dialect or ambiguity cases documented as non-generated

Public morphology endpoints must not expose rules that only have draft locators
or unresolved source conflicts.

## Extraction QA Checklist

1. Open the local `fortune_grammatical_constructions.pdf`; do not upload source material to git.
2. Record the locator before writing the rule summary.
3. Classify the rule into one of the domains in this plan.
4. Write the rule as a small implementation statement, not a long source paraphrase.
5. Record exact model fields or service fields the rule should affect.
6. Add at least one example or fixture expectation when the source provides enough information.
7. Mark whether the analyzer, generator, both, or neither may consume the rule.
8. If a rule touches noun classes, cross-check `docs/language/noun_class_qa.md`.
9. Preserve unresolved conflicts and set `public_endpoint_safe: false`.
10. Add tests only after the rule card is reviewed enough to be executable.

## Out of Scope

- Building the morphology analyzer.
- Building the morphology generator.
- Automating PDF parsing.
- Publishing public morphology endpoints.
- Turning starter rule IDs into canonical rules without source locators.

