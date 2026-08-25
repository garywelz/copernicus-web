# Handoff — 25 August 2026 (PR #6 merged; glmp synced; checkout status)

**From:** Claude Code
**To:** Cursor
**Repos:** `copernicus-web` @ `57fd620e8` (main, origin), `glmp` @ `0cf417d` (main, origin)
**Regenerate from a fresh fetch before acting.**

Share this file as-is. Continues `papers/claude_code_handoff_2026-08-23_leftover_picks.md`.

---

## What closed this session

**`copernicus-web` PR #6 — merged.** The 5 commits on `cursor/ingest-synthesize-citations`
(citations[] synthesis fix, 13-chart leftover-pick attaches, Gaifman
Gödel/Cantor-walk episode listings + ATAP proof-graph attaches, opt-in player
credits) were reviewed commit-by-commit, both test scripts run and passing
(`test_ingest_papers_id_stability.py`, `package_credits.py --self-test`), then
pushed and merged into `main` (merge commit `57fd620e8`). Branch deleted, local
and remote.

**`glmp` synced to match.** The same 12 process-chart citation fixes
(Sourjik, Levine/Kroemer, Xie/Klionsky, etc. — verified identical to the
copernicus-web versions) were sitting **uncommitted** in the `glmp` working
tree, per the "both trees" instruction in the 23 August handoff. Committed
(`63a6e76`) and pushed. A separate, unrelated doc fix
(`docs/open-questions/loop-audit-candidates-2026-08-04.md` — corrected a
misdiagnosis: `normalize()` already lowercases/collapses whitespace, so the
actual gap is same-entity-different-wording with no shared substring, not
case/whitespace variants) was also committed separately (`0cf417d`) and
pushed.

Both repos are now clean of anything from this work and in sync with
`origin/main`.

---

## Still open — needs your read

**The 23 August reply block was never answered as far as I can tell.**
`papers/claude_code_handoff_2026-08-23_leftover_picks.md` has a reply block
(4a Qi 16105880, Cox RecA leftover, Zeng→DiRusso keep/revert, Section C ~90
rows, collection-remainder accept/reject) addressed to Gary for you to apply.
I have no record of it being filled in or applied. Confirm with Gary before
assuming it's stale.

**Uncommitted state in the `copernicus-web` checkout** (not touched by me,
flagging per the shared-checkout note):
- Modified: `cloud-run-backend/content_fixes.py`,
  `cloud-run-backend/elevenlabs_voice_service.py`,
  `cloud-run-backend/tests/unit/test_content_fixes.py`, `tsconfig.tsbuildinfo`
- ~55 untracked files — `huggingface-space/scripts/acquire_papers/*` (batch
  apply/search/verify scripts, several `*.jsonl` reports), `papers/_*` scratch
  files, `nsf-proposal/*` (résumé docs — looks personal/unrelated, worth
  checking it isn't accidentally sitting in this repo), a few root-level audit
  docs (`COPERNICUS_LEGACY_AUDIT.md`, `REORG_PLAN_UPDATE_SPEC.md`,
  `SUITE_REORG_PLAN (1).md`), and some standalone scripts
  (`corpus_audit.py`, `execute_glmp_sync*.py`, `run_prune_glmp_local.py`,
  `targeted_sync_glmp.py`).

If this is your in-progress work, no action needed from me — just noting it
survived the branch switch/merge untouched. If any of it is done and should
be committed, say so and I can review + commit on request.

**Uncommitted state in the `glmp` checkout** (same caveat): ~15 untracked
files under `collaborations/krampis-virtual-cell/` (harvest TSVs/scripts,
`net_new_papers.tsv`, `reference_works.tsv`, draft docs) plus two root docs
(`docs/KNOWLEDGE_ENGINE_BROWSE_LINKS_HANDOFF_2026-07-17.md`,
`docs/glmp-square-one-redraft.md`) and `scripts/master_todo_cron_python.sh`,
`scripts/_tmp_recovery_probe.py`. Same question — yours to commit or leave.

---

## Claude Code — first moves if Gary opens you next

1. Fresh-fetch this file and confirm the two merge/commit SHAs above are
   still the tips of `main` on both repos before trusting anything else here.
2. Do not touch the uncommitted files listed above without Cursor confirming
   what they are.
3. If Gary wants the 23 August reply block resolved, that decision is his to
   make, not mine — surface the block, don't fill it in.
