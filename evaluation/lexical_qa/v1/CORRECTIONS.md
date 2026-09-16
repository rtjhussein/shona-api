# Corpus corrections

Expectations in this corpus are derived by `tools/lexical_qa.py`, so a change to
that reader changes what counts as a defect. Every such change is recorded here
with the evidence that justified it. Silent edits that make a result look better
are forbidden; a correction must be attributable to a misreading of the source
format, not to a disagreement with a measured outcome.

## 2026-09-16 — tone segments may span words (reader fix)

**Wrong:** the reader captured only the leading `[HL]+` run of a tone segment,
so `[LLL HH]` (the multi-word headword `munhondo churu`) read as `LLL` and every
multi-word entry appeared to have lost a tone alternative.

**Evidence:** the published records carry the full pattern as one value
(`munhondo churu` → `["LLL HH"]`), and the project's own normalizer already has
a `test_gpt_normalization_accepts_multiword_hannan_tone_patterns` case. Hannan
writes one pattern group per word of the headword.

**Fix:** a tone segment is `[HL]+(?:\s+[HL]+)*`; a following token that is not
all H/L is the dialect restriction (`LLH Z` → pattern `LLH`, restriction `Z`).

**Effect:** tone disagreements fell from 1,446 to 133, and the remaining 133 are
grouping-only differences (`[H H H]` vs `HHH`) that the evaluator now normalises
away. No measured outcome improved without evidence; the previous figure was a
reader artifact, not a defect count.

## 2026-09-16 — plural lists may contain commas (reader fix)

**Wrong:** `pl:` was read up to the first comma, so `bimha [LL]KMZ n 5, pl: map-,
mab- (M), Reedbuck R 292.` yielded only `map-`.

**Evidence:** the line format lists plural prefixes comma-separated and then
continues into the definition, which may itself contain commas. Hannan attests
the second form with a dialect restriction (`mab- (M)`).

**Fix:** items are consumed after `pl:` only while they still look like plural
prefixes (a token, optionally followed by a dialect parenthesis); the first item
is always taken. `pl: map-, mab- (M), Reedbuck R 292.` → `["map-", "mab- (M)"]`,
`pl: mad-, Gen name for edible plants…` → `["mad-"]`.

**Effect:** the corpus hash changes (plural expectations are stored), and the
report gains a plural coverage statistic: of 42 sampled nouns whose source line
records a plural, 0 publish a form matching one of those prefixes.



**Change:** the corpus was rebuilt from (parser, word class) strata to
(parser, source-line shape) strata, raising it from 108 to 324 cases.

**Reason:** the first sampling drew 18 cases per parser and word class and
reported 108/108 on four of five checks, while direct queries showed 266
sub-class losses and 484 misclassified word classes. A uniform draw under-reports
rare defects, and an instrument that cannot fail measures nothing.

Each shape is a property of the Hannan line (`n 1a`, a `pl:` list, a multi-word
headword), never of the implementation's output, so this is not selection on the
result.
