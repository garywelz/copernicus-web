# Stub leak — Phase 1–2 findings

**Date:** 2026-07-17 (revised after Claude Chat + landing + deploy-probe writeup)  
**Status:** Diagnostic complete. Gate on `main` (`940970a4b`, observe-first). **Deploy not yet proven.** No live cleanup.  
**Artefacts:**  
- `C:\Users\garyw\exports\stub_leak_phase12_20260717.json`  
- `C:\Users\garyw\exports\stub_leak_phase12_20260717_rows.jsonl`  
- Probe: `papers/_stub_leak_phase12_probe.py`  
- Gate: `cloud-run-backend/scripts/ingest_papers_from_metadata_json.py`  
- Stability test: `cloud-run-backend/scripts/test_ingest_papers_id_stability.py`  
- Deploy checklist: `papers/STUB_GATE_PR_DRAFT_NOTES_2026-07-17.md` § Deploy probe  

---

## Critical path: prove the executed path (Yoga-only first)

**“Landed on `main`” and “fixed” are not the same sentence.**

Production cron calls Jetson’s `scout_ingest.sh` (10:30 / 20:15 ET). That entrypoint is **not in the repo**. Two failure shapes:

1. It calls a tree that has pulled `main` (wrapper + Python) → new code runs.  
2. It calls an older Python path *outside* that tree → **deploy is a silent no-op**. `main` looks fixed; the corpus keeps accruing ~97/day and climbing.

Sharper than “sync the workers”: `sync_to_jetson.sh` only `scp`s `scheduler/scout/*.py`. It does **not** ship `ingest_metadata_to_firestore.sh` or `ingest_papers_from_metadata_json.py`. So the pinned reject-log args on `main` are inert until the wrapper reaches the box some other way (full-tree `git pull`, or extend the sync script). Hardcoded `_DEFAULT_REJECT_GCS_PREFIX` still makes GCS Signal A work **if** the new Python runs.

Same defect class as the leak: an unreviewable / partially shipped ingest chain. When SSH returns: version `scout_ingest.sh`, put the wrapper on the sync path, and confirm the gate Python is on the executed path.

**You do not need SSH to resolve “is new code running?”** After the next PM run (≥ 20:15 ET), check GCS + daily stub creates from Yoga (ADC). See § Deploy probe below.

---

## Verdict

**H-remint is confirmed.** Cosine ≈ 1.0 across **1,162** vectors = one degenerate point: the engine embedded the literal string `"Untitled"` repeatedly. **Nothing to recover** — eventual deletion of the live stubs is defensible after the gate ships and reject counts are observed.

The 1,259 “new stubs” since May are not 1,259 distinct junk papers. They are repeated writes of the same empty shell, each minting a new `paper_{abs(hash(...))}` because process-salted `hash()` defeats `--skip-existing`.

### Quadratic growth (urgency)

Daily mint *count* rises by **+4/day** because the reminted **pool** grows by ~4/day. Cumulative stubs are the **integral of a rising line**, not a constant rate.

| | |
|---|---|
| Observed | Jun 26: 13/day → Jul 17: **97/day** (exact +4 each day for 21 steps) |
| Shape | Linear daily mint ⇒ **quadratic** cumulative |
| Directional Extrapolation | ~800/day by year-end, O(10⁴–10⁵) added stubs if unchecked — on the order of the real corpus |

Treat the year-end number as directional (21 days of data), not a forecast. The shape is unambiguous. The “2.25% hygiene footnote” framing is dead.

### The `--skip-existing` punchline (transferable lesson)

The flag whose purpose is **idempotency** checks existence by doc id. Random `hash()` ids **never repeat**, so the safeguard reports success every run while inserting duplicates. It did not fail loudly — it failed **invisibly**.

---

## Phase 1 — Who writes these?

### Writer
Production uses **split scheduler workers** (`SCOUT_ARCHITECTURE.md`), not the monolithic `run_daily_scout_with_ingest.sh` alone:

```
AM 10:30 ET  scout_ingest.sh  → ingest_metadata_to_firestore.sh
PM 20:15 ET  scout_ingest.sh  → ingest_metadata_to_firestore.sh
         → ingest_papers_from_metadata_json.py --skip-existing
```

