# Tone audit — first sample (2026-09-16)

The first check of the tone field against the scan. No tone record had ever been
verified against the page, and the same extraction pipelines have been caught
misreading this scan elsewhere (`dikanwa … pl: mad-` recorded as `madh-`), so the
field was unmeasured rather than known-good.

## Method

Rendered one column of Hannan dictionary page 22 (PDF page 46) with
`tools/render_dictionary_entry.py`, read every bracket on it, and compared each
with the `ToneRecord.pattern` values published for that headword.

A whole column was read at once rather than one entry per call: the crop the tool
writes is wider than a single entry (it spans the column), so asking about the
column costs the same and covers more. Narrowing the crop to one entry is worth
doing if this becomes routine, since a question naming the column invites the
reader to report every headword on it rather than the one wanted.

## Result

| headword | scan bracket | published `pattern` | agrees |
| --- | --- | --- | --- |
| `bimhimhi` | `[LHL]` | `LHL` | yes |
| `bimhiri` | `[LLL]` | `LLL` | yes |
| `bimvu` | `[HL]` | `HL` | yes |
| `bimwa` | `[LH]` | `LH` | yes |
| `bina` | `[HL]` | `HL` | yes |
| `binamhina` | `[LLHH]` | `LLHH` | yes |
| `binduka` | `[H]` | `H` | yes |
| `bindupindu` | `[LHLL]` | `LHLL` | yes |
| `bimhidza` | `[H M; LHLH Z]` | `LHL`, `H`, `LHLH` | yes — both dialect alternatives are present (`H` for M, `LHLH` for Z); the extra `LHL` is not contradicted by this bracket |
| `binduko` | `[HHL]` and `[LLL]`, two entries | `HHL`, `LLL` | yes — one value per entry |

**No disagreement found.** Every value the scan prints is represented in the
published records, including the dialect-split bracket, which is the case most
likely to be dropped by a pipeline that keeps only the first value.

## Limits, stated plainly

- **One column of one page.** Ten headwords compared, out of 42,054 tone
  records. This does not support a claim about the field as a whole, and it is
  not evidence that the field is correct — only that this sample found nothing
  wrong.
- It does *not* contradict the plural finding: the `d` → `dh` misread was in a
  plural prefix, a different field written by a different part of the pipeline.
- A field can be right in one column and wrong in another; a sample only bounds
  the error rate, and ten records bound it weakly.

## Why it is worth recording anyway

A clean result is information. The plural audit found a systematic misread within
its first few entries; this one found none in its first ten, which is the first
evidence that the tone pipeline is more reliable than the plural prefix path —
and worth knowing before commissioning a large audit of either.

---

## Second sample (independent)

A subagent audited eight more entries on dictionary page 129 using the same
method, reading the crops itself rather than only through a vision query, and
using targeted queries as an independent second reading of each row:

| headword | scan | published | agrees |
| --- | --- | --- | --- |
| `dikinyarwa` | `[HHLH]` | `HHLH` | yes |
| `dikisa` | `[LLL]` | `LLL` | yes |
| `dikisingwi` | `[LLHH]` | `LLHH` | yes |
| `dikita` | `[LLH]` | `LLH` | yes |
| `dikiti` | `[HHH M; LHL Ko]` | `HHH`, `LHL` | yes |
| `dikitiki` | `[LLLL]` | `LLLL` | yes |
| `diko` | `[HL]` | `HL` | yes |
| `dikurwa` | `[HLH]` | `HLH` | yes |

8 of 8 agreed. **Combined: 18 tone records verified against the scan, no
disagreement.** Still a small sample, and the limits above stand.

Two things it reported that the table cannot show:

- `dikiti` prints one bracket carrying two patterns with dialect tags inside it
  (`[HHH M; LHL Ko]`), and the corpus stores that as two tone records which drop
  the M/Ko attribution and the fact that they are variants of one entry. The
  values are right; the structure loses information.
- `diko` occurs twice on the page with the same bracket, so the noun row is
  confirmed but is not the only `diko` there.

## The method itself had two defects, now fixed

The audit found bugs in `tools/render_dictionary_entry.py` — the tool both
samples were taken with — and they are worth recording because they affect any
reading made with it before this commit:

1. **It framed the wrong hit.** `page.search_for(headword)[0]` returns the first
   *substring* occurrence, and a headword also occurs in cross-references
   (`cp -dimba`) and running heads. For `dimba` the crop framed a cross-reference
   in the facing column, and the reading that came back was a merge of a
   neighbouring entry's line with `dimba`'s plural. The tool now prefers the hit
   whose line continues into a tone bracket, which is what an entry looks like.
2. **The crop was wide enough to include the facing column**, so a question about
   it could be answered from a neighbouring line — asking about `dikita`
   returned `dikisingwi`. The crop is now bounded to the entry's column.

Both readings taken before the fix that carry weight were re-checked with it:

- `budiriro [HHHL]KMZn 9, pl: mab-` — unchanged, so the class 9 / Fortune
  conflict stands and its register entry is sound.
- `dimba` — the door entry reads `pl: mad-` and the rice-field entry `pl: mat-`,
  independently confirming the extraction misread of `madh-`.

The general lesson, which is the same one the plural work kept producing: a
reading is only as good as the crop it came from, and a tool that silently
frames the wrong line produces confident answers about the wrong text.
