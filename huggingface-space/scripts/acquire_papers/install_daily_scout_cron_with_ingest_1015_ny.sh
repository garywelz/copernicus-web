#!/usr/bin/env bash
# Installs 10:10 reminder + 10:15 run_daily_scout_with_ingest (America/New_York).
# Removes old 10:10/10:15 Copernicus scout lines that call run_daily_scout.sh, then appends the new block.
# Backup first:  crontab -l > ~/crontab.bak
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
REMIND="${SCRIPT_DIR}/remind_paper_scout_coffee.sh"
RUN="${SCRIPT_DIR}/run_daily_scout_with_ingest.sh"
CRON_LOG="${BASE_DIR}/paper_acquisition_logs/daily_scout/cron.log"
chmod +x "$REMIND" "$RUN" "$SCRIPT_DIR/run_daily_scout.sh" "${BASE_DIR}/scripts/ingest_metadata_to_firestore.sh" 2>/dev/null || true
mkdir -p "$(dirname "$CRON_LOG")"

if crontab -l 2>/dev/null | grep -qF "run_daily_scout_with_ingest.sh"; then
  echo "run_daily_scout_with_ingest.sh already in crontab. Nothing to do."
  crontab -l | grep -E '10 10|15 10|CRON_TZ' || true
  exit 0
fi

FILTERED="$(mktemp)"
crontab -l 2>/dev/null | grep -vF "remind_paper_scout_coffee.sh" \
  | grep -vF "run_daily_scout.sh" \
  | grep -v "Copernicus paper scout (NY" \
  | grep -v "Copernicus paper scout + Firestore" || true > "$FILTERED"

# If user had only run_daily_scout.sh on the 10:15 line, it's removed. Re-append block:
{
  cat "$FILTERED"
  echo ""
  echo "# Copernicus paper scout + Firestore ingest (NY 10:10 / 10:15) — $BASE_DIR"
  echo "CRON_TZ=America/New_York"
  echo "10 10 * * * BASE_DIR=${BASE_DIR} ${REMIND} >> ${BASE_DIR}/paper_acquisition_logs/daily_scout/reminder_coffee.log 2>&1"
  echo "15 10 * * * ${RUN} >> ${CRON_LOG} 2>&1"
} | crontab -

rm -f "$FILTERED"
echo ""
echo "Installed (America/New_York):"
echo "  10:10 — coffee-break reminder"
echo "  10:15 — run_daily_scout_with_ingest.sh (scout, then Firestore ingest)"
echo "  Scout log: $CRON_LOG"
echo "  Ingest log: ${BASE_DIR}/paper_acquisition_logs/daily_scout/ingest.log"
echo ""
crontab -l | tail -30
