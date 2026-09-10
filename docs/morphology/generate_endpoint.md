# Morphology Generate Endpoint v1

`POST /v1/generate` generates bounded morphology forms from structured feature
input. 

## Request

```json
{
  "lemma_public_id": "lemma_...",
  "features": {
    "generation_type": "verb_form",
    "subject": {
      "type": "person",
      "person": "first",
      "number": "singular"
    },
    "object": {
      "type": "person",
      "person": "second",
      "number": "singular"
    },
    "tense_aspect": "present",
    "polarity": "positive"
  }
}
```

The `features` value must be an object. Free-text descriptions are rejected with
`GENERATION_FEATURES_REQUIRED`.
Infinitive generation uses `generation_type: "infinitive"` (see item 6 below)
with exactly five accepted feature fields (`generation_type`, `polarity`,
`object`, `reflexive`, `extensions`); anything else — finite-only
`subject`/`tense_aspect`, `mood`, or any other grammatical field — is rejected
with `422 GENERATION_UNSUPPORTED` instead of being ignored.
Imperative generation uses `generation_type: "imperative"` (see item 7 below)
with exactly five accepted feature fields (`generation_type`, `number`,
`polarity`, `object`, `extensions`); `subject`, `tense_aspect`, `mood`,
`reflexive`, and any other field are rejected with
`422 GENERATION_UNSUPPORTED` instead of being ignored.

### Supported Features:

1. **Subjects**:
   - Person subjects: first/second person, singular/plural.
   - Noun-class subjects: reviewed noun classes with a stored `subject_concord`.

2. **Polarity**:
   - `positive`: Generates positive present verb forms (`ndi-no-buda` -> `ndinobuda`) under rule ID `fortune.verbal.slots.001`.
   - `negative`: Generates negative present verb forms mutating the final vowel from `-a` to `-e` with prefix `ha-` (`ha-ndi-bude` -> `handibude`) under rule ID `fortune.verbal.negation.001`.

3. **Object Markers (Extension 2)**:
   - Supports `features.object` block for both person and noun-class object markers (`ndi-no-ku-da` -> `ndinokuda` / `ha-ndi-ku-de` -> `handikude`) under rule ID `fortune.concord.object.001`.

4. **Verb Extensions (morphology-rules-v3)**:
   - Supported types: `passive`, `causative`, `applicative`, `neuter`,
     `reciprocal`, `reversive`, `repetitive`, given as strings
     (`"causative"`) or dicts (`{"type": "causative", "style": "dz"}`).
   - Source: Fortune Vol. 1, section 2.10.2.3.3 (PDF p. 33 / printed p. 21);
     see rule cards `fortune.verbal.extensions.001`,
     `fortune.verbal.reversive.001`, `fortune.verbal.repetitive.001`,
     `fortune.verbal.reciprocal.001` and
     `fortune.verbal.extensions.retained.001`.
   - Height harmony is enforced: `-iC-` after `/a/`, `/i/`, `/u/` (e.g. `buda`
     -> `budisa`, `budira`, `budika`) and `-eC-` after `/e/`, `/o/` (e.g.
     `tenga` -> `tengesa`, `govera`).
   - Reversive uses vowel copy (`-anur-`/`-enur-`/`-inur-`/`-onor-`/`-unur-`,
     default and `style: "long"`; e.g. `pfeka` -> `pfekenura`,
     `kora` -> `koronora`). Old `long_urur`/`urur`/`oror` styles are rejected:
     those surfaces are the separate `repetitive` type (`-urur-`, `-oror-`
     after `/o/`; e.g. `kora` -> `kororora`).
   - Evidence-gated allomorphs are refused with `422 EXTENSION_UNVERIFIED`
     (structured unsupported result, not a warning): causative `style: "dz"`
     (`-idz-`/`-edz-`) and `style: "ts"` (`-its-`/`-ets-`), and reversive
     `style: "short"` (`-ur-`/`-or-`). Their per-lemma distribution is not
     verified in the available sources (see the retained rule card). The same
     evidence gate applies to inferred analyzer derivations: a reviewed base
     lemma is not evidence for a restricted derivation, so analyzing such a
     surface (e.g. `ndinobuditsa` when only `-buda` is published) returns `422
     ANALYSIS_UNSUPPORTED` with an `unverified_extension_derivation` lane, and
     search never reports matched enrichment for the excluded derivation. The
     supported path for an attested derived form is to publish it as its own
     reviewed verb-stem lemma, which then analyzes and searches as an exact
     lexical entry with no derivation claim.
   - Reciprocal `-an-` is evidence-backed (Fortune 3.3.18, 3.4.2.8; Hannan
     p. 2) and generates normally.
   - Extension stacks follow one shared convention (enforced identically by
     the analyzer): at most 3 extensions, each type at most once, in
     `causative < applicative < reciprocal < reversive < repetitive < neuter <
     passive` order (passive outermost). The canonical order is a documented
     product convention for deterministic round-trips - Fortune states the
     constructional pattern "R + extension(s)" without an ordering rule - not
     a claimed grammar rule. Anything else returns `422
     GENERATION_UNSUPPORTED` with the supported boundary in `error.detail`.
   - Malformed values never reach the engine: `type` must be a supported
     string and `style` must be a string from the type's style set (or
     `null`, which matches an omitted style). Lists, objects, booleans and
     numbers in either field return `422 GENERATION_UNSUPPORTED` instead of a
     server error.
   - Unknown types (`intensive`, `extensive`, `perfective`), unknown styles,
     and styles on style-less types also return `422` instead of silently
     choosing a default.

