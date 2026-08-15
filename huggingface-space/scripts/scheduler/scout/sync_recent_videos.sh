#!/usr/bin/env bash
# Recent-video cron: ScienceVideoDB → Firestore science_videos + embeddings.
# Intended Jetson line (America/New_York), after paper ingest:
#   30 21 * * * .../sync_recent_videos.sh >> .../video_sync_cron.log 2>&1
# First backfill (once, not cron): omit --since-days or pass a large window.
set -euo pipefail

ROOT="${COPERNICUS_WEB_ROOT:-/media/sdcard/copernicus-worker/copernicus-web}"
PY="${VIDEO_SYNC_PYTHON:-/media/sdcard/venvs/master-todo-cron/bin/python}"
SINCE_DAYS="${VIDEO_SYNC_SINCE_DAYS:-14}"
LOG="${VIDEO_SYNC_LOG:-/media/sdcard/logs/video_sync_cron.log}"

cd "$ROOT"
mkdir -p "$(dirname "$LOG")"
echo "$(date -Iseconds) sync_recent_videos since_days=${SINCE_DAYS}" >> "$LOG"
"$PY" cloud-run-backend/scripts/sync_videos.py --since-days "$SINCE_DAYS" >> "$LOG" 2>&1
echo "$(date -Iseconds) exit=$?" >> "$LOG"
