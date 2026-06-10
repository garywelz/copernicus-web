#!/usr/bin/env bash
# Run Daily Paper Scout, then push new/updated local JSON to Firestore.
# For cron, point the 10:15 job to this instead of run_daily_scout.sh (see install script).
# Logs: same cron.log; ingest writes to paper_acquisition_logs/daily_scout/ingest.log
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HFS_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
INGEST_LOG="${HFS_DIR}/paper_acquisition_logs/daily_scout/ingest.log"
mkdir -p "$(dirname "$INGEST_LOG")"

cd "$HFS_DIR"
SCOUT_EXIT=0
bash scripts/acquire_papers/run_daily_scout.sh || SCOUT_EXIT=$?

{
  echo ""
  echo "================================================================================"
  echo "Firestore ingest — $(date -Iseconds 2>/dev/null || date)"
  echo "================================================================================"
} >> "$INGEST_LOG"

# Ingest: safe to re-run; skips existing doc ids (always attempt after scout)
INGEST_EXIT=0
bash scripts/ingest_metadata_to_firestore.sh >> "$INGEST_LOG" 2>&1 || INGEST_EXIT=$?
[ "$INGEST_EXIT" -ne 0 ] && exit "$INGEST_EXIT"
exit "$SCOUT_EXIT"
