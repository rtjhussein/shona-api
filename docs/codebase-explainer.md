# Shona API Codebase Explainer

## 1. Project Overview

Shona API is a Django 5.2 / Django REST Framework project for publishing reviewed
Shona language data. It currently combines three related product surfaces:

- A protected public JSON API for lexical search, lemma reads, figurative
  expressions, and bounded morphology analysis/generation.
- A local/staff web interface for dictionary browsing, data progress, API key
  creation, and Hannan ingestion runs.
- A data-ingestion and editorial workflow that turns source-backed extraction
  units into canonical public records.

The implementation is still foundation-stage, but it is already domain-heavy:
it models provenance, source authority, review state, release metadata, phonology
fields, noun classes, Hannan dictionary parsing, and learner metadata.

## 2. Repository Purpose

The repository appears to be building the backend for a Shona language platform:

- ingest candidate dictionary data from trusted sources, especially Hannan;
- preserve parser output and provenance before publication;
- review and promote extraction units into canonical lemma, sense, tone, and form
  records;
- expose only reviewed/published data through stable API envelopes;
- provide limited rule-based morphology services tied to versioned rule sets;
- track progress toward an MVP data population target.

## 3. Tech Stack

- Language: Python, requiring Python >=3.12 in `pyproject.toml`.
- Web framework: Django >=5.2.
- API framework: Django REST Framework.
- Database: Postgres by default, with SQLite used by test settings unless
  `DATABASE_URL` is set.
- Cache and broker: Redis via `django-redis`; Celery is configured with Redis
  broker/result backend.
- Testing: pytest and pytest-django.
- CI: GitHub Actions, running Django checks, migrations, and pytest against a
  Postgres 16 service.
- API style: REST-ish JSON endpoints with a shared v1 success/error envelope and
  a committed OpenAPI 3.1 spec.
- Web UI: server-rendered Django templates plus app-specific static CSS/JS.

## 4. Top-Level Folder and File Map

- `config/`: Django project settings, URL routing, ASGI/WSGI entrypoints, Celery
  setup.
- `shona_api/`: application packages grouped by domain.
- `tests/`: pytest suite covering API behavior, models, ingestion, parser logic,
  docs, infra, and web views.
- `docs/`: developer docs, OpenAPI spec, source strategy, morphology plans,
  ingestion docs, language policy, and pedagogy metadata.
- `key_documents/`, `local_batches/`, `local_source_cache/`: local data/project
  working folders. These appear to be implementation support areas rather than
  deployable application code.
- `manage.py`: Django CLI entrypoint using `config.settings.dev` by default.
- `pyproject.toml`: package metadata, runtime dependencies, dev dependencies,
  setuptools package discovery, and pytest config.
- `.github/workflows/ci.yml`: CI smoke workflow.

## 5. System Design / Subsystem Architecture

The codebase is organized around explicit Django apps:

- `api_auth`: API key model, authentication backend, per-key minute throttling,
  rate-limit response headers, and key creation command.
- `api_docs`: OpenAPI spec builder and `/openapi.json` view.
- `editorial`: shared review states, review notes, editorial decisions, decision
  record links, and audit logs.
- `extraction`: candidate data units, Hannan batch import, Gemini pipeline
  orchestration, quality reports, and publication into canonical records.
- `figurative_language`: proverbs/figurative expression records and public list
  and detail APIs for active reviewed subtypes.
- `health`: unauthenticated health endpoint.
- `infra`: database infra migrations, currently Postgres search extensions.
- `lexicon`: canonical noun classes, lemmas, senses, tone records, forms,
  serializers, exact search, and learner metadata mapping.
- `morphology`: bounded v1 analyzer/generator for single-token verb forms.
- `observability`: placeholder metric recording hook.
- `phonology`: core Shona grapheme segmentation and syllabification.
- `records`: shared canonical-record base model and public ID generation.
- `releases`: current data release and rule-set metadata.
- `sources`: source registry model and seed command.
- `web`: staff/local web views and data progress dashboard.

The core architectural pattern is a pipeline:

`Source -> ExtractionUnit -> ReviewState/EditorialDecision -> CanonicalRecord -> Public API`

Canonical records inherit stable UUID primary keys and stable public IDs from
`records.CanonicalRecord`. Public API responses include current release metadata,
so the system expects a `DataRelease` row with `is_current=True` before protected
language endpoints can serve successfully.

## 6. Runtime Flows

### Public API Request Flow