5. **Finite Vowel Boundaries (morphology-rules-v5)**:
   - Morphemes concatenate plainly; duplicate `a` vowels are no longer
     collapsed at subject-concord or object-concord boundaries. The prior-v1
     coalescence (`va` + `ambura` -> `vambura`) had no source locator and is
     removed. See rule card `fortune.verbal.slots.001`.
   - Retained (attested) contacts keep both vowels: the negative prefix
     before the subject concord (`ha` + class 1 `a` -> `haa...`, cf. Hannan
     `Mabhuku haakodzi`), the subject concord before an `a`-initial object
     concord (`va` + `a` -> `vaa...`, cf. FSI `Havaazivi`), and the tense
     marker before an object concord or stem (`no` + class 6 `a` ->
     `noa...`, cf. FSI `Ndinoada`, Hannan `Umba yaambura`).
  - Deferred pending evidence (`deferred_pending_evidence`, never presented
    as ungrammatical): an `a`-final subject or object concord immediately
    before an `a`-initial stem (evaluated on the stem as built after
    extensions and the negative terminal mutation). No available source
    witnesses that contact, and neither contraction nor universal hiatus is
    invented for it. Generation returns `422 GENERATION_UNSUPPORTED` with
    `error.detail.field = "finite_boundary"`, the stable boundary code
    (`subject_before_a_initial_stem` or `object_before_a_initial_stem`) and
    `reason: deferred_pending_evidence`; analysis infers no reading across
    the boundary and reports a `deferred_finite_boundary` lane when the
    excluded reading would have resolved lexically; search enrichment
    follows the analysis policy. Independently supported readings of the
    same surface stay available, and a completed spelling is never
    blacklisted merely for resembling an unsupported derivation.
  - Negated `-no-` present terminal: the final `-a` of a lexical stem becomes
    `-i` in the generated dialect. Sources: FSI Unit 12, Note 1 ("The final
    vowel of the stem is /-i/ in some dialects, /-e/ in others"; FSI's own
    forms are `-i`: `Handízíví`, `Handítaúrí`, `Haváazíví`); FSI Unit 13,
    Note 1 (`-sa-` past negatives keep `-a`, scoping the mutation to the
    `-no-` lane); Hannan front matter, Present Indicative negative
    `Handidyi St. Sh.` versus Zezuru `Handidye Z`, and the `-ziva` entry
    `Handimuzivi`. The Zezuru `-e` spelling (Fortune TC VII
    `ha-ndí-zív-é`) remains an analyzed dialect variant of the same
    construction and is never blacklisted. Stems that do not end in `-a`
    (divergent stems `-ti`/`-nzi`, Fortune 3.3.18) are taken as-is. The
    defective pro-verb `-na` (own `-ne`/`-na` paradigm) is refused with
    `GENERATION_UNSUPPORTED` / `defective_pro_verb_stem` instead of
    inventing a terminal. Analysis mirrors the refusal: the ordinary terminal
    rule infers no `ni`/`ne` reading from `-na` (through the mutated lookup,
    the object-marked path, or an extension decomposition), so those surfaces
    get `ANALYSIS_UNSUPPORTED` with an `excluded_defective_pro_verb_stem`
    future lane naming the excluded stem; search enrichment follows the
    analyzer and never reports them as matched. The surface is not
    blacklisted: an independently reviewed stem (for example a reviewed
    `-ni`) still resolves `handini` and its object-marked forms.
  - Examples: positive class 2 object + `-ambura` (`vanovambura`,
    `vanovaambura`) and negative class 2 subject + `-ambura` (`havamburi`)
    are refused; `ndinomuambura`, `ndinoabadanudza`, `havaabadanudzi` and
    `haabadanudzi` keep generating and analyzing (the `-e` spellings
    `havaabadanudze`/`haabadanudze` still analyze as Zezuru variants).

