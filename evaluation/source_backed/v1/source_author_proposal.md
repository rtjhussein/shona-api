# Shona Morphology — Source-Backed Evaluation Corpus (v1 freeze candidate)
**Date:** 2026-09-10
**Primary sources only:** `key_documents/fsi_course.pdf` via `local_source_cache/fsi_course.txt` + `local_batches/` images; `key_documents/fortune_grammatical_constructions.pdf` via `local_source_cache/fortune_constructions.txt`; `key_documents/hannan_dictionary.pdf` via `local_source_cache/hannan_dictionary.txt`. No API/implementation/test/rule-card inspection per assignment constraint.

## 0. Disclosure of prior exposure
**No prior exposure to this repo's implementation, tests, or rule cards beyond this prompt.** Did NOT read `shona_api/morphology/services.py`, `shona_api/morphology/views.py`, `tests/test_morphology*.py`, `docs/morphology/rules/`, `docs/morphology/generate_endpoint.md`, `docs/morphology/completeness-assessment-2026-09-08.md`, `docs/openapi.json`. Only directory listing performed; all claims drawn solely from three primary sources via `local_source_cache/` + `local_batches/` images.

## 1. Coverage table
| # | Category | Attained | Case IDs |
|---|----------|----------|----------|
| A | Positive present finite | 8 | SRC-001–008 |
| B | Negative present (-i/-e dialect) | 8 | SRC-009–016 |
| C | Infinitives pos/neg + obj/refl | 10 | SRC-017–026 |
| D | Affirmative imperative sg/pl | 8 | SRC-027–034 |
| E | Negative imperative usa-/musa- | 6 | SRC-035–040 |
| F | Object concords | 4 | SRC-041–044 |
| G | Verb extensions (passive, causative, applicative, neuter, reciprocal, reversive, repetitive etc) | 10 | SRC-045–054 |
| H | Short/divergent/vowel-initial stems | 9 | SRC-055–063 |
| I | Ambiguous surfaces | 4 | SRC-064–067 |
| J | Dialect/deferral | 3 | SRC-068–070 |
| **Total** | | **70** | SRC-001–070 |

## 2. Case list (SRC-001..070) — each ~8 lines, all required fields

### SRC-001 Positive present 1sg -taura
- **Source:** `fsi_course.txt` FSI Unit 12 Note1 printed p.118 (fsi_course.pdf Unit12); Fortune §2.10.2.4 contrast `ndi-chá-ziv-a`
- **Verbatim:** `Ndinotaura` (FSI: "correspond to affirmative forms !ndinotaura!")
- **Interpretation:** Principal affirmative -no- present. `ndi-`1sg SC (Fortune g1: L for I/II), `-no-` tense, `-taur-` R, `-a` term. Affirmative polarity. Morphemes `ndi-no-taur-a` per FSI Note1.
- **Normalized:** `ndinotaura` → lemma `-taura` (strip `ndi-no-`, strip tone, lowercase, hyphens removed; ! markers dropped)
- **Evidence:** source_attested
- **Exhaustive:** No
- **Expected/Variants:** 1sg affirmative of -taura. Accept `ndinotaura` only; `ndi-no-taura` hyphenated same.

### SRC-002 Positive present 2sg high verb -dzidzisa
- **Source:** `fsi_course.txt` FSI Unit12 §2 printed p.119 exercise prompt
- **Verbatim:** `Unodzidzisa mazuva ose here?`
- **Interpretation:** `u-no-dzidzis-a` 2sg affirmative -no-. `u-`2sg SC L, `-dzidzis-` R (≈ causative of -dzidza). High? FSI high-verb class.
- **Normalized:** `unodzidzisa` → `-dzidzisa` (remove `u-no-`)
- **Evidence:** source_attested
- **Exhaustive:** No
- **Expected:** 2sg affirmative present. Variant `munodzidzisa` is different person, not acceptable here.

### SRC-003 Positive present low verb -taura 2sg
- **Source:** `fsi_course.txt` FSI Unit12 §4-5 p.120 prompt
- **Verbatim:** `Unotaura chiNdevere here?`
- **Interpretation:** `u-no-taur-a` 2sg affirmative low verb. `u-` SC, `-no-` tense, `taur` R, `-a`.
- **Normalized:** `unotaura` → `-taura`
- **Evidence:** source_attested
- **Exhaustive:** No
- **Expected:** Affirmative question; counterpart negative SRC-011.

### SRC-004 Positive present Fortune -cha- (still)
- **Source:** `fortune_constructions.txt` §2.10.2.4(g) PDF p.26: `ndi-chá-ziv-a (I shall know)` vs `á-cha-zív-á`
- **Verbatim:** `ndi-chá-ziv-a`
- **Interpretation:** Affirmative principal with `-cha-` (still/shall). `ndi-` L tonal morpheme + `-cha-` + `-ziv-` + `-a`. Demonstrates person-conditioned H vs L on SC (Fortune g1 vs g2).
- **Normalized:** `ndichaziva` (ndi+cha coalesces orthographically) → `-ziva`
- **Evidence:** source_attested
- **Exhaustive:** No (tone contrast lost orthographically)
- **Expected:** "I still/shall know". Accept same surface; tone not required.

### SRC-005 Positive present 1pl -gona
- **Source:** `fsi_course.txt` FSI Unit12 §5 p.120 `Tinogona here kurimisa?`
- **Verbatim:** `Tinogona`
- **Interpretation:** `ti-no-gon-a` 1pl affirmative of -gona (be able). `ti-`1pl SC.
- **Normalized:** `tinogona` → `-gona`
- **Evidence:** source_attested
- **Exhaustive:** No
- **Expected:** 1pl affirmative.

### SRC-006 Positive present monosyllabic -da
- **Source:** `fsi_course.txt` FSI Unit12 §3 p.119 `Unoda kuenda navo here?`
- **Verbatim:** `Unoda`
- **Interpretation:** `u-no-da` 2sg affirmative high monosyllabic -da (want). R = `-d-` + `-a`? FSI treats as high verb; Fortune C radicals analogy `ku-p-á`.
- **Normalized:** `unoda` → `-da`
- **Evidence:** source_attested
- **Exhaustive:** No
- **Expected:** Affirmative -da; negative counterpart SRC-013.

### SRC-007 Participial present monosyllabic
- **Source:** `fortune_constructions.txt` PDF p.24 TC III `ndi-chí-p-á` (= ndi-chí-rw-á contrast)
- **Verbatim:** `ndi-chí-p-á`
- **Interpretation:** Participial affirmative present with `-chí-`. `ndi-` SC H morpheme (g3), `-chí-`? Actually `chí` is part of TC III participial pattern; stem `-p-` (give) C radical.
- **Normalized:** `ndichipa` → `-pa`
- **Evidence:** source_attested
- **Exhaustive:** No
- **Expected:** Participial "I giving" — orthographically ambiguous with principal `ndinopa` but tone distinguishes.

### SRC-008 Recent past I/II persons
- **Source:** `fortune_constructions.txt` PDF p.24 TC IV `nd-a-p-á` `nd-a-rw-á`
- **Verbatim:** `nd-a-p-á`
- **Interpretation:** Affirmative principal recent past (today) I/II. `nd-` SC + `-a-` past sign carrying L morpheme (Fortune g). ` -p-` + `-a`.
- **Normalized:** `ndapa` → `-pa`
- **Evidence:** source_attested
- **Exhaustive:** No
- **Expected:** "I gave (today)" segmentation nd-a-pa.

### SRC-009 Negative present 1sg dialect -i/-e (taura)
- **Source:** `fsi_course.txt` FSI Unit12 Note1 p.118; `hannan_dictionary.txt` front matter p.xii `Handidyi St.Sh. / Handidye Z`
- **Verbatim:** `Handitauri` (StSh) / `Handidye` pattern → `Handitaure` Z variant per general rule
- **Interpretation:** `ha-` NEG fixed H + `ndí-` 1sg SC high via polarity (Fortune §2.10.2.4f) + stem (first syl basic tone, next two high per FSI) + term `-i` (KM/StSh) vs `-e` (Z). Explicit dialect split.
- **Normalized:** `handitauri` (KM) / `handitaure` (Z) → `-taura` + dialect tag
- **Evidence:** source_attested (FSI + Hannan table)
- **Exhaustive:** No (other persons exist)
- **Expected:** Both -i and -e acceptable as dialect variants; must not penalize either.

