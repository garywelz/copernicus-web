#!/usr/bin/env bash
# Read-only: compare Jetson live digests to the Jetson HFS tree copy of this
# package (same LF blobs git will have after pull).
#
# Usage (from repo root):
#   bash huggingface-space/scripts/scheduler/scout/check_scout_drift.sh
#
# Observes and reports only — no pull, copy, kill, or write on the Jetson.
# Exit 0 when every compared file matches (LF-normalised); non-zero on drift.
#
# Optional: SCOUT_DRIFT_LOCAL=1 also prints LF-normalised hashes of the local
# checkout (informational; does not fail unless SCOUT_DRIFT_LOCAL_STRICT=1).
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

echo "Comparing Jetson live ${REMOTE_DIR} ↔ HFS ${HFS_SCOUT} (LF-normalised)"

# Prefer hashing the Jetson HFS tree (LF git blobs) against live, not a Windows
# working copy. Python is base64-wrapped so Windows shells do not mangle it.
REMOTE_PY_B64="$(python - <<'PY'
import base64
src = r'''
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
'''
print(base64.b64encode(src.encode()).decode())
PY
)"

set +e
ssh -o BatchMode=yes -o ConnectTimeout=15 "${JETSON}" \
  "echo '${REMOTE_PY_B64}' | base64 -d | python3 - '${REMOTE_DIR}' '${HFS_SCOUT}' ${FILES[*]}"
remote_rc=$?
set -e

if [[ "${SCOUT_DRIFT_LOCAL:-0}" == "1" ]]; then
  echo "Local LF-normalised hashes (${SCRIPT_DIR}):"
  local_drift=0
  for f in "${FILES[@]}"; do
    local_path="${SCRIPT_DIR}/${f}"
    if [[ ! -f "$local_path" ]]; then
      echo "MISSING_LOCAL $f"
      local_drift=1
      continue
    fi
    local_sha="$(python -c "import hashlib,sys; b=open(sys.argv[1],'rb').read().replace(b'\\r\\n',b'\\n').replace(b'\\r',b'\\n'); print(hashlib.sha256(b).hexdigest())" "$local_path")"
    echo "LOCAL $f $local_sha"
  done
  if [[ "${SCOUT_DRIFT_LOCAL_STRICT:-0}" == "1" && "$local_drift" -ne 0 ]]; then
    exit 1
  fi
fi

if [[ "$remote_rc" -ne 0 ]]; then
  echo "check_scout_drift: DRIFT detected" >&2
  exit 1
fi
echo "check_scout_drift: all compared files match (LF-normalised live vs HFS)"
exit 0