1. `config.urls` routes `/v1/search`, `/v1/lemmas/{public_id}`,
   `/v1/figurative-expressions/...`, `/v1/analyze`, and `/v1/generate`.
2. DRF applies `APIKeyAuthentication` by default.
3. `APIKeyRateThrottle` enforces a fixed one-minute window per key prefix.
4. Views call domain services or querysets.
5. Views fetch `DataRelease` metadata and return the shared v1 envelope.

`/health` opts out of authentication and permissions.

### Lexicon Search Flow

1. `SearchView` reads `q`.
2. `normalize_search_query` trims, collapses whitespace, casefolds, and removes
   a leading hyphen.
3. Search tries exact published lemma matches first.
4. Remaining result slots are filled by exact published form matches.
5. The view attempts morphology analysis as an enrichment and attaches lemma
   details when analysis points to a known lemma.

### Lemma Read Flow

1. `LemmaReadView` loads a lemma by public ID.
2. It preloads noun class, senses, tone records, and forms.
3. It serializes a nested payload with the canonical lemma and related records.
4. Missing IDs are converted into a structured `LEMMA_NOT_FOUND` response.

### Morphology Flow

Analyze and generate are intentionally bounded. The current rule set supports
single-token present-tense verb forms:

- positive: `subject_concord + no + [object_concord] + verb_stem`;
- negative: `ha + subject_concord + [object_concord] + verb_stem ending in e`.

The service pulls reviewed noun-class concords from the database and reviewed
verb-stem lemmas from the lexicon. It returns rule IDs, confidence scores,
slots, limitations, and computed phonology.

### Ingestion and Publication Flow

There are two ingestion tracks:

- local Hannan batch JSON imports using the local Hannan parser;
- Gemini pre-parsed Hannan JSONL imports through the staff web dashboard or
  management commands.

The web ingestion dashboard starts a background Python thread, validates local
parser/PDF paths, runs an external parser repository via subprocess, compiles
page outputs into JSONL, imports them as `ExtractionUnit` rows, and can
auto-publish parseable units.

Publishing requires an approved extraction unit. The publication service creates
the lemma, senses, optional tone record, derived forms, editorial decision, audit
log, and back-links the extraction unit to the canonical lemma inside a database
transaction.

## 7. Important Folders

- `shona_api/lexicon`: the main canonical data model and public read/search API.
  This is the center of the product.
- `shona_api/extraction`: the main data ingestion and promotion layer. It holds
  the most workflow complexity and the biggest coupling to local tooling.
- `shona_api/morphology`: rule-based language logic. It is deliberately narrow
  but quite valuable because it turns lexical data into interactive analysis and
  generation.
- `shona_api/editorial`: review/audit primitives shared by data domains.
- `shona_api/web`: local operational UI, especially data-progress and ingestion
  dashboard workflows.
- `docs/`: domain policy and API docs. The docs are unusually important in this
  project because many rules are linguistic/editorial rather than purely
  technical.
- `tests/`: broad regression coverage, including docs-as-contract tests.

## 8. Important Files and Responsibilities

- `config/settings/base.py`: shared Django settings, installed apps, database,
  Redis cache, Celery settings, DRF defaults, and JSON-style logging.
- `config/urls.py`: all public API and local web routes.
- `shona_api/api_auth/models.py`: stores hashed API keys, prefixes, plans, rate
  limits, and key lifecycle metadata.
- `shona_api/api_auth/authentication.py`: accepts `Authorization: Api-Key ...`
  or `X-API-Key`.
- `shona_api/api_auth/throttles.py`: fixed-window per-key throttling, with a
  local-memory fallback if Redis is unavailable.
- `shona_api/records/models.py`: abstract canonical record base with UUID,
  stable public ID, provenance, revision, and deprecation fields.
- `shona_api/lexicon/models.py`: noun class, lemma, sense, tone, and form schema.
  It also computes phonology fields on lemma/form save.
- `shona_api/lexicon/views.py`: exact search and lemma read endpoints.
- `shona_api/morphology/services.py`: bounded analyzer/generator rule logic.
- `shona_api/extraction/models.py`: extraction unit and ingestion run state.
- `shona_api/extraction/services.py`: transactional promotion from reviewed
  extraction unit into canonical lexicon records.
- `shona_api/extraction/ingestion.py`: staff-triggered Gemini pipeline runner.
- `shona_api/parsers/hannan.py`: fixture-oriented local parser for Hannan entries.
- `shona_api/figurative_language/models.py`: canonical figurative expression
  model with active/reserved subtype support.
