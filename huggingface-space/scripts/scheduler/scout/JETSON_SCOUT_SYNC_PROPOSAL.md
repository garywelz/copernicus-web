# Proposal: end Jetson scout wrapper drift

**Status:** implemented on the scout-wrapper-hardening PR (snapshot +
`sync_to_jetson.sh` wrapper install + `check_scout_drift.sh`). Deploy remains
attended; this file keeps the rationale.
**Context:** Live cron runs `/media/sdcard/scheduler/scout/*.py`, not the
worker/HFS checkout. On 2026-10-18 the live `scout_common.py` hash differed from
the worker tree (`a88da6c0612d` vs `5a89f07dbcf3`). `sync_to_jetson.sh` already
copies *repo → Jetson*; the reverse (Jetson → repo) and a drift check are missing.

## Goal

Make `huggingface-space/scripts/scheduler/scout/` the single source of truth, with
an explicit sync path and a CI/local check that fails when the live Jetson tree
drifts.

## Proposed steps (follow-up PR, after Gary names it)

1. **Snapshot into the repo** — copy the current Jetson live files
   (`/media/sdcard/scheduler/scout/scout_*.py`, `scout_common.py`, and any
   companion modules the cron imports) over the repo copies under
   `huggingface-space/scripts/scheduler/scout/`, after a human diff review.
   Do not edit those files on the Jetson in place.

2. **Sync step** — extend (or pair with) `sync_to_jetson.sh` so a named, gated
   deploy always pushes the repo scout package to `/media/sdcard/scheduler/scout/`
   (Python files + LF-safe wrapper install already sketched there). Document that
   HFS/`copernicus-worker` checkouts are not the cron entrypoint unless the
   symlink story is changed deliberately.

3. **Drift check** — a read-only script (or CI job with SSH) that hashes
   Jetson live `*.py` against `huggingface-space/scripts/scheduler/scout/*.py`
   and exits non-zero on mismatch. Run after every scout deploy and on a
   schedule.

## `run_scout` changes needed for failure recording

Once `acquire_arxiv_batch.py` exits non-zero on all-query failure (this PR), the
**existing** `run_scout` path already writes `scheduler_status` failure when
`rc != 0` (`scout_common.py` around the acquire subprocess check). No Jetson
edit is required for that basic signal.

Recommended follow-ups when the wrapper is brought in-repo (still not this PR):

- Parse `errors=N` from `SCOUT_STATS` (today only `fetched=` is read) so
  heartbeats can show partial failures even when exit code is 0.
- Treat “acquire exited 0 but `errors>0`” as a WARNING status if product wants
  that visible without failing the job.
- Confirm the live Jetson `scout_common` matches the reviewed repo copy before
  deploying the arXiv acquire change, so exit-code → failure wiring is the
  version we think it is.
