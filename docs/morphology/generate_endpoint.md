# Morphology Generate Endpoint v1

`POST /v1/generate` generates bounded morphology forms from structured feature
input. v1 is intentionally narrow: it supports single-token positive present
verb forms built from a reviewed verb-stem lemma, a supported subject concord,
the `no` present marker, and the lemma stem.

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
    "tense_aspect": "present",
    "polarity": "positive"
  }
}
```

The `features` value must be an object. Free-text descriptions are rejected with
`GENERATION_FEATURES_REQUIRED`.

Supported subjects:

- person subjects: first/second person, singular/plural
- noun-class subjects: reviewed noun classes with a stored `subject_concord`

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

- no negative forms
- no past/future or advanced tense/aspect generation
- no object markers
- no extensions
- no tone modeling
- no async or batch generation
