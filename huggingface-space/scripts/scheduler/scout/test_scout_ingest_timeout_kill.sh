#!/usr/bin/env bash
# Local / attended test for scout_ingest.sh timeout --kill-after + flock release
# + process-group reap (no SIGTERM-ignoring descendant may survive).
#
#   bash huggingface-space/scripts/scheduler/scout/test_scout_ingest_timeout_kill.sh
#
# Part A (GNU timeout): grandchild ignoring SIGTERM is gone after kill-after.
# Part B (flock): lock released; second run with lock held exits 75.
# Part C (attended / Linux with flock): full scout_ingest.sh against a fake HFS
# hung tree; assert no descendant of the timed PGID survives.
#
# Use a scratch lock only: SCOUT_INGEST_LOCK=/tmp/scout_ingest_test.lock
set -euo pipefail

if ! timeout --help 2>&1 | grep -q -- '--kill-after'; then
  echo "FAIL: timeout(1) lacks --kill-after (need GNU coreutils)" >&2
  exit 1
fi

WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/scout_timeout_test.XXXXXX")"
cleanup() { rm -rf "$WORKDIR"; }
trap cleanup EXIT

CHILD_PID_FILE="${WORKDIR}/grandchild.pid"
MARKER="${WORKDIR}/grandchild_still_alive"

cat >"${WORKDIR}/hung_tree.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
pidfile="${1:?}"
marker="${2:?}"
(
  trap '' TERM
  # BASHPID is the subshell; $$ is the parent bash (misleading for reaping tests).
  echo "${BASHPID:-$$}" >"$pidfile"
  while true; do
    date +%s >"$marker"
    sleep 1
  done
) &
wait $! || true
EOF
chmod +x "${WORKDIR}/hung_tree.sh"

echo "=== Part A: timeout --kill-after + PGID reap (raw timeout alone is not enough) ==="
# GNU timeout returns when its direct child exits; a SIGTERM-ignoring grandchild
# in the same PGID can survive. Mirror scout_ingest.sh: record PGID, wait, reap.
set +e
timeout --kill-after=2s 1s bash "${WORKDIR}/hung_tree.sh" "$CHILD_PID_FILE" "$MARKER" &
timeout_pid=$!
pgid="$(ps -o pgid= -p "$timeout_pid" 2>/dev/null | tr -d ' ' || true)"
wait "$timeout_pid"
timeout_rc=$?
if [[ -n "$pgid" ]]; then
  kill -TERM -"$pgid" 2>/dev/null || true
  sleep 1
  kill -KILL -"$pgid" 2>/dev/null || true
fi
set -e
sleep 1

if [[ ! -f "$CHILD_PID_FILE" ]]; then
  echo "FAIL: grandchild pid file never written" >&2
  exit 1
fi
GPID="$(cat "$CHILD_PID_FILE")"
if kill -0 "$GPID" 2>/dev/null; then
  echo "FAIL: grandchild pid $GPID still alive after timeout + PGID reap" >&2
  kill -9 "$GPID" 2>/dev/null || true
  exit 1
fi
if [[ "$timeout_rc" -ne 124 ]]; then
  echo "FAIL: expected timeout rc 124, got $timeout_rc" >&2
  exit 1
fi
echo "OK: grandchild $GPID gone; timeout_rc=124; PGID reaped"

if ! command -v flock >/dev/null 2>&1; then
  echo "SKIP Part B/C: flock not on PATH (run attended on Jetson / Linux)"
  echo "PASS test_scout_ingest_timeout_kill (Part A only)"
  exit 0
fi

echo "=== Part B: flock released after timeout + PGID reap ==="
LOCK="${WORKDIR}/scout_ingest.lock"
rm -f "$CHILD_PID_FILE" "$MARKER"
(
  exec 9>"$LOCK"
  flock -n 9
  set +e
  timeout --kill-after=2s 1s bash "${WORKDIR}/hung_tree.sh" "$CHILD_PID_FILE" "$MARKER" 9>&- &
  timeout_pid=$!
  pgid="$(ps -o pgid= -p "$timeout_pid" 2>/dev/null | tr -d ' ' || true)"
  wait "$timeout_pid"
  echo "timeout_rc=$?"
  if [[ -n "$pgid" ]]; then
    kill -TERM -"$pgid" 2>/dev/null || true
    sleep 1
    kill -KILL -"$pgid" 2>/dev/null || true
  fi
  set -e
)
sleep 1
GPID="$(cat "$CHILD_PID_FILE")"
if kill -0 "$GPID" 2>/dev/null; then
  echo "FAIL: grandchild $GPID still alive under flock wrapper" >&2
  kill -9 "$GPID" 2>/dev/null || true
  exit 1
