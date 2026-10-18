#!/usr/bin/env bash
# Stress-test scout_ingest.sh run_timed PGID handling.
#
#   bash huggingface-space/scripts/scheduler/scout/test_scout_ingest_run_timed_pgid.sh
#
# Loops N times (default 50) with a fast fake ingest+hooks tree. Each iteration
# must exit 0 and reach the hooks step (HOOKS_RAN marker). Catches the race where
# run_timed read pgid via ps before timeout setpgid and then kill'd its own PGID.
#
# Scratch lock only. Does not touch live /media/sdcard/scheduler/scout/.
#
# Optional: RACE_REPRO=1 runs the same loop against a wrapper that still uses
# the pre-fix `ps`-based pgid read (as in 3d76aca) to try to reproduce a failure.
set -euo pipefail

if ! command -v flock >/dev/null 2>&1; then
  echo "SKIP: flock not on PATH (run on Jetson / Linux)" >&2
  exit 0
fi
if ! timeout --help 2>&1 | grep -q -- '--kill-after'; then
  echo "FAIL: need GNU timeout --kill-after" >&2
  exit 1
fi

LOOPS="${LOOPS:-50}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INGEST_SH="${SCOUT_INGEST_UNDER_TEST:-$SCRIPT_DIR/scout_ingest.sh}"
WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/scout_pgid_stress.XXXXXX")"
cleanup() { rm -rf "$WORKDIR"; }
trap cleanup EXIT

FAKE_HFS="${WORKDIR}/fake_hfs"
mkdir -p "${FAKE_HFS}/scripts"
cat >"${FAKE_HFS}/scripts/ingest_metadata_to_firestore.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
cat >"${FAKE_HFS}/scripts/run_post_ingest_hooks.sh" <<EOF
#!/usr/bin/env bash
echo HOOKS_RAN >> "${WORKDIR}/hooks.log"
exit 0
EOF
chmod +x "${FAKE_HFS}/scripts/"*.sh

run_loops() {
  local label="$1"
  local wrapper="$2"
  local i rc hooks_before hooks_after
  : >"${WORKDIR}/hooks.log"
  echo "=== ${label}: ${LOOPS} fast ingest loops ==="
  for i in $(seq 1 "$LOOPS"); do
    hooks_before="$(wc -l <"${WORKDIR}/hooks.log" | tr -d ' ')"
    rm -f "${WORKDIR}/lock.$label"
    set +e
    HFS="$FAKE_HFS" \
      SCOUT_INGEST_LOCK="${WORKDIR}/lock.$label" \
      INGEST_LOG="${WORKDIR}/ingest.$label.log" \
      INGEST_TIMEOUT=30s \
      HOOKS_TIMEOUT=30s \
      SCOUT_TIMEOUT_KILL_AFTER=2s \
      bash "$wrapper"
    rc=$?
    set -e
    hooks_after="$(wc -l <"${WORKDIR}/hooks.log" | tr -d ' ')"
    if [[ "$rc" -ne 0 ]]; then
      echo "FAIL ${label} iter=$i rc=$rc (hooks_before=$hooks_before after=$hooks_after)" >&2
      tail -n 30 "${WORKDIR}/ingest.$label.log" >&2 || true
      return 1
    fi
    if [[ "$hooks_after" -le "$hooks_before" ]]; then
      echo "FAIL ${label} iter=$i: hooks did not run (rc=0 but no HOOKS_RAN)" >&2
      return 1
    fi
  done
  echo "OK ${label}: ${LOOPS}/${LOOPS} reached hooks and exited 0"
  return 0
}

if [[ ! -f "$INGEST_SH" ]]; then
  echo "FAIL: missing $INGEST_SH" >&2
  exit 1
fi
run_loops "fixed" "$INGEST_SH"

