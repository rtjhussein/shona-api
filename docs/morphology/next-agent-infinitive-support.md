# Fresh-agent prompt: complete bounded infinitive analysis and generation

Implement the next Shona API language-product milestone: source-backed infinitive generation and richer infinitive analysis.
The user prioritizes completing linguistic capabilities before deployment, billing, or infrastructure work.
The supervisor has accepted the preceding verb-extension correction milestone after API-level review and 268 passing tests in an isolated SQLite database.
Preserve those corrections and deliver working functionality, documentation, and verification evidence.

## Workspace and workflow

Repository: `C:/Users/user/Documents/Projects/shona-api`.
Stack: Python 3.12+, Django, Django REST Framework; use `.venv/Scripts/python.exe` on Windows.
Read applicable `AGENTS.md`, `CONTEXT.md`, and `C:/Users/user/.codex/OPINIONS.md`.
Use CodeGraph first if a `.codegraph` directory exists; otherwise use normal source inspection.
Inspect status and branch before editing, preserve unrelated work, and create a `codex/` feature branch from the synchronized main branch.
Use the evidence-validation skill for closeout.
This prompt authorizes implementation of the direction below; do not stop at another general assessment or ask for routine implementation permission.
Do not merge or push unless separately instructed.

## Existing behaviour to preserve

`POST /v1/analyze` and `POST /v1/generate` require API-key authentication and a current `DataRelease`.
The engine currently implements `morphology-rules-v3`.
The public analyze/generate endpoints reject a release with a different rule version using structured `503 MORPHOLOGY_RULES_VERSION_UNSUPPORTED`.
Search continues serving lexical results while reporting morphology enrichment unavailable on a version mismatch.

Generation currently accepts `generation_type: verb_form`, `tense_aspect: present`, positive/negative polarity, person or noun-class subjects, optional object markers, and supported extensions.
Analysis supports those finite constructions and simple `ku + reviewed verb stem` infinitives.
Infinitive generation and explicit negative/object/reflexive infinitive constructions are missing.

Recent work established these safeguards:

- Lexicon-aware segmentation preserves stems whose endings resemble extensions.
- Multiple legitimate lexical and object-marker readings remain available with deterministic ranking and bounds.
- Reversive and repetitive extensions have separate semantics and source-backed vowel handling.
- Generator and analyzer share a conservative extension-sequence policy, explicitly documented as a product boundary rather than universal grammar.
- Unverified causative `dz`/`ts` and short-reversive derivations are refused in generation and excluded from inferred analyses.
- Independently published derived lemmas remain accessible as their own lexical entries, without invented derivational relationships.
- Invalid request types/styles produce structured errors rather than HTTP 500.

Do not bypass these rules through the new infinitive paths.
Do not confuse a reviewed base lemma with evidence for an arbitrary derivation.

## Read these files

- `shona_api/morphology/services.py` and `views.py`
- `tests/test_morphology_api.py`, `tests/test_morphology_verb_extensions.py`, and `tests/test_morphology_rules_version.py`
- `docs/morphology/rules/README.md` and the infinitive/extension cards
- `docs/morphology/generate_endpoint.md` and `docs/developer_quickstart.md`
- `shona_api/lexicon/views.py` for search morphology enrichment, and relevant search tests
- `shona_api/api_docs/spec.py` and the OpenAPI generation command/tests
- `shona_api/releases/services.py` for setup/version messaging
- `docs/morphology/completeness-assessment-2026-09-08.md`, including the dated status update

The earlier assessment and handoffs contain historical failures; the current tests/code and latest status are the baseline.
Use `key_documents/prd_v5.md` for product intent, not linguistic authority.

## Source evidence already located

The local `key_documents/fortune_grammatical_constructions.pdf` is *Shona Grammatical Constructions, Volume 1*, third edition 1985.
Inspect section 3.3.18, Noun Class 15, especially PDF pages 90-91, printed pages 78-79, and adjacent context.
The supervisor previously located these examples there:

- `kuzvitora`: object-marked infinitive
- `kuzviziva`: reflexive infinitive
- `kusaziva`: negative infinitive
- `kusazviziva`: combined negative and object-marked construction
- Simple `ku` infinitives and their class-15 nominal behaviour

The text distinguishes object and reflexive prefixes even when they share the surface `zvi`.
It also notes divergent stems such as `-ti` and `-nzi`, so blindly assuming every lemma ends in `a` is unsafe.
The page mentions further formatives; these do not automatically become part of this assignment.

Validate examples directly against the PDF, including visual inspection where notation or layout matters.
Use the local Hannan dictionary and FSI material for relevant attested lexical examples and corroboration.
Record exact locators and distinguish source-attested examples from constructed combinations.
Do not invent source pages or human review decisions, commit source PDFs, or copy long source passages into artifacts.

## Required product result

1. Generate ordinary positive infinitives from eligible lexical verb stems.
2. Analyze and generate negative infinitives using source-supported negation and ordering.
3. Analyze and generate infinitives containing one supported object concord.
4. Analyze and generate source-supported reflexive infinitives, with reflexive meaning represented distinctly from object agreement.
5. Support source-justified combinations with negation and the existing permitted extension operations, preserving their evidence and sequence restrictions.
6. Expose the richer analyses through existing search enrichment and document the new generation contract accurately.

