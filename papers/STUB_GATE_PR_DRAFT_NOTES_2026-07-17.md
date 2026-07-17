# Stub gate notes — observe-first + minimal identity ids

**Landed:** `copernicus-web` `940970a4b` on `main` (2026-07-17).  
**Not yet proven on Jetson.** See deploy probe below.

## Critical path
1. **Prove deploy** from Yoga (GCS + stub creates) — no SSH required.  
2. When SSH returns: version `scout_ingest.sh`; extend `sync_to_jetson.sh` so the ingest wrapper (+ whatever path actually runs the Python) ships with the workers.  
3. Then observe day-log hits → `enforce` → cleanup.

## Identity fingerprint (minimal core — not wide allowlist)
Hash **identity**, not record state:

- normalized title  
- first-author surname  
- year (or year from `published_date`)  
- plus doi / pmid / arxiv_id / bibcode when present  

**Excluded (mutable knowledge):** abstract, categories, sources, urls, journal_*, acquired_date, and any future scout metadata.

Title normalized (case, whitespace, trailing punctuation, crude LaTeX strip) like DOI.

No list-order trap: fingerprint holds scalars only (first surname, not full authors list).

**Observe-mode side effect:** empty/Untitled stubs collapse onto a small set of last-resort ids → `--skip-existing` collapses remints even before enforce. Empty-title stubs fingerprint as `{}`; literal `"Untitled"` as `{"title":"untitled"}` — two collapse ids, both bounded.

The **~97/day prediction is `gate_hits_day_log`** (line count of the shared daily reject JSONL across AM+PM), not this-run `gate_hits` and not new Firestore docs. “0 new stubs” is not a failed observation.

## Trap notes
1. `sort_keys=True` + volatile `acquired_date` in hash → false determinism.  
2. Wide content allowlist → enrichment remints. Narrowed to identity core.  
3. Unversioned Jetson `scout_ingest.sh` → sync can be a silent no-op if it does not call the repo wrapper/Python. Same defect class as invisible `--skip-existing` failure.  
4. **`sync_to_jetson.sh` ships only `scheduler/scout/*.py`.** It does **not** ship `ingest_metadata_to_firestore.sh` or `cloud-run-backend/scripts/ingest_papers_from_metadata_json.py`. Pinning `--reject-log` / `--reject-gcs-uri` on `main` is inert until that wrapper (or a Jetson `git pull` of the full tree) reaches the executed path. GCS Signal A still works via hardcoded `_DEFAULT_REJECT_GCS_PREFIX` in Python — but only if that Python file is what runs.

## Gate
Default `--stub-gate-mode observe`; conjunctive Untitled∧no-id; full payload → local day JSONL (append) + per-run GCS object.

`ingest_metadata_to_firestore.sh` pins `--reject-log` and `--reject-gcs-uri` on `main`. Until that wrapper is on the Jetson executed path, the Python falls back to `hfs_guess` path arithmetic for the local log.

## Deploy probe (Yoga-only, after next 20:15 ET)

Old code cannot produce GCS objects under `research_data/ingest_rejects/`.
New stable ids should drive new stub creates/day to ~0 even in observe mode.

| GCS object | New stubs/day | Reading |
|---|---|---|
| appears | ~0 | New code running. Gate live; leak stopped. |
| appears | still ~97+ | New code running + **second writer** (do not dismiss). |
| absent | ~0 | Suspicious — did scout run? |
| absent | ~97+ | Old code; executed path not synced (gate Python never reached Jetson). |

**Sync-gap footnote (note, don’t shrug):** GCS object appears, but Jetson local log is at the *guessed* path (`hfs_guess` / no pinned args in process cmdline or logs) rather than the pinned wrapper path → new Python ran, wrapper did not. Confirms `sync_to_jetson.sh` / checkout gap; Signal A still valid.

Checks (ADC on Yoga):
- `gsutil ls gs://regal-scholar-453620-r7-podcast-storage/research_data/ingest_rejects/`
- Count Untitled stubs with `created_at` on the calendar day after both cron slots
- When SSH returns: confirm whether `ingest_papers_from_metadata_json.py` is on the executed path at all (not in `sync_to_jetson.sh`’s `*.py` worker set)

## Tests
`python cloud-run-backend/scripts/test_ingest_papers_id_stability.py`
- cross-process PYTHONHASHSEED  
- unexpected extra keys  
- title normalization  
- **enrichment (abstract+categories) → same id**  
- stub collapse  
- predicate conjunctive  
