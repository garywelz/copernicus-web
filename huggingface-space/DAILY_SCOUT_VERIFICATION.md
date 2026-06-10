# Daily Paper Scout — Verification (Track A)

**Last verified:** 2026-02-20 (repo paths)

## Status: Operational

| Check | Result |
|--------|--------|
| **Cron** | Installed: `0 7 * * *` (07:00 UTC daily ≈ 2:00 AM EST) |
| **Script** | `scripts/acquire_papers/run_daily_scout.sh` |
| **Cron log** | `paper_acquisition_logs/daily_scout/cron.log` |
| **Per-source logs** | `paper_acquisition_logs/daily_scout/{pubmed,arxiv,nasa_ads}_YYYYMMDD.log` |
| **Summary JSON** | `paper_acquisition_logs/daily_scout/summary_YYYYMMDD.json` |
| **PubMed** | Running successfully (e.g. 200 recent papers / run) |
| **arXiv** | Running successfully |
| **NASA ADS** | Runner **implemented** in `daily_scout_runner.py` (calls `acquire_nasa_ads_batch.py`) |

## Config note — NASA ADS

`daily_scout_config.json` has **`nasa_ads.enabled`: `false`** so the daily job stays **green** until you confirm:

- Secret `NASA_ADS_API_TOKEN` in project `regal-scholar-453620-r7`, **or**  
- `export NASA_ADS_API_TOKEN=...` on the machine that runs cron  

Then test:

```bash
cd /home/gdubs/copernicus-web-public/huggingface-space
source paper_acquisition_venv/bin/activate  # if you use venv
python3 scripts/acquire_papers/acquire_nasa_ads_batch.py --test
```

If that succeeds, set `"enabled": true` for `nasa_ads` in `daily_scout_config.json`.

## Code fixes applied (2026-02-20)

1. **`run_nasa_ads_recent()`** — Daily Scout now runs NASA ADS the same way as PubMed/arXiv (no more stub).
2. **`results['success']`** — Set after all sources: **true** only if **every** source succeeded (matches exit code and summary JSON).
3. **Exit code** — Process exits with **1** if any source failed (so schedulers can alert).

## Manual test (full scout)

```bash
cd /home/gdubs/copernicus-web-public/huggingface-space
bash scripts/acquire_papers/run_daily_scout.sh
```

Single source:

```bash
python3 scripts/acquire_papers/daily_scout_runner.py --source pubmed
```

## Progress counts

```bash
bash scripts/acquire_papers/check_progress.sh
```

Note: `check_progress.sh` tail only lists `paper_acquisition_logs/*.log` at the top level; Daily Scout details live under `paper_acquisition_logs/daily_scout/`. Use `tail` on `cron.log` or the dated logs there.

## Related

- `AGENT_TASK_ORGANIZATION.md` — full Knowledge Engine agent plan  
- `scripts/acquire_papers/install_daily_scout_cron.sh` — (re)install cron  

---

*CopernicusAI Knowledge Engine*