6. **Infinitive Generation (morphology-rules-v4 lane, unchanged in v5)**:
   - Shape: `ku + [sa] + [object_concord | zvi-reflexive] + verb_stem`
     (`kuziva`, `kusaziva`, `kuzvitora`, `kuzviziva`, `kusazviziva`) under
     rule ID `fortune.verbal.infinitive.001` (Fortune Vol. 1, section 3.3.18,
     PDF pp. 90-91).
   - `polarity`: `positive` (default) or `negative` (`sa-`); unlike finite
     negatives the terminal vowel stays `-a`.
   - `object` reuses the structured object feature (person or reviewed
     noun-class concords); `reflexive: true` selects the reflexive `zvi`
     prefix, reported in `slots.reflexive`, never merged into `slots.object`.
     At most one of object/reflexive; requesting both is `422`.
   - Only five top-level feature fields are accepted (`generation_type`,
     `polarity`, `object`, `reflexive`, `extensions`); `subject`,
     `tense_aspect`, `mood`, and anything else return `422
     GENERATION_UNSUPPORTED` with the offending field in `error.detail`.
     Divergent stems without terminal `-a` (e.g. `-ti`) are refused with a
     structured `lemma_stem` error instead of a fabricated surface.
   - Extensions, evidence gating, and sequence policy are shared with finite
     generation and analysis, so supported infinitives round-trip (`kuzivira`,
     `kusazvizivira`, `kuazivira`). Two `a`-vowel boundaries are deferred
     pending applicable evidence (`deferred_pending_evidence`, never
     presented as ungrammatical): `sa-` before an `a`-initial object concord
     or stem, and an `a`-final object concord before an `a`-initial stem.
     Deferred requests return `422 GENERATION_UNSUPPORTED` naming the
     boundary, and analysis infers no reading across it
     (`deferred_infinitive_boundary` lane); independently supported readings
     stay available. Witnesses for the surrounding retention pattern:
     `kuasakura`, `akaenda`, `Usaenda`, `Ndaatora` (FSI p225), `kumuona`
     and `tisina kumuona` (FSI p333). See the infinitive rule card.
   - Deferred: the two `a`-vowel boundaries above; progressive/exclusive
     `-cha-`/`-chi-` infinitives, multiword complements, nominal plurals, tone.

