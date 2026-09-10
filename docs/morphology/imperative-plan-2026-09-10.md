# Imperative plan and evidence (2026-09-10)

Bounded imperative milestone plan, written before implementation. Every rule
below names its source locator; "attested" means the surface appears verbatim
in the cited source, "constructed" means a combination of attested parts built
by an attested general rule. No independent linguistic review of the enabled
patterns has occurred; this is an implementation contract, not a
certification.

## Sources verified for this milestone

- FSI Shona Basic Course, Unit 13 Note 2 (printed pp. 126-127; PDF pp.
  144-145): plural affirmative imperative `Nyorai`, `Taurai`, `Garai pasi`;
  "In form, these words consist of the stem of the verb, plus /-i/ (in some
  dialects /-nyi/)"; "the plural form may be used in speaking to one person,
  as a mark of respect"; "The singular form of the imperative is like the
  plural except that it lacks the suffix". Dialogue examples `Pinda` (sg,
  p. 126) and `Pindai` (pl).
- FSI Unit 32, note and exercises 3-4 (printed pp. 323-324; PDF p. 341):
  "the final vowel in negative commands may be /-a/ (as in /usaputsa/) or
  /-e/ (/usaputse/), depending on the dialect"; FSI's own printed forms use
  the -a terminal: singular `Usapinda`, `Usaputsa`, `Usagadzira`,
  `Usachera`, `Usadonhesa`, `Usafusira`, `Usahara`; plural `Musapfutsa`,
  `Musaisa`, `Musasevha`, `Musakurungira`, `Musakwidibidza`, `Musabura`,
  `Musabvisa`, `Musageza`, `Musatsvaira`.
- FSI Unit 34 Notes 1, 2, 4 (printed pp. 338-342; PDF pp. 356-360):
  object-marked affirmative imperatives `Ipe`, `Ape`, `Adye`, `Ridye`,
  `Imwe`, `Riise`, `Uise`, `Muradzike`, `Varadzike`, `Aise`, `Ugeze`,
  `Dzigeze`, `Rigeze` (terminal -e) and object-marked negative commands
  printed with the -a terminal: `Usariisa`, `Usauisa`, `Usadziisa`
  (adjacent vowels retained).
- Hannan, front matter TABLE OF VERB FORMS, Imperative Mood (printed p. xvii;
  PDF p. 19): affirmative `Idya`, `Idyai`, `Idyanyi M`; negative
  `Usadya. Musadya KM` / `Usadye. Musadye Z`; exclusive `Chidya`, `Usachidya`.
- Hannan `-i` entry (PDF p. 239): "†-i pl v suffix. Ipai: you (pl) give".
- Hannan `i-` entry (PDF p. 239): "prefixal form of imperative of
  monosyllabic v, sg & pl. Idya: eat (sg)! Idyai: eat (pl)!".
- Hannan `-nyi` entry (PDF p. 513): "sfx form > pl imperative. cp -i KMZ.
  Idyanyi: eat!" (Manyika).
- Hannan `-sa-` entry (PDF p. 613): "in neg of hortative, imperative &
  infin. ... Usadye: do not eat. Kusadya: to not eat."
- Hannan `chi-` entry (PDF p. 82): chi- prefixed to imperative = exclusive
  ("Stop what you are doing and do this") and politeness; `Chiuya: come at
  once`, `Chisarai henyu`.
- Fortune Vol. 1, 2.10.2.2 (printed p. 20; PDF p. 32): the imperative
  inflection completes the radical with a terminal vowel: `i-p-á`, `i-rw-á`,
  `tem-a`, `bik-a`, `zoror-a`, `tever-a`.
- Fortune Vol. 1, 2.10.2.4(f)(ii) Tone Conjugation II (printed p. 23; PDF
  p. 35): the imperative inflection carries extended radicals
  `taúrís-á` (causative), `tevér-á` (applied), `kángánís-a` (reciprocal).
- Fortune Vol. 1, TC X (printed p. 24; PDF p. 36): imperative exclusive
  `chí-p-a`, `chí-rw-a`.
