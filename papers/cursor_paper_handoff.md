# Knowledge Engine Vision Paper — Cursor Agent Handoff
**Date:** 2026-06-07  
**File:** `papers/knowledge_engine_vision.md`  
**Journal:** Discover Artificial Intelligence (Springer Nature)  
**Status:** Major revision submitted 2026-05-28; infrastructure updates made post-submission

---

## Paper overview
- **Argument:** Knowledge engines require nine integrated capabilities; CopernicusAI is a proof-of-concept
- **Empirical content:** Lexical retrieval pilot, 30 queries, frozen corpus of 59,499 papers, nDCG@10 = 0.545
- **What it does NOT claim:** Validated superiority, production readiness, new ML algorithms

---

## Issues to fix (priority order)

### CRITICAL: Process count inconsistency — ✅ RESOLVED (2026-06-07)
Canonical count **594** is now used in Abstract, Table 3, §5, and §8. Historical reference "from 582 to 594" retained in migration narrative.

**Resolved (2026-06-07 audit):** `math_processes` = 237/237 embedded; no math top-up needed. GLMP pruned to 108 canonical IDs (see `cursor_session_handoff_for_claude.md`).

### IMPORTANT: GLMP duplicate ID note — ✅ DONE
Footnote [^glmp] added to Table 3 GLMP row (115 Firestore vs 108 canonical).

### IMPORTANT: Biology collection not mentioned — ✅ DONE
Table 3 includes "Biology (discipline charts) | 55"; §5 lists biology in process families and `biology_processes` in technology stack.

### IMPORTANT: Dense retrieval language in §6 and §7 — ✅ DONE
§7 Limitations now includes explicit paragraph distinguishing live dense retrieval from lexical-only Table 4 benchmark.

### MODERATE: Knowledge Map deserves more prominence — ✅ DONE
- §5 subsection "Knowledge Graph Navigation" added
- Table 3 row: Knowledge Map build time ~10 s
- Table 1 / §3 Communication already mention knowledge map and focus-id RAG

### MODERATE: Embedding architecture should be explicit in §3.2 — ✅ DONE
§3.2 prose expanded with single-provider rationale and Vertex 768d vs OpenAI 1536d warning.

### MINOR: Table 3 stats to verify and update
Current Table 3 values that need verification against live system:
| Stat | Paper says | Actual |
|------|-----------|--------|
| Papers indexed | 59,499 | 59,499 ✅ |
| Papers embedded | "100%" | 100% ✅ |
| Process diagrams | 582 | 594+ ⚠️ |
| Videos | 753 | 753 ✅ |
| Podcasts | 90 | 90 ✅ |
| Process families | 6 | 6 (+ biology = 7?) ⚠️ |
| Embedding model | OpenAI 3-small | ✅ |

### MINOR: Reference 17 date
Reference 17 (Programming Framework paper, Zenodo) cites 2026 — verify the
Zenodo DOI resolves and the year matches the actual deposit date.

---

## What NOT to change
- **Table 4 lexical pilot metrics** — frozen, citable, do not alter
- **30-query list in Appendix A** — frozen with SHA256
- **SHA256 hashes** for corpus and query set
- **Zenodo DOI** https://doi.org/10.5281/zenodo.18463303
- **Paper count 59,499** — matches frozen evaluation export
- **nDCG@10 = 0.545** — verified empirical result
- **"existence proof" framing** — deliberate and reviewer-approved

---

## Style and consistency notes
- The paper consistently uses "knowledge engine" (lowercase) — maintain this
- "nine capabilities" not "9 capabilities" — spell out numbers under 10
- RAG is defined on first use in Abstract — no need to re-define in body
- Citations use numeric format [N] — maintain consistency
- The Mermaid flowchart in §3.1 should render in the journal's system — verify

---

## Suggested Cursor tasks for paper work
1. Search for all instances of "582" and propose replacements with correct count
2. Draft the §7 Limitations dense retrieval paragraph (template above)
3. Draft a §5.x Knowledge Map subsection (~150 words)
4. Draft the §3.2 embedding architecture note (~75 words)
5. Verify Table 3 against `huggingface-space/knowledge-engine-status.json`
6. Check biology_processes appears correctly in all process family listings

