# Shona API Developer Quickstart

This guide covers the public API that exists in the current codebase. It does
not describe SDKs, billing, self-service key creation, or endpoints planned for
future backlog items.

## 1. Run the API locally

```powershell
python -m pip install -e ".[dev]"
python manage.py migrate
python manage.py ensure_current_release --version 2026.09.local --label "Local development release" --rule-set-version morphology-rules-v6
python manage.py runserver
```

Protected language endpoints require exactly one current `DataRelease` so the
response envelope can expose `data_release` and `rule_set_version`. If no
current release exists, the API returns `CURRENT_RELEASE_NOT_CONFIGURED` with
the setup command above in `error.detail.setup_command`. The release must also
declare the morphology rules version this deployment implements
(`morphology-rules-v6`; v6 adds the imperative lanes and keeps the v5
finite, v4 infinitive, and v3 extension rules unchanged): otherwise analyze
and generate return `503 MORPHOLOGY_RULES_VERSION_UNSUPPORTED`, and search
keeps serving lexical results while reporting
`morphology_enrichment.status = "unavailable"`.

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
`ndinobuda`, a simple `ku-` infinitive such as `kubuda`, or an imperative
such as `usadye` or `budai`, the response also includes `morphology` and
`morphology_enrichment` with linked lemma details.
Unsupported or failed morphology enrichment keeps the search response
successful and records the fallback under `zero_result.morphology_enrichment`
when there are no exact matches. Some unsupported surfaces include
`future_lanes` with rule-card IDs, for example passive or extension-like forms
point at `fortune.verbal.extensions.001` without claiming v1 support.

Search accepts compact optional filters:

- `headword_kind`: one of `word`, `noun`, `verb_stem`, `ideophone`, `unknown`
- `pos`: one of `n`, `vi`, `vt`, `v t`, `v i`, `adj`, `adv`, `ideo`, `interj`
- `dialect`: one of `K`, `Ko`, `M`, `Z`
- `limit`: integer from `1` to `50`, defaulting to `20`

Invalid filter values return `SEARCH_FILTER_INVALID` with `error.detail.field`,
`value`, and `allowed_values`.

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

Morphology analysis v1 is intentionally bounded. It supports `ku-`
infinitive constructions shaped as:

```text
ku + [sa] + [object_concord | zvi-reflexive] + reviewed verb stem
```

Example:

```json
{
  "text": "kubuda"
}
```

It also supports single-token positive present verb forms
(`subject_concord + no + [object_concord] + verb_stem`), negative present
verb forms (`ha + subject_concord + [object_concord] + verb_stem` ending in
`-i`), and imperative forms: positive bare stems (`buda`), the plural `-i`
suffix (`budai`), the prothetic `i-` for monosyllabic radicals (`idya`,
`idyai`), singular object-marked imperatives (`riise`, `muradzike`), and
negative commands (`usadye`, `musadye`, `usariisa`).

Unsupported forms return `ANALYSIS_UNSUPPORTED` with detail about the supported
shape. Infinitive complements, progressive/exclusive `-cha-`/`-chi-`
infinitives, tone, and complex verbal morphology remain outside v1 support;
`a`-vowel boundaries without source evidence (infinitive `sa-` boundaries,
finite concord|stem contacts, and the imperative `sa-`/object-concord
contacts) are deferred pending evidence and return structured unsupported
responses. Ambiguous forms return competing readings (no-object, object,
reflexive, imperative) ordered by confidence; imperative addressee
information is reported in a dedicated `addressee` slot, never as a finite
subject prefix. Passive or extension-like surfaces may include a future-lane
explanation and rule-card ID in `error.detail.future_lanes`.

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

Generation v1 supports reviewed verb-stem lemmas, the finite
`subject_concord + no + [object_concord] + verb_stem` shape with the
documented verb extensions, a `generation_type: "infinitive"` branch
(`ku + [sa] + [object_concord | zvi-reflexive] + verb_stem`, e.g.
`kusaziva`), and a `generation_type: "imperative"` branch
(`number` singular/plural plus `polarity`: the positive singular is the bare
stem, the plural adds `-i`, the singular object-marked imperative is
`object_concord + stem + -e`, and negative commands are `usa-`/`musa-` +
stem + `-e`, e.g. `buda`, `budai`, `idya`, `riise`, `usadye`, `musadye`).
Finite and imperative `a`-vowel boundaries without source evidence are
deferred with structured `finite_boundary` / `imperative_boundary`
refusals; the imperative plural-with-object combination and
divergent-stem/pro-verb imperative readings are refused and excluded on
both generation and analysis (`deferred_imperative_plural_object` /
`excluded_divergent_stem_imperative` lanes), while plural commands without
objects and singular object-marked commands stay supported.
The negated `-no-` present terminal is the Standard Shona
`-i` (`handidyi`-type; the Zezuru `-e` spelling stays analyzable); the
negative imperative terminal is generated as `-e` with the attested `-a`
spelling analyzed as a dialect variant. Evidence-gated allomorphs
(causative styles `dz` and `ts`, reversive style `short`) return `422
EXTENSION_UNVERIFIED` on all branches; other unsupported feature requests
return `GENERATION_UNSUPPORTED`. See `docs/morphology/generate_endpoint.md`
for the full contract.

## 8. Response envelope

Protected public API success responses use:

```json
{
  "api_version": "v1",
  "data_release": "2026.09.0",
  "rule_set_version": "morphology-rules-v6",
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
