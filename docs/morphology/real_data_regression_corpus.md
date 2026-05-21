# Real-Data Morphology Regression Corpus

This corpus anchors the present-tense morphology tests in Hannan-derived verb
lemmas rather than only hand-picked toy examples.

## Fixture Source

Fixture file:

```text
tests/fixtures/morphology/real_data_present_verbs.json
```

The first tranche uses verbs that are present in the local Hannan publication
workflow:

- `-badanudza` from `hannan:page_004:entry_004:badanudza`
- `-badanuka` from `hannan:page_004:entry_005:badanuka`
- `-ambura`, retained as the vowel-initial coalescence fixture used by the
  current morphology extension tests

## Supported V1 Coverage

The regression tests cover the existing public v1 rule boundary only:

- positive present person-subject forms
- negative present person-subject forms
- person object concords
- noun-class object concords
- vowel coalescence at object-concord/stem boundaries

## Unsupported Observed Forms

These are intentionally documented rather than implemented:

- passive or extension-like forms such as `badanudzwa`
- infinitive or nominalized forms such as `kuambura`
- tense/aspect forms outside present positive and present negative
- tone-aware analysis or generation

Future morphology issues should promote these only after reviewed Fortune rule
cards and fixtures exist.
