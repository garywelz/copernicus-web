# Quick Start: Ralph Wiggum Daily Paper Scout

## Simple Setup (5 Minutes)

### Step 1: Test the Script Manually

```bash
cd /home/gdubs/copernicus-web-public/huggingface-space
source paper_acquisition_venv/bin/activate
python3 scripts/acquire_papers/daily_scout_runner.py --source pubmed
```

This will collect ~100 recent papers from PubMed as a test.

### Step 2: Create Ralph Wiggum Loop

**Ralph Wiggum Action:**
1. **Type:** System Command / Execute Script
2. **Command:**
   ```bash
   /home/gdubs/copernicus-web-public/huggingface-space/scripts/acquire_papers/run_daily_scout.sh
   ```
   
   **OR** if using terminal/command:
   ```bash
   cd /home/gdubs/copernicus-web-public/huggingface-space && bash scripts/acquire_papers/run_daily_scout.sh
   ```

3. **Wait:** Allow 30-60 minutes for script to complete
4. **Schedule:** Set to run daily (e.g., 2:00 AM UTC)

### Step 3: Monitor

Check logs:
```bash
tail -f /home/gdubs/copernicus-web-public/huggingface-space/paper_acquisition_logs/daily_scout/*.log
```

### What It Does

- **Daily:** Collects ~100-200 recent papers per source
- **Sources:** PubMed, arXiv (NASA ADS coming soon)
- **Focus:** Recent papers (2024-2025) from all disciplines
- **Pace:** Slow, API-friendly rate limiting
- **Output:** Papers saved to `metadata-database/papers/`

### Customization

Edit `daily_scout_config.json`:
- Change `papers_per_source_per_day` (default: 100)
- Enable/disable sources
- Adjust priorities

### Full Documentation

See `RALPH_WIGGUM_DAILY_SCOUT_SETUP.md` for detailed instructions.
