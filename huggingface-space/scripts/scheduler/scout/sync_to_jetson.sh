#!/usr/bin/env bash
# Sync version-controlled scout package from repo to Jetson production path.
# Usage (from repo root): bash huggingface-space/scripts/scheduler/scout/sync_to_jetson.sh
#
# SIDE-EFFECTING — run attended only. Re-check preconditions at deploy time:
#   1. Desired commit is on origin/main (or the named branch Gary approved).
#   2. Jetson HFS tree already at that commit (`git pull` on
#      /home/gdubs/copernicus-web-public) BEFORE this script copies files.
#   3. No scout_ingest lock held / no live ingest mid-run (or Gary accepts overlap).
#   4. Drift check after sync exits 0.
#
# Both *.py and *.sh are installed from the Jetson HFS tree — never scp'd from
# the calling machine — because a Windows CRLF transfer corrupts digests and
# can break bash.
set -euo pipefail

JETSON="${JETSON:-gary@192.168.1.223}"
REMOTE_DIR="/media/sdcard/scheduler/scout"
HFS_REPO="${HFS_REPO:-/home/gdubs/copernicus-web-public/huggingface-space}"
HFS_SCOUT="${HFS_REPO}/scripts/scheduler/scout"

echo "Installing scout package from Jetson HFS tree (LF-safe; pull first)"
ssh "${JETSON}" "set -euo pipefail
  HFS_SCOUT='${HFS_SCOUT}'
  REMOTE_DIR='${REMOTE_DIR}'
  test -d \"\${HFS_SCOUT}\" || { echo \"MISSING \${HFS_SCOUT} — git pull HFS before sync\" >&2; exit 2; }
  for f in \"\${HFS_SCOUT}\"/*.py \"\${HFS_SCOUT}\"/*.sh; do
    test -f \"\$f\" || continue
    base=\$(basename \"\$f\")
    # Skip helper docs / local-only scripts that are not cron entrypoints
    case \"\$base\" in
      sync_to_jetson.sh|check_scout_drift.sh|test_*) continue ;;
    esac
    cp \"\$f\" \"\${REMOTE_DIR}/\${base}\"
    chmod +x \"\${REMOTE_DIR}/\${base}\" 2>/dev/null || true
    if [[ \"\$base\" == *.sh ]]; then
      bash -n \"\${REMOTE_DIR}/\${base}\"
    fi
    echo \"installed \${base} oid=\$(git -C /home/gdubs/copernicus-web-public hash-object \"\${REMOTE_DIR}/\${base}\")\"
  done
  rm -rf \"\${REMOTE_DIR}/__pycache__\"
  echo 'Cleared __pycache__; deployed:'
  ls -la \"\${REMOTE_DIR}\"/*.py \"\${REMOTE_DIR}\"/*.sh
"
echo "Done. Run check_scout_drift.sh (read-only) to confirm live == HFS/repo (LF-normalised)."
