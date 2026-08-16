#!/usr/bin/env bash
# Scoped MathOverflow + BioStars paper-ID harvest (official APIs only).
# Bioinformatics SE is the locked GLMP fallback when BioStars is blocked.
# Jetson line (America/New_York), weekly, after PM paper ingest:
#   0 22 * * 0 .../scout_discussion_boards.sh
# Does not change production PubMed/bioRxiv/arXiv cron.
set -euo pipefail

ROOT="${COPERNICUS_WEB_ROOT:-/media/sdcard/copernicus-worker/copernicus-web}"
PY="${DISCUSSION_SCOUT_PYTHON:-/media/sdcard/copernicus-worker/copernicus-web/cloud-run-backend/venv/bin/python}"
LOG="${DISCUSSION_SCOUT_LOG:-/media/sdcard/logs/discussion_board_cron.log}"
ENV_FILE="${COPERNICUS_ENV:-/home/gary/.config/copernicus/env}"
CREDS="${GOOGLE_APPLICATION_CREDENTIALS:-/home/gary/.config/copernicus/gcp-sa.json}"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  . "$ENV_FILE"
fi
export GOOGLE_APPLICATION_CREDENTIALS="$CREDS"
export COPERNICUS_WEB_ROOT="$ROOT"

cd "$ROOT"
mkdir -p "$(dirname "$LOG")"
echo "$(date -Iseconds) discussion_board_scout --write" >> "$LOG"
"$PY" huggingface-space/scripts/acquire_papers/discussion_board_scout.py --write >> "$LOG" 2>&1
echo "$(date -Iseconds) exit=$?" >> "$LOG"
