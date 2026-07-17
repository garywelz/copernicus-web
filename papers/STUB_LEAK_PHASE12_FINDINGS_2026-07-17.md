# Stub leak — Phase 1–2 findings

**Date:** 2026-07-17 (revised after Claude Chat + diff review)  
**Status:** Diagnostic complete. Gate draft revised (observe-first, GCS logs, stable fingerprint). **Not committed.** No live cleanup.  
**Artefacts:**  
- `C:\Users\garyw\exports\stub_leak_phase12_20260717.json`  
- `C:\Users\garyw\exports\stub_leak_phase12_20260717_rows.jsonl`  
- Probe: `papers/_stub_leak_phase12_probe.py`  
- Gate draft: `cloud-run-backend/scripts/ingest_papers_from_metadata_json.py`  
- Stability test: `cloud-run-backend/scripts/test_ingest_papers_id_stability.py`  

---

## Critical path: restore Jetson SSH

**This is the highest-value open item — not a limits footnote.**

Committing the gate to `main` does **not** stop the leak. Production runs on Jetson via AM/PM `scout_ingest.sh`. SSH from Yoga is currently `Connection refused`. Until SSH works and the script is synced, the corpus keeps accruing **quadratically** at **10:30 and 20:15 America/New_York** regardless of git.

**Blocked after gate ships (still):** *What upstream path adds ~4 new unidentifiable payloads per day?* That needs Jetson logs/JSON. The observe-mode reject log on **GCS** keeps the signal readable off-box once the script is actually running there.

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

## Gate draft (revised — still not committed)

See `papers/STUB_GATE_PR_DRAFT_NOTES_2026-07-17.md` and the four-check table there.

Defaults: `--stub-gate-mode observe`; full payload → local JSONL + `gs://…/research_data/ingest_rejects/`; sha256 after stripping `acquired_date` etc.; conjunctive predicate; stability test green.

---

## Ask for Gary

1. Read the **current** diff (not the first draft).  
2. Restore Jetson SSH (critical path).  
3. Then commit → sync → observe 2 days → flip `enforce` → cleanup last.

---

*H-remint confirmed; SSH is the critical path; gate draft awaits your read of the revised diff.*
