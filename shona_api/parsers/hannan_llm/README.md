# Hannan LLM Parser

Local extraction scripts used by the shona-api ingestion dashboard.

Generated files are intentionally ignored:

- `source/`
- `llm_extracted_batches/`
- `*.pdf`
- `*.json`
- `*.jsonl`
- rendered page images

## Gemini Extraction

```powershell
cd C:\Users\user\Documents\Projects\shona-api
.\.venv\Scripts\python.exe shona_api\parsers\hannan_llm\llm_parser.py --start-page 29 --end-page 30
.\.venv\Scripts\python.exe shona_api\parsers\hannan_llm\compile_llm_batches.py --start-page 29 --end-page 30
```

The Django dashboard uses the same scripts and defaults.

## GPT JSONL Imports

Place precompiled GPT JSONL files in:

```text
shona_api\parsers\hannan_llm\llm_extracted_batches\
```

Then import them from the Hannan ingestion dashboard.
