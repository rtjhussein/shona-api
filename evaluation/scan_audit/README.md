# Scan audits

Checks of the published corpus against the original Hannan scan. Each file
records what was read, what it showed, and the sample size, because a clean
result and a small sample are both facts that get lost if they are not written
down.

| file | what it covers |
| --- | --- |
| `field-fidelity-2026-09-16.md` | per-field audit of three pages: tone, POS, noun class, dialects, headword |
| `sizing-2026-09-16.md` | sizes the two defect classes the field audit found, and records three silent failures in the screening tool |
| `tone-sample-2026-09-16.md` | the first scan-verified tone sample (in `../plural_scan_audit/`) |
| `ideophone-tone-candidates.tsv` | the 26 multi-word ideophones whose stored tone cannot cover every word, with page locators — the work list for the repair |

## Method

```console
python tools/render_dictionary_entry.py <dict_page> <headword> C:/tmp/entry.png
read("C:/tmp/entry.png?q=Quote the tone bracket verbatim.")
```

Printed page = PDF page − 24. Two hazards, both found the hard way and since
fixed or noted: pass `--` before a headword beginning with `-`, and check the
crop frames the intended entry before reading it — the tool picks the hit whose
line continues into a bracket, but a page also carries the headword in
cross-references and running heads.

## Rule learned here

**A screen that returns zero gets checked against a case known to be positive
before it is believed.** Three separate bugs in the sizing tool each produced a
confident zero for a defect the scan had already shown to be real. Silent
measurement failures look exactly like results.

## A confusable pair is settled by the letter's shape, not by eye

The headword sample (38 of 527 candidates, 2026-09-16) found that a pair like
`bumba`/`bumha` is hard to read by eye below roughly 20x - one reading of `p148`
`dzimbabwe` came out as `dzimbahwe` and had to be corrected. Two tests settle the
letter from page pixels instead, and both are independent of any extracted text:

- **b against h**: a printed `b` encloses a counter, a hole in the glyph; `h`
  never does. Count the holes in the rendered headword and compare with the count
  the spelling predicts. Calibrated on the same page before use (`dzimba`=3,
  `dzimbo`=3, `madz`=2, `dzikiti`=1).
- **v against w**: measure the disputed letter's ink width. At this page size
  `v` runs about 4.8-5.1 pt and `w` about 7.2-7.8 pt.

The sample also narrowed what the 527 screen is actually looking at: both the
flagged pairs and the symmetric pairs are almost entirely **legitimate distinct
words** - `bwabwa` and `bwahwa` are two entries the dictionary prints on the same
page, one an ideophone of talking rapidly and one a noun meaning potato blight.
A screen that flags such pairs is reporting a feature of the dictionary, not a
defect in the record.