- `shona_api/api_docs/spec.py`: hand-built OpenAPI spec matching current
  supported endpoints.
- `shona_api/releases/models.py`: current data release invariant.
- `shona_api/web/progress.py`: data population snapshot for staff dashboard.

## 9. Cross-Module Dependency Relationships

- `lexicon`, `figurative_language`, and `extraction` depend on
  `editorial.ReviewState`.
- Canonical data models depend on `records.CanonicalRecord` for public identity
  and provenance shape.
- `extraction.services` writes into `lexicon` and records editorial/audit events.
- Public API views depend on `releases.services.get_current_release_metadata`.
- `morphology.services` depends on `lexicon` noun classes and verb-stem lemmas.
- `web` depends on `api_auth`, `extraction`, `lexicon`, `figurative_language`,
  `sources`, and `releases` to present local operational state.
- `api_docs.spec` depends on URL names to reverse current routes.

## 10. Tests and What They Validate

The suite currently has 141 passing tests. It covers:

- API key creation, authentication, throttling, and headers;
- health endpoint;
- source registry and source seeding;
- canonical public IDs;
- lexicon models and public API behavior;
- noun-class fixtures and documentation;
- phonology segmentation/syllabification;
- morphology analyze/generate endpoints;
- figurative expression models and public APIs;
- Hannan parser fixtures, batch imports, segment imports, and publishing;
- extraction unit publication and batch reports;
- ingestion pipeline orchestration;
- data progress and reference web views;
- OpenAPI generation and committed spec alignment;
- infra migration scaffolding;
- release metadata/current-release behavior.

Verification run:

```text
python -m pytest
141 passed
```

## 11. Deployment / Infrastructure / Environment Model

Runtime configuration is environment-driven through `django-environ`, with local
`.env` support. The default dev database URL points at local Postgres. Tests
default to `test.sqlite3`, although CI overrides that with Postgres.

Redis is expected for cache and Celery. The throttle implementation has a local
fallback for Redis outages, which keeps requests from crashing but makes rate
limits process-local during fallback.

The project has a Celery app configured, but the ingestion dashboard currently
uses an in-process daemon thread rather than a Celery task. That is acceptable
for local tooling, but it is not a robust production background-job model.

CI runs on GitHub Actions with Python 3.12 and Postgres 16.

## 12. Observations, Risks, and Ambiguities

Strengths:

- The domain model is thoughtful. Provenance, review states, release metadata,
  public IDs, source authority, and parser confidence are first-class concepts.
- The repository has broad tests for its current surface area.
- The ingestion-to-publication boundary is explicit and transactional.
- Public API responses are versioned and mostly consistent.
- Documentation is unusually strong for an early backend: quickstart, OpenAPI,
  source strategy, morphology plans, pedagogy metadata, and language policy are
  all present.

Risks and improvement opportunities:

- Public endpoints depend on a current `DataRelease`; without one, most protected
  API calls will fail rather than returning a friendly setup/configuration error.
- `SearchView` silently swallows all morphology-enrichment exceptions. That keeps
  search resilient, but it can hide real regressions in morphology or data
  loading.
- The staff ingestion dashboard stores a Gemini key in `.local_gemini.env` and
  launches local subprocesses from a web request-triggered thread. That looks
  intentionally local-only, but it should stay out of any production deployment
  path.
- The search implementation is exact-match only. That is a reasonable MVP, but
  the Postgres `pg_trgm`/`unaccent` infra suggests the future direction is more
  forgiving search.
- The Hannan parser is explicitly partial/fixture-oriented. The Gemini pipeline
  seems to be the trusted path for richer extraction.
- DRF authentication errors may use DRF's default `detail` shape while
  application errors use the project envelope. The docs mention this, but API
  clients will need to handle both.
- The test environment in this local checkout ran under Python 3.14.3 despite
  `pyproject.toml` requiring Python >=3.12 and CI using Python 3.12. That is
  not a failure, but Python version drift is worth watching.

Overall assessment:

This is a well-shaped early backend for a linguistically complex product. The
best parts are the explicit editorial/provenance model and the decision to make
language/source policy visible in code and docs. The areas I would watch most
closely are production hardening around ingestion/background jobs, consistency
of API error envelopes, and making release setup impossible to forget. The code
already has enough tests and domain structure that future work can proceed in
small vertical slices without losing the thread.