- Fortune Vol. 1, "penultimate i-" (printed p. 37; PDF p. 48): `i-d-á!`
  with Rs of C shape in the imperative inflection.
- Fortune Vol. 1, pronoun section examples (printed pp. 122-123; PDF pp.
  134-135): `Usádaró mwanáwe!`, `Musádaró vanámi!`, `Usátúkéní!` (Zezuru
  negative imperatives).

## Supported constructions

### Affirmative imperative (rule `fortune.verbal.imperative.001`)

- Singular, no object: the reviewed verb stem itself (radical + terminal
  `-a`). Attested: `Pinda` (FSI p. 126), `tem-a`/`bik-a`/`zoror-a`/`tever-a`
  (Fortune 2.10.2.2).
- Plural, no object: stem + `-i`. Attested: `Nyorai`/`Taurai`/`Garai` (FSI
  Unit 13 Note 2), `Pindai` (FSI), `Ipai` (Hannan p. 239), `Idyai` (Hannan
  front matter). Tone is excluded from the API.
- Monosyllabic radicals whose radical (stem minus terminal `-a`) contains no
  vowel take the prothetic `i-` prefix in both numbers. Attested: `Idya`
  (Hannan front matter; `i-` entry), `i-p-á`/`i-rw-á` (Fortune 2.10.2.2),
  `i-d-á` (Fortune p. 37), `Imwa`/`Imwe` (FSI Unit 34). Product rule: the
  prothetic applies exactly when the radical is vowelless; vowel-bearing
  radicals (e.g. -enza) never take it. This is a generalization of the
  attested C-shape radicals, marked as constructed in the card.
- Object-marked singular: object concord + radical + terminal `-e`. Attested:
  `Ipe`/`Ape`/`Adye`/`Ridye`/`Imwe` (FSI Unit 34 Note 1), `Riise`/`Uise`
  (Note 2), `Muradzike`/`Varadzike`/`Aise` (Note 4), `chidye: eat it`
  (Hannan `chi-` entry). The terminal `-e` is part of the attested forms, not
  a transferred finite rule.
