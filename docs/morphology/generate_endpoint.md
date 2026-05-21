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

4. **Phonological Coalescence**:
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
shape.

## Current Limits

- no past/future or advanced tense/aspect generation
- no extensions (e.g. passive, causative, etc. except stem-final mutations)
- no tone modeling
- no async or batch generation