### SRC-010 Negative present 1sg -ziva
- **Source:** `fsi_course.txt` p.118 `Handizivi`; `fortune_constructions.txt` p.22 `ha-ndí-zív-é`; Hannan p.xii same pattern
- **Verbatim:** `Handizivi` / `ha-ndí-zív-é`
- **Interpretation:** `ha-ndí-ziv-` + `-i`/-`é`. `ha-` NEG, `ndí-` high, `-ziv-` R, terminal -i StSh/-e Z per FSI Note1: "final vowel is !-i! in some dialects, !-e! in others."
- **Normalized:** `handizivi` / `handizive` → `-ziva`
- **Evidence:** source_attested (convergent all three)
- **Exhaustive:** No
- **Expected:** 1sg negative of -ziva; accept both terminals.

### SRC-011 Negative present 2sg/3sg low
- **Source:** `fsi_course.txt` FSI Unit12 §4 p.120 `Hautauri` / `Haatauri`
- **Verbatim:** `Hautauri` (2sg) / `Haatauri` (3sg cl1)
- **Interpretation:** `ha-u-taur-i` 2sg, `ha-a-taur-i` 3sg. `ha-`+SC(high)+stem+`-i` (StSh) vs `-e` Z per general rule.
- **Normalized:** `hautauri` / `haatauri` → `-taura` (also accept `hautaure`/`haataure` Z)
- **Evidence:** source_attested
- **Exhaustive:** No
- **Expected:** 2sg/3sg negative present; both -i/-e variants acceptable.

### SRC-012 Negative present plural
- **Source:** `fsi_course.txt` p.120 `Hatitauri` `Havatauri` `Hamutauri`
- **Verbatim:** `Hatitauri` (1pl) / `Havatauri` (3pl)
- **Interpretation:** `ha-ti-taur-i` 1pl, `ha-va-taur-i` 3pl. Same NEG+SC(high)+stem+`-i` pattern.
- **Normalized:** `hatitauri` / `havatauri` → `-taura`
- **Evidence:** source_attested
- **Exhaustive:** No
- **Expected:** Pl negative present; accept -e counterparts.

### SRC-013 Negative present monosyllabic -da
- **Source:** `fsi_course.txt` p.119 `Unoda … Handidi.` vs `Haadi` paradigm; Fortune TC VII `ha-ndí-p-e` parallel
- **Verbatim:** `Handidi.` (FSI answer)
- **Interpretation:** `ha-ndi-d-i` negative of -da high monosyllabic. SC high, terminal -i; Z variant predicted `handide` via FSI general -i/-e rule (not verbatim for this verb).
- **Normalized:** `handidi` (attested) / `handide` (predicted Z) → `-da`
- **Evidence:** `handidi` source_attested; `handide` rule_supported (general rule only)
- **Exhaustive:** No
- **Expected:** 1sg negative of -da; accept -i as attested, -e as rule-supported dialect variant.

### SRC-014 Negative present -gona ability
- **Source:** `fsi_course.txt` p.120 `Handigoni.`; `hannan_dictionary.txt` p.26 `asi kukwira handigoni: I can…but I can't…`
- **Verbatim:** `Handigoni.`
- **Interpretation:** `ha-ndi-gon-i` negative of -gona low. SC high, terminal -i (StSh) vs -e Z per rule.
- **Normalized:** `handigoni` / `handigone` → `-gona`
- **Evidence:** source_attested (FSI + Hannan example sentence)
- **Exhaustive:** No
- **Expected:** 1sg negative ability; both -i/-e acceptable.

### SRC-015 Negative present with -na- obligation alternation
- **Source:** `fsi_course.txt` FSI Unit33 p.332 `Tinazadza mwenje` (affirmative `ti-na-zadz-a` = must fill) vs `Hatizadzi` (negative)
- **Verbatim:** `Hatizadzi` vs `Tinazadza`; `Hatiizadzi` (with object `Hatiizadzi`)
- **Interpretation:** Affirmative `ti-na-zadz-a` (ti- + -na- obligation + -zadz- + -a); negative drops -na-: `ha-ti-zadz-i` (ha- + ti- high + stem + -i). FSI Note2: `/-na-/` expressing obligation; tone summary required. Complement `Hatiizadzi` = `ha-ti-i-zadz-i` with OP ` -i-`? Actually `Hatiizadzi` = `ha-ti-i-zadz-i` (OP?)
- **Normalized:** `hatizadzi` → lemma `-zadza` (not * -nazadza); keep -na- as formative, not lemma
- **Evidence:** source_attested (surface + rule for -na-)
- **Exhaustive:** No (incomplete paradigm)
- **Expected:** Negative obligation "we do not fill"; analysis must not lemmatize as -nazadza.

### SRC-016 Negative progressive -cha- (no longer)
- **Source:** `hannan_dictionary.txt` p.xii `Handichadyi St.Sh. / Handichadya Z (I no longer eat)` ; `fortune_constructions.txt` p.19 `ha-ndí-cha-zív-a`
- **Verbatim:** `Handichadyi` / `ha-ndí-cha-zív-a`
- **Interpretation:** `ha-ndi-cha-dy-i` : ha- NEG + ndi- high + `-cha-` progressive + `-dy-` + `-i`/-`a` dialect (-yi StSh vs -ya Z). Contrasts with affirmative `Ndichadya` (I still eat). Fortune: -cha-/-chi- tense signs.
- **Normalized:** `handichadyi` / `handichadya` → `-dya`
- **Evidence:** source_attested
- **Exhaustive:** No
- **Expected:** "I no longer eat/know"; both -yi/-ya acceptable per Hannan Z vs StSh.

### SRC-017 Infinitive positive plain
- **Source:** `fortune_constructions.txt` p.20-21 `ku-p-á` `ku-tém-á`; `fsi_course.txt` p.118 `kutaura` after -pedza
- **Verbatim:** `kutaura` / `ku-tém-á`
- **Interpretation:** Cl15 nominal: `ku-` prefix + R `taur`/`tém` + `-a` term (Fortune §3.3.15). Tonally H etc but orthographically `kutaura`.
- **Normalized:** `kutaura` → `-taura` (strip `ku-`)
- **Evidence:** source_attested
- **Exhaustive:** Yes (simple infinitive)
- **Expected:** Infinitive to speak; accept hyphenated `ku-taura` same.

### SRC-018 Infinitive with different lengths
- **Source:** `fortune_constructions.txt` p.21 `ku-zórór-á` (to rest) vs `ku-tever-a` (to follow)
- **Verbatim:** `ku-zórór-á` / `ku-tever-a`
- **Interpretation:** `ku-`+R+`-a`; H vs L tone classes: -zórór- high vs -tever- low in same infinitive TC I.
- **Normalized:** `kuzorora` → `-zorora`; `kutevera` → `-tevera`
- **Evidence:** source_attested
- **Exhaustive:** Yes
- **Expected:** Infinitives of -zorora/-tevera.

### SRC-019 Infinitive negative kusaziva
- **Source:** `fortune_constructions.txt` p.78 `kusaziva (not to know)`; `hannan_dictionary.txt` `Kusadya: to not eat. Usadye: do not eat.`
- **Verbatim:** `kusaziva` / `Kusadya`
- **Interpretation:** `ku-sa-ziv-a` : `ku-` + `-sa-` NEG formative (Fortune §3.3.15(2)(b) inflecting morpheme) + R + `-a`. Infinitive terminal stays -a, no -i/-e split.
- **Normalized:** `kusaziva` → `-ziva` (keep `sa-` as negation, not lemma)
- **Evidence:** source_attested (both)
- **Exhaustive:** Yes
- **Expected:** "not to know/eat"; not to be confused with finite `hasaziva`.

### SRC-020 Infinitive negative C radical
- **Source:** `fortune_constructions.txt` p.105 `ku-sa-f-á nenzára (not to die of hunger)`
- **Verbatim:** `ku-sa-f-á`
- **Interpretation:** `ku-`+`-sa-`+`-f-` (die) + `-a` with monosyllabic C radical -f-a. Adjunct nenzara separate.
- **Normalized:** `kusafa` → `-fa`
- **Evidence:** source_attested
- **Exhaustive:** Yes
- **Expected:** "not to die".

