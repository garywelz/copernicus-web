# Daily Paper Scout — 1,000/day, 10:15 AM Eastern, coffee reminder 10:10

**Config (limits):** `scripts/acquire_papers/daily_scout_config.json`  
- `total_papers_per_day`: **1000**  
- `papers_per_source_per_day`: **500** (PubMed + arXiv ≈ 500 each, ~1,000 total when both are enabled)

**On-screen reminder in Cursor?**  
Cursor does not expose a scheduled in-editor notification. The setup uses a **10:10 AM Eastern** job that, on **WSL + Windows**, shows a **Windows message box** in front of your session (so you can see it while using Cursor in Windows). If that fails, it falls back to `notify-send` (Linux) or a log line.

**Install the schedule (WSL / Linux with cron):**

```bash
cd /home/gdubs/copernicus-web-public/huggingface-space
chmod +x scripts/acquire_papers/install_daily_scout_cron_1015_ny.sh
bash scripts/acquire_papers/install_daily_scout_cron_1015_ny.sh
```

**Check:**

```bash
crontab -l
# Expect CRON_TZ=America/New_York and 10:10 + 15 10 lines
```

**WSL note:** start the cron service if needed: `sudo service cron start` (and ensure WSL doesn’t go fully idle-suspended during 10:10–10:15 if you need absolute reliability—often fine when you are at the machine).

**Remove duplicate runs:** if you previously installed the **07:00 UTC** `run_daily_scout` line, open `crontab -e` and **delete** that line so the job runs **once** per day (at 10:15 Eastern).

**Files:**

| Role | Path |
|------|------|
| Reminder | `scripts/acquire_papers/remind_paper_scout_coffee.sh` |
| Daily run | `scripts/acquire_papers/run_daily_scout.sh` |
| Installer | `scripts/acquire_papers/install_daily_scout_cron_1015_ny.sh` |
| Reminder log | `paper_acquisition_logs/daily_scout/reminder_coffee.log` |

---

*See also: `DAILY_PAPER_AGENT_RALPH_WIGGUM.md`, `DAILY_SCOUT_VERIFICATION.md`.*
