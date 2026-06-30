#!/usr/bin/env bash
# Sync version-controlled scout workers from repo to Jetson production path.
# Usage (from repo root): bash huggingface-space/scripts/scheduler/scout/sync_to_jetson.sh
set -euo pipefail

JETSON="${JETSON:-gary@192.168.1.222}"
REMOTE_DIR="/media/sdcard/scheduler/scout"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Syncing scout workers to ${JETSON}:${REMOTE_DIR}"
scp "${SCRIPT_DIR}"/*.py "${JETSON}:${REMOTE_DIR}/"
ssh "${JETSON}" "rm -rf ${REMOTE_DIR}/__pycache__ && echo 'Cleared __pycache__; deployed:' && ls -la ${REMOTE_DIR}/*.py"
echo "Done."
