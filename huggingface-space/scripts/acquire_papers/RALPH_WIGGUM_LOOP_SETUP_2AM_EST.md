# Ralph Wiggum Loop Setup - 2:00 AM EST Daily

## Time Conversion
- **2:00 AM EST** = **7:00 AM UTC** (Eastern Standard Time)
- **2:00 AM EDT** = **6:00 AM UTC** (Eastern Daylight Time)
- **Note:** Cron uses UTC, so we'll use 7:00 AM UTC (EST) or set up with system timezone

## Option 1: Ralph Wiggum Extension Setup

### Step 1: Open Ralph Wiggum
1. Open Chrome/Chromium
2. Click the Ralph Wiggum extension icon
3. Create a new loop/workflow

### Step 2: Add Actions to Loop

**Action 1: System Command / Execute Script**
- **Type:** System Command / Terminal / Execute Script
- **Command:**
  ```bash
  /home/gdubs/copernicus-web-public/huggingface-space/scripts/acquire_papers/run_daily_scout.sh
  ```
- **Or Full Path:**
  ```bash
  cd /home/gdubs/copernicus-web-public/huggingface-space && bash scripts/acquire_papers/run_daily_scout.sh
  ```

**Action 2: Wait for Completion** (if needed)
- **Type:** Wait / Sleep
- **Duration:** 60 minutes (to allow script to complete)

**Action 3: Log Results** (optional)
- Check if log file was created
- Send notification if error (optional)

### Step 3: Set Schedule

**If Ralph Wiggum has scheduling:**
- **Frequency:** Daily
- **Time:** 2:00 AM EST (7:00 AM UTC)
- **Timezone:** EST/EDT (or set to UTC: 7:00 AM)

**If Ralph Wiggum doesn't have scheduling:**
- Use Option 2 (Cron) instead - it's more reliable for scheduled tasks

### Step 4: Test the Loop
1. Run the loop manually once to verify it works
2. Check logs: `paper_acquisition_logs/daily_scout/`
3. Verify papers were collected

## Option 2: System Cron Job (Recommended for Reliability)

Cron is more reliable for scheduled tasks. I'll set this up for you.

### Cron Setup Instructions

The cron job will run daily at 2:00 AM EST (7:00 AM UTC).

**To view the cron job after setup:**
```bash
crontab -l
```

**To edit the cron job:**
```bash
crontab -e
```

**Cron job entry:**
```
0 7 * * * cd /home/gdubs/copernicus-web-public/huggingface-space && /home/gdubs/copernicus-web-public/huggingface-space/scripts/acquire_papers/run_daily_scout.sh >> /home/gdubs/copernicus-web-public/huggingface-space/paper_acquisition_logs/daily_scout/cron.log 2>&1
```

**For EDT (Daylight Saving Time - 6:00 AM UTC):**
```
0 6 * * * cd /home/gdubs/copernicus-web-public/huggingface-space && /home/gdubs/copernicus-web-public/huggingface-space/scripts/acquire_papers/run_daily_scout.sh >> /home/gdubs/copernicus-web-public/huggingface-space/paper_acquisition_logs/daily_scout/cron.log 2>&1
```

## Recommended Approach: Use Cron (More Reliable)

Browser extensions like Ralph Wiggum are great for interactive automation but cron is better for scheduled tasks because:
- ✅ Runs even if browser is closed
- ✅ More reliable scheduling
- ✅ Better logging
- ✅ System-level, always available
- ✅ Works across reboots

**You can still use Ralph Wiggum for:**
- Manual triggers
- Testing the script
- Monitoring/logging in browser
- Interactive workflows

## Verification

After setup (either option), verify it's working:

1. **Check logs:**
   ```bash
   ls -lh /home/gdubs/copernicus-web-public/huggingface-space/paper_acquisition_logs/daily_scout/
   ```

2. **Check cron status:**
   ```bash
   systemctl status cron  # On systemd systems
   service cron status    # On older systems
   ```

3. **Manually test the script:**
   ```bash
   /home/gdubs/copernicus-web-public/huggingface-space/scripts/acquire_papers/run_daily_scout.sh
   ```

## Next Steps

1. ✅ Choose Option 1 (Ralph Wiggum) or Option 2 (Cron)
2. ✅ Set up the schedule
3. ✅ Test manually first
4. ✅ Monitor logs for first few days
5. ✅ Adjust as needed