- Politeness: FSI Unit 13 Note 2 attests that the plural form may address one
  person politely ("the plural form may be used in speaking to one person, as
  a mark of respect"). The API reports `number` only; the politeness
  interpretation is documented in the slot label and rule card, never encoded
  as a separate feature.
- Extensions: the stem slot is built by the shared extension machinery.
  Attested extended imperatives: `taúrís-á`, `tevér-á`, `kángánís-a` (Fortune
  TC II). All existing extension evidence gates, styles, and the sequence
  convention apply unchanged.

### Negative imperative (rule `fortune.verbal.imperative.negative.001`)

- Shape: second-person addressee concord + negative imperative prefix `sa-`
  + [object concord] + radical + terminal vowel. Singular addressee `u`
  (`usa-`), plural addressee `mu` (`musa-`). The addressee is reported in a
  dedicated `addressee` slot, never as the ordinary finite subject-prefix
  slot. `sa-` in the negation of the imperative is attested (Hannan `-sa-`
  entry, p. 613).
- Terminal vowel is a dialect split, both spellings attested: `-e`
  (Zezuru: Hannan `Usadye. Musadye Z`; Fortune `Usádaró`, `Usátúkéní`) and
  `-a` (Karanga/Korekore: Hannan `Usadya. Musadya KM`; FSI's own printed
  exercises).
- Attested singular: `Usaputsa`, `Usapinda`-type forms (FSI Unit 32
  exercise 3, printed with the -a terminal), `Usadye`/`Usadya` (Hannan),
  `Usádaró`, `Usátúkéní` (Fortune).
- Attested plural: `Musadye`/`Musadya` (Hannan front matter), `Musaisa`,
  `Musakurungira`, `Musageze`, `Musatsvaira` (FSI Unit 32 exercise 4),
  `Musádaró vanámi` (Fortune).

## Generated dialect policy and analyzed variants

- Generated affirmative: singular = bare stem; plural = stem + `-i` (the
  `KMZ` `-i`; FSI's own plural examples and Hannan `Ipai`/`Idyai`). The
  Manyika `-nyi` plural suffix is analyzed as a dialect variant, never
  generated (Hannan `-nyi` entry: "cp -i KMZ"; front-matter `Idyanyi M`).
- Generated negative: terminal `-e` (Zezuru; the dialect of the Fortune
  grammar; Hannan tags it Z). The `-a` spelling (Hannan
  `Usadya. Musadya KM`; FSI's printed exercises) is analyzed as a dialect
  variant of the same construction, never blacklisted, never generated.
  - Tiebreakers for generating `-e` over the FSI-practice `-a`: Fortune (the
  project's primary rule source, a Zezuru grammar) attests `-e`
  (`Usadaro`, `Usatukeni`); Hannan's own `-sa-` entry example is `-e`
  ("Usadye: do not eat"); Hannan's table tags `-e` as Z (Zezuru), the
  primary component of Standard Shona. FSI's printed `-a` exercises are the
  analyzed variant. This parallels the finite lane, which generates the
  standard-tagged terminal and analyzes attested variants.

- Monosyllabic radicals generate with the prothetic `i-` in both numbers and
  both polarities (negative imperatives of monosyllabic stems keep the bare
  stem, per Hannan `Usadya`/`Usadye`, not `Usidya`).

## Analysis readings and slots

`POST /v1/analyze` gains imperative readings under `analysis_type:
"imperative"` with slots:

- `mood`: `{surface: "", value: "imperative", label: ...}`
- `polarity`: positive (no marker) or negative (`surface: "sa"`)
- `addressee`: `{person: "second", number: "singular"|"plural",
  surface: ""|"usa"|"musa", label: ...}` — imperative addressee information
  is never placed in the ordinary finite `subject` slot, which stays `null`.
- `object`: structured concord slot or null; `reflexive` stays `null`
  (reflexive imperatives are deferred, see below).
- `verb_stem`, `extensions`, `final_vowel` as in the other constructions.

Bounded candidate readings (each lexically gated against reviewed verb-stem
lemmas through the shared `_get_stem_candidates` machinery, so no spelling is
called an imperative merely because it ends in a familiar shape):

1. Positive singular: the whole surface resolves as a reviewed stem whose
   radical contains a vowel (`buda`, `pinda`); or `i-` + a vowelless-radical
   stem (`idya`).
2. Positive plural: surface minus final `-i` resolves (`budai`), or minus
   final `-nyi` (Manyika variant, `tauranyi`).
3. Positive object-marked singular: an object concord prefixes a remainder
   ending in `-e` whose terminal restores to `-a` (`ridise` -> `-disa`) or
   which resolves as-is (`imwe` -> `-mwa` via mutation; divergent `-e` stems
   by identity).
4. Negative: `usa-`/`musa-` prefix, then optional object concord, then a stem
   reading with terminal `-e` (restored to `-a` for lookup, or identity) or
   terminal `-a` (identity only; the Karanga spelling keeps the lexical
   terminal).
5. Extensions resolve through the shared decomposition machinery with all
   evidence gates intact (`musakurungire` -> `-runga` + applied).

Ambiguity policy: imperative readings are added alongside, never instead of,
independently supported readings. Bare imperative singulars share their
spelling with the lexical stem (exact lexical search results remain
unaffected); a surface like `kudai` keeps both the exact `-dai` lexical
reading (search) and the imperative plural of `-kuda` (morphology). The
shared-surface `zvi` yields only the class-8 object reading in the imperative
lane; no reflexive reading is inferred (reflexive imperatives are deferred).

## Deferrals (structured, stable reasons)

- Plural with object concord: no attested witness in the available sources
  (FSI's object-marked imperatives are all singular-addressee; Hannan's
  ambiguous `Kukupai` cannot be parsed as one). Generation refuses with
  `GENERATION_UNSUPPORTED`, `reason: deferred_pending_evidence`, boundary
  `plural_with_object_concord`; analysis infers no such reading and
  enforces the deferral identically — for both negative terminal variants
  and through extension-derived candidates — recording a
  `deferred_imperative_plural_object` lane when the excluded reading would
  have resolved to supported lexical material (`musaridye`, `musaridya`,
  `musaridyise`).
- Reflexive imperatives (`usazvidye`): no attested witness; refused at
  generation with `deferred_pending_evidence`; analysis infers no reflexive
  reading (zvi keeps only its class-8 object reading).
- Divergent stems without terminal `-a` (`-ti`, `-nzi`): no attested
  imperative shape; refused like the infinitive lane at generation
  (`divergent_stem_without_terminal_a`), and excluded from inferred
  imperative readings with an `excluded_divergent_stem_imperative` lane
  naming the excluded stem when a reading would have resolved. The shared
  imperative stem scope (`_imperative_stem_supported`) sits inside the
  candidate resolution used by every imperative path (bare, prothetic,
  plural, object-marked, negative), so an exact-identity surface such as
  `ti`/`nzi` cannot authorize an imperative reading while `kuti`/`handiti`
  keep their infinitive/finite readings. Extension-derived candidates
  structurally rebuild canonical stems with terminal `-a`, so a divergent
  stem is never reachable through them and no lane is recorded there.
- The defective pro-verb `-na`: excluded from imperative derivations on both
  sides (same defective-stem evidence as the finite lane; FSI: pro-verb stems
  keep their final vowels).
- Deferred vowel boundaries (same discipline as the v5 finite and v4
  infinitive lanes; every attested imperative contact retains adjacent
  vowels — `Riise`, `Aise`, `Usauisa`): an `a`-final object concord
  immediately before an `a`-initial stem (`object_before_a_initial_stem`),
  `sa-` before an `a`-initial object concord (`sa_before_a_initial_object`),
  and `sa-` before an `a`-initial stem (`sa_before_a_initial_stem`). No
  available source witnesses any of these contacts; generation refuses with
  `422 GENERATION_UNSUPPORTED` (`field: imperative_boundary`,
  `reason: deferred_pending_evidence`), analysis records a
  `deferred_imperative_boundary` lane when the excluded reading would resolve
  to reviewed lexical material, and no contracted spelling is invented.
  Boundaries are evaluated on the stem as built after extensions and the
  terminal mutation, exactly like the finite lane.
- Exclusive/polite `chi-` imperative (`Chidya`, `Usachidya`, `Chisarai`;
  Fortune TC X): a distinct construction with its own tone behaviour;
  deferred, documented with locators.
- The `rega` prohibitive strategy (Fortune printed p. 112, `Regá kúbika`) and
  the interrogative `-ei`/`-nyi` enclitic (Hannan `-i` entry, `Unomirirei`):
  different constructions; not part of this lane.
- Radical vowel allomorphs (`gar/gere`, Fortune 2.10.2.3.1) are out of scope;
  the imperative terminal restoration follows the reviewed finite policy and
  does not model radical-internal changes.

## Source-attested example matrix

| Surface | Reading | Source (locator) | Status |
| --- | --- | --- | --- |
| `pinda` | imperative, positive, sg, no object | FSI Unit 13 dialogue, printed p. 126 (`Pinda. Enter!`) | attested |
| `taurai` | imperative, positive, pl, no object | FSI Unit 13 Note 2, printed p. 126 (`Taurai`) | attested |
| `idyai` | imperative, positive, pl, monosyllabic stem with prothetic `i-` | Hannan front matter, printed p. xvii / PDF p. 19 (`Idyai`) | attested |
| `ipa` | imperative, positive, sg, monosyllabic stem | Fortune 2.10.2.2 (`i-p-á`, give!); Hannan `i-` entry | attested |
| `ridise` | imperative, positive, sg, object class 5, stem `-disa`-type | FSI Unit 34 Note 2 (`Riise` = ri + ise) | attested shape, fixture stem |
| `aise` | imperative, positive, sg, object class 6 | FSI Unit 34 Note 4 (`Aise ... Put them down`) | attested |
| `muradzike` | imperative, positive, sg, object person 3sg, stem `-radzika` | FSI Unit 34 Note 4 (`Muradzike pakaoma`) | attested |
| `usadye` | imperative, negative, sg, Zezuru terminal | Hannan front matter (`Usadye Z`); Hannan `-sa-` entry p. 613 | attested |
| `usadya` | imperative, negative, sg, Karanga variant | Hannan front matter (`Usadya KM`); FSI Unit 32 note | attested |
| `usaputse`/`usaputsa` | negative sg, both dialect terminals | FSI Unit 32 note (printed p. 323) | attested |
| `musadye` | imperative, negative, pl | Hannan front matter (`Musadye Z`) | attested |
| `usauisa` | negative sg, object class 6, `a|u` contact retained | FSI Unit 34 Note 2 (`Usauisa muhari`) | attested |
| `usadzise` | negative sg, object class 10 | FSI Unit 34 Note 2 | attested |
| `musakurungire` | negative pl, stem `-runga` + applied | FSI Unit 32 exercise 4 (`Musakurungira` with `-ir-`) | attested construction, terminal variant |
| `tauranyi` | imperative, positive, pl, Manyika `-nyi` | Hannan `-nyi` entry, PDF p. 513 (`Idyanyi`); FSI Unit 13 Note 2 | attested suffix, constructed example |
| `taurisa` | imperative, positive, sg, causative stem | Fortune TC II (`taúrís-á`) | attested |
| `aambura` | (deferred) positive object class 6 + `-ambura`, `a|a` contact | no witness found in available sources | deferred |
| `usaambure` | (deferred) negative + object class 6 + `-ambura` | no witness found | deferred |

Constructed-combination examples justified by the general rules (documented
in the cards, never presented as verbatim source forms): object-marked
imperatives on fixture stems (`ridise`, `aise`, `muradzike` on non-source
stems), extension-bearing imperative surfaces beyond the TC II radicals,
`-nyi` spellings on stems other than `-dya`.

## Generation feature shape

```json
{
  "lemma_public_id": "lemma_...",
  "features": {
    "generation_type": "imperative",
    "number": "singular",
    "polarity": "positive",
    "object": {"type": "person", "person": "third", "number": "singular"},
    "extensions": []
  }
}
```

- Allowlist: `generation_type`, `number`, `polarity`, `object`,
  `extensions`. Defaults: `polarity: "positive"`, `number: "singular"`.
- `subject`, `tense_aspect`, `mood`, `reflexive`, and any other field return
  structured `422 GENERATION_UNSUPPORTED` naming the field.
- Generation surfaces: `stem` / `stem+i` / `oc + stem_radical + e` /
  `usa + [oc] + stem_radical + e` / `musa + [oc] + stem_radical + e`, with
  the prothetic `i-` for vowelless radicals, terminal `-e` for negatives,
  and plain concatenation with the deferred-boundary refusals above.

## Version boundary

New public behavior is bounded by `morphology-rules-v6`
(`MORPHOLOGY_RULES_VERSION` in `shona_api/morphology/services.py`). The two
imperative cards carry `affected_rule_set: morphology-rules-v6`; the v5
finite, v4 infinitive, and v3 extension cards stay byte-identical. Releases
declaring older versions keep receiving `503
MORPHOLOGY_RULES_VERSION_UNSUPPORTED`; no DataRelease records are rewritten.

## Out of scope (explicit)

Past/future and subjunctive families, noun morphology, hortative
(`Ngandidye`), subjunctive-form imperatives (`Endayi`), tone, `chi-`
exclusive/polite imperative, `rega` prohibitive, interrogative enclitics,
radical vowel allomorphs, deployment and infrastructure.

## Implementation status addendum (same day, supervisor correction pass)

Implemented and verified after the initial milestone: the plural-with-object
and divergent-stem/pro-verb restrictions are enforced identically by
inferred analysis and search enrichment, not only by generation. Analysis
records `deferred_imperative_plural_object` and
`excluded_divergent_stem_imperative` lanes when an excluded reading would
have resolved (including extension-derived candidates), and search follows
the analyzer. Preserved on the same lemmas: exact lexical results,
plural commands without objects (both negative terminal variants),
singular object-marked commands (positive object-marked imperatives
included), finite and infinitive readings (`kuti`, `handiti`). Covered by
`tests/test_morphology_imperatives.py` (shared-scope regression tests) and
the corpus fixture's `unsupported_observed_forms`.
