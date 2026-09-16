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
