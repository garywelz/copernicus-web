#!/usr/bin/env bash
# Recent-video cron: ScienceVideoDB → Firestore science_videos + embeddings.
# Jetson line (America/New_York), daily after PM paper ingest:
#   30 21 * * * bash /media/sdcard/scheduler/scout/sync_recent_videos.sh
# Does not change production PubMed/bioRxiv/arXiv cron.
# ScienceVideoDB secret points at localhost:5433; this wrapper starts
# Cloud SQL Auth Proxy for that slot if nothing is already listening.
set -euo pipefail

ROOT="${COPERNICUS_WEB_ROOT:-/media/sdcard/copernicus-worker/copernicus-web}"
PY="${VIDEO_SYNC_PYTHON:-/media/sdcard/copernicus-worker/copernicus-web/cloud-run-backend/venv/bin/python}"
SINCE_DAYS="${VIDEO_SYNC_SINCE_DAYS:-14}"
LOG="${VIDEO_SYNC_LOG:-/media/sdcard/logs/video_sync_cron.log}"
ENV_FILE="${COPERNICUS_ENV:-/home/gary/.config/copernicus/env}"
CREDS="${GOOGLE_APPLICATION_CREDENTIALS:-/home/gary/.config/copernicus/gcp-sa.json}"
PROXY="${CLOUD_SQL_PROXY:-/media/sdcard/bin/cloud-sql-proxy}"
INSTANCE="${SCIENCEVIDDB_INSTANCE:-regal-scholar-453620-r7:us-central1:scienceviddb-db}"
PROXY_PORT="${SCIENCEVIDDB_PROXY_PORT:-5433}"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  . "$ENV_FILE"
fi
export GOOGLE_APPLICATION_CREDENTIALS="$CREDS"
export GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-regal-scholar-453620-r7}"
export COPERNICUS_WEB_ROOT="$ROOT"

cd "$ROOT"
mkdir -p "$(dirname "$LOG")"
echo "$(date -Iseconds) sync_recent_videos since_days=${SINCE_DAYS}" >> "$LOG"

started_proxy=0
proxy_pid=""
if ! (ss -lnt 2>/dev/null || netstat -lnt 2>/dev/null) | grep -q ":${PROXY_PORT} "; then
  if [[ ! -x "$PROXY" ]]; then
    echo "$(date -Iseconds) missing cloud-sql-proxy at $PROXY" >> "$LOG"
    exit 2
  fi
  "$PROXY" --address 127.0.0.1 --port "$PROXY_PORT" "$INSTANCE" >> "$LOG" 2>&1 &
  proxy_pid=$!
  started_proxy=1
  ready=0
  for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
    if (ss -lnt 2>/dev/null || netstat -lnt 2>/dev/null) | grep -q ":${PROXY_PORT} "; then
      ready=1
      break
    fi
    sleep 1
  done
  if [[ "$ready" -ne 1 ]]; then
    echo "$(date -Iseconds) cloud-sql-proxy did not listen on ${PROXY_PORT}" >> "$LOG"
    kill "$proxy_pid" 2>/dev/null || true
    exit 2
  fi
fi

set +e
"$PY" cloud-run-backend/scripts/sync_videos.py --since-days "$SINCE_DAYS" >> "$LOG" 2>&1
rc=$?
set -e

if [[ "$started_proxy" -eq 1 && -n "$proxy_pid" ]]; then
  kill "$proxy_pid" 2>/dev/null || true
  wait "$proxy_pid" 2>/dev/null || true
fi

echo "$(date -Iseconds) exit=${rc}" >> "$LOG"
exit "$rc"
