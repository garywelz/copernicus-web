#!/usr/bin/env bash
# Ordered steps after a successful Firestore paper ingest.
#
# Called by scout_ingest.sh only when ingest exits 0. Ingest failure must never
# reach this script — prior knowledge-engine-status.json stays known-good stale.
#
# Chain shape (insert new stages without reworking callers):
#   1. embed gap backfill --auto   ← before publish; non-blocking for later hooks
#   2. status publish
#   3. MASTER_TODO assembler
#
# Each hook appends to its existing cron log destination. A failing hook does
# not skip later hooks; the script exits non-zero if any hook failed.
# Embed uses the worker venv + tracked backfill script under copernicus-worker.
set -uo pipefail

HFS="${HFS:-/home/gdubs/copernicus-web-public/huggingface-space}"
STATUS_LOG="${STATUS_LOG:-${HFS}/paper_acquisition_logs/daily_scout/status_publish_cron.log}"
MASTER_TODO_LOG="${MASTER_TODO_LOG:-/media/sdcard/logs/master_todo_cron.log}"
MASTER_TODO_PY="${MASTER_TODO_PY:-/media/sdcard/venvs/master-todo-cron/bin/python}"
MASTER_TODO_SCRIPT="${MASTER_TODO_SCRIPT:-/media/sdcard/glmp-cron/build_master_todo.py}"

mkdir -p "$(dirname "$STATUS_LOG")" "$(dirname "$MASTER_TODO_LOG")"

overall_rc=0

run_hook() {
  local name="$1"
  local log="$2"
  local rc=0
  shift 2
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) START hook=${name}" | tee -a "$log"
  "$@" >>"$log" 2>&1
  rc=$?
  if [ "$rc" -eq 0 ]; then
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) OK   hook=${name}" | tee -a "$log"
  else
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) FAIL hook=${name} rc=${rc}" | tee -a "$log" >&2
    overall_rc=$rc
  fi
}

# --- ordered post-ingest chain -----------------------------------------------
# Embed is non-blocking for later hooks (status_publish / MASTER_TODO still run
# if this exits non-zero). Pin --collection research_papers explicitly.
EMBED_PY="${EMBED_PY:-/media/sdcard/copernicus-worker/venv/bin/python}"
EMBED_SCRIPT="${EMBED_SCRIPT:-/media/sdcard/copernicus-worker/copernicus-web/cloud-run-backend/scripts/backfill_research_paper_embeddings.py}"
EMBED_LOG="${EMBED_LOG:-/media/sdcard/logs/embed_auto_cron.log}"
mkdir -p "$(dirname "$EMBED_LOG")"

run_hook "embed_auto" "$EMBED_LOG" \
  "$EMBED_PY" "$EMBED_SCRIPT" \
  --auto --collection research_papers --log-dir /media/sdcard/logs

run_hook "status_publish" "$STATUS_LOG" \
  bash "${HFS}/scripts/publish_knowledge_engine_status.sh"

run_hook "master_todo" "$MASTER_TODO_LOG" \
  "$MASTER_TODO_PY" "$MASTER_TODO_SCRIPT"

exit "$overall_rc"
