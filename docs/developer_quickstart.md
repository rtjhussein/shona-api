# Shona API Developer Quickstart

This guide covers the public API that exists in the current codebase. It does
not describe SDKs, billing, self-service key creation, or endpoints planned for
future backlog items.

## 1. Run the API locally

```powershell
python -m pip install -e ".[dev]"
python manage.py migrate
python manage.py ensure_current_release --version 2026.05.local --label "Local development release" --rule-set-version morphology-rules-v2
python manage.py runserver
```

Protected language endpoints require exactly one current `DataRelease` so the
response envelope can expose `data_release` and `rule_set_version`. If no
current release exists, the API returns `CURRENT_RELEASE_NOT_CONFIGURED` with
the setup command above in `error.detail.setup_command`.

The OpenAPI spec is published at:

```http
GET /openapi.json
```

The committed copy lives at `docs/openapi.json`. Regenerate it with:

```powershell
python manage.py generate_openapi_spec
```

## 2. Create an API key

Public API endpoints require an API key. Local development keys can be created
with the management command:

```powershell
python manage.py create_api_key "Docs client" --plan developer --rate-limit-per-minute 60
```

Use the raw key printed by the command. Raw keys are shown only once.

Send the key with either header:

```http
Authorization: Api-Key shona_sk_...
```

or:

```http
X-API-Key: shona_sk_...
```

Successful protected responses include rate-limit headers such as
`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, and
`X-RateLimit-Plan`.

## 3. Search lemmas and forms

```http
GET /v1/search?q=buda
Authorization: Api-Key shona_sk_...
```

Example curl:

```powershell
curl.exe "http://127.0.0.1:8000/v1/search?q=buda" `
  -H "Authorization: Api-Key shona_sk_..."
```

Search currently supports exact lemma and exact form lookup using the v1
orthography normalizer. Empty searches return `SEARCH_QUERY_REQUIRED`.
Zero-result searches return a successful envelope with `count: 0` and a
`zero_result` object. When search can analyze a supported verb form such as
`ndinobuda` or a simple `ku-` infinitive such as `kubuda`, the response also
includes `morphology` and `morphology_enrichment` with linked lemma details.
Unsupported or failed morphology enrichment keeps the search response
successful and records the fallback under `zero_result.morphology_enrichment`
when there are no exact matches. Some unsupported surfaces include
`future_lanes` with rule-card IDs, for example passive or extension-like forms
point at `fortune.verbal.extensions.001` without claiming v1 support.

## 4. Read a lexical entry

Use a `public_id` returned by search:

```http
GET /v1/lemmas/{public_id}
Authorization: Api-Key shona_sk_...
```

The response includes the standard envelope plus:

- `lemma`: headword, normalized headword, POS, noun class when available,
  learner metadata, phonology, provenance, revision, review state, and an
  `entry_quality` count summary for senses, examples, forms, tone records, and
  cross references
- `senses`: definitions, grammar, examples, dialects, and cross references.
  Hannan examples use a shared object shape with `shona` and `english` keys,
  plus optional `source_note` or `dialects` when preserved from source data.
  Cross references keep `type`, `target`, `dialects`, and raw `source_note`;
  when the target is a published lemma they also include `resolved: true`,
  `target_public_id`, and `target_headword`. Unresolved references remain in
  the list with `resolved: false`.
- `tone_records`: tone pattern metadata when available
- `forms`: exposed forms and grammatical metadata. Hannan-derived forms may
  include `derived_form_evidence` with relation markers such as `>`, relation
  direction, and raw source notes when that evidence came through publication.

Missing lemma IDs return `LEMMA_NOT_FOUND`.

## 5. Browse figurative-language records

The current public figurative-language subtypes are `tsumo` and `madimikira`.
Only active reviewed records are returned.

Seed the small reviewed starter set with:

```powershell
python manage.py seed_figurative_expressions
```

```http
GET /v1/figurative-expressions/tsumo
GET /v1/figurative-expressions/tsumo/{public_id}
GET /v1/figurative-expressions/madimikira
GET /v1/figurative-expressions/madimikira/{public_id}
Authorization: Api-Key shona_sk_...
```

List responses include `subtype`, `count`, and `results`. Detail responses
return one expression with text, meaning, English rendering, usage notes,
cultural themes, linked lemmas, provenance, and review status.

## 6. Analyze a supported morphology form

```http
POST /v1/analyze
Authorization: Api-Key shona_sk_...
Content-Type: application/json

{
  "text": "ndinobuda"
}
```

Morphology analysis v1 is intentionally bounded. It supports simple `ku-`
infinitive or nominal verb forms shaped as:

```text
ku + reviewed verb stem
```

Example:

```json
{
  "text": "kubuda"
}
```

It also supports single-token positive present verb forms shaped as:

```text
subject_concord + no + verb_stem
```

Unsupported forms return `ANALYSIS_UNSUPPORTED` with detail about the supported
shape. Infinitive generation, infinitive complements, extensions, tone, and
complex verbal morphology remain outside v1 support. Passive or extension-like
surfaces may include a future-lane explanation and rule-card ID in
`error.detail.future_lanes`.

## 7. Generate a supported morphology form

```http
POST /v1/generate
Authorization: Api-Key shona_sk_...
Content-Type: application/json

{
  "lemma_public_id": "lemma_abc123",
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

Generation v1 supports reviewed verb-stem lemmas and the same
`subject_concord + no + verb_stem` shape. Unsupported feature requests return
`GENERATION_UNSUPPORTED`.

## 8. Response envelope

Protected public API success responses use:

```json
{
  "api_version": "v1",
  "data_release": "2026.05.0",
  "rule_set_version": "morphology-rules-v2",
  "generated_at": "2026-05-12T12:00:00Z",
  "data": {}
}
```

Structured application errors use:

```json
{
  "api_version": "v1",
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message.",
    "detail": null
  }
}
```

Authentication and throttling errors may come from Django REST Framework and
can use DRF's standard `detail` response shape.
