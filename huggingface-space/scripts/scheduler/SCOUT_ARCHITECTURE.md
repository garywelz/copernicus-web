# Copernicus Paper Scout — Production Architecture

Last updated: 2026-06-30

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
10:30  scout_ingest.sh
20:00  scout_pubmed.py pm
20:05  scout_biorxiv.py pm
20:10  scout_arxiv.py pm
20:15  scout_ingest.sh
```

Logs: `/media/sdcard/logs/scout_*_{am,pm}.log` and per-run logs under `paper_acquisition_logs/daily_scout/`.

## Source of truth vs live deployment

| Location | Role |
|----------|------|
| `huggingface-space/scripts/scheduler/scout/` | **Git source of truth** (version controlled) |
| `/media/sdcard/scheduler/scout/` | **Live production copy** on Jetson — outside git |

After changing files in the repo, **sync to the Jetson**:

```bash
bash huggingface-space/scripts/scheduler/scout/sync_to_jetson.sh
```

Or manually:

```bash
scp huggingface-space/scripts/scheduler/scout/*.py gary@192.168.1.222:/media/sdcard/scheduler/scout/
ssh gary@192.168.1.222 "rm -rf /media/sdcard/scheduler/scout/__pycache__"
```

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
