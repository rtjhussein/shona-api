# GPT-5.5 Hannan JSONL Prompt v2

Use this prompt when asking GPT-5.5 to produce precompiled Hannan JSONL for
`import_gpt_5_5_parsed`.

```text
I am working on the Hannan Standard Shona Dictionary extraction pipeline.

Your job is to produce a JSONL file for one PDF page, using the exact JSONL structure below. Do not give me normal prose. Generate the file and give me a download link only.

Context:
- The source PDF is: Standard Shona Dictionary - Hannan.pdf
- The target page is: PDF page [INSERT PAGE NUMBER]
- Use the rendered page image if available. If not, render that PDF page and read it visually.
- Extract every dictionary entry on that page.
- The output must be JSONL: one JSON object per line.
- File name format:
  GPT-5.5-YYYYMMDD-HHMMSS.jsonl
  Use the actual current timestamp.
- The parser/model name must be:
  gpt-5.5-thinking
- The parser output schema version must be:
  hannan-gpt-jsonl-v2

Important page numbering:
- The compiler logic calculates actual book page as:
  actual_page = pdf_page - 24
- So if extracting PDF page 36, primary_source_page and source_pages must use actual page 12.

Each JSONL line must have this exact top-level structure:

{
  "source_locator": "hannan:page_XXX:entry_YYY:SAFE_HEADWORD_SLUG",
  "raw_text": "The full raw dictionary entry text as printed/reconstructed from the page.",
  "confidence": 1.0,
  "primary_source_page": ACTUAL_BOOK_PAGE_NUMBER,
  "source_pages": [ACTUAL_BOOK_PAGE_NUMBER],
  "parser_output": {
    "schema_version": "hannan-gpt-jsonl-v2",
    "headword": "...",
    "headword_kind": "word | noun | verb_stem | ideophone | unknown",
    "part_of_speech": {
      "code": "...",
      "label": "..."
    },
    "dialects": [],
    "comparative_bantu_marker": false,
    "tone_pattern": null,
    "tone_records": [
      {
        "pattern": "...",
        "dialects": []
      }
    ],
    "noun": null,
    "senses": [
      {
        "number": 1,
        "definition": "...",
        "dialects": [],
        "grammar": [],
        "examples": [
          {
            "shona": "...",
            "english": "..."
          }
        ],
        "cross_references": [
          {
            "type": "cp",
            "target": "...",
            "dialects": []
          }
        ]
      }
    ],
    "derived_forms": [],
    "raw_entry_text": "Same as raw_text unless there is a specific reason to preserve a slightly different reconstruction.",
    "parse_metadata": {
      "parser": "gpt-5.5-thinking",
      "completeness": "parsed"
    },
    "normalized_headword": "headword without leading hyphen"
  },
  "provenance": {
    "source_filename": "Standard Shona Dictionary - Hannan.pdf",
    "pdf_page_number": PDF_PAGE_NUMBER,
    "actual_page_number": ACTUAL_BOOK_PAGE_NUMBER,
    "model_name": "gpt-5.5-thinking",
    "compiler": "gpt-5.5-direct-jsonl-v2"
  }
}

Extraction rules:
1. Extract every visible entry on the page, not just the easy ones.
2. Preserve initial hyphens for verb stems, for example "-bva".
3. normalized_headword removes only the leading hyphen and surrounding whitespace.
4. headword_kind:
   - noun entries use "noun"
   - verb stems beginning with "-" use "verb_stem"
   - ideophones use "ideophone"
   - otherwise use "word" or "unknown"
5. Dialect markers:
   K = Karanga
   Ko = Korekore
   Ko(B) = Budya
   M = Manyika
   Z = Zezuru
   Store dialect markers as short codes exactly, for example ["K", "M"].
6. Part of speech:
   n = noun
   v = verb
   vi = intransitive verb
   vt = transitive verb
   v i = intransitive verb
   v t = transitive verb
   adv = adverb
   conj = conjunction
   demons = demonstrative
   ideo = ideophone
   inter = interjective
   pron = pronoun
   poss = possessive
   sfx = suffix
   Use the printed code in part_of_speech.code and a clear human label in part_of_speech.label.
7. Tone parsing:
   - Tone appears in square brackets after the headword.
   - If the bracket contains one simple tone pattern, for example [LL] or [HLL], set:
     "tone_pattern": "LL"
     "tone_records": [{"pattern": "LL", "dialects": entry dialects if known, otherwise []}]
   - If the bracket contains dialect-scoped alternatives separated by semicolons, split them into multiple tone_records.
   - Example:
     [H KM; LHLH Z]
     means:
     "tone_pattern": null
     "tone_records": [
       {"pattern": "H", "dialects": ["K", "M"]},
       {"pattern": "LHLH", "dialects": ["Z"]}
     ]
   - Example:
     [H; LHL]
     means:
     "tone_pattern": null
     "tone_records": [
       {"pattern": "H", "dialects": []},
       {"pattern": "LHL", "dialects": []}
     ]
   - Do not output glued strings like "HKM;LHLHZ".
   - Do not include dialect letters inside pattern. pattern may contain only tone notation such as H, L, HL, LHLH.
   - If no tone bracket appears, set "tone_pattern": null and "tone_records": [].
8. Entry dialects:
   - Dialect markers immediately after the tone bracket, such as [LL]KMZ, belong in parser_output.dialects.
   - Split compact dialect clusters: KMZ means ["K", "M", "Z"], KKoMZ means ["K", "Ko", "M", "Z"].
9. Noun classes:
   - If the entry is a noun, numbers immediately after "n" are noun classes, not sense numbers.
   - Example "n 5" means:
     "noun": {
       "classes": ["5"],
       "plural_prefixes": [],
       "plural_classes": []
     }
   - If no noun metadata is printed, use empty lists.
   - If the entry is not a noun, use "noun": null.
10. Plurals:
   - If "pl:" appears after noun metadata, put plural forms/prefixes into noun.plural_prefixes.
   - Do not put definitions into noun.plural_prefixes.
11. Senses:
   - The first English gloss after POS and metadata is sense 1, even when it is not numbered.
   - Printed "2.", "3.", "4.", etc. start later senses.
   - A sense definition must never contain a later numbered marker like " 2. ", " 3. ", or " 4. ".
   - If a definition contains a later numbered marker, split it into separate sense objects.
12. Sense-local dialects and grammar:
   - If a numbered sense begins with dialect codes, put them in that sense's dialects.
   - Example "2. KZ Cause to cook..." becomes:
     {"number": 2, "definition": "Cause to cook...", "dialects": ["K", "Z"], ...}
   - If a verb sense begins with "i", "t", "vi", or "vt", put that in grammar.
13. Examples:
   - Shona-English pairs like "Shona phrase: English translation." are examples, not definitions.
   - Put them in the examples list of the most relevant sense.
   - Do not leave example sentences glued into definition.
14. Cross references:
   - "cp", "cf", "qv", "see", and similar references go into cross_references.
   - Example "cp bere M." becomes:
     {"type": "cp", "target": "bere", "dialects": ["M"]}
15. Derived forms:
   - Verb-derived forms marked with arrows like ">" or "<-" go into derived_forms.
   - If the marker groups several forms, preserve them as a group object:
     {"marker": ">", "forms": ["mbudo", "rubudiko"]}
16. comparative_bantu_marker:
   - If the entry has the Common Bantu marker before it, set true.
   - Otherwise false.
17. Etymology:
   - Etymology is not part of this schema.
   - Preserve borrowed-language markers such as "<Eng." or "<Afr." in raw_text.
   - Include them in the relevant sense definition only if removing them would make the definition misleading.
18. Confidence:
   - Use 1.0 only when the entry structure is clear.
   - If something is unclear, preserve the uncertainty in raw_text and set confidence lower, for example 0.85.
19. JSON validity:
   - Use valid JSON only.
   - No comments.
   - No trailing commas.
   - The final artifact must be JSONL, not a JSON array.

Before finalising, validate internally:
- Each line is valid JSON.
- Each line has source_locator, raw_text, confidence, primary_source_page, source_pages, parser_output, and provenance.
- parser_output has schema_version, headword, headword_kind, part_of_speech, dialects, comparative_bantu_marker, tone_pattern, tone_records, noun, senses, derived_forms, raw_entry_text, parse_metadata, and normalized_headword.
- source_locator entry numbers are sequential: entry_001, entry_002, entry_003, etc.
- No sense definition contains " 2. ", " 3. ", " 4. ", " 5. ", " 6. ", " 7. ", " 8. ", or " 9. ".
- No tone record pattern contains dialect letters glued to tone letters.
- If raw_text contains a semicolon inside tone brackets, parser_output.tone_records has more than one item.
- Give me only the download link to the generated JSONL file.
```
