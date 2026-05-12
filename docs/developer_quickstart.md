# Shona API Developer Quickstart

This guide covers the public API that exists in the current codebase. It does
not describe SDKs, billing, self-service key creation, or endpoints planned for
future backlog items.

## 1. Run the API locally

```powershell
python -m pip install -e ".[dev]"
python manage.py migrate
python manage.py runserver
```

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
`zero_result` object.

## 4. Read a lexical entry

Use a `public_id` returned by search:

```http
GET /v1/lemmas/{public_id}
Authorization: Api-Key shona_sk_...
```

The response includes the standard envelope plus:

- `lemma`: headword, normalized headword, POS, noun class when available,
  learner metadata, phonology, provenance, revision, and review state
- `senses`: definitions, grammar, examples, dialects, and cross references
- `tone_records`: tone pattern metadata when available
- `forms`: exposed forms and grammatical metadata

Missing lemma IDs return `LEMMA_NOT_FOUND`.

## 5. Browse figurative-language records

The current public figurative-language subtypes are `tsumo` and `madimikira`.
Only active reviewed records are returned.

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

Morphology analysis v1 is intentionally bounded. It supports single-token
positive present verb forms shaped as:

```text
subject_concord + no + verb_stem
```

Unsupported forms return `ANALYSIS_UNSUPPORTED` with detail about the supported
shape.

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
