# Noun plural milestone — evidence and plan (2026-09-16)

Written **before implementation**. Every rule below names its source locator;
attested and constructed material are labelled separately. This is an
implementation contract, not linguistic certification.

## Why this is the next capability

Measured today: **0 of 42** sampled nouns publish a form matching the plural
their source line records, while **2,060** published nouns carry a plural prefix
in their parser output and **19,104** noun lemmas carry a noun class. The data is
extracted; the rule that turns it into surface forms is what is missing. Noun
singular/plural pairs are a product requirement (section 8.2) and the first thing
a dictionary consumer expects from a Shona noun.

## Sources verified for this milestone

Page numbers are the source's own table of contents (Fortune Vol 1). PDF pages
are printed + 12, the offset used by the extension and infinitive milestones
(printed p.21 → PDF p.33; printed pp.78-79 → PDF pp.90-91).

- **Fortune Vol 1, 3.3.8 Noun class 5** — printed p.50, PDF p.62, body text at
  `local_source_cache/fortune_constructions.txt:3858`. Prefix `(ri-)` with
  allomorphs conditioned on the stem's initial phoneme:
  - (2) before `/p, t/`: "voiced implosive" — `(ri-) + -pangá > banga`, cp.
    `ma-panga` (6); `(ri-) + -tangá > dangá`, cp. `ma-tangá` (6).
  - (3) before `/k, pf, ch, tsv/`: "voiced depressor" — `-koré > gore` cp.
    `ma-kore`; `-pfeni > bveni` cp. `ma-pfeni`; `-chírá > jírá` cp. `ma-chírá`;
    `-tsvatsvát sva > dzvatsvatsva` cp. `ma-tsvatsvatsva`.
  - (4) before `/ts, f, s, sv, sh/`: "voiced affricate depressor", secondary
    prefix only.
  - (5) before some vowel-commencing stems: `/z-/` — `-íno > zínó` cp.
    `meno` (6), `ma-zínó` (6,5).
  - (6) otherwise `/ø-/`.
- **Fortune Vol 1, 3.3.9 Noun class 6** — printed p.52, PDF p.64, body at
  `:4032`. Prefix `/ma-/`, "no allomorphs"; coalescence `ma- + -ino > meno`
  (a+i > e) and the doublets `mazano`/`mano`, `mazíno`/`meno`, `mazíso`/`meso`
  (6,5). **Number:** "Cl. 6 nouns are correlative plurals of nouns in cll. **5,
  11, 21, 1a, 1, and 14**"; "All nouns of cl. 5, whether of primary or secondary
  prefix, form correlative plurals in cl. 6."
- **Fortune Vol 1, 3.3.3 Noun class 1a** — printed p.42, PDF p.54, body at
  `:3197`. Prefix `/ø-/`; "A few class 1a nouns have three plurals, one in class
  2a and the others with prefixes of 2a and 10, 6 and 10 respectively. Plurals
  in 2a are almost always **honorific**, the others almost always **numerical**."
- **Fortune Vol 1, 3.3.4 Noun class 2a** — printed p.44, PDF p.56, body at
  `:3387`. Prefix `/va-/`, with `/vadzi-/` and `/madzi-/` for numerical plurals.
- Hannan, `pl:` notation: the plural is recorded as a prefix with a trailing
  hyphen (`pl: map-`, `pl: mab- (M)`, `pl: vana-`) or, for irregular plurals, as
  a complete form (`pl: moyo`).

## The rule

A trailing-hyphen prefix carries the stem's **underlying** initial consonant,
because the class 5 prefix has already changed that consonant in the singular.
So:

```
plural = prefix_without_hyphen + stem_without_its_initial_grapheme   (consonant-final prefix)
plural = prefix_without_hyphen + stem                                (vowel-final prefix)
plural = recorded_form                                               (no hyphen: full form)
```

Worked from the sources and confirmed against the data:

| singular | class | recorded plural | derived | source |
| --- | --- | --- | --- | --- |
| `banga` | 5 | `map-` | `mapanga` | Fortune 3.3.8(2) `ma-panga` cp. `banga` |
| `biku` | 5 | `mab-` | `mabiku` | Fortune 3.3.9 `ma-` + stem |
| `bimha` | 5 | `map-` | `mapimha` | as above |
| `derere` | 5 | `mad-` | `maderere` | as above |
| `gufu` | 1a | `vana-` | `vanagufu` | Fortune 3.3.3/3.3.4, honorific plural |
| `moyo` | 3 | `moyo` | `moyo` | full form recorded; Fortune 3.3.7 cl.4 correlative |

## Measured distribution across the corpus

`tools/measure_plural_prefixes.py` (added with this plan) walks every published
noun that has both a class and parser output:

- **2,060** nouns carry a trailing-hyphen plural prefix. By class: **5 → 1,956**,
  1a → 54, 1 → 27, 9 → 12, 11 → 4, other/missing → 7.