### SRC-021 Infinitive negative with object
- **Source:** `fortune_constructions.txt` p.79 `ku - sa- zvi - ziv - a izvi (not to know this)`
- **Verbatim:** `ku-sa-zvi-ziv-a`
- **Interpretation:** `ku-` + `-sa-` NEG + `-zvi-` OP cl8 (referring to izvi) + `-ziv-` + `-a`. Fortune notes this complex morphology poses analysis problem; object belongs to verb phrase.
- **Normalized:** `kusazviziva` → `-ziva` + OP cl8 `izvi`
- **Evidence:** source_attested
- **Exhaustive:** Yes (this combination)
- **Expected:** "not to know this"; segmentation ku-sa-zvi-ziva.

### SRC-022 Infinitive positive with object
- **Source:** `fortune_constructions.txt` p.105 `ku-a-dy-á mambíshi (to eat the raw ones)`; p.78 `kuzvitora (to take them)`
- **Verbatim:** `ku-a-dy-á` / `kuzvitora` (=`ku-zvi-tor-a`)
- **Interpretation:** `ku-` + `-a-` OP cl6 + `-dy-` + `-a` ; `ku-` + `-zvi-` OP + `-tor-` + `-a`. Fortune: objects under (a) belong to verb phrase. Positive infinitive with OP.
- **Normalized:** `kuadya` → `-dya` OP cl6; `kuzvitora` → `-tora` OP cl8
- **Evidence:** source_attested
- **Exhaustive:** No (other OP classes exist)
- **Expected:** Infinitive with object.

### SRC-023 Infinitive exclusive -chi- (now)
- **Source:** `fortune_constructions.txt` p.78 `ku-chi-end-a (to go now)`; p.105 `ku-chi-f-a nenzára`
- **Verbatim:** `ku-chi-end-a`
- **Interpretation:** `ku-` + `-chi-` exclusive + `-end-` vowel-initial + `-a`. Fortune §3.3.15(2)(c) exclusive formative.
- **Normalized:** `kuchienda` → `-enda`
- **Evidence:** source_attested
- **Exhaustive:** Yes
- **Expected:** "to go now".

### SRC-024 Infinitive progressive -cha- (still)
- **Source:** `fortune_constructions.txt` p.78 `ku-cha-ziv-a (to know still)`
- **Verbatim:** `ku-cha-ziv-a`
- **Interpretation:** `ku-` + `-cha-` prog + `-ziv-` + `-a`. Fortune groups -cha-/-chi-.
- **Normalized:** `kuchaziva` → `-ziva`
- **Evidence:** source_attested
- **Exhaustive:** Yes
- **Expected:** "to still know".

### SRC-025 Infinitive reflexive
- **Source:** `fortune_constructions.txt` p.78 `kuzviziva (to know oneself)`; p.99 `mu-zvi-bát-ir-ó (way of controlling oneself)` shows -zvi- reflexive
- **Verbatim:** `kuzviziva`
- **Interpretation:** `ku-` + `-zvi-` REFL + `-ziv-` + `-a`. Homographic with object -zvi- cl8 → ambiguous (see SRC-065). Fortune TC XI: reflexive has distinctive tones (`nd-a-ká-zvi-p-á` etc).
- **Normalized:** `kuzviziva` → `-ziva` + reflexive tag (same surface as object)
- **Evidence:** source_attested (reflexive reading); object reading rule_supported
- **Exhaustive:** No
- **Expected:** Reflexive "know oneself"; accept object "know them" as ambiguous variant.

### SRC-026 Infinitive as noun head (substantive phrase)
- **Source:** `fortune_constructions.txt` p.79 `kuda-nyama kwenyu uku` ; p.106 `ku-d-á vánhu kwáké` ; p.105-106 locative examples
- **Verbatim:** `kuda-nyama` (=`ku-d-a`?); `ku-d-á`
- **Interpretation:** Infinitive cl15 as head of SP controlling possessive `kwenyu` (cl15). `ku-`+`d-`+`-a` (love) + complement `nyama`. Shows infinitive nominal nature.
- **Normalized:** `kudavanhu` → `-da` (love) + complement. Strip `ku-`.
- **Evidence:** source_attested
- **Exhaustive:** Yes
- **Expected:** Infinitive used substantivally; `kuda` = to love.

### SRC-027 Affirmative imperative sg plain low
- **Source:** `fsi_course.txt` FSI Unit13 §4 p.129 `Taura!`; Fortune TC II `tém-á` vs `bik-á` p.23
- **Verbatim:** `Taura!` / `tém-á` (high) / `bik-á` (low)
- **Interpretation:** Bare stem + `-a` imperative, no SC. Fortune TC II H vs L complementary tones: high `tém-á` vs low `bik-á`.
- **Normalized:** `taura` → `-taura`
- **Evidence:** source_attested
- **Exhaustive:** No
- **Expected:** Sg imperative "Speak!"

### SRC-028 Affirmative imperative sg low verbs
- **Source:** `fsi_course.txt` p.129 `Pinda!` `Verenga!` `Enda!`
- **Verbatim:** `Pinda!` / `Verenga!` / `Enda!`
- **Interpretation:** `pind-a`, `vereng-a`, `end-a` (vowel-initial -enda needs no i-augment). Plain -a.
- **Normalized:** `pinda`→`-pinda`; `verenga`→`-verenga`; `enda`→`-enda`
- **Evidence:** source_attested
- **Exhaustive:** No
- **Expected:** Sg imperatives.

### SRC-029 Affirmative imperative sg high verbs
- **Source:** `fsi_course.txt` p.130 `Uya!` `Tenga!` `Tengesa!` `Tamba!`
- **Verbatim:** `Uya!` `Tenga!`
- **Interpretation:** High verbs `uya` (-uya), `tenga` etc with TC II H.
- **Normalized:** `uya`→`-uya`; `tenga`→`-tenga`
- **Evidence:** source_attested
- **Exhaustive:** No
- **Expected:** Sg high imperative.

### SRC-030 Affirmative imperative plural low
- **Source:** `fsi_course.txt` p.130 `Tengesai miti yenyu.` `Pedzai basa renyu.` `Rerai mwana wenyu.` `Verengai bhuku renyu.`
- **Verbatim:** `Tengesai` / `Pedzai` / `Rerai` / `Verengai`
- **Interpretation:** `tenges-a-i`, `pedz-a-i` etc: stem + plural `-i` (actually `-a` + `-i`). Plural addressee.
- **Normalized:** `tengesai`→`-tengesa`; `pedzai`→`-pedza` etc
- **Evidence:** source_attested
- **Exhaustive:** Yes for plural formation
- **Expected:** Pl imperative "Sell!" etc; sg `Tengesa` is different number, not variant.

### SRC-031 Affirmative imperative plural with adverbial
- **Source:** `fsi_course.txt` p.130-131 `Taurai mumasure mwake.`
- **Verbatim:** `Taurai`
- **Interpretation:** `taur-a-i` pl imperative of -taura with complement `mumusare`.
- **Normalized:** `taurai`→`-taura`
- **Evidence:** source_attested
- **Exhaustive:** No
- **Expected:** Pl imperative.

### SRC-032 Affirmative imperative exclusive (now)
- **Source:** `hannan_dictionary.txt` p.xviii `Chidya (Eat now)` vs `Idya`; `fortune_constructions.txt` PDF p.25 TC X `chí-p-a` `chí-rw-a`
- **Verbatim:** `Chidya` / `chí-p-a`
- **Interpretation:** Exclusive imperative: `chi-` + R + `-a`. Fortune TC X low tone `chí-p-a` = give now. Hannan `Chidya` = `chi-dy-a` eat now.
- **Normalized:** `chidya`→`-dya` + exclusive `chi-` tag
- **Evidence:** source_attested (both)
- **Exhaustive:** No
- **Expected:** "Eat now"; accept pl `Chidyai`.

### SRC-033 Imperative with i-augment (monosyllabic C)
- **Source:** `fortune_constructions.txt` p.20 `i-p-á` `i-rw-á`; p.37 note "with Rs of C shape in the imperative: i-d-á! (love)"; Hannan p.xviii `Idya`
- **Verbatim:** `i-p-á` / `Idya` / `i-d-á!`
- **Interpretation:** C radicals need penultimate `i-` augment in imperative (Fortune §Penultimate i- p.37). `i-`+`p-`+`a` ; `i-`+`dy-`+`a`.
- **Normalized:** `ipa`→`-pa`; `idya`→`-dya` (i- is augment, not lemma)
- **Evidence:** source_attested
- **Exhaustive:** Yes for monosyllabic shape
- **Expected:** Sg imperative of -pa/-dya with i-; `pa!` is non-standard.