fi
if ! ( exec 8>"$LOCK"; flock -n 8 ); then
  echo "FAIL: lock still held after timeout wrapper exited" >&2
  exit 1
fi
echo "OK: lock released after kill-after + PGID reap"

echo "=== Part C: scout_ingest.sh reaps whole timed PGID (no descendant survives) ==="
# Requires the repo (or live) scout_ingest.sh under test. Prefer SCRIPT_DIR.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INGEST_SH="${SCOUT_INGEST_UNDER_TEST:-$SCRIPT_DIR/scout_ingest.sh}"
if [[ ! -x "$INGEST_SH" && ! -f "$INGEST_SH" ]]; then
  echo "SKIP Part C: scout_ingest.sh not found at $INGEST_SH" >&2
  echo "PASS test_scout_ingest_timeout_kill (Part A+B)"
  exit 0
fi

FAKE_HFS="${WORKDIR}/fake_hfs"
mkdir -p "${FAKE_HFS}/scripts"
cp "${WORKDIR}/hung_tree.sh" "${FAKE_HFS}/scripts/ingest_metadata_to_firestore.sh"
# hung_tree needs two args; wrap it
cat >"${FAKE_HFS}/scripts/ingest_metadata_to_firestore.sh" <<EOF
#!/usr/bin/env bash
exec bash "${WORKDIR}/hung_tree.sh" "${WORKDIR}/partc_grandchild.pid" "${WORKDIR}/partc_marker"
EOF
chmod +x "${FAKE_HFS}/scripts/ingest_metadata_to_firestore.sh"
echo '#!/usr/bin/env bash' >"${FAKE_HFS}/scripts/run_post_ingest_hooks.sh"
echo 'exit 0' >>"${FAKE_HFS}/scripts/run_post_ingest_hooks.sh"
chmod +x "${FAKE_HFS}/scripts/run_post_ingest_hooks.sh"

SCRATCH_LOCK="${SCOUT_INGEST_LOCK:-/tmp/scout_ingest_test.lock}"
rm -f "$SCRATCH_LOCK" "${WORKDIR}/partc_grandchild.pid"
export HFS="$FAKE_HFS"
export SCOUT_INGEST_LOCK="$SCRATCH_LOCK"
export INGEST_LOG="${WORKDIR}/partc_ingest.log"
export INGEST_TIMEOUT=2s
export HOOKS_TIMEOUT=1s
export SCOUT_TIMEOUT_KILL_AFTER=2s

set +e
bash "$INGEST_SH"
partc_rc=$?
set -e
# Allow reap sleep + kill to finish
sleep 3

if [[ "$partc_rc" -ne 124 ]]; then
  echo "FAIL Part C: expected rc 124, got $partc_rc" >&2
  exit 1
fi
if [[ -f "${WORKDIR}/partc_grandchild.pid" ]]; then
  CGPID="$(cat "${WORKDIR}/partc_grandchild.pid")"
  if kill -0 "$CGPID" 2>/dev/null; then
    echo "FAIL Part C: grandchild $CGPID still alive after scout_ingest timeout+reap" >&2
    ps -eo pid,ppid,pgid,sid,stat,args | grep -E "$CGPID|scout_ingest|hung_tree|fake_hfs" || true
    kill -9 "$CGPID" 2>/dev/null || true
    exit 1
  fi
fi
# No leftover processes referencing the fake HFS hung tree
leftover="$(ps -eo pid,args | grep -F "$FAKE_HFS" | grep -v grep || true)"
if [[ -n "$leftover" ]]; then
  echo "FAIL Part C: leftover processes still reference fake HFS:" >&2
  echo "$leftover" >&2
  exit 1
fi
if ! ( exec 8>"$SCRATCH_LOCK"; flock -n 8 ); then
  echo "FAIL Part C: scratch lock still held" >&2
  exit 1
fi
echo "OK: Part C no descendant survived; scratch lock free"

# Lock-busy exit 75
flock "$SCRATCH_LOCK" sleep 60 &
holder=$!
sleep 0.3
set +e
bash "$INGEST_SH"
busy_rc=$?
set -e
kill "$holder" 2>/dev/null || true
wait "$holder" 2>/dev/null || true
if [[ "$busy_rc" -ne 75 ]]; then
  echo "FAIL Part C: expected lock-busy rc 75, got $busy_rc" >&2
  exit 1
fi
if ! grep -q "lock held" "$INGEST_LOG"; then
  echo "FAIL Part C: expected lock-held log line" >&2
  exit 1
fi
echo "OK: lock busy exits 75"

echo "PASS test_scout_ingest_timeout_kill"
exit 0