- **85** record a full form (no hyphen) and **13** a prefix with an internal
  hyphen; those need their own handling and are out of the first slice.

Prefix-final grapheme (underlying) against the singular's initial grapheme,
counts of the 2,060:

| pair | count | Fortune 3.3.8 |
| --- | --- | --- |
| `g → g` | 320 | already depressor |
| `t → d` | 244 | (2) attested |
| `k → g` | 195 | (3) attested |
| `d → d` | 190 | already depressor |
| `j → j` | 187 | already depressor |
| `dh → d` | 142 | **not listed** |
| `p → b` | 129 | (2) attested |
| `gw → gw` | 121 | already depressor |
| `dz → dz` | 85 | already depressor |
| `b → b` | 78 | already depressor |
| `bh → b` | 55 | **not listed** |
| `kw → gw` | 51 | (3) attested, labialisation preserved |
| `bv → bv` | 45 | already depressor |
| `ch → j` | 27 | (3) attested |
| `dzv → dzv` | 19 | already depressor |
| `bw → bw` | 17 | already depressor |
| `w → dy` | 10 | **not listed** |
| `ts → dz` | 5 | (4) attested |

The identity pairs are the expected consequence of the rule: `b`, `d`, `g`, `j`,
`dz`, `bv`, `dzv`, `gw`, `bw` are already in depressor form, so the prefix
carries them unchanged.

## Open questions this milestone must settle with evidence, not assumption

1. **`dh → d` (142) and `bh → b` (55).** Fortune's list gives `p, t, k, pf, ch,
   tsv, ts, f, s, sv, sh`. It does not mention `dh` or `bh`. Either Hannan's
   orthography distinguishes a breathy series Fortune writes plainly, or the
   parser recorded a different underlying consonant. Until one is established
   these pairs are **refused** (`EXTENSION_UNVERIFIED`-style structured refusal),
   not generated.
2. **`w → dy` (10).** The prefix-final grapheme is `w` but the singular begins
   `dyw` (`gwachara`/`madyw-` is `gw`), which suggests the grapheme inventory is
   missing `dyw` — the same class of gap as `ngw`/`mbw` in `shona-core-v2`.
   Check the inventory before treating this as a linguistic exception.
3. **Class labels disagree between sources.** Hannan labels the `vana-` plural
   nouns `n 1a`; Fortune's 3.3.5 **class 2b is `/a-/`, occurring with two stems
   only (`amai`, `ambuya`)**. Under the conflict policy the two labellings must
   be preserved and cross-referenced, never silently merged.
4. **Honorific vs numerical.** Fortune states the 2a plural of class 1a is
   honorific. If plurals are published as forms, an honorific plural must not be
   presented as the ordinary plural; it needs a label or its own field.
5. **Coalescence.** `ma- + -ino > meno` (a+i > e) means some plurals are not
   concatenations at all; `zino` has two attested plurals (`meno`, `mazino`) and
   `moyo` has an identical-form plural. These are recorded as full forms in
   Hannan and must be published as recorded, never regenerated.

## Generation shape (proposed)

```json
{
  "lemma_public_id": "lemma_...",
  "features": {"generation_type": "noun_plural"}
}
```

- Allowlist: `generation_type` only in the first slice. No subject, no
  extensions, no polarity.
- Output: the plural surface plus the rule id, the class pair, the recorded
  prefix, and the allomorph pair used — so a consumer can audit the derivation.
- Refusals carry stable codes: `NO_RECORDED_PLURAL`, `PLURAL_ALLOMORPH_UNVERIFIED`
  (the `dh`/`bh`/`dyw` pairs), `PLURAL_NOT_A_PREFIX` (internal hyphen),
  `PLURAL_SUPPLETIVE` (full form recorded).
- Rule-set version boundary: a new `MORPHOLOGY_RULES_VERSION`, with generation
  and analysis sharing one rule table so they cannot drift, as the extension
  milestone established.

## Acceptance boundary

- Every generated plural derives from a **recorded** prefix, not from a rule
  applied to a guessed stem.
- The attested allomorph pairs are exercised by corpus cases with locators; the
  unlisted pairs are refused with a structured code and named in the rule card.
- Published plural forms appear on the lemma read endpoint and resolve in
  search (`match_type` for a form match), with `form_kind` distinguishing a
  recorded plural from a derived one.
- The lexical QA harness gains a scored `plural_form` check in place of today's
  coverage statistic, and the baseline is raised deliberately with
  `--write-baseline`.

## Out of scope (explicit)

Locatives (`pa-`, `ku-`, `mu-`), diminutives (`ka-`, `tu-`), augmentatives
(`zi-`, `ma-` of class 21), plural analysis (surface → singular), tone on
plural forms, and any plural whose prefix is not recorded in the source line.
