#!/usr/bin/env bash
# Sync version-controlled scout workers from repo to Jetson production path.
# Usage (from repo root): bash huggingface-space/scripts/scheduler/scout/sync_to_jetson.sh
#
# Prereq for the ingest wrapper: Jetson HFS tree already at the desired commit
# (`git pull` on /home/gdubs/copernicus-web-public). The wrapper is copied from
# that tree on the Jetson — never scp'd from the calling machine — because a
# Windows CRLF transfer breaks bash (`unexpected end of file` / rc from syntax).
set -euo pipefail

JETSON="${JETSON:-gary@192.168.1.222}"
REMOTE_DIR="/media/sdcard/scheduler/scout"
HFS_REPO="${HFS_REPO:-/home/gdubs/copernicus-web-public/huggingface-space}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Syncing scout workers (*.py) to ${JETSON}:${REMOTE_DIR}"
scp "${SCRIPT_DIR}"/*.py "${JETSON}:${REMOTE_DIR}/"

echo "Installing scout_ingest.sh from Jetson HFS tree (LF-safe; pull first)"
ssh "${JETSON}" "set -euo pipefail
  src='${HFS_REPO}/scripts/scheduler/scout/scout_ingest.sh'
  test -f \"\$src\" || { echo \"MISSING \$src — git pull HFS before sync\" >&2; exit 2; }
  cp \"\$src\" '${REMOTE_DIR}/scout_ingest.sh'
  chmod +x '${REMOTE_DIR}/scout_ingest.sh'
  bash -n '${REMOTE_DIR}/scout_ingest.sh'
  echo \"wrapper oid=\$(git -C /home/gdubs/copernicus-web-public hash-object '${REMOTE_DIR}/scout_ingest.sh')\"
"

ssh "${JETSON}" "rm -rf ${REMOTE_DIR}/__pycache__ && echo 'Cleared __pycache__; deployed:' && ls -la ${REMOTE_DIR}/*.py ${REMOTE_DIR}/scout_ingest.sh"
echo "Done."
