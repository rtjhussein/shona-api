# Fresh-agent prompt: finish the verb-extension correction pass

You are implementing a focused correction pass for the Shona API morphology subsystem.
The user wants the language product completed before deployment, billing, or infrastructure work.
A previous agent implemented the first verb-extension improvement pass, and the supervisor reviewed it.
Preserve the useful work and resolve the five review findings below.
Deliver working code, tests, and evidence; do not stop at another plan or assessment.

## Workspace and starting state

Repository: `C:/Users/user/Documents/Projects/shona-api`.
Environment: Windows PowerShell, Python 3.12+, Django and Django REST Framework.
The project interpreter is `.venv/Scripts/python.exe`.

Read applicable `AGENTS.md`, `CONTEXT.md`, and `C:/Users/user/.codex/OPINIONS.md`.
Use CodeGraph before locating or understanding code only if a `.codegraph` directory exists in your checkout.
Use the evidence-validation skill for meaningful implementation closeout.
This assignment authorizes implementation of the specified correction pass; resolve routine implementation choices yourself.

IMPORTANT: the previous agent's implementation is currently uncommitted, with both modified and untracked files.
Do not reset, clean, stash away, overwrite, or discard that work.
Do not start from a clean HEAD-only worktree and assume it contains the implementation being reviewed.
Inspect `git status` and the actual working tree first.
If isolation is needed, explicitly preserve the complete starting working tree, including untracked implementation files.
Use a `codex/` branch if creating a branch, and do not run concurrent editors against this checkout.
Do not merge, push, or modify the live corpus or live release records as part of this task.

At handoff, modified files include:

- `shona_api/morphology/services.py`
- `shona_api/api_docs/spec.py`
- `docs/openapi.json`
- `docs/morphology/generate_endpoint.md`
- `docs/morphology/real_data_regression_corpus.md`
- `docs/morphology/rules/cards/fortune.verbal.extensions.001.json`
- `tests/test_morphology_api.py`
- `tests/test_lexicon_api.py`

Untracked implementation files include `tests/test_morphology_verb_extensions.py` and the retained, repetitive, and reversive rule cards under `docs/morphology/rules/cards/`.
There are also assessment and assignment documents in `docs/morphology/`.
Recheck the current state rather than treating this list as exhaustive.

## Product context and existing work

The public morphology endpoints are `POST /v1/analyze` and `POST /v1/generate`.
They require an API key and a current `DataRelease`.
Present positive/negative generation supports person or noun-class subjects, an optional object concord, and extensions.
Analysis supports those present constructions and simple ku-infinitives.
Generation currently accepts `generation_type: verb_form` and `tense_aspect: present`.
Verb-stem resolution uses reviewed lexical records.

The first pass fixed greedy stripping past stems such as `-ambura`, corrected long reversive vowels, separated repetitive from reversive extensions, added multiple lexical candidates, tightened some feature validation, and added source-labelled regression examples.
Keep these improvements.
The supervisor ran the full suite in an isolated SQLite database: **255 passed in 8.44 seconds**.
A narrower morphology/search/docs run passed **76 tests**.
Additional authenticated routed API checks exposed the remaining defects despite the green suite.

The original assessment is `docs/morphology/completeness-assessment-2026-09-08.md`.
The original implementation assignment is `docs/morphology/next-agent-verb-extensions.md`.
Those provide background; this correction prompt defines your immediate scope and supersedes stale descriptions of already-fixed behaviour.
Do not assume the original assessment was updated after the first pass.

## Files to inspect

- `shona_api/morphology/services.py`, especially `_normalize_generation_extensions`, `_candidate_decompositions`, `_get_stem_candidates`, `_analyze_present_positive`, `_analyze_present_negative`, `_apply_extensions`, and rule/version metadata
- `shona_api/morphology/views.py`
- `tests/test_morphology_verb_extensions.py`, `tests/test_morphology_api.py`, and `tests/test_morphology_rule_cards.py`
- Morphology enrichment in `shona_api/lexicon/views.py` and relevant search/corpus tests
- `shona_api/releases/services.py`, release models and release tests, only as needed for truthful morphology-version behaviour
- `docs/morphology/rules/README.md` and the rule cards
- `docs/morphology/generate_endpoint.md`
- `shona_api/api_docs/spec.py`, API-doc tests, and the OpenAPI generation command

## Finding 1: malformed extension styles produce HTTP 500

For a valid published verb-stem fixture, send a normal generation request with either:

```json
{"extensions": [{"type": "reversive", "style": []}]}
```

