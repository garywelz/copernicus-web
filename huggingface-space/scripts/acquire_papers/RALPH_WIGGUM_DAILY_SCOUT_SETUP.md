# Ralph Wiggum Daily Paper Scout Setup Guide

## Overview

This guide helps you set up a **Ralph Wiggum automation loop** that runs daily to collect recent, popular papers from top journals across all disciplines. The loop acts as your "daily scout" - automatically gathering the latest, trend-catching papers to keep your Knowledge Engine timely and current.

## What the Daily Scout Does

- ✅ Runs **daily** at a scheduled time (e.g., 2:00 AM UTC)
- ✅ Collects **recent papers** (last 7-30 days) from top journals
- ✅ Focuses on **popular, high-impact** papers
- ✅ Covers **all major disciplines** (Biology, Physics, CS, Math, Astronomy)
- ✅ Uses **multiple sources** (PubMed, arXiv, NASA ADS)
- ✅ Runs at a **slow, consistent pace** (respects API rate limits)
- ✅ **Logs all activity** for monitoring and debugging

## Files Created

1. **`daily_scout_config.json`** - Configuration file with queries and schedule
2. **`daily_scout_runner.py`** - Python script that runs the acquisition
3. **This guide** - Setup instructions

## Ralph Wiggum Loop Setup Steps

### Step 1: Install and Open Ralph Wiggum

1. Install the Ralph Wiggum Chrome extension (if not already installed)
2. Open Ralph Wiggum (usually accessible from Chrome extensions menu)
3. Create a new loop/workflow

### Step 2: Create the Loop Structure

Your Ralph Wiggum loop should have these actions:

```
LOOP START: Daily Paper Scout
├── Action 1: Navigate to terminal/command prompt (or use system command)
├── Action 2: Change directory to project folder
├── Action 3: Activate Python virtual environment (if needed)
├── Action 4: Run daily_scout_runner.py script
├── Action 5: Wait for script completion
├── Action 6: Check for errors (optional)
├── Action 7: Log completion status
└── LOOP END: Schedule next run (24 hours)
```

### Step 3: Configure the Loop Actions

#### Action 1: System Command / Terminal
**Type:** System Command or Terminal
**Command:**
```bash
cd /home/gdubs/copernicus-web-public/huggingface-space && source paper_acquisition_venv/bin/activate && python3 scripts/acquire_papers/daily_scout_runner.py --config scripts/acquire_papers/daily_scout_config.json
```

**OR** if Ralph Wiggum works better with a script file:

Create a wrapper script: `run_daily_scout.sh`
```bash
#!/bin/bash
cd /home/gdubs/copernicus-web-public/huggingface-space
source paper_acquisition_venv/bin/activate
python3 scripts/acquire_papers/daily_scout_runner.py --config scripts/acquire_papers/daily_scout_config.json
```

Then call: `bash /home/gdubs/copernicus-web-public/huggingface-space/run_daily_scout.sh`

#### Action 2: Wait/Sleep
**Duration:** Wait for script to complete (may take 30-60 minutes depending on queries)
**Or:** Set up error handling to check completion status

#### Action 3: Schedule Next Run
**Type:** Schedule/Timer
**Frequency:** Daily
**Time:** 02:00 (2:00 AM UTC) - adjust to your preference
**Note:** Some Ralph Wiggum versions may require external scheduling (cron, system scheduler)

### Step 4: Test the Loop Manually First

**Before scheduling:**
1. Run the loop manually once to verify it works
2. Check the logs in `paper_acquisition_logs/daily_scout/`
3. Verify papers are being collected
4. Check for any errors

**Test command:**
```bash
cd /home/gdubs/copernicus-web-public/huggingface-space
source paper_acquisition_venv/bin/activate
python3 scripts/acquire_papers/daily_scout_runner.py --source pubmed
```

### Step 5: Configure Scheduling

**Option A: Ralph Wiggum Built-in Scheduler**
- Use Ralph Wiggum's scheduling feature if available
- Set to run daily at your chosen time (e.g., 2:00 AM UTC)

**Option B: System Cron (Linux/Mac)**
If Ralph Wiggum doesn't have scheduling, use cron:
```bash
crontab -e
```

Add line:
```
0 2 * * * cd /home/gdubs/copernicus-web-public/huggingface-space && /home/gdubs/copernicus-web-public/huggingface-space/paper_acquisition_venv/bin/python3 scripts/acquire_papers/daily_scout_runner.py --config scripts/acquire_papers/daily_scout_config.json >> paper_acquisition_logs/daily_scout/cron.log 2>&1
```

**Option C: System Scheduler (Windows Task Scheduler)**
- Create a scheduled task that runs the script daily

### Step 6: Monitor and Adjust

**Monitor:**
- Check logs daily: `paper_acquisition_logs/daily_scout/`
- Review summary files: `summary_YYYYMMDD.json`
- Check for errors or failures

**Adjust:**
- Modify `daily_scout_config.json` to change:
  - Queries (add/remove journal searches)
  - Paper limits (increase/decrease daily collection)
  - Sources (enable/disable PubMed, arXiv, NASA ADS)
  - Schedule timing

## Configuration Customization

### Editing Queries in `daily_scout_config.json`

**PubMed Queries:**
```json
{
  "name": "Recent Nature Papers",
  "query": "(Nature[JOUR] OR Nature Medicine[JOUR]) AND (\"2025\"[PDAT])",
  "max_results": 50
}
```

**arXiv Queries:**
```json
{
  "name": "Recent Physics",
  "categories": ["physics:astro-ph", "physics:cond-mat"],
  "max_results": 50,
  "days_back": 7
}
```

### Adding More Journals/Sources

Add entries to the `queries` array in the config file:
- **PubMed:** Add journal names using `[JOUR]` tag
- **arXiv:** Add category codes (e.g., `cs.AI`, `physics:quant-ph`)
- **NASA ADS:** Add query strings

## Expected Results

**Daily Collection:**
- ~200-500 papers per day (configurable)
- Distributed across all disciplines
- Recent papers (last 7-30 days)
- From top journals and high-impact sources

**Weekly Collection:**
- ~1,400-3,500 papers per week
- Growing database of recent, topical papers
- Trend-catching, timely content for reviewers

## Troubleshooting

### Script Fails to Run
- Check Python virtual environment is activated
- Verify script paths are correct
- Check file permissions
- Review error logs

### No Papers Collected
- Verify API keys/tokens are set (PubMed API key, NASA ADS token)
- Check network connectivity
- Review query syntax in config file
- Check source-specific logs

### Rate Limiting Errors
- Increase delays between queries
- Reduce `max_results` per query
- Add more delay between sources
- Consider adding API keys for higher limits

### Ralph Wiggum Not Running
- Verify Ralph Wiggum extension is enabled
- Check browser is open (if required)
- Verify scheduling is set correctly
- Consider using system cron/scheduler instead

## Next Steps

1. ✅ Review and customize `daily_scout_config.json`
2. ✅ Test the script manually: `python3 daily_scout_runner.py --source pubmed`
3. ✅ Set up Ralph Wiggum loop with the script command
4. ✅ Test loop manually once
5. ✅ Configure daily scheduling
6. ✅ Monitor logs for first few days
7. ✅ Adjust configuration based on results

## Support

- Check logs: `paper_acquisition_logs/daily_scout/`
- Review script output for errors
- Adjust configuration as needed
- Scale up gradually (start with fewer queries, increase over time)
