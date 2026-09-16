# Per-field fidelity audit — first pages (2026-09-16)

How faithfully the published corpus reproduces the scan, measured **per field**
rather than one field at a time. Two fields had been checked before (plural
prefixes, tone); POS and noun class never had. One page-read yields verdicts on
all of them, so the audit reads a column and scores every field on it.

Rendered with `tools/render_dictionary_entry.py`, read directly and through an
independent vision query, with the published values read from the database.

## Results

| page | entries read | tone | POS | class | headword |
| --- | --- | --- | --- | --- | --- |
| 680 | 11 | 11/11 | 11/11 | 11/11 | 11/11 |
| 500 | 9 | 9/9 | 9/9 | 9/9 | **6/9** |

**20 entries audited. Tone 20/20, POS 20/20, noun class 20/20. Headword 17/20.**

Two clean pages on the fields that were scored, and the only errors found are in
a field that was not — which is the point of scoring several at once.

## Headword divergences on page 500

Not a verdict on the field, but three divergences on one page is worth recording:

| scan prints | published | what differs |
| --- | --- | --- |
| `nzvinzvi-i` | `nzvinzi-i` | the `v` is missing |
| `nzvirihi` | `nzvirihì` | a grave accent on the final vowel that the scan does not print |
| `nzwaivhi` | `nzwaiwhi` | `v` recorded as `w` |

The first and third are the same shape as the plural-prefix misread found
earlier: a consonant read as a neighbour. The second is different in kind — a
tone diacritic inside a headword the scan prints without one — and is the sort of
error that survives review because it looks like data rather than damage.

## Limits

- **Twenty entries of ~40,500.** This bounds the error rate weakly and supports
  no claim about any field as a whole.
- Both pages are ordinary dictionary pages. Notes, tables, letters, and the
  front matter are unsampled and are where the plural audit found most of its
  parser garbage.
- Fields not yet scored at all: definitions, senses, examples, cross-references,
  dialects, etymology, comparative-Bantu markers. Tone, POS, class and headword
  are all short tokens; a definition is prose, and prose is where a reader is
  least able to tell a misreading from a paraphrase.

## Why this shape of audit

Three passes over two fields produced one systematic defect and one clean result.
One pass over four fields produced both a clean result *and* a new defect class
in a field nobody had scored. Reading a page is the expensive part; scoring more
fields per read is nearly free, and it stops the audit from reporting "no error
found" simply because it was not looking.

---

## Third page — 40 entries, and the first systematic defect

Page 300 was audited entry by entry (40 rows, both columns, every crop
independently re-read through a vision query). Unlike the first two pages it is
**not clean**, and what it found is a different kind of error from the ones so
far:

| finding | count | shape |
| --- | --- | --- |
| **multi-word ideophone tone truncated** | **4 of 40** | scan `[LLL LLL]`, published `LLL` |
| headword consonant misread | 1 of 40 | scan `-kwamba`, published `-kwamha` |
| tone, POS, class, dialects | rest | all agree |

The ideophones are the significant one. `kwakwara kwakwara`, `kwakwari kwakwari`
and `kwakwasha kwakwasha` are two-word headwords whose bracket carries a pattern
**per word** (`[LLL LLL]`), and the corpus publishes only the first (`LLL`). Four
of the page's ideophones do this — a tenth of the page — and page 300 is a
dense ideophone page, so the field is likely to show the same on other
ideophone-heavy pages. The engine already handles a multi-word bracket correctly
elsewhere (`munhondo churu` publishes `LLL HH`), so this is a gap in the
ideophone path rather than a missing capability.

`-kwamba` -> `-kwamha` is the same consonant misread as the plural prefixes and
the page-500 headwords: `b` read as `h`, this time with the two adjacent on the
keyboard rather than in a cluster.

One row was flagged and should not be counted as a defect: the scan prints what
looks like `n la` for class `1a`, which is a glyph confusion between `l` and `1`
in the typeface, and the published `1a` is the correct reading.

### Running totals

| page | entries | tone | POS | class | dialects | headword |
| --- | --- | --- | --- | --- | --- | --- |
| 680 | 11 | 11/11 | 11/11 | 11/11 | — | 11/11 |
| 500 | 9 | 9/9 | 9/9 | 9/9 | — | 6/9 |
| 300 | 40 | **36/40** | 40/40 | 40/40 | 40/40 | 39/40 |

**60 entries across three pages.** Tone 56/60, POS 60/60, class 60/60, dialects
40/40, headword 56/60.

Sixty entries still bounds the error rate weakly, and the three pages are not a
random sample — but the shape of the answer has changed from "clean" to
**uneven by entry type**: single-word entries scored perfectly on every field,
and the errors cluster in multi-word ideophones and in headwords containing a
consonant pair that can be misread. That is a much more useful thing to know
before commissioning repairs, because it names where to look rather than
justifying a blanket re-check of 40,500 records.