or the same request with `style: {}`.
These are the extensions field within the complete features object, not standalone request bodies.
Both currently raise an unhashable-type `TypeError` because invalid values reach membership tests against the legacy-style sets.
Using the Django client with `raise_request_exception=False`, the supervisor confirmed **HTTP 500 with an HTML response**.

Required result: malformed types produce the documented structured client error, normally `422 GENERATION_UNSUPPORTED`, without an exception escaping.
Validate type before membership or dictionary operations and cover relevant JSON values, including lists, objects, booleans, numbers and null according to the documented contract.
Keep useful hints for legacy string styles.
Do not add a broad exception handler that disguises programming errors as invalid input.

## Finding 2: object-marker parsing can discard the originating lemma

In an isolated database, create published verb-stem fixtures `-kura` and `-ra`.
Generate from `-kura` using first-person singular positive present with `extensions: ["causative"]` and no object.
The API returns `ndinokurisa`.
Analyze that returned surface.
The current result contains only `-ra` with second-person singular object marker `ku`; the originating `-kura` analysis is absent.
This is a structural ambiguity reproduction using test fixtures, not independent certification of every possible lexical derivation.

The positive and negative analyzers still return on the first object segmentation with a lexical match.
Returning several stem candidates behind that one segmentation does not solve the larger ambiguity.

Required result: consider viable no-object and object interpretations, competing object concord readings, and applicable vowel-coalescence alternatives before ranking and bounding results.
Retain the originating lemma and compatible feature reading among the analyses of a supported generated form when legitimate alternatives exist.
Keep deterministic ordering, deduplicate equivalent readings without merging distinct meanings/features, and apply sensible resource bounds.
Test both polarities and relevant shared-surface object concords.
Do not solve this by always choosing no-object first and dropping object readings instead.
Verify search enrichment can consume the expanded analyses safely.

## Finding 3: analyzer and generator use inconsistent extension-sequence rules

With a published `-buda` fixture:

| Generation request | Generation result | Analyzed surface | Analysis result |
| --- | --- | --- | --- |
| `["passive", "causative"]` | 422 | `ndinobudwisa` | 200, passive then causative |
| `["causative", "causative"]` | 422 | `ndinobudisisa` | 200, repeated causative |

The generator validates an ordering/uniqueness policy; `_candidate_decompositions` checks suffix forms and depth but does not enforce that policy.
The current documented total order is not itself demonstrated to be a grammatical rule by the cited source page.

Required result: establish one explicit source-backed policy for sequence validity and apply it consistently.
Distinguish grammatical constraints from conservative product/resource limits.
If analysis intentionally recognizes attested forms the generator cannot safely produce, model and document that distinction with source-backed tests; do not retain accidental asymmetry.
Do not mechanically declare every accepted existing sequence grammatical, or every currently rejected sequence impossible.
Keep source-supported combinations working and provide clear unsupported behaviour for unverified combinations.

## Finding 4: lexical restrictions and source-review gates are not enforced

The generator still applies causative `dz` and `ts` styles to arbitrary accepted stems.
`EXTENSION_LEXICALLY_RESTRICTED` is a warning, not an actual restriction.
The retained extension rule card enables `public_endpoint_safe`, analyzer and generator use while explicitly acknowledging missing source locators and unresolved lexical distribution.
Reciprocal and short-reversive compatibility cases also remain enabled without verified evidence in that card.

Required result: seek actual source evidence and preserve support where it can be justified.
Where only particular derived forms are attested, use an explicit reviewed lexical relation or another clear evidence-backed eligibility mechanism rather than generalizing a suffix to every lemma.
Where evidence is unavailable, return a structured unsupported result for the unverified operation instead of unrestricted generation with a warning.
An attested lexical form can remain searchable or analyzable as that lexical entry without asserting an unverified derivational relationship.
Keep uncertainty honest and visible, and do not invent a human review decision.
Do not blanket-disable the entire extension subsystem to make the task easier.
Do not mark a source search with no matching rule as positive evidence for public rule approval.

Sources available locally:

- `key_documents/fortune_grammatical_constructions.pdf`: *Shona Grammatical Constructions, Volume 1*, third edition 1985, 205 PDF pages
- PDF page 33, printed page 21, section 2.10.2.3.3, “Extended radicals”, with adjacent pages for context
- That page supports the repetitive/reversive distinction and gives long-reversive vowel forms and examples; it does not establish every lexical distribution or extension-stack rule
- The source refers to later verbal sections for causative distribution; confirm availability rather than inventing locators in another volume
- `key_documents/hannan_dictionary.pdf` and local extracted text in `local_source_cache/hannan_dictionary.txt` can help locate attested lexical forms and relationships; validate relevant passages against the source PDF
- Supporting local source documents may supply additional evidence, subject to the project's source-authority policy

