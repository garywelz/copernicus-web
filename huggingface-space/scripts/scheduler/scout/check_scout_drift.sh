#!/usr/bin/env bash
# Read-only: compare Jetson live digests to the Jetson HFS tree copy of this
# package (same LF blobs git will have after pull).
#
# Usage (from repo root on Yoga):
#   bash huggingface-space/scripts/scheduler/scout/check_scout_drift.sh
# Usage (already on the Jetson):
#   bash …/check_scout_drift.sh
#   → compares local live vs local HFS (no SSH to self).
#
# Observes and reports only — no pull, copy, kill, or write on the Jetson.
# Exit 0 when every compared file matches (LF-normalised); non-zero on drift.
set -euo pipefail

JETSON="${JETSON:-gary@192.168.1.223}"
REMOTE_DIR="/media/sdcard/scheduler/scout"
HFS_REPO="${HFS_REPO:-/home/gdubs/copernicus-web-public/huggingface-space}"
HFS_SCOUT="${HFS_REPO}/scripts/scheduler/scout"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

FILES=(
  scout_common.py
  scout_arxiv.py
  scout_biorxiv.py
  scout_pubmed.py
  query_terms.py
  glmp_pubmed_supplement.py
  scout_ingest.sh
  scout_discussion_boards.sh
  sync_recent_videos.sh
)

COMPARE_PY_FILE="$(mktemp)"
cleanup_py() { rm -f "$COMPARE_PY_FILE"; }
trap cleanup_py EXIT
cat >"$COMPARE_PY_FILE" <<'PY'
import hashlib, sys
from pathlib import Path
remote_dir, hfs_scout, *files = sys.argv[1:]

def lf_sha(path: Path):
    if not path.exists():
        return "MISSING"
    b = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(b).hexdigest()

drift = 0
for name in files:
    live = lf_sha(Path(remote_dir) / name)
    hfs = lf_sha(Path(hfs_scout) / name)
    if live == "MISSING" or hfs == "MISSING":
        print("MISSING %s live=%s hfs=%s" % (name, live, hfs))
        drift = 1
    elif live == hfs:
        print("MATCH %s %s" % (name, live))
    else:
        print("DRIFT %s live_lf=%s hfs_lf=%s" % (name, live, hfs))
        drift = 1
raise SystemExit(drift)
PY

# On the Jetson both trees exist locally — do not SSH to ourselves.
if [[ -d "$REMOTE_DIR" && -d "$HFS_SCOUT" ]]; then
  echo "Comparing local live ${REMOTE_DIR} ↔ local HFS ${HFS_SCOUT} (LF-normalised; on Jetson, no SSH)"
  set +e
  python3 "$COMPARE_PY_FILE" "$REMOTE_DIR" "$HFS_SCOUT" "${FILES[@]}"
  remote_rc=$?
  set -e
else
  echo "Comparing Jetson live ${REMOTE_DIR} ↔ HFS ${HFS_SCOUT} via SSH ${JETSON} (LF-normalised)"
  REMOTE_PY_B64="$(base64 -w0 <"$COMPARE_PY_FILE" 2>/dev/null || base64 <"$COMPARE_PY_FILE" | tr -d '\n')"
  set +e
  ssh -o BatchMode=yes -o ConnectTimeout=15 "${JETSON}" \
    "echo '${REMOTE_PY_B64}' | base64 -d | python3 - '${REMOTE_DIR}' '${HFS_SCOUT}' ${FILES[*]}"
  remote_rc=$?
  set -e
fi

if [[ "$remote_rc" -ne 0 ]]; then
  echo "check_scout_drift: DRIFT detected" >&2
  exit 1
fi
echo "check_scout_drift: all compared files match (LF-normalised live vs HFS)"
exit 0
