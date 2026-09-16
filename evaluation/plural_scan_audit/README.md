# Plural refusal audit — open work list

`worklist.tsv` lists the noun-plural refusals that remain after the class rules,
the grapheme inventory, and the dictionary-text reading were applied. Columns:
`dict_page`, `headword`, `class`, `unit_recorded_prefix`, `source_locator`.

Each row is resolved by reading the scan, not by inference:

```console
python tools/render_dictionary_entry.py <dict_page> <headword> /tmp/entry.png
read("/tmp/entry.png?q=Quote verbatim the pl: value printed for this entry.")
```

## What the sample read so far shows

| entry | class | the scan prints | verdict |
| --- | --- | --- | --- |
| `dikanwa` | 5 | `pl: mad-` | the extraction unit's `madh-` is a misread; the dictionary text is right |
| `dimba` (door) | 5 | `pl: mad-` | same misread; its rice-field entry reads `mat-`, which the unit got right |
| `gwama` ×3 | 5 | `magw-`, `makw-`, `makw-` | three homographs, three plurals; the unit recorded all three correctly |
| `budiriro` | **9** | `pl: mab-` | **not a misread** — see below |
| `biko` | 5 | (plural recorded under `-bika` as `mabiko`) | the unit's `mah-` came from a derived-forms list, not the entry |

`budiriro` is the interesting one. The scan shows a class 9 noun taking a
class-6 plural, and Fortune 3.3.9 states class 6 is the correlative plural of
classes **5, 11, 21, 1a, 1 and 14** — class 9 is not among them. That is a
disagreement between the two primary sources, not a pipeline artefact, and the
conflict policy says preserve both and let an editor decide. Several other class
9 rows carry `mab-`/`mabv-` shapes and are likely the same disagreement.

## Why this is not resolved here

Choosing between Hannan and Fortune about which class a plural belongs to is an
editorial decision about the language, not an implementation one. The rules
refuse those entries, which is the correct behaviour under the evidence policy,
and this list is the queue for the decision.