Same Python writer for both slots. **One gate covers both bursts.**

Critical behaviors:
1. `title = paper.get("title") or "Untitled"`
2. Empty `sources` without pmid/arxiv/source
3. `paper_{abs(hash(...))}` — unstable across processes
4. `--skip-existing` defeated by (3)

### Two bursts explained (repo evidence; Jetson confirm still open)
2026-07-17 stub `created_at` clusters at:
- **14:30 UTC** = **10:30 EDT** → AM `scout_ingest.sh`
- **00:15 UTC** = **20:15 EDT** → PM `scout_ingest.sh`

Matches production cron in `huggingface-space/scripts/scheduler/SCOUT_ARCHITECTURE.md`. Not two different writers — **twice-daily same writer**.

### Yoga local tree
47,303 JSON files (bulk mtime 2026-06-29) — not a daily accretion trail; does not by itself explain the pool.

---

## Phase 2 — Evidence summary

| Window | Stub `created_at` count |
|---|---:|
| ≤ 2026-05-26 | **182** (= May freeze stubs) |
| \> 2026-05-26 | **1,259** |
| ≥ 2026-06-26 | **1,210** |

- Empty abstract: **100%** of 1,441  
- Embedding vectors: 1,162 → **1 cluster @ cosine 1.0**  
- May 27–Jun 15: gap (no stub creates)

---

## Fix sequence (agreed)

1. **Gate first** (stop bleeding) — reject empty/Untitled title **and** no doi/pmid/arxiv/bibcode  
   - **Must log and count every rejection** (not silent drop) — preserves upstream +4/day signal  
2. **sha256 ids** from **canonical source payload** (not title+abstract — those are empty and would collide)  
3. **Cleanup last** — delete/quarantine live stubs only after gate is live and reject metrics watched; record before/after `n`  
4. **Embed-time precondition** — skip `"Untitled"`-only text (after write gate)

**July ops snapshot** keeps all 1,441 as evidence. **May freeze** untouched at 182.

---

## Deploy probe (Yoga-only — do this before anything else)

Landed code is its own instrument. Old code cannot write reject objects under
`gs://regal-scholar-453620-r7-podcast-storage/research_data/ingest_rejects/`.
Stable ids mean `--skip-existing` should collapse remints even in **observe** mode
(no enforce needed for stub mint rate to fall).

| GCS reject object (after 10:30 + 20:15 ET) | New stubs/day | Reading |
|---|---|---|
| appears | ~0 | New code running. Gate live; remint leak stopped. |
| appears | still ~97+ | New code running **and** a **second writer** still minting stubs. Do not rationalize this away. |
| absent | ~0 | Suspicious — scout may not have run. Check before celebrating. |
| absent | ~97+ | Old code. Gate Python never reached the executed path. |

**Sync-gap footnote:** GCS appears, but local reject log is at the *guessed* (`hfs_guess`) path rather than the pinned wrapper path → new Python ran, wrapper did not. Note it; don’t shrug.

**When:** first check after the next full day of cron (both AM and PM), before enforce/cleanup/SSH rabbit holes.

---

## Gate on main

See `papers/STUB_GATE_PR_DRAFT_NOTES_2026-07-17.md`.

Defaults: `--stub-gate-mode observe`; day JSONL append + per-run GCS; sha256 of minimal identity core; conjunctive predicate; stability test green. Wrapper pins `--reject-log` / `--reject-gcs-uri`.

---

## Ask for Gary

1. **Tomorrow after 20:15 ET:** run the deploy probe (GCS + stub creates/day; note guessed vs pinned local log if SSH allows a peek).  
2. Restore Jetson SSH; version `scout_ingest.sh`; extend `sync_to_jetson.sh` to ship the ingest wrapper (and confirm gate Python is on the executed path).  
3. Only then: observe day-log ~97 → flip `enforce` → cleanup last (before/after `n`).

---

*H-remint confirmed; deploy not yet proven; unversioned cron entrypoint is the deeper structural finding.*