Keep this bounded to single-token constructions justified by available evidence.
Defer progressive/exclusive formatives, multiword complements, finite past/future, new moods, nominal plural generation, tone generation, new extension families and batch endpoints.
If an exceptional stem or combination cannot be justified, reject it clearly and document the boundary rather than fabricate a surface.

## Public request/response design

Use the existing `/v1/generate` endpoint with a distinct `features.generation_type: "infinitive"` branch.
Use `polarity: "positive" | "negative"` and reuse the existing structured `object` feature where semantically appropriate.
Represent reflexivity explicitly, for example `reflexive: true`; document the exact contract and defaults.
Do not require a finite subject or tense marker for infinitive generation.
Reject conflicting finite-only features, invalid types, and unsupported object/reflexive combinations instead of ignoring them.
Unless the source establishes otherwise, limit this slice to either one object marker or reflexivity in a construction; do not invent double-object or reflexive-plus-object rules.

Illustrative request, subject to source validation of the lexical fixture:

```json
{
  "lemma_public_id": "<public ID of a reviewed -ziva lemma>",
  "features": {
    "generation_type": "infinitive",
    "polarity": "negative"
  }
}
```

The intended supported example is `kusaziva`.
Keep the existing v1 envelope and valid finite-generation request shapes intact.
Use the existing analysis-list design for ambiguity; a `zvi` object interpretation must not silently overwrite a supported reflexive interpretation.
Expose prefix, polarity, object/reflexive, stem, extension and final-vowel information honestly, including null/not-applicable slots where appropriate.
Do not make an incompatible reinterpretation of an existing finite field merely to avoid adding a necessary field for infinitives.

Before editing, briefly state your chosen additive request/response design and evidence boundary, then implement it.
This is not a request to stop for approval of ordinary API design choices within the stated direction.

## Engineering requirements

Start by demonstrating the currently missing behaviours through authenticated routed API tests with isolated fixtures.
Share lexical resolution, evidence gating, morphophonemic transformations and feature validation where appropriate so analysis and generation cannot drift.
Keep construction-specific distinctions explicit rather than forcing infinitives through the finite-present concatenation path.
Preserve exact lexical readings, legitimate prefix ambiguities and homographs; bound candidate exploration and use deterministic ordering.
Distinguish a real negative/object/reflexive construction from a lexical stem that happens to begin with the same letters.
Do not return an unsupported derivation merely because an exact lexical candidate was excluded or missing.

Treat the new grammar behaviour as a rule-set change under the existing version policy.
Use the next explicit implementation version, expected to be `morphology-rules-v4` if v3 is still current, and update activation documentation, relevant rule cards, fixtures and callers consistently.
Never relabel rules silently or alter the user's live release records as a shortcut.
Validate mismatch handling on analyze, generate and search.
Keep the underlying source evidence version/history understandable when existing extension rules remain unchanged.

Update the OpenAPI source, regenerate `docs/openapi.json` through its owning command, and update developer examples and morphology coverage notes.
Do not hand-edit generated artifacts.
Do not introduce infrastructure changes, bulk corpus mutations, or a generic grammar framework rewrite.

## Acceptance evidence

- Source-backed positive and negative infinitive examples work through both public endpoints.
- Object and reflexive examples retain the correct features; shared-surface ambiguity is preserved when supported.
- Each supported generated form recovers its originating lemma and compatible features among the analyses, including negative/object/reflexive cases and permitted extensions.
- Independent source expectations supplement round-trip tests; two matching algorithms can share the same mistake.
- Cover vowel-initial stems, ordinary consonant-initial stems, short/exceptional stems according to the declared boundary, lexical-prefix collisions, malformed payloads and unsupported combinations.
- Base-only fixtures still cannot authorize restricted derivations; independently published derived lemmas still resolve as themselves.
- Existing finite morphology, ambiguity, evidence gates, sequence policy and search tests remain valid.
- Search handles new supported infinitives, unsupported forms and rules-version mismatch coherently.
- OpenAPI and documentation describe the implemented contract, not planned capabilities.
- Run targeted tests first and then the full suite, reporting source or backend limitations honestly.

## Safe test setup

The project reads `.env` with overwrite enabled and has a reusable test-database configuration.
Do not assume a shell `DATABASE_URL` override isolates tests.
The supervisor used this explicit isolated settings approach successfully:

```powershell
@'
import sys, types
import config.settings.test as original
s = types.ModuleType('review_settings')
s.__dict__.update({k: v for k, v in vars(original).items() if k.isupper()})
s.DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
sys.modules['review_settings'] = s
import pytest
raise SystemExit(pytest.main(['--ds=review_settings', '--create-db', '-q']))
'@ | .\.venv\Scripts\python.exe -
```

For standalone Django-client checks, configure the isolated database before `django.setup()`, migrate that database and create API keys, release and lemma fixtures there.
Do not create test fixtures in the ordinary project database.

## Closeout

Return working implementation and a concise report covering supported constructions, source locators, API examples, test commands/results, changed files, version/compatibility decisions and remaining limits.
Include risk rating, review hotspots and a code/configuration rollback approach.
Do not claim morphology as a whole is finished or independent linguistic accuracy certification.
If essential evidence is missing, complete independent supported work and identify the exact unresolved construction and missing source rather than inventing a rule.
