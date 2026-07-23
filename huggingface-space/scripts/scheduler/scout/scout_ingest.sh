#!/usr/bin/env bash
# Push metadata JSON to Firestore (research_papers). Safe to re-run.
#
# Jetson cron (10:30 / 20:15 ET) entrypoint. Live copy:
#   /media/sdcard/scheduler/scout/scout_ingest.sh
# Repo SoT (this file) — ship via sync_to_jetson.sh after git pull so
# run_post_ingest_hooks.sh is present under HFS.
#
# On ingest success: run ordered post-ingest hooks (status publish, MASTER_TODO).
# On ingest failure: skip hooks; leave prior status JSON in place
# (known-good stale beats fresh-wrong mid-ingest numbers).
set -euo pipefail

HFS="${HFS:-/home/gdubs/copernicus-web-public/huggingface-space}"
# shellcheck source=/dev/null
source /home/gary/.config/copernicus/env
export GOOGLE_APPLICATION_CREDENTIALS="${GOOGLE_APPLICATION_CREDENTIALS:-/home/gary/.config/copernicus/gcp-sa.json}"

mkdir -p /media/sdcard/logs
INGEST_LOG="${INGEST_LOG:-/media/sdcard/logs/scout_ingest.log}"

# Do not exec — post-ingest hooks must run after ingest returns.
set +e
bash "${HFS}/scripts/ingest_metadata_to_firestore.sh" >>"$INGEST_LOG" 2>&1
ingest_rc=$?
set -e

if [ "$ingest_rc" -ne 0 ]; then
  msg="$(date -u +%Y-%m-%dT%H:%M:%SZ) ingest failed rc=${ingest_rc}; skipping post-ingest hooks"
  echo "$msg" | tee -a "$INGEST_LOG" >&2
  exit "$ingest_rc"
fi

bash "${HFS}/scripts/run_post_ingest_hooks.sh"
