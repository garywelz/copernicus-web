#!/bin/bash
# Install Daily Paper Scout: 10:10 AM reminder, 10:15 AM run (America/New_York)
# On WSL: ensure cron is running (e.g. sudo service cron start). Remove old 0 7 * * * run_daily_scout if present to avoid two runs.
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
REMIND="${SCRIPT_DIR}/remind_paper_scout_coffee.sh"
RUN="${SCRIPT_DIR}/run_daily_scout.sh"
CRON_LOG="${BASE_DIR}/paper_acquisition_logs/daily_scout/cron.log"
chmod +x "$REMIND" "$RUN" 2>/dev/null || true
mkdir -p "$(dirname "$CRON_LOG")"

if crontab -l 2>/dev/null | grep -qF "remind_paper_scout_coffee.sh" && crontab -l 2>/dev/null | grep -qF "10 10"; then
  echo "NYC 10:10/10:15 block may already be installed. Check: crontab -l"
  exit 0
fi

(
  crontab -l 2>/dev/null || true
  echo ""
  echo "# Copernicus paper scout (NY 10:10 reminder / 10:15 run) — $BASE_DIR"
  echo "CRON_TZ=America/New_York"
  echo "10 10 * * * BASE_DIR=${BASE_DIR} ${REMIND} >> ${BASE_DIR}/paper_acquisition_logs/daily_scout/reminder_coffee.log 2>&1"
  echo "15 10 * * * cd ${BASE_DIR} && ${RUN} >> ${CRON_LOG} 2>&1"
) | crontab -

echo ""
echo "Installed (America/New_York):"
echo "  10:10 — coffee-break reminder (Windows message box from WSL when possible)"
echo "  10:15 — run_daily_scout.sh (~1,000 papers/day with current config)"
echo "  Main log: $CRON_LOG"
echo ""
echo "If you also have the old 07:00 UTC job, remove it: crontab -e  (delete that line)"
echo ""
crontab -l | tail -25
