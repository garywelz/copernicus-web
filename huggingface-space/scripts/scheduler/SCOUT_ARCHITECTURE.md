# Copernicus Paper Scout — Production Architecture

Last updated: 2026-07-23

## Two scout paths exist

| Path | Used by cron? | Entry point |
|------|---------------|-------------|
| **Split scheduler workers** | **Yes (production)** | `/media/sdcard/scheduler/scout/scout_*.py` |
| **Monolithic runner** | No | `scripts/acquire_papers/daily_scout_runner.py` via `run_daily_scout_with_ingest.sh` |

Production cron (user `gary` on Jetson) calls the **split workers**, not `daily_scout_runner.py`.
Repo install scripts such as `install_daily_scout_cron_with_ingest_1015_ny.sh` describe the monolithic path and are **not** what is live today.

## Production cron schedule (America/New_York)

```
10:10  remind_paper_scout_coffee.sh
10:15  scout_pubmed.py am
10:20  scout_biorxiv.py am
10:25  scout_arxiv.py am
10:30  scout_ingest.sh          → on success: run_post_ingest_hooks.sh
                                 (status publish, then MASTER_TODO;
                                  future: embed --auto before publish)
20:00  scout_pubmed.py pm
20:05  scout_biorxiv.py pm
20:10  scout_arxiv.py pm
20:15  scout_ingest.sh          → same post-ingest chain
                                 (PM also publishes status + MASTER_TODO)
```

Standalone 10:40 status-publish and 10:45 MASTER_TODO cron lines are **removed
only after the first chained AM cycle validates** (see cutover below). Until then
they may double-publish: 10:40 writes mid-ingest numbers; ~11:35 chain overwrites
with correct ones. Final GCS state is right because publish is a regeneration.

**MASTER_TODO twice daily:** the chain runs both hooks after AM and PM. Safe —
`build_master_todo.py` overwrites fixed GCS objects (`GLMP_MASTER_TODO.md`,
`GLMP_STATUS.html`) and local debug copies; the only append-only side effect is
one line in `master_todo_cron.log` per run. No versioned/duplicate GCS artifacts.

**Expectation shift (not a regression):** published `knowledge-engine-status.json`
moves from **10:40 ET** to **ingest-completion** (~11:35 ET after AM; similarly
after PM). Until the chain finishes, the GCS object is the prior cycle's numbers
(or, during cutover, the 10:40 stale write until the chain overwrites).
Accurate-later beats wrong-on-time.

**Locks:** `/tmp/scout_{source}_{run_type}.lock` is held only by the Python scout
workers (`scout_common.acquire_lock` / `release_lock` in a `finally`). Production
`scout_ingest.sh` does **not** take those locks, so lengthening the wrapper with
hooks does not extend any lock hold. AM vs PM use distinct lock names; workers
finish and release before the 10:30 / 20:15 ingest slots.

**Paths:** live wrapper uses `HFS=/home/gdubs/copernicus-web-public/huggingface-space`
(repo owned by user `gary` under a legacy home directory name) and credentials
under `/home/gary/.config/copernicus/`. Confirmed working on Jetson 2026-07-23.

Logs: `/media/sdcard/logs/scout_*_{am,pm}.log` and per-run logs under `paper_acquisition_logs/daily_scout/`.
Ingest stdout/stderr → `/media/sdcard/logs/scout_ingest.log` (wrapper redirect);
cron also appends wrapper chatter to `paper_acquisition_logs/daily_scout/ingest.log`.
Hook bodies keep prior destinations: `status_publish_cron.log`, `master_todo_cron.log`.

### Cutover (ordering fix) — load-bearing order

1. Commit + push on Yoga.
2. **`git pull` on Jetson first** so `run_post_ingest_hooks.sh` exists under HFS.
   If the new wrapper is synced *before* the pull, every ingest ends at **rc 127**
   (hooks script missing) and nothing publishes — worse than the mid-ingest defect.
3. `sync_to_jetson.sh` to ship `scout_ingest.sh` into `/media/sdcard/scheduler/scout/`.
4. **Leave** the standalone 10:40 / 10:45 cron lines in place for the first AM cycle.
5. Validate: chain fired after ingest; status/MASTER_TODO logs show START/OK near
   ingest completion (~11:35); GCS status reflects post-ingest counts.
6. **Then** remove the two standalone cron lines (verbatim restore copy in Rollback).

Partial ship of (3) before (2) is the dangerous failure mode. Keeping cron through
(5) turns cutover into a step: a failed chain still gets the clocked publish.
### Rollback (ordering fix)

1. Revert the wrapper/hooks commit (or restore the prior one-line `exec` wrapper
   on Jetson via sync of an older tree).
