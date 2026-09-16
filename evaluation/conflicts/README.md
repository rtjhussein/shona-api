# Source conflicts

Facts the sources disagree about, or that a source states in a way the corpus
cannot yet follow. Each entry is a finding about the **sources**, not about one
record, so it lives here — versioned, diffable, and readable without a database —
and is then materialised onto the affected records as `ReviewNote` rows so it
reaches the editorial queue.

The product requirements already specify this mechanism: "When two sources
disagree on a fact, the conflict is preserved as a `ReviewNote` linked to both
records. An editor must explicitly resolve it. No source silently wins." Until
this register existed the database held **zero** `ReviewNote` rows, so the
policy had never actually been exercised.

## Why a register and not just notes

A `ReviewNote` records that a record is disputed. It does not record *what*
disagrees, *where* each source says it, what has already been checked, or what
would settle it — and those are the things a person returning to the question in
six months needs. A note pointing at a register entry, and a register entry
quoting both sources verbatim with locators, together answer both.

## Format

`open.json` holds a `conflicts` array. Each entry:

| key | meaning |
| --- | --- |
| `id` | stable slug, used to make note creation idempotent |
| `title` | the disagreement in one line |
| `field` | which field or subsystem it blocks |
| `status` | `open`, `mitigated`, or `resolved` |
| `kind` | `source_conflict`, `source_defect`, or `source_gap` |
| `summary` | what disagrees |
| `sources[]` | each side: `source`, `locator`, `claim`, and `verbatim` where the text is short enough to quote |
| `evidence[]` | what was actually checked, and how — so a reader can tell measurement from inference |
| `resolution_needed` | **the point of the whole file**: what would settle it, and whose judgement is required |
| `impact` | how much published data is affected |
| `affected_worklist` + `affected_filter` | optional: a TSV with a `unit_recorded_prefix`-style column and a regex selecting the affected rows |

Locators name the printed page, the PDF page, and — where the source is a local
text extraction — the line number. A conflict that cannot be checked against a
locator is not evidence and does not belong here.

## Materialising onto records

```console
python manage.py sync_source_conflicts --dry-run
python manage.py sync_source_conflicts
```

Creates one `ReviewNote` per affected canonical record, in state `needs_review`,
idempotently: a record already carrying a note for that conflict id is skipped,
so the command can be re-run after new rows appear. Notes are never deleted by
this command — closing a conflict is an editorial act, performed on the note.

## Statuses

- **open** — nothing available settles it; needs a source or an expert.
- **mitigated** — the corpus is protected from the effect, but the underlying
  question stands (e.g. a normaliser that strips the defect on read).
- **resolved** — settled, with the ruling recorded in the entry rather than
  deleted, because the next person will wonder why the corpus reads as it does.

## Policy: publish what is attested, flag the classification

When two sources disagree, the corpus publishes what the primary source for
**that kind of fact** states, and records the disagreement rather than resolving
it. The product requirements assign source authority by fact type, so the
division is already determined:

| fact | authority |
| --- | --- |
| lemmas, senses, dialect labels, examples, tone, cross-references, orthographic variants, noun class data | Hannan (lexical) |
| morphology, noun class concord tables, extension rules, morphophonemics | Fortune (grammatical) |

Applied to `class-9-takes-class-6-plural`: the per-entry plural is a lexical fact
Hannan states and the scan confirms, so the attested surface publishes; which
class that plural belongs to is a concord question on which Fortune's list
disagrees, so the classification stays flagged here. Withholding an attested
surface would lose data the source states plainly; treating Fortune's rule as
overriding Hannan's data would silently pick a winner, which the conflict policy
forbids.

The general form, for the next disagreement: **publish the attested surface,
carry the uncertainty in provenance, and keep the note open.** A conflict that
cannot be expressed that way — where the disputed thing *is* the surface — stays
refused.