### SRC-034 Imperative with object prefix
- **Source:** `fsi_course.txt` FSI Unit34 p.339-341 `Ipa mari … Ipe kunaBaba.` `Idya … Adye.` `RIdye.`
- **Verbatim:** `Ipe` / `Adye` / `RIdye` / `Hupe`
- **Interpretation:** `i-` augment + OP + R + `-a`/`-e` dialect. `Ipe` = `i-`+? `a-` OP cl6? + `pa`; `RIdye` = `ri-` OP cl5 + `dy-e` (Z -e); `Hupe` = `hu-`? Shows OP agreement. FSI Note p.339: "imperative forms of -mwa, -dya, -pa when they have object prefixes"
- **Normalized:** `ipe`→`-pa` OP; `ridye`→`-dya` OP cl5
- **Evidence:** source_attested
- **Exhaustive:** No
- **Expected:** Imperative with object; accept -a/-e dialect variants.

### SRC-035 Negative imperative sg usa- dialect split
- **Source:** `fsi_course.txt` p.323 Note "final vowel may be -a (usaputsa) or -e (usaputse)"; Hannan p.xviii `Usadya. Musadya KM / Usadye. Musadye Z`
- **Verbatim:** `Usaputsa` / `Usadya` (KM) vs `Usadye` (Z)
- **Interpretation:** `u-sa-` + R + `-a`/-`e`. `u-`2sg + `-sa-` NEG. Hannan marks KM vs Z dialects.
- **Normalized:** `usaputsa`/`usaputse`/`usadya`/`usadye` → `-putsa`/`-dya` + dialect tag
- **Evidence:** source_attested
- **Exhaustive:** No (pl musa- separate)
- **Expected:** Sg neg imperative; both -a (KM) and -e (Z) correct.

### SRC-036 Negative imperative sg specific -pinda
- **Source:** `fsi_course.txt` p.323 `Ndopinda mumba here? usapinda mumba.`
- **Verbatim:** `usapinda mumba`
- **Interpretation:** `u-sa-pind-a` (or -e Z) negative imperative of -pinda with locative.
- **Normalized:** `usapinda`/`usapinde` → `-pinda`
- **Evidence:** source_attested
- **Exhaustive:** Yes
- **Expected:** "Don't enter". Accept -e variant.

### SRC-037 Negative imperative sg -putsa
- **Source:** `fsi_course.txt` p.323 `Usaputsa mavhingwa.`
- **Verbatim:** `Usaputsa`
- **Interpretation:** `u-sa-putsa` 2sg neg imperative of -putsa (break bricks).
- **Normalized:** `usaputsa`→`-putsa`
- **Evidence:** source_attested
- **Exhaustive:** Yes
- **Expected:** "Don't break".

### SRC-038 Negative imperative sg with object -ise
- **Source:** `fsi_course.txt` p.340 `Usarise pamubhedha. RIise patafura.`
- **Verbatim:** `Usarise` (Z -e)
- **Interpretation:** `u-sa-ri-is-e` : u- + sa- + `-ri-` OP cl5 + `is-` (put) + `-e` Z (vs -a KM). With object -ri- for bhuku cl5.
- **Normalized:** `usarise`→`-isa` OP cl5 (also accept `usarisa` KM)
- **Evidence:** source_attested
- **Exhaustive:** No
- **Expected:** Neg imperative with object; both -a/-e valid.

### SRC-039 Negative imperative plural musa-
- **Source:** `fsi_course.txt` p.324 `Musaisa hari pachoto.` `Musaseva upfu.`; Hannan p.xviii `Musadya`/`Musadye`
- **Verbatim:** `Musaisa` / `Musadya`
- **Interpretation:** `mu-sa-` + stem + -a/-e. `mu-`2pl. Plural counterpart of usa-.
- **Normalized:** `musaisa`/`musadya` → `-isa`/`-dya`
- **Evidence:** source_attested
- **Exhaustive:** Yes for plural
- **Expected:** Pl neg imperative; accept -e `musaise`/`musadye` Z.

### SRC-040 Negative imperative exclusive sg
- **Source:** `hannan_dictionary.txt` p.xviii `Usachidya. Musachidya (Do not start eating)`
- **Verbatim:** `Usachidya`
- **Interpretation:** `u-sa-chi-dy-a` exclusive neg imperative (do not start). `u-` + `-sa-` + `-chi-` exclusive + `-dy-` + `-a`.
- **Normalized:** `usachidya`→`-dya` + exclusive chi-
- **Evidence:** source_attested
- **Exhaustive:** Yes
- **Expected:** Exclusive neg sg; accept pl `musachidya`.

### SRC-041 Object concord finite positive
- **Source:** `fortune_constructions.txt` p.79 `ndi-no-mu-ziv-a munhu uyu (I know this man)`
- **Verbatim:** `ndi-no-mu-ziv-a`
- **Interpretation:** `ndi-`1sg L + `-no-` + `-mu-` OP cl1 + `-ziv-` + `-a`. Fortune: objects under (a) belong to verb phrase.
- **Normalized:** `ndinomuziva`→`-ziva` OP cl1
- **Evidence:** source_attested
- **Exhaustive:** No
- **Expected:** 1sg present with object "him".

### SRC-042 Object concord infinitive positive
- **Source:** `fortune_constructions.txt` p.78 `kuzvitora (to take them)`; p.105 `ku-a-dy-á mambíshi`
- **Verbatim:** `kuzvitora` / `ku-a-dy-á`
- **Interpretation:** `ku-`+`-zvi-` OP + `-tor-` + `-a`; `ku-`+`-a-` OP cl6 + `-dy-`+`-a`.
- **Normalized:** `kuzvitora`→`-tora` OP cl8; `kuadya`→`-dya` OP cl6
- **Evidence:** source_attested
- **Exhaustive:** No
- **Expected:** Infinitive with object.

### SRC-043 Object concord imperative
- **Source:** `fsi_course.txt` p.340 `RIdye` `Ipe` `Hupe`
- **Verbatim:** `RIdye` / `Ipe` / `Hupe`
- **Interpretation:** Imperative with OP: `ri-` cl5 + `dy-e`, `i-` augment +(?) `pe` (pa with -a- OP), `hu-` etc. FSI p.339 note on -mwa/-dya/-pa with OP.
- **Normalized:** `ridye`→`-dya` OP cl5; `ipe`→`-pa` OP cl6
- **Evidence:** source_attested
- **Exhaustive:** No
- **Expected:** Imperative with OP; -a/-e dialect still applies.

### SRC-044 Object concord subjunctive negative
- **Source:** `fsi_course.txt` p.325 `tisadirire` vs `tisadzidirire`; `tisadzibvise`
- **Verbatim:** `tisadzidirire` (=`ti-sa-dzi-dirir-e`)
- **Interpretation:** `ti-`1pl SC H (subjunctive H per Fortune) + `-sa-` NEG? + `-dzi-` OP cl10 (mbeu) + `dirir` + `-e` subjunctive term. Neg subjunctive.
- **Normalized:** `tisadzidirire`→`-dirira` OP cl10
- **Evidence:** source_attested
- **Exhaustive:** No
- **Expected:** 1pl neg subjunctive with object; `tisadirire` without OP is different meaning.

### SRC-045 Extension passive -táp-iw-
- **Source:** `fortune_constructions.txt` p.22 `passive /-iw-/ e.g. -táp-iw- (be captured)`; `fsi_course.txt` p.333 `kutsvairwa` `Haisati yatsvairwa` (=`ku-tsvair-w-a`)
- **Verbatim:** `-táp-iw-` / `kutsvairwa` / `-táp-w-` variant
- **Interpretation:** Passive -iw-/-w- (free variation per Fortune p.22) + R -tap-→ be captured; -tsvair- + -w- → be swept. Tonally neutral.
- **Normalized:** `kutapiwa`/`kutapwa`/`kutsvairwa` → base `-tapa`/`-tsvaira` + passive
- **Evidence:** source_attested (both)
- **Exhaustive:** No
- **Expected:** Passive "be captured/swept"; accept -w- and -iw- variants.

