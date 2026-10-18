#!/usr/bin/env bash
# Push metadata JSON to Firestore (research_papers). Safe to re-run.
#
# Jetson cron (10:30 / 20:15 ET) entrypoint. Live copy:
#   /media/sdcard/scheduler/scout/scout_ingest.sh
# Repo SoT (this file) — ship via sync_to_jetson.sh after git pull so
# run_post_ingest_hooks.sh is present under HFS.
#
# On ingest success: run ordered post-ingest hooks (status publish, MASTER_TODO).
# On ingest failure or ingest timeout: skip hooks; leave prior status JSON in place
# (known-good stale beats fresh-wrong mid-ingest numbers).
#
# Wall-clock: ingest capped at INGEST_TIMEOUT (default 2h); hooks at HOOKS_TIMEOUT
# (default 30m). Uses timeout --kill-after=5m so SIGTERM-ignoring grandchildren
# are SIGKILLed and the flock is released. timeout exit 124 → hooks skipped.
#
# Concurrency: exclusive flock on SCOUT_INGEST_LOCK covers ingest + hooks so AM
# and PM cron cannot overlap. Non-blocking: if the lock is held, exit 75
# (EX_TEMPFAIL) so a skipped ingest is not recorded as success.
set -euo pipefail

HFS="${HFS:-/home/gdubs/copernicus-web-public/huggingface-space}"
# shellcheck source=/dev/null
source /home/gary/.config/copernicus/env
export GOOGLE_APPLICATION_CREDENTIALS="${GOOGLE_APPLICATION_CREDENTIALS:-/home/gary/.config/copernicus/gcp-sa.json}"

mkdir -p /media/sdcard/logs
INGEST_LOG="${INGEST_LOG:-/media/sdcard/logs/scout_ingest.log}"
INGEST_TIMEOUT="${INGEST_TIMEOUT:-2h}"
HOOKS_TIMEOUT="${HOOKS_TIMEOUT:-30m}"
KILL_AFTER="${SCOUT_TIMEOUT_KILL_AFTER:-5m}"
LOCK="${SCOUT_INGEST_LOCK:-/media/sdcard/logs/scout_ingest.lock}"
LOCK_BUSY_RC=75

exec 9>"$LOCK"
if ! flock -n 9; then
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) scout_ingest: lock held (${LOCK}); exiting ${LOCK_BUSY_RC}" | tee -a "$INGEST_LOG" >&2
  exit "$LOCK_BUSY_RC"
fi

# Do not exec — post-ingest hooks must run after ingest returns.
set +e
timeout --kill-after="$KILL_AFTER" "$INGEST_TIMEOUT" \
  bash "${HFS}/scripts/ingest_metadata_to_firestore.sh" >>"$INGEST_LOG" 2>&1
ingest_rc=$?
set -e

if [ "$ingest_rc" -ne 0 ]; then
  if [ "$ingest_rc" -eq 124 ]; then
    msg="$(date -u +%Y-%m-%dT%H:%M:%SZ) ingest timed out after ${INGEST_TIMEOUT} (kill-after=${KILL_AFTER}, rc=124); skipping post-ingest hooks"
  else
    msg="$(date -u +%Y-%m-%dT%H:%M:%SZ) ingest failed rc=${ingest_rc}; skipping post-ingest hooks"
  fi
  echo "$msg" | tee -a "$INGEST_LOG" >&2
  exit "$ingest_rc"
fi

set +e
timeout --kill-after="$KILL_AFTER" "$HOOKS_TIMEOUT" \
  bash "${HFS}/scripts/run_post_ingest_hooks.sh"
hooks_rc=$?
set -e

if [ "$hooks_rc" -eq 124 ]; then
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) post-ingest hooks timed out after ${HOOKS_TIMEOUT} (kill-after=${KILL_AFTER}, rc=124)" | tee -a "$INGEST_LOG" >&2
fi
exit "$hooks_rc"
