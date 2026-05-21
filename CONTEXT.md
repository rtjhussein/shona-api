# Shona API Context

## Glossary

- **Gemini pipeline**: The trusted Hannan ingestion path that renders dictionary PDF pages, sends them to Gemini for structured extraction, compiles the page JSON into JSONL, and imports those entries as extraction units with parser `gemini-2.5-flash-v1`.
- **Extraction unit**: A source-backed candidate dictionary entry stored before or during editorial/publication workflow. It preserves raw text, parser output, parser status, review state, batch id, and provenance.
- **Review candidate**: An extraction unit that has been imported but is not yet canonical public dictionary data.
- **Canonical lemma**: A public dictionary lemma record produced from an approved extraction unit and exposed through the lexical API when published.
- **Published word**: A canonical lemma or form with review state `published`; dictionary search should only expose published records.