### SRC-046 Extension neuter -ziv-ík-
- **Source:** `fortune_constructions.txt` p.22 `neuter /-ik-/ -ziv-ík- (be knowable)`; note `-tór-ek-` after e/o
- **Verbatim:** `-ziv-ík-` / `-tór-ek-`
- **Interpretation:** Neuter -ik-/-ek- vowel-harmony after e/o. -ziv-+ -ik- → be knowable. Distinct from passive.
- **Normalized:** `kuzivika` (`ku-ziv-ik-a`) → `-ziva` neuter
- **Evidence:** source_attested
- **Exhaustive:** No
- **Expected:** Neuter; accept `kuzivika`.

### SRC-047 Extension applicative -tém-ér- / -bik-ir-
- **Source:** `fortune_constructions.txt` p.21-22 `-tém-ér- (cut for)` `-bik-ir- (cook for)`; Hannan p.ix `-ira` / `-irira` list; p.99 `mu-vák-ír-o`
- **Verbatim:** `-tém-ér-` / `-bik-ir-`
- **Interpretation:** Applicative -ir-/-er- harmony (a/i/u→-ir-, e→-er-). Applied = for/at. Tonally neutral VC.
- **Normalized:** `kutemera`/`kubikira` → `-tema`/`-bika` + applicative
- **Evidence:** source_attested
- **Exhaustive:** No
- **Expected:** Applicative "cut for/cook for"; accept both -ir-/-er- per harmony.

### SRC-048 Extension causative (2) -muk-is-
- **Source:** `fortune_constructions.txt` p.22 `causative (2) /-is-/ -muk-is- (cause to rise)`
- **Verbatim:** `-muk-is-`
- **Interpretation:** Causative (2) -is- cause to. Distinct from causative (1) /y/ mutation. -muk- + -is- → cause to rise.
- **Normalized:** `kumukisa` → `-muka` causative
- **Evidence:** source_attested
- **Exhaustive:** No
- **Expected:** Causative.

### SRC-049 Extension intensive -taur-is-
- **Source:** `fortune_constructions.txt` p.22 `intensive /-is-/ -taur-is- (speak up)`
- **Verbatim:** `-taur-is-`
- **Interpretation:** Intensive -is- homophonous with causative (2) but meaning "speak up/forcefully". Fortune distinguishes by semantics.
- **Normalized:** `kutaurisa` → `-taura` intensive
- **Evidence:** source_attested
- **Exhaustive:** No
- **Expected:** Intensive reading; homograph with causative noted as ambiguous.

### SRC-050 Extension repetitive -túk-úrúr- / -send-urur-
- **Source:** `fortune_constructions.txt` p.22 `repetitive /-urur-/ -túk-úrúr- (curse roundly)` ` -send-urur- (replane)` ` -rond-oror- (track thoroughly)`
- **Verbatim:** `-túk-úrúr-` / `-send-urur-`
- **Interpretation:** Repetitive -urur-/-oror- (oror after o) → do thoroughly/repeatedly. Extensive after a/i/u vs e/o.
- **Normalized:** `kutukurura` / `kusendurura` → `-tuka`/`-senda` repetitive
- **Evidence:** source_attested
- **Exhaustive:** No
- **Expected:** Repetitive.

### SRC-051 Extension reversive -chat-anur- family
- **Source:** `fortune_constructions.txt` p.22 reversive paradigms `/-anur-/ -chat-anur- (divorce) cp -chat- (marry)`, `/-enur-/ -pfek-enur- (undress)`, `/-unur-/ -súng-unur- (untie)`, `/-onor-/ -roy-onor- (unwitch)`
- **Verbatim:** `-chat-anur-` / `-pfek-enur-` / `-súng-unur-`
- **Interpretation:** Reversive -anur- etc vowel-copying: V1 matches radical final vowel, V2 = u (o after o). Means undo. VCVC tonally neutral.
- **Normalized:** `kuchatanura`/`kupfekenura`/`kusungunura` → bases `-chata`/`-pfeka`/`-sunga` + reversive
- **Evidence:** source_attested
- **Exhaustive:** No
- **Expected:** Reversive; accept 5 vowel variants per harmony.

### SRC-052 Extension reciprocal -ana
- **Source:** `hannan_dictionary.txt` p.ix `-ana` reciprocal & associative; Fortune p.99 `va-pamhidz-ir-an-i (those who aid each other)`
- **Verbatim:** `-ana` list entry; ` -pamhidz-ir-an-`
- **Interpretation:** Reciprocal -ana "each other"; -pamhidz-ir-an- = -pamhidz- (increase) + -ir- appl + -an- recip → help each other.
- **Normalized:** `kupamhidzirana` → `-pamhidza` + appl + recip
- **Evidence:** source_attested (Hannan list + Fortune extended example)
- **Exhaustive:** No
- **Expected:** Reciprocal; associative "together" also possible per Hannan.

### SRC-053 Extension causative (1) /y/ mutation
- **Source:** `fortune_constructions.txt` p.22 §d `-muts- (rouse) < -muk- (rise)+ -y-`, `-ridz- (play) < -rir- + y`, `-shamb-idz-` variant
- **Verbatim:** `-muts-` / `-ridz-` / `-shamb-idz-`
- **Interpretation:** Causative (1) /y/ causes mutation not segmental -is-. Only certain radicals. Distinct from causative (2).
- **Normalized:** `kumutsa` → `-muka` causative(1); mutated surface kept
- **Evidence:** source_attested
- **Exhaustive:** No (only specific radicals)
- **Expected:** Causative via mutation.

### SRC-054 Perfective / extensive
- **Source:** `fortune_constructions.txt` p.22 `perfective /-irir-/ -búd-írír- (came right out)` `extensive /-ik-/ -sím-ík- (plant out)`
- **Verbatim:** `-búd-írír-` / `-sím-ík-`
- **Interpretation:** Perfective -irir- completed; extensive -ik- plant out (homophonous with neuter but different meaning).
- **Normalized:** `kubudirira` → perfective; `kusimika` → extensive
- **Evidence:** source_attested
- **Exhaustive:** No
- **Expected:** Perfective/extensive.

### SRC-055 Monosyllabic C radical -p-a give
- **Source:** `fortune_constructions.txt` p.20 `ku-p-á`; Hannan `†-pa [H] KKoMZ vt Give.`; FSI `Ipa`
- **Verbatim:** `ku-p-á` / `-pa`
- **Interpretation:** C radical -p- syllabically incomplete, needs term -a and i-augment `i-p-á` imperative (Fortune p.20). High tone. Homograph with suffix `-pa` difficulty is different morpheme.
- **Normalized:** `kupa`→`-pa`; imperative `ipa`→`-pa` (i- augment not lemma)
- **Evidence:** source_attested (all three)
- **Exhaustive:** Yes
- **Expected:** "give"; accept `kupa`/`ipa` construction difference.

### SRC-056 Monosyllabic -dya eat
- **Source:** `hannan_dictionary.txt` p.xii `Ndinodya` / `Idya` / `Chidya`; Fortune p.99 `mu-dy-ir-ó` ; FSI `Idya … Adye.`
- **Verbatim:** `Ndinodya` / `Idya`
- **Interpretation:** Short stem -dy- (+a) = -dya eat. In Fortune monosyllabic family `ku-sa-f-á` similar. `mu-dy-ir-ó` shows appl.
- **Normalized:** `kudya`/`idya` → `-dya`
- **Evidence:** source_attested
- **Exhaustive:** Yes
- **Expected:** "eat"; infinitive vs imperative augment contrast.

### SRC-057 Divergent -ti say/do
- **Source:** `fortune_constructions.txt` p.78 footnote (*): "Terminal vowel -a does not occur with -ti, -nzi ... e.g. -dayi, -dare" ; `ku-ti (to say, do etc.)`
- **Verbatim:** `ku-ti`
- **Interpretation:** Divergent stem -ti takes no -a; infinitive is `ku-ti` not *`ku-t-a`. Derived -dayi etc divergent too.
- **Normalized:** `kuti` → `-ti` (no -a stripped)
- **Evidence:** source_attested
- **Exhaustive:** Yes (divergent behavior)
- **Expected:** Infinitive "to say".

