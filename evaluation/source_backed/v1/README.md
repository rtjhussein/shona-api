# Source-backed morphology evaluation — reproducible runs

Frozen corpus: `evaluation/source_backed/v1/corpus.json`
(`source-backed-eval-v1`; full SHA-256 hash inside the file).
Protocol: `docs/morphology/source-backed-evaluation-protocol.md` (plus the
2026-09-11 repair amendment at its end).
Corrections: `evaluation/source_backed/v1/CORRECTIONS.md`.
Incident record: `evaluation/source_backed/v1/INCIDENT.md`.

## One-command evaluation (isolated SQLite; never touches db/shona.sqlite3)

```console
python tools/evaluate_source_backed.py --corpus evaluation/source_backed/v1/corpus.json --out evaluation/source_backed/v1/results
```

Writes `results/results.json` (machine-readable, with metrics) and
`results/report.md` (human-readable, with code revision + dirty flag,
evaluator hash, corpus hash). Exit 1 on scored failure. Prior outputs in
`--out` archive to `--out/history/`; the v1-proposed baseline is preserved
there. Nothing under `--out` is ever deleted.

Isolation: the runner uses `config.settings.eval` with `EVAL_DB_PATH` pointing
at a fresh temporary file it owns, then asserts the live connection equals it
before migrating. `config/settings/base.py` re-reads the project `.env` with
`overwrite=True`, so `DATABASE_URL` is never consulted for evaluation. Do not
"simplify" this back to a `DATABASE_URL` export (see INCIDENT.md).

## Corpus build and validation

```console
python tools/build_source_backed_corpus.py --parts evaluation/source_backed/v1 --out evaluation/source_backed/v1/corpus.json
python tools/build_source_backed_corpus.py --check-only
```

`corpus.json` is generated from `corpus_part{1,2,3,4}.json` + `fixtures.json`
(edit the parts, never `corpus.json` directly). The builder validates the
schema (unique IDs, known flows/statuses/keys, resolvable fixtures, scored
cases carry assertions, unresolved never scored) and stamps a full SHA-256
over canonical `{version, fixtures, cases}`. Both runners re-verify hash and
schema before any request. Any expectation change needs a `CORRECTIONS.md`
entry with source evidence — never silent rewrites.

## Durable pytest gate (uses the Django test database, like the rest of suite)

```console
pytest tests/test_source_backed_evaluation.py -q
```

Covers: full frozen corpus (hash-verified), finite-boundary search parity,
all six supervisor false-pass reproductions (wrong polarity/extension,
exhaustive extras, generated-vs-fixed round trip, search lemma/reading
mismatch, report denominators, hash trust), matching semantics, corpus
integrity (tamper/unknown-keys/empty-case/determinism), and settings
isolation (subprocess proof against a decoy database path).

## Full suite

```console
python -m pytest tests/ -q
git diff --check
```

## Operational note (2026-09-10 incident; full record in INCIDENT.md)

An early runner revision relied on `DATABASE_URL` for isolation and was
overwritten by `.env`, writing one `DataRelease` (`eval-release`) and one API
key (`eval`) into `db/shona.sqlite3` and flipping the current-release flag.
Both rows were deleted and the flag restored to `2026.09.0`; the prior flag
value cannot be reconstructed from available evidence (best-supported guess:
`2026.09.0`, via creation mechanism + timestamp logic — not verified, do not
treat as verified). No eval lemmas were created in the dev database (verified
count 0). No development-database repair is applied without explicit user
authorization.
