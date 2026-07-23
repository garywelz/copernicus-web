#!/bin/bash
# SUPERSEDED — do not install on Jetson once scout_ingest.sh chains
# run_post_ingest_hooks.sh. Historical reference only (old 10:45 clock slot).
#
# Append a 10:45 AM (America/New_York) cron job: publish knowledge-engine-status.json to GCS.
# Requires the same CRON_TZ=America/New_York line in crontab as the 10:10/10:15 block (vixie: applies to following lines).
# If you have no CRON_TZ, add one line: CRON_TZ=America/New_York  before the 10:45 line (see crontab -e).

set -e
BASE="/home/gdubs/copernicus-web-public/huggingface-space"
PUBLISH="${BASE}/scripts/publish_knowledge_engine_status.sh"
LOG="${BASE}/paper_acquisition_logs/daily_scout/status_publish_cron.log"
mkdir -p "$(dirname "$LOG")"
chmod +x "$PUBLISH" 2>/dev/null || true

if crontab -l 2>/dev/null | grep -qF "publish_knowledge_engine_status.sh"; then
  echo "A cron line for publish_knowledge_engine_status.sh is already present:"
  crontab -l | grep -F "publish_knowledge_engine_status.sh" || true
  exit 0
fi

(
  crontab -l 2>/dev/null || true
  echo ""
  echo "# Copernicus — publish knowledge-engine-status.json to GCS (45 min after paper scout) — $BASE"
  echo "45 10 * * * cd ${BASE} && ${PUBLISH} >> ${LOG} 2>&1"
) | crontab -

echo "Installed: 10:45 America/New_York — $PUBLISH"
echo "Log: $LOG"
echo "Current crontab (tail):"
crontab -l | tail -30