7. **Imperative Generation (morphology-rules-v6)**:
   - Shapes: positive singular = the bare stem (`pinda`; FSI Unit 13 dialogue
     "Pinda. Enter!", Fortune 2.10.2.2 `tem-a`, `bik-a`); positive plural =
     stem + `-i` (`taurai`, `budai`; FSI Unit 13 Note 2, Hannan `-i` entry
     `Ipai`); monosyllabic radicals take the prothetic `i-` (`idya`, `idyai`;
     Hannan front matter `Idya`/`Idyai`, Fortune `i-p-a`/`i-d-a`); the
     singular object-marked imperative = object concord + radical + `-e`
     (`riise`, `aise`, `muradzike`, `ipe`; FSI Unit 34, Hannan `chidye`
     "eat it"); negative commands = `usa-`/`musa-` + [object concord] +
     radical + `-e` (`usadye`, `musadye`, `usariise`, `usauise`; Hannan
     front matter and `-sa-` entry, FSI Units 32/34). Rule IDs
     `fortune.verbal.imperative.001` (positive) and
     `fortune.verbal.imperative.negative.001` (negative).
   - Dialect policy: the negative terminal is generated as `-e` (Zezuru:
     Fortune `Usadaro`/`Usatukeni`, Hannan "Usadye. Musadye Z" and the
     `-sa-` entry example "Usadye: do not eat"); the attested `-a` spelling
     (Hannan "Usadya. Musadya KM"; FSI's printed `Usaputsa`/`Usariisa`
     forms) analyzes as a dialect variant of the same construction and is
     never generated or blacklisted. The Manyika plural suffix `-nyi`
     (Hannan `-nyi` entry, `Idyanyi`) analyzes as a variant and is never
     generated.
   - `number` records the addressee number; FSI Unit 13 Note 2 attests that
     the plural form may politely address one person, which the API records
     as number only. The addressee is reported in a dedicated `addressee`
     slot (surface `usa`/`musa` in the negative), never in the ordinary
     finite `subject` slot, which stays null.
   - Extensions reuse the shared gate unchanged (`taurisa` — Fortune TC II;
     `usafusire`, `musakurungire` — FSI Unit 32 on the reviewed
     `-kurungira` stem).
   - Refusals: `plural` with an `object` and a truthy `reflexive` return
    `422 GENERATION_UNSUPPORTED` with `reason:
    deferred_pending_evidence` and stable boundaries
    `plural_with_object_concord` / `reflexive_imperative` (no attested
    witness). Divergent stems (`-ti`, `-nzi`) and the defective pro-verb
    `-na` are refused with `lemma_stem` reasons instead of a fabricated
    surface. Unwitnessed `a`-vowel boundaries (`sa-` before an `a`-initial
    object concord or stem; an `a`-final object concord before an
    `a`-initial stem, evaluated on the stem as built after extensions)
    return `422 GENERATION_UNSUPPORTED` with
    `field: imperative_boundary` and the stable boundary code while
    independently supported readings stay available.
   - Shared generation/analysis scope: the refusals above are mirrored by
    inferred analysis. The plural-object and divergent-stem/pro-verb
    restrictions are enforced on both sides — analysis infers no such
    readings and records a `deferred_imperative_plural_object` or
    `excluded_divergent_stem_imperative` lane when the excluded reading
    (including extension-derived candidates) would have resolved to
    supported lexical material; a-vowel boundary deferrals keep the
    `deferred_imperative_boundary` lane policy. Exact lexical results,
    plural commands without objects, singular object-marked commands, and
    finite/infinitive readings on the same lemmas are unchanged.

## Analysis additions (morphology-rules-v6)
`POST /v1/analyze` gains bounded imperative readings under
`analysis_type: "imperative"` with `mood`, `polarity`, `addressee`, `object`,
`verb_stem`, `extensions`, and `final_vowel` slots (the finite `subject` slot
stays null). Every reading is lexically gated through the shared stem
machinery: a spelling is never called an imperative merely because it ends in
a familiar shape, and a bare vowelless-radical spelling (`dya`) gets no
imperative reading because the attested imperative of `-dya` is `idya`.
Imperative readings are additive: exact lexical results, ku- infinitive
readings, and finite readings of the same surface stay available
(`kudai` keeps both the `ku` + `-dai` infinitive reading and the
`-kuda` + `-i` plural imperative reading).