The supervisor found Hannan text hits for `petenura`, `pfekenura`, and an explicit `kupeta > kupetenura` relationship.
The PRD supplies product intent, not authority for linguistic claims.
Use minimal source examples and locators; do not commit source PDFs or bulk copied text.

## Finding 5: reported rule versions do not identify executed behaviour

The new cards and documentation describe the corrections as `morphology-rules-v3`.
However, create a current release labelled `morphology-rules-v2`, then generate the long reversive of `-kora`.
It already returns the corrected `ndinokoronora` while reporting `morphology-rules-v2`.
The code echoes the supplied release label; it does not select or validate the implementation version.
The documentation's activation wording is therefore misleading.

Required result: make the version reported to API consumers identify the rules actually executed.
Choose a simple explicit policy: either dispatch to genuinely implemented versions, or validate configuration against the available implementation and return a clear structured configuration/readiness error on mismatch.
Do not pretend historical implementations exist or duplicate the whole engine just to satisfy a label.
Retain `data_release` separately from morphology-rule identity.
Cover analyze, generate and search morphology enrichment, including how search behaves on an incompatible rules configuration.
Update activation instructions and compatibility notes without changing live release records.
Do not silently rewrite an incoming version label to hide invalid configuration.

## Reproduction setup and test safety

Each routed API test needs an API key, a current release and the relevant reviewed/published lemma fixtures.
Use the existing test helpers where practical and ensure throttling does not mask the behaviour being tested.

Common generation request:

```json
{
  "lemma_public_id": "<fixture public ID>",
  "features": {
    "generation_type": "verb_form",
    "subject": {"type": "person", "person": "first", "number": "singular"},
    "tense_aspect": "present",
    "polarity": "positive",
    "extensions": ["causative"]
  }
}
```

The project reads `.env` with overwrite enabled and has a reusable test-database configuration.
Do not assume a shell `DATABASE_URL` override isolates tests.
Use an explicit isolated settings module after importing base settings, or an equivalent verified test configuration.
This was the supervisor's safe full-suite invocation in PowerShell:

```powershell
@'
import sys, types
import config.settings.test as original
settings = types.ModuleType('assessment_settings')
settings.__dict__.update({k: v for k, v in vars(original).items() if k.isupper()})
settings.DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
sys.modules['assessment_settings'] = settings
import pytest
raise SystemExit(pytest.main(['--ds=assessment_settings', '--create-db', '-q']))
'@ | .\.venv\Scripts\python.exe -
```

For standalone Django-client reproductions, configure the same isolated database before `django.setup()`, run migrations there, and create test data there.
Never run those fixture-creation scripts against the project's ordinary database.

## Implementation boundaries

Keep the existing valid v1 response envelope and useful feature support.
Document intentional corrections to inaccurate semantics, unsupported inputs and version configuration.
Prefer shared validation/rule logic where it prevents divergence, without turning this into a generic grammar-engine rewrite.
Keep the positive first-pass improvements covered by regression tests.
Do not alter ingestion/publication workflows, introduce new finite tenses or noun generation, or add deployment and billing work.

Update the OpenAPI source and regenerate `docs/openapi.json` through its owning command when necessary; do not edit generated output by hand.
Update the relevant docs and append a dated status section to the original assessment, preserving its historical findings and clearly marking what is now resolved.

## Acceptance and closeout

Reproduce the five findings before fixing them and add meaningful regression tests that fail against the current behaviour.
Verify through authenticated routed API calls, including invalid input, legitimate ambiguity, unsupported sequences, evidence gating and incompatible version configuration.
Use source-backed expected forms in addition to round-trip tests; two matching algorithms can still share the same grammatical mistake.
Run the focused tests, then the complete suite using safe isolated settings.
Investigate failures honestly; do not weaken tests merely to obtain a green suite.
Report backend-specific or linguistic-review limitations without claiming independent accuracy certification.

Return a concise closeout containing:

- Each of the five findings marked resolved or explicitly unresolved, with evidence
- What supported behaviour now works for an API customer
- The chosen sequence, lexical-evidence and rule-version policies
- Before/after request examples and responses
- Files changed during your pass, distinguished from the inherited working tree where practical
- Commands run, results, source locators and compatibility changes
- Remaining source gaps, unsupported cases and review hotspots
- A risk rating and rollback approach for the code/configuration changes

Completion means the five findings are resolved under explicit, tested policies and valid first-pass functionality is preserved.
If essential source evidence is unavailable, finish independent corrections and identify the precise remaining blocker instead of claiming the whole milestone complete.
Do not move on to broader infinitives or additional tenses until this correction pass is ready for supervisory review.
