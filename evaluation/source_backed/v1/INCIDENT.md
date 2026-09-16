# Development-database incident record (2026-09-10 evaluator runs)

No development-database writes were made during this investigation (read-only
SQLite `mode=ro` plus git/log inspection). No repair is applied in this task.
A prior-task cleanup is documented below as a known change; it is not presented
as verified.

## What is known to have changed (evidence in parentheses)

1. On 2026-09-10 ~19:00 UTC, the first standalone evaluator revision created
   `DataRelease(version="eval-release", is_current=True)` and one API key
   (`name="eval"`) in `db/shona.sqlite3`, because it trusted `DATABASE_URL`
   while `config/settings/base.py` re-reads `.env` with `overwrite=True`.
   (Direct observation of both tracebacks; row later deleted, see 4.)
2. That `save(is_current=True)` flipped whichever release was current to
   `is_current=False` via the model's queryset update. (Model code
   `shona_api/releases/models.py::save`; partial unique constraint allows at
   most one current row.)
3. A second run failed immediately on the duplicate `eval-release` version and
   wrote nothing further. (Traceback: `UNIQUE constraint failed:
   releases_datarelease.version`.)
4. In the prior task both rows were deleted (`releases` 1 row, `apikey` 1 row),
   zero eval lemmas were ever created
   (`provenance__regression_corpus="source_backed_eval_v1"` count 0), and
   `2026.09.0.is_current` was set back to True. (Bash transcripts; current
   read-only check below.)

## Current verified state (read-only check 2026-09-11)

- `releases_datarelease`: `2026.05.browser` current=0 (created/updated
  2026-05-12); `2026.09.0` ("Repro release", `morphology-rules-v2`) current=1
  (created 2026-09-08 22:55, updated 2026-09-10 19:02 by the prior-task restore).
- `api_auth_apikey`: 14 keys; none named `eval` (deleted row's prefix is not
  recoverable from the database).
- `lexicon_nounclass`: 21 rows, the standard 1–21 set (dev class 1 uses subject
  `u`); the failed run errored on the first insert (`class_number` "1"
  already present), so no noun-class row was added.
- `db/shona.sqlite3` is untracked by git (`git log -- db/shona.sqlite3` empty);
  journal mode `delete`, freelist 0. No WAL/forensic residue to mine.

## Timeline evidence for the pre-incident flag

- 2026-08-25 backups (`backups/shona-populated-20260825.sqlite3.gz`,
  `db/legacy-root-backup.sqlite3`, both read read-only from copies since
  removed): exactly one release, `2026.05.browser`, `is_current=1`.
- `2026.09.0` was created 2026-09-08 22:55 ("Repro release", rules v2). The
  in-repo command for this (`ensure_current_release`) uses `update_or_create`
  with `is_current=True`, which would have made it current at creation.
- `2026.05.browser` retains `updated_at == created_at` (2026-05-12): it was
  never `.save()`d after creation, so its flip to 0 came from another row's
  `save(is_current=True)` queryset update — i.e. the `2026.09.0` creation or
  the incident's `eval-release`. There is no third release row.
- Therefore `2026.09.0` was made current at some point before the incident.
  Whether it was *still* current at incident time rests on the absence of a
  later manual unset (a queryset-level unset leaves no timestamp; an admin
  `.save()` unset would have bumped `updated_at`, but the prior-task restore
  overwrote that timestamp — a forensic cost of the cleanup, disclosed here).

## What remains uncertain

- The exact pre-incident flag value cannot be reconstructed from available
  evidence: most likely `2026.09.0` current (mechanism + timestamp logic above),
  alternatively no current release (only via an untraceable manual unset), or a
  deleted third release (no evidence for or against).
- The deleted `eval` API key's prefix and the pre-restore `updated_at` of
  `2026.09.0` are unrecoverable.

## Proposed exact repair (requires explicit user authorization; NOT applied)

- If the user confirms `2026.09.0` ("Repro release", rules v2) was the working
  current release: no action — current state already matches (only its
  `updated_at` differs, which is cosmetically wrong but behaviorally inert).
- If the user instead wants a known-clean state: run
  `python manage.py ensure_current_release --version <V> --label <L>
  --rule-set-version morphology-rules-v6` with the release the team actually
  serves, or set the intended flag explicitly. Do not delete rows by name
  resemblance and do not flip flags on assumption.
