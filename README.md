# Shona API

[![Python Version](https://img.shields.io/badge/python-%3E%3D%203.12-blue.svg)](https://www.python.org/)
[![Django Version](https://img.shields.io/badge/django-%3E%3D%205.2-green.svg)](https://www.djangoproject.com/)
[![Built with DRF](https://img.shields.io/badge/built%20with-django%20rest%20framework-red.svg)](https://www.django-rest-framework.org/)

A structured, source-grounded, and high-performance lexical engine and platform for the Shona language. This project provides a robust framework to ingest dictionary source material, including trusted Hannan GPT JSONL batches, perform editorial review, and serve canonical lexical data, rule-based morphology analysis, and figurative expressions through a protected public API and web dashboards.

---

## 📖 Table of Contents
1. [Project Overview](#-project-overview)
2. [Architecture & Data Pipeline](#-architecture--data-pipeline)
3. [Core Subsystems & Django Apps](#-core-subsystems--django-apps)
4. [Local Setup & Quickstart](#%EF%B8%8F-local-setup--quickstart)
5. [Hannan Ingestion Workflows](#hannan-ingestion-workflows)
6. [API Endpoints Reference](#-api-endpoints-reference)
7. [Linguistic & Parsing Tools](#%EF%B8%8F-linguistic--parsing-tools)
8. [Running Tests](#-running-tests)
9. [Configuration Reference](#-configuration-reference)

---

## 🌟 Project Overview

Shona API is more than a simple dictionary search backend; it acts as a canonical, multi-layered linguistic engine for the Shona language. It is designed around the principles of **trustworthy structure, staged delivery, and strict source authority**.

- **Canonical Lexical Backbone**: Captures and models lemmas, definitions, cross-references, tones, and grammatical structures mapped directly to authoritative sources.
- **Rule-Based Grammar & Morphology**: Exposes real-time analysis and generation of inflected word forms, verified against versioned grammatical rule sets.
- **Pedagogical Enrichment**: Enhances lexical data with curriculum-aware, learner-friendly metadata (difficulty levels, syllabus domains, and communication contexts).
- **Figurative Language Subsystem**: Holds proverbs (`tsumo`) and idioms (`madimikira`) linked directly back to the lexical terms that form them.
- **Editorial Governance**: Integrates a full staff review flow to maintain strict audit trails, track provenance, and prevent unvetted data publication.

---

## 🏗️ Architecture & Data Pipeline

The system is built as a **modular monolith** using Django 5.2 and Django REST Framework. Data moves through a highly secure, transaction-safe pipeline:

```mermaid
flowchart TD
    %% Styling
    classDef source fill:#f9f,stroke:#333,stroke-width:2px;
    classDef process fill:#bbf,stroke:#333,stroke-width:2px;
    classDef db fill:#fbf,stroke:#333,stroke-width:2px;
    classDef public fill:#bfb,stroke:#333,stroke-width:2px;

    subgraph Ingestion ["1. Ingestion Layer"]
        S1["Source Materials (Hannan PDF, FSI, etc.)"] --> |"Local Hannan Parser / Gemini PDF Pipeline / GPT JSONL Import"| EU["Extraction Units (shona_api.extraction)"]
    end
    
    subgraph Editorial ["2. Editorial & Governance"]
        EU --> |"Staff Dashboard Review / Approval"| ED["Editorial Decisions (shona_api.editorial)"]
        ED --> |"Audit Logging & Status Transition"| RS["Review State (Approved/Needs Review)"]
    end
    
    subgraph Lexicon ["3. Canonical Lexicon"]
        RS --> |"Transactional Promotion (atomic)"| CR["Canonical Records (shona_api.lexicon)"]
        CR --> |"Lemmas, Senses, Tone, Word Forms"| DR["Data Releases (shona_api.releases)"]
    end
    
    subgraph Serving ["4. Public Serving & UI"]
        DR --> |"Active Release Filter"| API["Protected DRF REST API (/v1/)"]
        DR --> |"Browse & Search"| WEB["Staff Explorer & Dashboard"]
    end

    class S1 source;
    class EU,ED,RS process;
    class CR,DR db;
    class API,WEB public;
```

---

## 📦 Core Subsystems & Django Apps

The codebase is organized into domain-specific internal apps under `shona_api/`:

*   **`lexicon`**: Houses the main canonical linguistic models—`NounClass`, `Lemma`, `Sense`, `ToneRecord`, `Form`, and `LearnerMetadata`. Computes phonological metadata on-the-fly and powers the exact search query logic.
*   **`morphology`**: Governs rule-based grammar processing. Includes a bounded analyzer and generator currently targeting present-tense, single-token verb forms (positive and negative polarities) tied to active rule sets.
*   **`extraction`**: Coordinates source-document parsing, tracking raw candidate dictionary entries (`ExtractionUnit`), orchestrating batch, Gemini pipeline, and precompiled GPT JSONL ingestion runs, and performing transactional promotion to the lexicon.
*   **`editorial`**: Implements governance controls, storing review status (`approved`, `needs_review`, `rejected`), notes, decisions, and detailed audit trails.
*   **`figurative_language`**: Manages cultural and expressive entries including proverbs (`tsumo`) and idioms (`madimikira`), complete with custom serializations, translations, and themes.
*   **`releases`**: Manages database versioning via `DataRelease` rows. Most public read endpoints require an active, current release to serve requests.
*   **`api_auth`**: Provides robust, hashed API keys (`shona_sk_...`), key prefix tracking, plan types, and custom per-key rate-limiting throttles (`APIKeyRateThrottle`) with automated header injection.
*   **`phonology`**: Core utility layer managing grapheme segmentation, digraph/trigraph parsing, and syllable count/syllabification rules.
*   **`sources`**: A central registry documenting source files (`hannan_dictionary.pdf`, `fortune_grammatical_constructions.pdf`, etc.), their roles, and authority levels.
*   **`web`**: A staff and local utility interface featuring a dictionary lookup interface, data progress counters, API key builder, and the Hannan ingestion dashboard.
*   **`api_docs`**: Hand-assembled OpenAPI 3.1 specification serving `/openapi.json`.
*   **`health`**: An unprotected `/health` status endpoint.

---

## 🛠️ Local Setup & Quickstart

### Prerequisites
- **Python >= 3.12**
- **PostgreSQL** (required for `pg_trgm` and `unaccent` search extensions in non-test modes)
- **Redis** (used as Django's cache backend and Celery's message broker/result backend)

---

### Step-by-Step Installation

#### 1. Setup Virtual Environment & Dependencies
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

#### 2. Configure Environment Variables
Copy the template `.env` file and configure your credentials:
```powershell
Copy-Item .env.example .env
```

#### 3. Run Database Migrations
Run core Django migrations followed by the Postgres search infrastructure migration:
```powershell
python manage.py migrate
python manage.py migrate infra
```

> [!NOTE]
> The `infra` migration installs the `pg_trgm` and `unaccent` extensions on PostgreSQL. When running test suites against SQLite, these SQL statements are safely ignored.

#### 4. Seed Seed-Data & Releases
Protected endpoints depend on standard seed records and a current release version. Run the following commands to bootstrap your database:
```powershell
# Seed the source registry
python manage.py seed_sources

# Seed the standard Shona noun classes
python manage.py seed_noun_classes

# Seed figurative language starter sets
python manage.py seed_figurative_expressions

# Create the current active data release and morphology rule-set mapping
python manage.py ensure_current_release --version 2026.05.local --label "Local development release" --rule-set-version morphology-rules-v2
```

#### 5. Generate a Local Developer API Key
Public endpoints are secured. Generate a developer API key to sign requests:
```powershell
python manage.py create_api_key "Local Development Key" --plan developer --rate-limit-per-minute 60
```
> [!WARNING]
> Keep the raw API key printed (starts with `shona_sk_...`) safe! The raw key is hashed and will **never** be shown in cleartext again.

#### 6. Start the Services
Start the local development server:
```powershell
python manage.py runserver
```

*(Optional)* Start the Celery worker to handle background queues (ensure Redis is running):
```powershell
celery -A config worker --loglevel=INFO
```

---

## Hannan Ingestion Workflows

The Hannan data pipeline supports two staff-facing ingestion modes from `/data-progress/ingestion/`:

- **Precompiled GPT JSONL import**: Imports a trusted GPT-5.5 JSONL batch directly into `ExtractionUnit` rows. This is the preferred path when a batch has already been structured and reviewed outside the app.
- **Gemini PDF pipeline**: Runs the local parser/Gemini flow against a selected PDF page range, writes compiled JSONL, then imports the output into the extraction queue.

For precompiled GPT JSONL imports, place `.jsonl` files in:

```text
shona_api/parsers/hannan_llm/llm_extracted_batches/
```

Then open `/data-progress/ingestion/`, choose **Import compiled GPT-5.5 output**, select the JSONL file, and keep duplicate skipping enabled unless you intentionally want to import corrected duplicate source references. The dashboard records import status per file, supports dry runs, and can mark imported extraction units as approved or publish them automatically.

The same import path is also available from the terminal:

```powershell
python manage.py import_gpt_5_5_parsed path\to\file.jsonl --dry-run
python manage.py import_gpt_5_5_parsed path\to\file.jsonl --batch-id GPT-5.5-THINKING-20260521-183447
```

Repair tooling is available for malformed or partially structured GPT output:

```powershell
python manage.py repair_gpt_hannan_structuring path\to\file.jsonl --dry-run
```

Local Hannan PDFs, page images, generated JSON, generated JSONL, and run logs are intentionally ignored by Git. Keep committed parser code and docs in the repo, but keep source PDFs and generated extraction artifacts local unless they have been deliberately curated for publication.

See `docs/data_population/hannan_ingestion_dashboard.md` and `shona_api/parsers/hannan_llm/README.md` for the operator checklist and parser notes.

---

## 🔌 API Endpoints Reference

All requests to endpoints (excluding `/health` and `/openapi.json`) require a valid API key passed in the headers:
- `Authorization: Api-Key shona_sk_...` OR
- `X-API-Key: shona_sk_...`

Successful responses are returned in a standard envelope:
```json
{
  "api_version": "v1",
  "data_release": "2026.05.local",
  "rule_set_version": "morphology-rules-v2",
  "generated_at": "2026-05-21T14:00:00Z",
  "data": { ... }
}
```

| Method | Endpoint | Description | Query / Body Parameters |
|:---|:---|:---|:---|
| **GET** | `/health` | Unprotected system health check. | None |
| **GET** | `/openapi.json` | Serves the OpenAPI 3.1 Spec. | None |
| **GET** | `/v1/search` | Search canonical lemmas & forms with orthographic normalization. Exposes rule-based morphology enrichment. | `q` (search query, e.g., `?q=buda`) |
| **GET** | `/v1/lemmas/{public_id}` | Retrieve a full canonical lemma, including senses, tones, and exposed forms. | `public_id` (e.g., `lemma_abc123`) |
| **GET** | `/v1/figurative-expressions/tsumo` | List active reviewed proverbs. | None |
| **GET** | `/v1/figurative-expressions/tsumo/{public_id}` | Retrieve details of a specific proverb. | `public_id` (e.g., `expr_xyz789`) |
| **GET** | `/v1/figurative-expressions/madimikira` | List active reviewed idioms. | None |
| **GET** | `/v1/figurative-expressions/madimikira/{public_id}` | Retrieve details of a specific idiom. | `public_id` |
| **POST** | `/v1/analyze` | Run rule-based morphological analysis on a single verb form (positive/negative present tense). | `{"text": "ndinobuda"}` |
| **POST** | `/v1/generate` | Synthesize an inflected verb form from a stem lemma, grammatical features, and polarity. | `{"lemma_public_id": "...", "features": {...}}` |

---

## 🛠️ Linguistic & Parsing Tools

The project contains custom command-line utilities to support local testing and data pipeline diagnostics.

### Syllable Parsing & Phonology Checks
Phonology utility code exposes rules to count syllables and parse grapheme clusters. Test it interactively using Django shell:
```python
from shona_api.phonology.syllables import segment_graphemes, count_syllables
segment_graphemes("mwana") # Returns ['mw', 'a', 'n', 'a']
count_syllables("mwana") # Returns 2
```

### OpenAPI Spec Generation
Re-generate and commit changes to the OpenAPI specification using:
```powershell
python manage.py generate_openapi_spec
```

---

## 🧪 Running Tests

A highly comprehensive suite of **175 automated tests** validates API auth, rate-limiting, schemas, models, parser segments, GPT JSONL ingestion, and rule-based morphology.

To execute tests against the fast-running local test configuration (which defaults to SQLite):
```powershell
pytest
```

---

## ⚙️ Configuration Reference

The application loads settings from environment variables. The key options are:

| Variable | Description | Default |
|:---|:---|:---|
| `DJANGO_SETTINGS_MODULE` | The settings module to boot with. | `config.settings.dev` |
| `DEBUG` | Enables/disables verbose debugging. | `False` |
| `SECRET_KEY` | Django standard security key. | `dev-only-change-me` |
| `DATABASE_URL` | Database connection URL. | `postgres://shona_api:shona_api@localhost:5432/shona_api` |
| `REDIS_URL` | Redis URL for caches and Celery tasks. | `redis://localhost:6379/0` |
| `LOG_LEVEL` | Logging level. | `INFO` |
| `APP_VERSION` | Application version returned in health response. | `0.1.0` |
| `CELERY_TASK_ALWAYS_EAGER` | Inline execution of Celery tasks. | `False` |
