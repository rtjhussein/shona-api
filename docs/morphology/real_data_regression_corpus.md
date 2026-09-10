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
- imperative forms (morphology-rules-v6): the positive singular bare stem
  (`badanudza`, `ambura`, `ziva`; FSI Unit 13 "Pinda", Fortune 2.10.2.2),
  the plural `-i` suffix (`badanudzai`, `badanukai`, `amburai`, `zivai`;
  FSI Unit 13 Note 2, Hannan `-i` entry `Ipai`), the negative
  `usa-`/`musa-` commands with the generated Zezuru `-e` terminal
  (`usabadanudze`, `musabadanudze`, `usabadanuke`, `usazive`, `musazive`;
  Hannan front matter "Usadye. Musadye Z" / "Usadya. Musadya KM", Hannan
  `-sa-` entry, FSI Unit 32 with its attested `-a` spellings), and the
  singular object-marked imperative (`vabadanudze`, `usavabadanudze`;
  FSI Unit 34 `Riise`/`Usariisa`/`Usauisa`). The corpus object cases use
  the class-2 concord on the reviewed Hannan stems; the construction is
  attested on FSI Unit 34 witnesses and the stems are the corpus's own
  Hannan-derived fixtures. The Manyika `-nyi` plural suffix (Hannan
  `-nyi` entry) is documented in the imperative rule cards as an analyzed
  variant and is covered in `tests/test_morphology_imperatives.py`.

The source-attested imperative witnesses (FSI Unit 13 `Pinda`/`Taurai`/
`Nyorai`/`Garai`; Hannan front matter `Idya`/`Idyai`/`Usadye`/`Musadye`/
`Usadya`/`Musadya`; FSI Unit 34 `Riise`/`Aise`/`Muradzike`/`Usariisa`/
`Usauisa`; Fortune TC II `tauris-a`; FSI Unit 32 `Musakurungira`) anchor
the shapes; the corpus surfaces on the fixture stems are constructed
combinations of those attested shapes, not verbatim source forms.

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


## Deferred Imperative Boundaries (morphology-rules-v6)

The imperative lanes defer the same unwitnessed `a`-vowel contacts the
finite and infinitive lanes defer: an `a`-final object concord immediately
before an `a`-initial stem (`aambure`), `sa-` before an `a`-initial stem
(`usaambure`), and `sa-` before an `a`-initial object concord
(`usaambure`-type with a class-6 object). Generation refuses them with
`422 GENERATION_UNSUPPORTED` (`field: imperative_boundary`,
`reason: deferred_pending_evidence`) and analysis infers no reading across
them (`deferred_imperative_boundary` lane), recorded in the fixture's
`unsupported_observed_forms`. The plural imperative with an object concord
and reflexive imperatives have no attested witness and are refused with the
same deferred reason (stable boundaries `plural_with_object_concord` /
`reflexive_imperative`); the plural-object deferral is enforced identically
by inferred analysis for both negative terminal variants and through
extension-derived candidates, recorded as a
`deferred_imperative_plural_object` lane (e.g. `musaridye`, `musaridya`,
`musaridyise`). Divergent stems (`-ti`, `-nzi`; Fortune 3.3.18) and the
defective pro-verb `-na` are outside the shared imperative stem scope on
both sides: generation refuses them with `lemma_stem` reasons and inferred
analysis records an `excluded_divergent_stem_imperative` lane for surfaces
that would otherwise read as an imperative of the divergent stem (`ti`,
`nzi`), while the same lemmas keep their exact lexical, finite, and
infinitive readings (`kuti`, `handiti`). The chi- exclusive/polite
imperative (Hannan front matter; Fortune TC X; FSI Unit 35) stays out of
scope with its locators recorded in the cards.

The same enforcement is recorded for the corpus's own lemma in the
fixture's `unsupported_observed_forms` (`musavabadanudze`,
`musavabadanudza`).

## Unsupported Observed Forms

These are intentionally documented rather than implemented:

- bare extension-like stems with no supported construction, such as `badanudzwa`
  (a fully inflected `vanobadanudzwa` would analyze as `-badanudza` + passive)
- tense/aspect forms outside present positive and present negative
- tone-aware analysis or generation
