# Handoff — 25 August 2026 (reply: leftover block closed; checkout status)

**From:** Cursor
**To:** Claude Code
**Repos:** `copernicus-web` @ `025084b91` (main, origin), `glmp` @ `0cf417d` (main, origin)
**Regenerate from a fresh fetch before acting.**

Share this file as-is. Replies to
`papers/cursor_handoff_2026-08-25_pr6_merge_and_glmp_sync.md`.
Continues `papers/claude_code_handoff_2026-08-23_leftover_picks.md`.

Do **not** regenerate `ever-bio-260009` or `ever-bio-260010`.
Do **not** attach Section C leftovers. Do **not** revert Zeng→DiRusso.
Do **not** use `--include-glob "**/chart_repair*.json"`.
Do **not** touch the uncommitted piles listed below unless Gary names a file.

---

## Fresh-fetch confirmation

Both tips match your 25 August note, plus the handoff commit you pushed:

| Repo | Tip of `origin/main` |
|---|---|
| `copernicus-web` | `025084b91` (your handoff). Merge of PR #6 is the parent: `57fd620e8` |
| `glmp` | `0cf417d` (loop-audit doc). Citation sync parent: `63a6e76` |

Working trees still have the uncommitted/untracked files you listed. I did not touch them.

---

## 23 August reply block — answered and applied (not stale)

The markdown checkboxes in
`papers/claude_code_handoff_2026-08-23_leftover_picks.md` were never filled in.
That is why the block looked unanswered. **Gary + Claude Code decided on 23 August;
Cursor applied the same day.** The filled packet is
`papers/LEFTOVER_HUMAN_PICK_2026-08-22.md` (OPEN PICKS at top). Chart rows are on
both trees and were in PR #6 (`f9dd6a05f` and the merge).

Filled block (historical — do not re-apply):

```
4a Qi 16105880 (glance/review, no publisher abstract):
  [x] write Gary-approved editorial synopsis then attach
      APPLIED 23 Aug both trees yeast_cell_cycle_control
      paper_id pubmed_16105880  DOI 10.1242/jcs.02470
      KE editorial synopsis; live resolve identifier

Cox RecA leftover on ecoli_sos_response (CW + glmp sources[2]):
  [x] B4b 10506835 Cox 1999 — stored YEAR + sole author Cox MM; has abstract
      APPLIED 23 Aug both trees ecoli_sos_response
      ingested leftover_pick_pubmed_10506835.json; citations[] patched
      live resolve identifier

Zeng → DiRusso 1569108 already attached on CW ecoli_fatty_acid_degradation:
  [x] keep
      CW-only (glmp twin never had the Zeng leftover)

Section C (~90 leftover-note rows):
  [x] leave all

Collection leftover-stripped remainder:
  [x] accepted remainder — identity+GAL goal closed 23 Aug after Cox/4a
```

Named leftovers still stripped on purpose: Knowles 2009 BamA; Umbarger 1969
Feedback control; the rest of C/D. Unique leftover repairs exist: **no**.
GAL `ever-bio-260010` is still Platt DOI `10.1093/emboj/17.14.4086` with
`animation_player_url`. 260009/260010 were not regenerated.

`papers/_staged_leftover_picks/README.md` is **stale** (still says “not applied”).
The live charts are the source of truth. Leave that directory untracked.

---

## Uncommitted state — Cursor’s classification

Leave everything below as-is unless Gary asks to commit a named subset.
Do not add `nsf-proposal/` or `tsconfig.tsbuildinfo` to git.

### `copernicus-web` — done, not committed (ready if Gary says commit)

TTS-only Gödel/Kleene pronunciation (23 Aug). Audio path respells Gödel→Girdle
and Kleene→Klaynee; stored scripts/transcripts keep the scholarly spelling.
Unit tests added. **Not deployed.** Existing `260001`/`260002` audio will not
change until a Cloud Run deploy + regenerate.

- Modified: `cloud-run-backend/content_fixes.py`
- Modified: `cloud-run-backend/elevenlabs_voice_service.py`
- Modified: `cloud-run-backend/tests/unit/test_content_fixes.py`

Gary said “not for now” on more mathematician episodes. Code is finished;
commit+deploy is a Gary call, not in-flight.

### `copernicus-web` — do not commit

| Path | What it is |
|---|---|
| `tsconfig.tsbuildinfo` | generated |
| `nsf-proposal/Gary_Welz_Resume*` | personal résumé — **not this repo** |
| `COPERNICUS_LEGACY_AUDIT.md`, `REORG_PLAN_UPDATE_SPEC.md`, `SUITE_REORG_PLAN (1).md` | unrelated planning drafts |
| `huggingface-space/scripts/acquire_papers/{apply,search,verify,hunt,audit,lookup}_*` plus `*.jsonl` reports | leftover-hunt scratch from the closed identity pass |
| `papers/_*` (`_staged_leftover_picks/`, `_cantor_rewrite_tmp/`, `_REVIEW_DIFF_*`, `_stub_leak_*`, `_task3_*`) | scratch / stale staging |
| `papers/cursor_handoff_2026-08-20_item26.md` | old item, leave |
| `corpus_audit.py`, `execute_glmp_sync*.py`, `run_prune_glmp_local.py`, `targeted_sync_glmp.py` | one-off sync/audit scripts |
| `public/cantor-diagonal-animation/render_illustrations.py` | local render helper |
| `collaborations/krampis-virtual-cell/files (2)/` | stray copy, not this repo’s lane |

None of that is active Cursor work.

### `glmp` — do not commit unless Gary names a file

July 2026 harvest/review leftovers, not current work:

- `collaborations/krampis-virtual-cell/` harvest TSVs, `net_new_papers.tsv`,
  `reference_works.tsv`, `flowchart-source-papers.harvested.tsv`, draft docs,
  `_rule2_*` probes
- `docs/KNOWLEDGE_ENGINE_BROWSE_LINKS_HANDOFF_2026-07-17.md`
- `docs/glmp-square-one-redraft.md`
- `scripts/_tmp_recovery_probe.py`
- `scripts/master_todo_cron_python.sh` — Jetson cron wrapper from 6 July;
  never landed on `origin/main` in this clone. Live Jetson may already have
  a copy. Do not commit without Gary saying the Yoga file is the canonical one.

---

## Claude Code — first moves if Gary opens you next

1. Fresh-fetch. Trust `025084b91` / `0cf417d`. Do not re-do leftover attaches.
2. Do not touch the uncommitted piles. If Gary wants the TTS pronunciation
   committed, review those three `cloud-run-backend` files only and leave
   everything else out.
3. No leftover-identity work remains unless Gary names a Section C chart.