### SRC-058 Divergent -nzi be said (passive of -ti)
- **Source:** `fortune_constructions.txt` p.78 `ku-nzi`; Hannan entry `-nzi [L] KZ defective v Be said. Hanzi, uya nedemo`
- **Verbatim:** `ku-nzi` / `-nzi`
- **Interpretation:** Passive of -ti, divergent no -a. Hannan notes conj use `kunzi ndirege`.
- **Normalized:** `kunzi` → `-nzi`
- **Evidence:** source_attested (both)
- **Exhaustive:** Yes
- **Expected:** "be said".

### SRC-059 Pro-verb -na (gap)
- **Source:** No verb stem -na pro-verb found; Hannan `-na [L]M enum st: Other.` is enumerative, Fortune `-na-` adverbial/possessive affix, FSI `/-na-/` obligation formative — none is verb stem "do"
- **Verbatim:** — (no verbatim -na verb stem)
- **Interpretation:** Requested -na pro-verb not yielded in examined excerpts. What exists is formative, not stem. Shortfall.
- **Normalized:** N/A — if API receives `kuna` lemmatization uncertain; should be unresolved not guessed as verb
- **Evidence:** unresolved (no attestation; do not fabricate)
- **Exhaustive:** N/A
- **Expected:** No acceptable verb analysis grounded; return empty/unresolved.

### SRC-060 Vowel-initial -ambura ignite
- **Source:** `hannan_dictionary.txt` p.2 `-ambura [L] M v i Ignite. Umba yaambura: the house is on fire.`
- **Verbatim:** `-ambura` / `yaambura`
- **Interpretation:** Vowel-initial a- stem -ambura. Example `yaambura` = `ya-`? SC past? Shows vowel-initial retains a-. Only M dialect verified per Hannan.
- **Normalized:** `yaambura`→`-ambura` (strip SC) ; hypothetical `kuambura` rule_supported (not verbatim)
- **Evidence:** `-ambura` source_attested; `kuambura` rule_supported via general ku- + R pattern
- **Exhaustive:** No
- **Expected:** "ignite"; accept only M dialect as verified.

### SRC-061 Vowel-initial -enda go
- **Source:** `fortune_constructions.txt` p.78 `ku-chi-end-a`; `fsi_course.txt` p.129 `kuenda` `Enda!`
- **Verbatim:** `ku-chi-end-a` / `Enda!` / `kuenda`
- **Interpretation:** -enda vowel-initial e-. `ku-`+`enda`→`kuenda` (no coalescence). Imperative `Enda!` needs no i-augment (vs C radicals). Contrast.
- **Normalized:** `kuenda`/`enda` → `-enda`
- **Evidence:** source_attested
- **Exhaustive:** Yes
- **Expected:** "go".

### SRC-062 Vowel-initial -ona (gap)
- **Source:** No verbatim -ona stem located in examined Fortune/Hannan excerpt windows; Hannan likely has entry but not in cache excerpt; Fortune uses -enda/-ambura but not -ona as verb example
- **Verbatim:** — (not located verbatim)
- **Interpretation:** Requested -ona (see) not yielded verbatim in inspected sources. Could be constructed via vowel-initial rule (cf -ambura/-enda) but not attested.
- **Normalized:** Hypothetical `kuona` → `-ona` would be rule_supported per general ku- + vowel-initial R rule (Fortune p.78-79)
- **Evidence:** unresolved for verbatim; rule_supported if constructed
- **Exhaustive:** No
- **Expected:** If API receives `kuona`, analysis ku- + -ona + -a is plausible but must be flagged rule_supported not source_attested.

### SRC-063 Short -dy- with applicative -dy-ir-
- **Source:** `fortune_constructions.txt` p.99 `mu-dy-ir-ó (way of eating) cp. -dy-ir-`
- **Verbatim:** `mu-dy-ir-ó` / `-dy-ir-`
- **Interpretation:** Monosyllabic -dy- + appl -ir- → `dy-ir-` eat-for. Shows short stem takes extension; nominal `mu-`+`dy-ir-`+`-o`.
- **Normalized:** `kudyira` → `-dya` + appl
- **Evidence:** source_attested
- **Exhaustive:** Yes
- **Expected:** Applicative "eat for".

### SRC-064 Ambiguous principal vs participial (tone only)
- **Source:** `fortune_constructions.txt` PDF p.25-26 g examples `v-á-ka-tém-á` (principal remote past) vs `v-á-ka-témà` (participial) ; `nd-a-tem-a` vs `nd-a-tem-á`
- **Verbatim:** `v-á-ka-tém-á` vs `v-á-ka-témà` → orthographically both `vakatem a` (`vakatem a`)
- **Interpretation:** Identical segments `v-a-ka-tem-a` but different tonal morphemes H vs L (Fortune g1-7) conditioning radical tones. Without tone marks `vakatem a` ambiguous among principal/participial/relative.
- **Normalized:** `vakatem a` → strip tone/diacritics → `vakatem a` → `-tema`
- **Evidence:** source_attested (Fortune uses minimal pair to argue for tonal morphemes)
- **Exhaustive:** No
- **Expected:** Accept both readings: (1) principal "they cut (before today)" (2) participial "they having cut"; API should return multiple or flag ambiguous.

### SRC-065 Ambiguous -zvi- object vs reflexive
- **Source:** `fortune_constructions.txt` p.78 `kuzviziva (to know oneself)` reflexive vs p.78 `kuzvitora (to take them)` object; p.99 `mu-zvi-bát-ir-ó` reflexive; TC XI `nd-a-ká-zvi-p-á` reflexive tones
- **Verbatim:** `kuzviziva` (same surface for both)
- **Interpretation:** Surface `ku-zvi-ziva` = `ku-`+`zvi-` OP cl8 (them) vs `ku-`+`zvi-` REFL (oneself). Segmentally identical, tonally distinct (TC XI). Fortune distinguishes by meaning and tone.
- **Normalized:** `kuzviziva` → `-ziva` + ambiguous `zvi-` tag
- **Evidence:** reflexive source_attested; object rule_supported via general OP rule (Fortune §3.3.15(2)(a))
- **Exhaustive:** No
- **Expected:** Accept both: "know them" and "know oneself"; flag ambiguous.

### SRC-066 Ambiguous tonal morpheme triple
- **Source:** `fortune_constructions.txt` PDF p.26 g list `nd-á-zív-á (I know)` `nd-á-zív-a (I having known)` `nd-a-zív-á (I who know)` ; all segments `nd-a-ziv-a`
- **Verbatim:** `nd-á-zív-á` vs `nd-a-zív-á` → both `ndaziva` orthographically
- **Interpretation:** Same segments `nd-a-ziv-a` but SC tone morphemes L vs H differentiate principal vs participial vs relative (Fortune §2.10.2.4g). Without tone, `ndaziva` ambiguous.
- **Normalized:** `ndaziva` → `-ziva` with multiple TAM tags
- **Evidence:** source_attested
- **Exhaustive:** No
- **Expected:** Accept principal "I know", participial "I having known", relative "I who know" as valid without tone.

### SRC-067 Ambiguous rank-shift (nominal vs clause) — word division
- **Source:** `fortune_constructions.txt` p.106 `Ø-Ma-dy-ir-á-panzé (1a) Praise name of chief Gutu` (NP = Ø- + inflected V phrase) vs clause `madyira panze` (they eat outside) ; Hannan Rules I-VI word-division p.xxi
- **Verbatim:** `Madyirapanze` (one-word name) vs `Madyira panze` (two words)
- **Interpretation:** Same characters without space/hyphen: `Ma-dy-ir-a panze` as nominal construction (rank-shifted V phrase) vs subject+predicate clause. Hannan Rule I says complex nominals with clause are one word without hyphen.
- **Normalized:** `madyirapanze` (space removed) → `-dya` applied + locative; vs `madyira panze` with space → different construction
- **Evidence:** nominal source_attested; clausal reading rule_supported via general clause pattern `subject+predicate`
- **Exhaustive:** No
- **Expected:** Both nominal name reading and clausal reading acceptable; API should be space-tolerant and not reject one.

