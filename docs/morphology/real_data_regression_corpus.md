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
- `-ambura` from `hannan:page_026:entry:ambura` (`-ambura [L] M v i Ignite.
  Get on fire. Umba yaambura: the house is on fire.`), retained as the
  vowel-initial boundary fixture used by the current morphology tests
- `-ziva` from `hannan:page_774:entry:ziva` (`-ziva [H] KMZ vt & i Know, be
  acquainted with. ... Handimuzivi: I do not know him.`), the attested
  negative-terminal fixture

## Supported V1 Coverage

The regression tests cover the existing public v1 rule boundary only:

- positive present person-subject forms
- negative present person-subject forms with the Standard Shona terminal `-i`
  (`handibadanudzi`-type; FSI Unit 12 Note 1 and Hannan "Handidyi St. Sh."),
  including the attested object form `handimuzivi` (Hannan `-ziva` entry);
  Zezuru `-e` spellings still analyze as dialect variants
  (`handibadanudze`-type, Fortune TC VII / Hannan "Handidye Z")
- person object concords
- ku- infinitive analysis and generation (positive `kuambura`; negative
  `kusaambura` is deferred, see below)

## Deferred Finite Vowel Boundaries (morphology-rules-v5)

The prior-v1 finite coalescence (`vanovambura`, `ndinovambura`,
`havavambure`, `havambure`) is removed: no source attests contraction at an
`a`-final subject/object concord before an `a`-initial stem, while every
attested verbal contact retains adjacent `a` vowels (Hannan `Umba yaambura`
and the `Ndakaaona` concord-list example; FSI `Ndinoada`, `Havaazivi`,
`Ndaatora`). Those combinations are now unsupported observed forms with
`deferred_pending_evidence` refusals on generation and
`deferred_finite_boundary` lanes on analysis, recorded in the fixture's
`unsupported_observed_forms`. Retained contacts (`haa-` negative prefix,
`vaa-` subject|object, `noa-` tense|object, `mu` object before `-ambura`)
remain supported cases.

## Unsupported Observed Forms

These are intentionally documented rather than implemented:

- bare extension-like stems with no supported construction, such as `badanudzwa`
  (a fully inflected `vanobadanudzwa` would analyze as `-badanudza` + passive)
- tense/aspect forms outside present positive and present negative
- tone-aware analysis or generation
