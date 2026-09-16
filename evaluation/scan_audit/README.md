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