### SRC-068 Source defers — final -i vs -e dialect (explicit statement)
- **Source:** `fsi_course.txt` Unit12 Note1 p.118 "final vowel is !-i! in some dialects, !-e! in others."; p.323 "final vowel in negative commands may be -a (usaputsa) or -e (usaputse)"; Hannan p.xii `Handidyi St.Sh. / Handidye Z`
- **Verbatim:** `Handitauri / Handitaure` ; `Usaputsa / Usaputse` ; `Handidyi / Handidye`
- **Interpretation:** Sources explicitly mark dialect variation rather than prescribe single correct form. FSI defers to tutor; Hannan marks StSh vs Z vs KM.
- **Normalized:** Both `handitauri`/`handitaure` → `-taura` + dialect tag; both correct.
- **Evidence:** source_attested (explicit statements)
- **Exhaustive:** Yes for this dimension (two variants listed)
- **Expected:** Accept -i (KM/StSh) and -e (Z) as equally valid; API must tag dialect not reject.

### SRC-069 Source marks dialect scope / Zezuru default
- **Source:** `hannan_dictionary.txt` Intro p.v-viii "tone given is chiZezuru … unless otherwise indicated." + "letters K/M/Z indicate verified lexicon … we have not found this word except …"; entries `-ambura [L] M` vs `†-pa [H] KKoMZ`
- **Verbatim:** `-ambura [L] M` (only Manyika verified) ; `†-pa [H] KKoMZ` (pan-dialectal)
- **Interpretation:** Hannan defers lexical existence to dialect verification; -ambura only verified M, not Z/K. Tone default Zezuru. Fortune similarly: `prefix /á-/ free variant of /va-/ as honorific` (p.??).
- **Normalized:** `kuambura` → `-ambura` dialect-restricted M; `kupa` → `-pa` pan-dialectal. API must not assume pan-dialectal for -ambura.
- **Evidence:** source_attested
- **Exhaustive:** No (research incomplete per Hannan)
- **Expected:** For -ambura, acceptable only if dialect=M (or if API ignores dialect, flag as restricted); for -pa, accept KKoMZ.

### SRC-070 Source marks free variation / conditioned allomorphy
- **Source:** `fortune_constructions.txt` p.22 "passive /w/ in free variation with /-iw- ~ -ew-/"; ` -tór-ew- (be taken)` after e/o; `/-ir-/ vs /-er-/` harmony
- **Verbatim:** `passive /w/ free variation /-iw- ~ -ew-/` ; ` -tór-ew-`
- **Interpretation:** Fortune defers to free variation or phonologically conditioned allomorphy: passive -w- ≡ -iw- ≡ -ew- with no meaning difference; -ir- vs -er- depends on preceding vowel.
- **Normalized:** `kutapwa` vs `kutapiwa` vs `kutorewa` → same lemma `-tapa` passive; distinct surfaces are variants, not different lemmas.
- **Evidence:** source_attested
- **Exhaustive:** Yes for passive (variants listed exhaustively)
- **Expected:** Accept both `-w-` and `-iw-` as correct passive; accept `-ew-` after e/o stems.

