# GPT-5.5 Hannan JSONL Prompt v3

Use this prompt when asking GPT-5.5 to produce precompiled Hannan JSONL for
`import_gpt_5_5_parsed`.

```text
I am working on the Hannan Standard Shona Dictionary extraction pipeline.

Your job is to produce a JSONL file for one PDF page, using the exact JSONL
structure below. Do not give me normal prose. Generate the file and give me a
download link only.

Context:
- The source PDF is: Standard Shona Dictionary - Hannan.pdf
- The target page is: PDF page [INSERT PAGE NUMBER]
- Use the rendered page image if available. If not, render that PDF page and
  read it visually.
- Extract every dictionary entry on that page.
- The output must be JSONL: one JSON object per line.
- File name format: GPT-5.5-YYYYMMDD-HHMMSS.jsonl
- The parser/model name must be: gpt-5.5-thinking
- The parser output schema version must be: hannan-gpt-jsonl-v3

Important page numbering:
- The compiler logic calculates actual book page as:
  actual_page = pdf_page - 24
- So if extracting PDF page 36, primary_source_page and source_pages must use
  actual page 12.

Each JSONL line must have this exact top-level structure:

{
  "source_locator": "hannan:page_XXX:entry_YYY:SAFE_HEADWORD_SLUG",
  "raw_text": "The full raw dictionary entry text as printed/reconstructed from the page.",
  "confidence": 1.0,
  "primary_source_page": ACTUAL_BOOK_PAGE_NUMBER,
  "source_pages": [ACTUAL_BOOK_PAGE_NUMBER],
  "parser_output": {
    "schema_version": "hannan-gpt-jsonl-v3",
    "headword": "...",
    "headword_kind": "word | noun | verb_stem | ideophone | unknown",
    "part_of_speech": {"code": "...", "label": "..."},
    "dialects": [],
    "comparative_bantu_marker": false,
    "tone_pattern": null,
    "tone_records": [{"pattern": "...", "dialects": []}],
    "noun": null,
    "senses": [
      {
        "number": 1,
        "definition": "...",
        "dialects": [],
        "grammar": [],
        "examples": [{"shona": "...", "english": "..."}],
        "cross_references": [{"type": "cp", "target": "...", "dialects": []}]
      }
    ],
    "idiomatic_expressions": [
      {
        "expression_text": "...",
        "idiomatic_meaning": "...",
        "english_rendering": "...",
        "dialects": [],
        "linked_headwords": [],
        "source_sense_number": 1,
        "usage_note": ""
      }
    ],
    "derived_forms": [],
    "raw_entry_text": "Same as raw_text unless preserving a different reconstruction.",
    "parse_metadata": {"parser": "gpt-5.5-thinking", "completeness": "parsed"},
    "normalized_headword": "headword without leading hyphen"
  },
  "provenance": {
    "source_filename": "Standard Shona Dictionary - Hannan.pdf",
    "pdf_page_number": PDF_PAGE_NUMBER,
    "actual_page_number": ACTUAL_BOOK_PAGE_NUMBER,
    "model_name": "gpt-5.5-thinking",
    "compiler": "gpt-5.5-direct-jsonl-v3"
  }
}

Extraction rules:
1. Extract every visible entry on the page, not just the easy ones.
2. Preserve initial hyphens for verb stems, for example "-bva".
3. normalized_headword removes only the leading hyphen and surrounding whitespace.
4. Dialect markers:
   K = Karanga; Ko = Korekore; Ko(B) = Budya; M = Manyika; Z = Zezuru.
   Store dialect markers as short codes exactly, for example ["K", "M"].
   Split compact dialect clusters: KMZ means ["K", "M", "Z"], KKoMZ means
   ["K", "Ko", "M", "Z"].
5. Part of speech:
   n = noun; v = verb; vi = intransitive verb; vt = transitive verb;
   adv = adverb; conj = conjunction; demons = demonstrative; ideo = ideophone;
   inter = interjective; pron = pronoun; poss = possessive; sfx = suffix.
6. Tone parsing:
   - Tone appears in square brackets after the headword.
   - If the bracket contains one simple tone pattern, set tone_pattern to that
     pattern and create one tone_records item.
   - If the bracket contains dialect-scoped alternatives separated by semicolons,
     split them into multiple tone_records.
   - Do not include dialect letters inside pattern. pattern may contain only tone
     notation such as H, L, HL, LHLH.
7. Noun classes:
   - If the entry is a noun, numbers immediately after "n" are noun classes, not
     sense numbers.
   - If no noun metadata is printed, use empty lists. If not a noun, use null.
8. Senses:
   - The first English gloss after POS and metadata is sense 1, even when it is
     not numbered.
   - Printed "2.", "3.", "4.", etc. start later senses.
   - A sense definition must never contain a later numbered marker like " 2. ".
   - If a numbered sense begins with dialect codes, put them in that sense's
     dialects.
9. Examples:
   - Examples are full Shona usage sentences or phrases that illustrate a sense
     and have an English translation.
   - Put examples in the examples list of the most relevant sense.
   - Do not put idiomatic expressions in examples.
10. Idiomatic expressions:
   - A named Shona expression with a non-literal meaning belongs in
     idiomatic_expressions, not in senses and not in examples.
   - This often appears as "Expression (KZ): English meaning." or
     "Expression: English meaning."
   - Capture the printed expression in expression_text.
   - Capture the source meaning in idiomatic_meaning.
   - If the source gives only one English rendering, repeat it in
     english_rendering.
   - Put dialect markers from parentheses such as (KZ) into dialects.
   - Put the headword and any other identifiable component words in
     linked_headwords.
   - Set source_sense_number when the idiom clearly belongs to a numbered sense;
     otherwise use null.
11. Cross references:
   - "cp", "cf", "qv", "see", and similar references go into cross_references.
12. Derived forms:
   - Verb-derived forms marked with arrows like ">" or "<-" go into derived_forms.
   - Preserve the relation marker and short raw note when present, for example
     {"marker": ">", "forms": ["mbudo", "rubudiko"], "source_note": "> mbudo; rubudiko."}
13. Etymology:
   - Etymology is not part of this schema. Preserve borrowed-language markers in
     raw_text, and include them in definitions only if removing them would mislead.
14. Confidence:
   - Use 1.0 only when the entry structure is clear. If unclear, preserve the
     uncertainty in raw_text and set confidence lower, for example 0.85.
15. JSON validity:
   - Use valid JSON only. No comments. No trailing commas.
   - The final artifact must be JSONL, not a JSON array.

Before finalising, validate internally:
- Each line is valid JSON.
- parser_output has schema_version, headword, headword_kind, part_of_speech,
  dialects, comparative_bantu_marker, tone_pattern, tone_records, noun, senses,
  idiomatic_expressions, derived_forms, raw_entry_text, parse_metadata, and
  normalized_headword.
- No sense definition contains " 2. ", " 3. ", " 4. ", " 5. ", " 6. ", " 7. ",
  " 8. ", or " 9. ".
- No tone record pattern contains dialect letters glued to tone letters.
- If raw_text contains a semicolon inside tone brackets, parser_output.tone_records
  has more than one item.
- Give me only the download link to the generated JSONL file.
```