The shared imperative stem scope is enforced identically by inferred
analysis: divergent stems (`-ti`, `-nzi`) and the defective pro-verb `-na`
never authorize an imperative reading (`excluded_divergent_stem_imperative`
lane when a reading would have resolved), and the plural imperative with an
object concord is deferred on both sides (`deferred_imperative_plural_object`
lane). Deferred `a`-vowel boundaries keep the `deferred_imperative_boundary`
lane policy. Exact lexical results, plural commands without objects,
singular object-marked commands, and finite/infinitive readings on the same
lemmas are unchanged.

## Response

Successful responses use the standard v1 envelope and include:

- generated form and normalized form
- lemma metadata
- slots used to build the form
- phonology metadata
- confidence
- warnings for partial v1 coverage
- generator and rule-set versions

Unsupported combinations return `422 GENERATION_UNSUPPORTED` with the unsupported
field, received value, supported values, supported rule IDs, and the supported
shape. Evidence-gated allomorphs return `422 EXTENSION_UNVERIFIED` with a
`reason` of `lexical_distribution_unverified` and the supported path in
`error.detail.supported`; the analyzer excludes the same unverified derivations
and returns `422 ANALYSIS_UNSUPPORTED` with an `unverified_extension_derivation`
future lane.

Generation `metadata.supported_rule_ids` includes the construction rule plus the
extension rule cards for any applied extensions. The `TONE_NOT_GENERATED`
message only mentions extensions when none were requested.

## Current Limits

- no past/future or advanced tense/aspect generation
- no tone modeling
- no async or batch generation
- extension stacks limited to the documented sequence convention (order,
  uniqueness, count); sequences outside it are unsupported on both
  generation and analysis
- no intensive, extensive, or perfective extension types
- causative `-idz-`/`-edz-` and `-its-`/`-ets-`, and short reversive
  `-ur-`/`-or-`, are refused at generation and excluded from inferred
  analyses until their per-lemma distribution is source-verified; attested
  forms resolve only as their own reviewed verb-stem lemmas
- imperatives: plural with an object concord, reflexive imperatives, the
  chi- exclusive/polite imperative, the rega- prohibitive, and the three
  unwitnessed `a`-vowel boundaries are deferred with structured refusals
  enforced identically by generation and inferred analysis (the
  plural-object and divergent-stem/pro-verb restrictions carry
  `deferred_imperative_plural_object` / `excluded_divergent_stem_imperative`
  lanes); the Manyika `-nyi` plural suffix analyzes as a variant and is
  never generated

## Rule-set activation
The implemented morphology rules are `morphology-rules-v6` (see the rule
cards' `affected_rule_set` and `MORPHOLOGY_RULES_VERSION` in
`shona_api/morphology/services.py`). The version returned to API consumers is
validated, not echoed: analyze and generate return `503
MORPHOLOGY_RULES_VERSION_UNSUPPORTED` when the current `DataRelease` declares
any other `rule_set_version`, and search keeps serving lexical results while
reporting `morphology_enrichment.status = "unavailable"` with the same code.
To serve corrected behaviour, create or promote a `DataRelease` with
`--rule-set-version morphology-rules-v6`. Incoming version labels are never
silently rewritten, and no live release records are mutated by this change.

Rule-set history: v6 adds the imperative lanes (new cards
`fortune.verbal.imperative.001` and
`fortune.verbal.imperative.negative.001`) and keeps the v5 finite, v4
infinitive, and v3 extension rules byte-identical; v5 corrected only the
finite joining rule (see the finite rule card `fortune.verbal.slots.001`);
v4 added the infinitive negation/object/reflexive and generation lane (see
the infinitive rule card `fortune.verbal.infinitive.001`).
