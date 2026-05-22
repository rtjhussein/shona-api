# Hannan Ingestion Dashboard

The staff ingestion dashboard can import a precompiled GPT JSONL file or run the
local Hannan Gemini pipeline from the Django UI instead of requiring a terminal
for every step.

## Local setup

1. Start the API server:

```powershell
python manage.py migrate
python manage.py seed_sources
python manage.py runserver
```

2. Log in as a staff user at `/admin/`.

3. Open `/data-progress/ingestion/`.

4. Save a Gemini API key in the dashboard. The key is written to
`.local_gemini.env`, which is ignored by git. If `GEMINI_API_KEY` is already set
in the server environment, that environment value is used instead.

The dashboard expects the local LLM parser scripts at:

```text
C:\Users\user\Documents\Projects\shona-api\shona_api\parsers\hannan_llm
```

and the Hannan PDF at:

```text
C:\Users\user\Documents\Projects\shona-api\shona_api\parsers\hannan_llm\source\Standard Shona Dictionary - Hannan.pdf
```

## UI workflow

### Precompiled GPT JSONL

1. Place the JSONL file in `shona_api\parsers\hannan_llm\llm_extracted_batches\`.
2. Open the dashboard and use **Import compiled GPT-5.5 output**.
3. Keep auto-approve enabled for parseable extraction units.
4. Leave duplicate skipping enabled unless intentionally importing corrected GPT
   units alongside existing entries with the same source locator.

The UI performs:

```text
Compiled JSONL -> import_gpt_5_5_parsed -> approved ExtractionUnit rows
```

### Gemini fallback

1. Choose a PDF page range.
2. Optionally provide a batch id. If left blank, the dashboard generates one.
3. Choose whether to re-extract existing page JSON.
4. Choose whether the import should be a dry run.
5. Choose whether to auto-approve and publish parseable Gemini entries.
6. Start ingestion and watch the run log.

The UI performs:

```text
PDF page image -> Gemini structured JSON -> compiled JSONL -> import_gemini_parsed
```

When auto-publish is enabled, only parseable `gemini-2.5-flash-v1` units from
the selected run are marked approved and passed through the existing publication
service. Failed parser outputs and outputs containing parser errors are left
unpublished.

## Terminal fallback

Extract pages directly from the API repo:

```powershell
cd C:\Users\user\Documents\Projects\shona-api
.\.venv\Scripts\python.exe shona_api\parsers\hannan_llm\llm_parser.py --start-page 29 --end-page 30
.\.venv\Scripts\python.exe shona_api\parsers\hannan_llm\compile_llm_batches.py --start-page 29 --end-page 30 --output-jsonl shona_api\parsers\hannan_llm\llm_extracted_batches\GEMINI-TEST.gemini.jsonl
```

Import and optionally publish from the API repo:

```powershell
cd C:\Users\user\Documents\Projects\shona-api
python manage.py import_gemini_parsed shona_api\parsers\hannan_llm\llm_extracted_batches\GEMINI-TEST.gemini.jsonl --batch-id GEMINI-TEST
python manage.py publish_hannan_batch --batch-id GEMINI-TEST
```

Or run the full local pipeline command:

```powershell
python manage.py run_hannan_gemini_pipeline --batch-id GEMINI-TEST --start-page 29 --end-page 30 --auto-publish
```

## Cleanup

Preview fixture cleanup:

```powershell
python manage.py cleanup_non_gemini_fixtures
```

Delete the targeted non-Gemini fixture records:

```powershell
python manage.py cleanup_non_gemini_fixtures --execute
```

The cleanup command preserves published Gemini/Hannan output.

## Viewing newly ingested words

Search only exposes published canonical records. After a run with auto-publish
enabled, open `/dictionary/`, create or paste a local API key, and search for one
of the headwords from the run log or admin extraction list.

Without auto-publish, review candidates first from the dashboard's review link
or the extraction unit admin, then publish approved units with:

```powershell
python manage.py publish_hannan_batch --batch-id YOUR-BATCH-ID
```