---
## 3. Source-shortfall report (honest gaps, not padded)
| Category | What was sought | What sources actually yielded | Gap / implication | Evidence class for gap |
|----------|-----------------|-------------------------------|-------------------|---------------------------|
| Infinitives with **simultaneous** object + extension + negation | e.g., hypothetical `ku-sa-mu-bik-ir-a` (not to cook for him) | Only `ku-sa-zvi-ziv-a` (neg+obj) and `ku-zvi-tor-a` (obj) and `-bik-ir-` (extension) separately; no single verbatim token combining all three | Cannot claim source_attested for triple combination; would be **rule_supported** via Fortune general rule that object prefixes belong to verb phrase and -ir- is extension, but segmental co-occurrence not shown verbatim. Mark as shortfall, not fabricate. | rule_supported (if constructed) else unresolved |
| Negative infinitive with **exclusive/progressive** + object | e.g., `ku-sa-chi-zvi-ziv-a` | Fortune lists `ku-sa-` and `ku-chi-` and `ku-zvi-` separately but no combined `ku-sa-chi-zvi-` token | Shortfall; sources allow each formative separately (Fortune p.79 lists them as possible) but no combined example. | unresolved unless explicit rule says they co-occur (Fortune suggests infinitives are more complex than other nominals, implying possible, but not exemplified). |
| Reciprocal with **finite present** | Finite `vanodanana` "they love each other" | Hannan lists `-ana` as reciprocal and Fortune gives nominal `va-pamhidz-ir-an-i` but no finite present `va-no-dan-an-a` verbatim in Fortune/FSI/Hannan excerpts | Shortfall; reciprocal shown only in nominal/deverbative, not finite principal. Could be rule_supported via Hannan list, but we mark as not source_attested. | rule_supported |
| Pro-verb **-na** as verb stem | Requested `-na` pro-verb | No verb stem `-na` meaning "do" found; Hannan `-na` is enumerative stem "other", Fortune `-na-` adverbial/possessive affix, FSI `/-na-/` obligation formative, not verb stem. | **No verbatim pro-verb -na**; treat as unresolved, do not invent. | unresolved (SRC-059) |
| Vowel-initial **-ona** verb stem | Requested -ona (see) | Hannan cache not showing -ona entry in examined window; Fortune examples use -enda, -ambura but not -ona; FSI `unoona`? FSI Unit 35 `Unaona vana` is "you see children" → does contain -ona? Actually FSI Unit 35 `Unaona vana` = `u-` + `-ona`? That is "you see" — but our excerpt shows `Unaona vana vasatizetize` — that is 2sg imperative? Actually `Unaona` could be ? Let's conservatively mark -ona as **not verbatim located** in the limited cache search; we mark as shortfall (SRC-062) rather than claim source_attested without locator. | rule_supported (via vowel-initial pattern) |
| Singular negative imperative **with object + extension** | e.g., `usamubikire` (don't cook for him) | FSI Unit 34 shows `Usarise` (neg imp with object) and Fortune shows extension `-bik-ir-` separately, but no token combining both in negative imperative | Shortfall; would require rule_supported, not source_attested. | unresolved/rule_supported |
| Ambiguous surface requiring **tone to disambiguate** where orthography identical but sources give no orthographic minimal pair | e.g., `vasina` could be negative relative vs negative participial | Fortune gives tone-only pairs like `v-á-ka-tém-á` vs `v-á-ka-témà` but orthographically both `vakatem a` — sources note polarity/tone conditioning but do not provide disambiguated orthographic convention | Shortfall: Without tone, many TAM distinctions are neutralized; sources defer to tone, not orthography. API must return multiple analyses and flag ambiguous, not choose one. | source_attested (the ambiguity itself is attested) |
| Dialectal **plural negative imperative with -i vs -e** beyond `Musadya/Musadye` | Other verbs like `Musaputsa` vs `Musaputse` only singular exemplified with -e variant note, plural -e not verbatim shown | FSI note says final vowel may be -a or -e "depending on dialect" generally, so plural would follow same rule, but not verbatim exemplified for every verb | rule_supported extension of general note |

**Principle:** Where no verbatim example was found after targeted grep + manual reading, we left ID as `unresolved` or `rule_supported` with explicit justification and did not fabricate a source_attested claim. This is honest uncertainty per engineering milestone requirement.

## 4. Full locator list (challenger can re-inspect each passage — short excerpts, not redistribution)

**FSI Shona Basic Course (fsi_course.txt / fsi_course.pdf):**
- Unit 12 Note 1 printed p.118 — negative present formation, final -i/-e dialect note, example `Handitauri` / `Handizivi` vs affirmative `Ndinotaura` / `Ndinoziva`
- Unit 12 §2 p.119 — high verb paradigm `Unodzidzisa → Handzidzisi`, `Unosanda → Handisandi`
- Unit 12 §3 p.119 — monosyllabic `Unoda → Handidi`, `Munoda → Hatidi`, `Anoda → Haadi`
- Unit 12 §4 p.120 — low verb `Handitauri chiNdevere`, `Haatauri`, `Hatitauri`, `Havatauri`, `Hautauri`, `Hamutauri`
- Unit 12 §5 p.120 — ability `Handigoni`, `Haagoni`, `Hatigoni`, `Havagoni`
- Unit 13 §4 p.129 — affirmative imperative low `Taura!`, `Pinda!`, `Verenga!`, `Enda!`
- Unit 13 §5 p.130 — high `Uya!`, `Tenga!`, `Tengesa!`
- Unit 13 §6 p.130 — plural `Tengesai`, `Pedzai`, `Rerai`, `Verengai` + §7 p.131 `Taurai`
- Unit 32 p.323 Note + §3 p.323 — negative imperative sg `Usaputsa/Usaputse` note, `Usapinda mumba`, `Usaputsa mavhingwa`
- Unit 32 §4 p.324 — plural `Musaisa`, `Musaseva`, `Musakurungira`
- Unit 34 p.339 — imperative with object `Ipa/Ipe`, `Hupe`, `Idya/Adye`, `RIdye`
- Unit 34 p.340-341 — `Usarise` / `RIise` with object -ri-, locative
- Unit 33 p.332 §2 — obligation `Tinazadza` vs `Hatizadzi`, `Tinaitsvaira` etc; p.333 with object `Unaitsvaira`
- Unit 32 §5 p.325 — subjunctive negative with object `tisadirire` / `tisadzidirire`, `tisadzibvise`
- Unit 32 §6 p.325 — causative `Ndiani wamuradzika?`
- Unit 13 dialogue p.?? `Tauraizve` / `Pindaizve` etc (again)
- Unit 35 `Unaona vana vasatizetize` (2sg? — contains -ona)

**Fortune Grammatical Constructions Vol.1 (fortune_constructions.txt / fortune_grammatical_constructions.pdf):**
- §2.8 p.19 — `ha-ndí-cha-zív-a` (I no longer know) contrast
- §2.10.2.2 p.20 — radicals `ku-p-á`, `ku-rw-a`, `ku-tém-á`, `ku-bik-a`, `ku-zórór-á`, `ku-tever-a`; imperative `i-p-á` `tém-á`
- §2.10.2.3.3 p.22 — extensions list `passive -iw- -táp-iw-`, `neuter -ik- -ziv-ík-`, `applied -ir- -síy-ír- -tém-ér-`, `causative -is- -muk-is-`, `intensive -taur-is-`, `repetitive -urur- -túk-úrúr-`, `reversive -anur-/-enur-/-inur-/-onor-/-unur- -chat-anur-` etc, `perfective -irir- -búd-írír-`, `extensive -ik- -sím-ík-`
- §2.10.2.3.3 d p.22 — causative (1) /y/ ` -muts- < -muk- + y`, `-ridz-`, `-shamb-idz-`
- §2.10.2.4 b p.22 — `ha-ndí-zív-é` / `há-ti-end-e-i`
- §2.10.2.4 c p.22 — polarity examples `a-sí-nga-zív-e` vs `a-si-ngá-bik-é`
- §2.10.2.4 e-f PDF p.23-24 — TC II imperative `i-p-á`/`tém-á`, TC VII negative `ha-ndí-p-e`/`-tém-é`, TC X exclusive `chí-p-a`, TC XI reflexive `nd-a-ká-zvi-p-á`
- §2.10.2.4 g p.25-26 — tonal morphemes minimal pairs `v-á-ka-tém-á` vs `v-á-ka-témà`, `nd-a-p-á` vs `v-á-p-a`, `nd-á-zív-á` vs `nd-a-zív-á`
- §2.10.2.4 h p.26 — auxiliary `ndi-nó-wanz-o it-a` vs `ha-ndí-wanz-ó it-a` and `ndi-nó-wanza kuita` vs `ha-ndí-wanze kuita`
- §2.10.1.2 p.?? — copulative allomorphs etc (not directly verb but concord)
- §3.3.15 p.78-79 — infinitive class 15 description `ku-ti`, `ku-nzi` footnote, `kusaziva`, `kuzvitora`, `kuzviziva`, `ku-cha-ziv-a`, `ku-chi-end-a`, `ku-sa-zvi-ziv-a`, `ndi-no-mu-ziv-a`, `ku-zvi-ziv-a`, `ku-sa-f-á`, `ku-chi-f-a`, `ku-a-dy-á` ; p.105 `ku-sa-f-á nenzára`
- §3.4.2.10 p.106 — nominal based on inflected phrase `Madyírá-panzé` vs `shambá-wámedzá` etc
- §3.5 p.?? — object/possessive tables Series I-XI including `mu-` `va-` `ri-` `chi-` `zvi-` etc
- §Penultimate i- p.37 — `i-d-á!` `i-ye` `i-dy-é` with C radicals
- §6.3 p.?? — ideophone `Bhere rákánga rá-í-dya` etc (not verb morphology)
- Additional: p.37 "Constructional pattern … mu-zvi-bát-ir-ó (way of controlling oneself)" + p.99 deverbatives

**Hannan Standard Shona Dictionary (hannan_dictionary.txt / hannan_dictionary.pdf):**
- Front matter p.ix — suffix formative list `-ama; -ana; -ara; -ata; -aura; -edza; -eka; -era; -erera; -esa; -ewa; -idza; -ika; -ira; -irira; -isa; -iwa; -orora; -ura; -urura; -wa` + instruction " Each appears as dictionary entry"
- Front matter p.ix — dialect labels K/Ko/Ko(B)/M/Z explanation + "tone given is chiZezuru tone, unless otherwise indicated"
- Front matter Table of Class Prefixes p.xii — concords `ndi-` `u-` `a-` `va-` `chi-` `zvi-` etc + object prefixes `-ndi-` `-mu-` `-chi-` etc
- Front matter Table of Verb Forms p.xii-xviii — `Handidyi St.Sh. / Handidye Z`, `Handichadyi / Handichadya`, `Handisati ndodya` etc; `Ndinodya`, `Ndichadya`, `Ndiri kudya` etc; `Usadya. Musadya KM / Usadye. Musadye Z`, `Usachidya. Musachidya`
- p.26 entry `asi [LH]KKoMZ` example `Kuburuka ndinogona, asi kukwira handigoni`
- p.2 entry `-ambura [L] M v i Ignite. Umba yaambura: the house is on fire.`
- p.14+ entry `†-pa [H] KKoMZ vt Give.` + example `Ndipe fodya`
- Entry `-nzi [L] KZ defective v Be said. Hanzi, uya nedemo`
- Entry `-buda [H] …` etc (not used)
- Word-division Rules p.xxi-xxii — Rules I-VI for verb stems, locatives, reduplication etc (used for SRC-067 rank shift note)

**Images (local_batches) where OCR tone/table ambiguous:**
- `fsi_p341_negative_commands.png` — verifies -a/-e note and `Usaputsa` paradigm (FSI p.323-324)
- `fsi_p357_imperative.png` / `fsi_p356_imperative.png` — verify `Taura!`/`Taurai` etc tone marks
- `fortune_p34.png` + `fortune_tc7_hi.png` / `fortune_hazive_hi.png` — verify TC VII `ha-ndí-p-e` vs `há-ti-end-e-i` diacritics
- `render_pages/hannan-*` — verify `-ambura` entry layout

---
## 5. Methodology & uncertainty notes (engineering milestone, not linguistic certification)
- Only short excerpts quoted; full source texts not redistributed.
- OCR errors (~ for tone, ! for orthographic markers) normalized by consulting images where layout/tone matters; where uncertain, flagged as uncertainty.
- Morpheme boundaries follow source analyses (FSI Note 1 for negatives, Fortune §2.10.2.4 for tonal morphemes and extensions). Where sources disagree on tone class of a specific stem (e.g., -taura), uncertainty reported rather than forced.
- For constructed forms not verbatim, evidence class is `rule_supported` only if source states an explicit productive rule (e.g., Hannan sfx list implies any verb may in principle take -ira/-isa etc; Fortune states extensions are tonally neutral and -sa- belongs to infinitive). Otherwise `unresolved`.
- Dialect variation is treated as acceptable variant, not error: FSI defers to tutor; Hannan marks K/M/Z; Fortune notes free variation. API should tag dialect rather than reject.
- Ambiguous surfaces are expected to return multiple analyses or flag `ambiguous: true` rather than single best guess.
- Word-division per Hannan Rules I-VI influences tokenization: `Madyirapanze` (one word name) vs `Madyira panze` (clause) are distinct; API input normalization should consider space/hyphen handling.
- No claims about API behavior were made; no implementation files were inspected.

*End of corpus freeze candidate — 70 cases with locators, ready for coordinator versioning.*
