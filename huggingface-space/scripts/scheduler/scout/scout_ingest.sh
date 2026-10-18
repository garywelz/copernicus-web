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
# (default 30m). Uses timeout --kill-after=5m, then explicitly reaps the timeout
# process group: GNU timeout returns when its *direct* child exits, so a
# SIGTERM-ignoring grandchild in the same PGID can survive kill-after (Jetson
# probe 2026-10-18). timeout exit 124 → hooks skipped.
#
# Concurrency: exclusive flock on SCOUT_INGEST_LOCK covers ingest + hooks so AM
# and PM cron cannot overlap. Non-blocking: if the lock is held, exit 75
# (EX_TEMPFAIL) so a skipped ingest is not recorded as success.
# Close fd 9 in timed children so orphans cannot keep the flock.
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

# Run cmd under timeout; after timeout returns, SIGKILL any survivors still in
# timeout's process group (timeout is PGID leader; orphans keep that PGID).
run_timed() {
  local duration="$1"
  shift
  local timeout_pid pgid own_pgid rc
  # Close flock fd in the timed tree (9>&-).
  timeout --kill-after="$KILL_AFTER" "$duration" "$@" 9>&- &
  timeout_pid=$!
  # GNU timeout makes PGID == its own pid once setpgid runs. Do NOT read pgid
  # via ps right after backgrounding: that races setpgid and can return this
  # wrapper's PGID, so the cleanup kill would terminate scout_ingest itself.
  pgid="$timeout_pid"
  own_pgid="$(ps -o pgid= -p $$ 2>/dev/null | tr -d ' ' || true)"
  if [[ -n "${own_pgid}" && "${pgid}" == "${own_pgid}" ]]; then
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) scout_ingest: refusing to signal own PGID ${pgid} (timeout_pid=${timeout_pid})" | tee -a "$INGEST_LOG" >&2
    set +e
    wait "$timeout_pid"
    rc=$?
    set -e
    return "$rc"
  fi
  set +e
  wait "$timeout_pid"
  rc=$?
  set -e
  # Always signal the recorded PGID (timeout_pid). Orphans keep that PGID after
  # the timeout leader exits.
  kill -TERM -"$pgid" 2>/dev/null || true
  sleep 1
  kill -KILL -"$pgid" 2>/dev/null || true
  return "$rc"
}

# Do not exec — post-ingest hooks must run after ingest returns.
set +e
run_timed "$INGEST_TIMEOUT" \
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
run_timed "$HOOKS_TIMEOUT" \
  bash "${HFS}/scripts/run_post_ingest_hooks.sh"
hooks_rc=$?
set -e

if [ "$hooks_rc" -eq 124 ]; then
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) post-ingest hooks timed out after ${HOOKS_TIMEOUT} (kill-after=${KILL_AFTER}, rc=124)" | tee -a "$INGEST_LOG" >&2
fi
exit "$hooks_rc"