2. Re-add the two crontab lines below. **Crontab is not version-controlled** — step 2
   is the only part of this change with no git record. The SUPERSEDED markers on
   `install_cron_1040_status_publish_ny.sh` / `install_cron_1045_status_publish_ny.sh`
   are the install-script trace; the verbatim lines to restore are:

```cron
# GLMP MASTER_TODO assembler — 10:45 AM ET (after scout ingest)
45 10 * * * /media/sdcard/venvs/master-todo-cron/bin/python /media/sdcard/glmp-cron/build_master_todo.py >> /media/sdcard/logs/master_todo_cron.log 2>&1

# Copernicus — publish knowledge-engine-status.json to GCS (after AM ingest, before MASTER_TODO) — /home/gdubs/copernicus-web-public/huggingface-space
40 10 * * * . /home/gary/.config/copernicus/env && GOOGLE_APPLICATION_CREDENTIALS=/home/gary/.config/copernicus/gcp-sa.json cd /home/gdubs/copernicus-web-public/huggingface-space && /home/gdubs/copernicus-web-public/huggingface-space/scripts/publish_knowledge_engine_status.sh >> /home/gdubs/copernicus-web-public/huggingface-space/paper_acquisition_logs/daily_scout/status_publish_cron.log 2>&1
```

## Source of truth vs live deployment

| Location | Role |
|----------|------|
| `huggingface-space/scripts/scheduler/scout/` | **Git source of truth** for scout workers (`*.py`) + `scout_ingest.sh` |
| `/media/sdcard/scheduler/scout/` | **Live production copy** on Jetson — outside git |
| `scripts/run_post_ingest_hooks.sh` | Ordered post-ingest chain (status, MASTER_TODO; embed slot reserved) |

`sync_to_jetson.sh` ships `scheduler/scout/*.py` **and** `scout_ingest.sh`.
It does **not** ship (those reach production via `git pull` of the Jetson tree):

- `scripts/ingest_metadata_to_firestore.sh`
- `scripts/run_post_ingest_hooks.sh` / `scripts/publish_knowledge_engine_status.sh`
- `cloud-run-backend/scripts/ingest_papers_from_metadata_json.py`

**Deploy order for the ordering fix:** see **Cutover** above. Short form:
(1) push, (2) Jetson `git pull` (hooks under HFS — required *before* wrapper sync
or ingest fails rc 127), (3) `sync_to_jetson.sh`, (4) keep 10:40/10:45 until AM
validates, (5) then remove those cron lines.

After changing scout worker files in the repo, **sync to the Jetson**:

```bash
bash huggingface-space/scripts/scheduler/scout/sync_to_jetson.sh
```

Or manually:

```bash
scp huggingface-space/scripts/scheduler/scout/*.py gary@192.168.1.222:/media/sdcard/scheduler/scout/
ssh gary@192.168.1.222 "rm -rf /media/sdcard/scheduler/scout/__pycache__"
```

**Deploy proof (no SSH):** after AM+PM ingest, reject objects under
`gs://…/research_data/ingest_rejects/` prove new ingest code ran; stub creates/day
should fall to ~0 under stable ids even in observe mode. See
`papers/STUB_GATE_PR_DRAFT_NOTES_2026-07-17.md`.

## How config queries reach batch scripts

1. Cron invokes `scout_pubmed.py` / `scout_biorxiv.py` / `scout_arxiv.py`
2. Each calls `scout_common.run_scout()`
3. `scout_common.py` reads `scripts/acquire_papers/daily_scout_config.json` (v2.0)
4. Writes JSON to `scripts/acquire_papers/.scout_query_cache/`
5. Invokes `acquire_*_batch.py` with `--config-queries` and weighted volume targets

Shared batch scripts live in `scripts/acquire_papers/` and are pulled via the main `copernicus-web` repo on Jetson.

## GLMP PubMed supplement (overlap note)

`scout_pubmed.py` runs `glmp_pubmed_supplement.py` **after** the main PubMed acquire by default (`--glmp-queries` on). That supplement uses 15 hardcoded terms from `query_terms.py`, which overlap conceptually with v2.0 `pubmed_queries` in config.

To skip the supplement: pass `--no-glmp-queries` to `scout_pubmed.py`, or change the cron line. **Do not disable until one production cycle confirms v2.0 config queries are working.**

## Related files

- Config: `scripts/acquire_papers/daily_scout_config.json`
- Batch scripts: `scripts/acquire_papers/acquire_*_batch.py`
- Ingest: `scripts/ingest_metadata_to_firestore.sh` (via `scout_ingest.sh` on Jetson)
- Monolithic runner (dev/manual): `scripts/acquire_papers/daily_scout_runner.py`
