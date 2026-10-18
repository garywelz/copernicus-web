#!/usr/bin/env bash
# Local / attended test for scout_ingest.sh timeout --kill-after + flock release.
#
#   bash huggingface-space/scripts/scheduler/scout/test_scout_ingest_timeout_kill.sh
#
# Part A (GNU timeout required): a grandchild that ignores SIGTERM must be gone
# after timeout --kill-after.
# Part B (flock required): the same pattern under flock must leave the lock
# releasable. Skips Part B with a clear message when flock is missing (e.g.
# Windows Git Bash) — run attended on the Jetson for the full check.
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
  echo $$ >"$pidfile"
  while true; do
    date +%s >"$marker"
    sleep 1
  done
) &
wait $! || true
EOF
chmod +x "${WORKDIR}/hung_tree.sh"

echo "=== Part A: timeout --kill-after reaps SIGTERM-ignoring grandchild ==="
set +e
timeout --kill-after=2s 1s bash "${WORKDIR}/hung_tree.sh" "$CHILD_PID_FILE" "$MARKER"
timeout_rc=$?
set -e
sleep 3

if [[ ! -f "$CHILD_PID_FILE" ]]; then
  echo "FAIL: grandchild pid file never written" >&2
  exit 1
fi
GPID="$(cat "$CHILD_PID_FILE")"
if kill -0 "$GPID" 2>/dev/null; then
  echo "FAIL: grandchild pid $GPID still alive after timeout --kill-after" >&2
  kill -9 "$GPID" 2>/dev/null || true
  exit 1
fi
if [[ "$timeout_rc" -ne 124 ]]; then
  echo "FAIL: expected timeout rc 124, got $timeout_rc" >&2
  exit 1
fi
echo "OK: grandchild $GPID gone; timeout_rc=124"

if ! command -v flock >/dev/null 2>&1; then
  echo "SKIP Part B: flock not on PATH (attended Jetson check: re-run this script there)"
  echo "PASS test_scout_ingest_timeout_kill (Part A only)"
  exit 0
fi

echo "=== Part B: flock released after timeout --kill-after ==="
LOCK="${WORKDIR}/scout_ingest.lock"
rm -f "$CHILD_PID_FILE" "$MARKER"
(
  exec 9>"$LOCK"
  flock -n 9
  set +e
  timeout --kill-after=2s 1s bash "${WORKDIR}/hung_tree.sh" "$CHILD_PID_FILE" "$MARKER"
  echo "timeout_rc=$?"
  set -e
)
sleep 2
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
echo "OK: lock released after kill-after"
echo "PASS test_scout_ingest_timeout_kill"
exit 0
