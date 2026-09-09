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

5. **Phonological Coalescence**:
   - Automatically collapses duplicate `a` vowels at subject-concord, object-concord, or stem boundaries (e.g. `va` + `ambura` -> `vambura`).

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

## Rule-set activation

The implemented morphology rules are `morphology-rules-v3` (see the rule
cards' `affected_rule_set` and `MORPHOLOGY_RULES_VERSION` in
`shona_api/morphology/services.py`). The version returned to API consumers is
validated, not echoed: analyze and generate return `503
MORPHOLOGY_RULES_VERSION_UNSUPPORTED` when the current `DataRelease` declares
any other `rule_set_version`, and search keeps serving lexical results while
reporting `morphology_enrichment.status = "unavailable"` with the same code.
To serve corrected behaviour, create or promote a `DataRelease` with
`--rule-set-version morphology-rules-v3`. Incoming version labels are never
silently rewritten, and no live release records are mutated by this change.

