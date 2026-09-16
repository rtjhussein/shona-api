# Lexical QA — published lexicon against its source lines

A frozen, reproducible check of the published lexicon against the Hannan lines
it came from. The morphology evaluation (`evaluation/source_backed/`) tests a
*rule engine* against fixtures; this tests *data* against its source.

## Why it can disagree with the implementation

Every extraction unit stores the verbatim Hannan line (`raw_text`) next to the
parser output that produced its published record. The expectations are derived
by `tools/lexical_qa.py`, a reader written from the documented line format
(product requirements section 17.1) that **imports nothing from `shona_api`**.
The published corpus, by contrast, was produced by two LLM parsers
(`gpt-5.5-thinking`, `ox-alpha-vision`). Comparing a separate implementation
against theirs is what makes disagreement meaningful; a reader that reused the
project's parser would only confirm itself.

The evaluator scores the **published record** — what the API serves — not the
parser output, so a value the parser lost at promotion counts as a defect and a
value it never recorded does not.

## What is measured

| Check | Contract |
| --- | --- |
| `headword` | published `normalized_headword` equals the source headword |
| `word_class` | published `headword_kind` equals the class the line attests (`noun` / `verb_stem` / `ideophone`) |
| `noun_class` | published `noun_class` equals the class written after `n` (nouns carrying a class only) |
| `tone` | every tone alternative in the bracket is present on the record (word grouping ignored) |
| `part_of_speech_label` | the published label is a category name, not entry text |

Raw numerators and denominators per check; measures are never blended.

## Sampling

Sampling is deterministic (seed `20260916`, 18 cases per stratum) and stratified
by **source-line shape**, never by anything the implementation produced:
`noun_subclass` (`n 1a`), `noun_with_plural`, `noun_plain`, `verb_transitive`,
`verb_intransitive`, `verb_ambitransitive`, `verb_other`, `ideophone`,
`multiword_headword`. Stratifying by shape is what lets the instrument reach the
entries where parsing is hard — a uniform draw over the whole dictionary missed
every known defect class.

## Running

```console
python tools/build_lexical_qa_corpus.py --out evaluation/lexical_qa/v1
python tools/build_lexical_qa_corpus.py --check-only          # corpus integrity
python tools/evaluate_lexical_qa.py \
    --corpus evaluation/lexical_qa/v1/corpus.json \
    --out evaluation/lexical_qa/v1/results
pytest tests/test_lexical_qa_evaluation.py -q
```

The corpus is regenerated from `db/shona.sqlite3`, which is opened **read-only**
(`mode=ro`); the evaluator cannot write to it.

## Baseline (lexical-qa-v1, 324 cases, 2026-09-16)

| Check | Correct |
| --- | --- |
| headword | 322/324 |
| word_class | 319/324 |
| noun_class | 112/112 |
| tone | 324/324 |
| part_of_speech_label | 323/324 |

Coverage (not scored): of 42 sampled nouns whose source line records a plural,
**0** publish a form matching one of those prefixes. The prefixes are recorded
in parser output; nothing surfaces them as `Form` records yet.

Confirmed defects behind the failures:

- **Generic `word` class (5 cases here; 1,866 published records).** Entries the
  line marks as noun or verb are published with the catch-all
  `headword_kind="word"`, which the morphology engine does not read:
  `†-ti [L]KKoMZ defective v Say.`, `-nga- [L]KMZ defective v Be.`,
  `-pfutura [L]Z v t`.
- **Truncated multi-word headwords (2 cases).** `wara wara` and `wushu wushu`
  publish as `wara` and `wushu`.
- **Part-of-speech residue (1 case here; 51 published records).** `†moyo
  [LL]KKo n 3, pl: moyo, Heart (physical organ).` publishes the label
  `o n 3, pl: moyo, Heart (physical organ).` — the parser mishandled the leading
  dagger marker. 5 of the 51 trace to dagger-marked lines.

## Fixed by the harness

**Sub-class loss.** Lines written `n 1a` published as class `1`
(`Chikumi [LHH]KMZ n 1a June.`, `godzonga [HH]Z n 1a & 5 Tyrant.`,
`gufu [LH]MZ n 1a (M), 5 (Z)`), and Hannan's 1a takes a different concord from
class 1. `noun_class` scored 97/112 when this was first measured.

Both parsers dropped the letter, so the parser output could not be re-read for
it; the source line is the authority. `shona_api/parsers/hannan.py` now reads
sub-classes, dialect-qualified alternatives, and classes without a `pl:` list
and exposes `read_attested_noun_classes`; `manage.py repair_noun_classes`
corrected 733 published records (465 of which had no class at all, including
401 nouns the parser had left bare), and promotion prefers the attested class,
recording the parser's conflicting reading in provenance.

Noun lemmas carrying a class moved from 8,924 (46.8%) to 19,040 (99.8%), and
this check reads 112/112. `2b` (9 records) and `2m` (1) remain unrepaired:
no `NounClass` row exists for them, and inventing one would invent a concord.

The remaining failures are **not** repaired by this harness: it reports them.
The promotion gate (`validate_publishable_parser_output`) now refuses new
records with residue labels, a missing class on a noun, or no part-of-speech
code, so the defects cannot grow while the existing rows await editorial review.

## Limitations, stated plainly

- The reader parses 40,205 of 40,519 published lines (99.2%); 314 lines (letters,
  notes, particles, entries without a tone bracket) carry no scoreable word
  class and are counted, not scored.
- Tone comparison normalises away word grouping, so `[H H H]` and `[HHH]` agree.
  Differences of that kind are reported as informational extras.
- Nine brackets in the corpus use a comma (`[HL, LH]`); a comma there is
  ambiguous between a second alternative and a trailing annotation
  (`[HL HL, strong t M]`), so the reader treats a comma as part of the segment
  and those cases are not distinguished. A handful of such records carry no tone
  at all rather than a wrong one.
- Definitions, sense counts, and multi-word phrasing are not scored yet.
- The corpus is a sample: it bounds the defect rate, it does not enumerate every
  bad record. Population counts quoted above come from direct queries.