# Deterministic proof the stress check can fail: signal own PGID after ingest.
echo "=== DET_FAIL: intentional own-PGID kill must skip hooks ==="
DET="${WORKDIR}/scout_ingest_own_pgid.sh"
cat >"$DET" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
HFS="${HFS:?}"
INGEST_LOG="${INGEST_LOG:?}"
LOCK="${SCOUT_INGEST_LOCK:?}"
mkdir -p "$(dirname "$INGEST_LOG")"
exec 9>"$LOCK"
flock -n 9
bash "${HFS}/scripts/ingest_metadata_to_firestore.sh" >>"$INGEST_LOG" 2>&1
own_pgid="$(ps -o pgid= -p $$ | tr -d ' ')"
# Simulate the race outcome: cleanup kills the wrapper's process group.
kill -KILL -"$own_pgid" 2>/dev/null || true
bash "${HFS}/scripts/run_post_ingest_hooks.sh"
exit 0
EOF
chmod +x "$DET"
: >"${WORKDIR}/hooks.log"
set +e
# setsid so intentional own-PGID kill cannot reap this test harness.
HFS="$FAKE_HFS" \
  SCOUT_INGEST_LOCK="${WORKDIR}/lock.det" \
  INGEST_LOG="${WORKDIR}/ingest.det.log" \
  setsid bash "$DET"
det_rc=$?
set -e
det_hooks=0
if [[ -f "${WORKDIR}/hooks.log" ]]; then
  det_hooks="$(grep -c HOOKS_RAN "${WORKDIR}/hooks.log" || true)"
fi
if [[ "$det_rc" -eq 0 && "$det_hooks" -ge 1 ]]; then
  echo "FAIL: DET_FAIL did not fail (rc=$det_rc hooks=$det_hooks)" >&2
  exit 1
fi
echo "OK DET_FAIL: rc=$det_rc hooks=$det_hooks (failure mode is detectable)"

if [[ "${RACE_REPRO:-0}" == "1" ]]; then
  echo "=== RACE_REPRO: ps-based pgid (3d76aca style), ${LOOPS} loops ==="
  BAD="${WORKDIR}/scout_ingest_ps_pgid.sh"
  # Minimal wrapper with the racy run_timed only (same flock/timeout shape).
  cat >"$BAD" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
HFS="${HFS:?}"
INGEST_LOG="${INGEST_LOG:?}"
INGEST_TIMEOUT="${INGEST_TIMEOUT:-30s}"
HOOKS_TIMEOUT="${HOOKS_TIMEOUT:-30s}"
KILL_AFTER="${SCOUT_TIMEOUT_KILL_AFTER:-2s}"
LOCK="${SCOUT_INGEST_LOCK:?}"
LOCK_BUSY_RC=75
mkdir -p "$(dirname "$INGEST_LOG")"
exec 9>"$LOCK"
if ! flock -n 9; then
  echo "lock held; exiting ${LOCK_BUSY_RC}" | tee -a "$INGEST_LOG" >&2
  exit "$LOCK_BUSY_RC"
fi
run_timed() {
  local duration="$1"
  shift
  local timeout_pid pgid rc
  timeout --kill-after="$KILL_AFTER" "$duration" "$@" 9>&- &
  timeout_pid=$!
  # INTENTIONALLY RACY (3d76aca): ps before setpgid may return wrapper PGID
  pgid="$(ps -o pgid= -p "$timeout_pid" 2>/dev/null | tr -d ' ' || true)"
  set +e
  wait "$timeout_pid"
  rc=$?
  set -e
  if [[ -n "${pgid}" ]]; then
    kill -TERM -"$pgid" 2>/dev/null || true
    sleep 1
    kill -KILL -"$pgid" 2>/dev/null || true
  fi
  return "$rc"
}
set +e
run_timed "$INGEST_TIMEOUT" bash "${HFS}/scripts/ingest_metadata_to_firestore.sh" >>"$INGEST_LOG" 2>&1
ingest_rc=$?
set -e
if [ "$ingest_rc" -ne 0 ]; then
  echo "ingest failed rc=${ingest_rc}" | tee -a "$INGEST_LOG" >&2
  exit "$ingest_rc"
fi
set +e
run_timed "$HOOKS_TIMEOUT" bash "${HFS}/scripts/run_post_ingest_hooks.sh"
hooks_rc=$?
set -e
exit "$hooks_rc"
EOF
  chmod +x "$BAD"
  set +e
  run_loops "racy_ps_pgid" "$BAD"
  race_rc=$?
  set -e
  if [[ "$race_rc" -ne 0 ]]; then
    echo "RACE_REPRO: reproduced failure against ps-based pgid"
  else
    echo "RACE_REPRO: could not reproduce failure in ${LOOPS} loops (race is timing-dependent)"
  fi
fi

echo "PASS test_scout_ingest_run_timed_pgid"
exit 0
