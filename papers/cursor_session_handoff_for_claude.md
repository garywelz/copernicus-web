# Cursor Session Handoff for Claude

**Date:** 2026-06-07  
**From:** Cursor agent (infrastructure + paper alignment)  
**To:** Claude (paper prose **review** after metrics; no Colab/API execution)  
**Repo:** `~/copernicus-web-public`

Share this document together with:
- `papers/dense_retrieval_benchmark_handoff.md` (track A protocol)
- `papers/knowledge_engine_vision.md` (already updated for June 2026)
- `papers/KNOWLEDGE_ENGINE_UPDATES_FOR_CLAUDE.md` (broader context)

---

## Executive summary

Cursor completed evaluation freeze enforcement, 100% paper embedding backfill, JSON-canonical process catalog rollout (594 charts), unified OpenAI RAG deploy, Knowledge Map fixes, paper alignment to live infrastructure, and **GLMP Firestore reconciliation** (115 legacy → **108 canonical**). Lexical Table 4 (nDCG@10 = 0.545) remains frozen. **Track A dense benchmark is not yet run** — see dense handoff doc.

---

## Actions taken (chronological)

### 1. Evaluation freeze
- Disabled scout/cron ingest jobs
- Documented in `docs/EVAL_FREEZE.md`
- Frozen export: 59,499 papers, SHA256 `3dd5e019…`, Zenodo https://doi.org/10.5281/zenodo.18463303

### 2. Embedding backfill
- `research_papers`: **59,499 / 59,499** embedded (`text-embedding-3-small`, 1536d)
- Process families embedded via `backfill_embeddings.py` (batch API)
- **Vertex AI disabled** for embeddings and chat (`DISABLE_VERTEX_AI=1` in `cloudbuild.yaml`)

### 3. JSON-canonical process pipeline
- Tools: `huggingface-space/scripts/process_catalog/` (`schema.py`, `publish.py`, `html_to_json.py`, `upload_to_gcs.py`, `prune_orphans.py`)
- **594** canonical processes across **6 families** (not 7 — GLMP biology pathways + separate biology discipline charts; footnote [^glmp] in paper)

| Family | Canonical JSON | Firestore collection |
|--------|---------------:|----------------------|
| GLMP v2 | 108 | `glmp_processes` |
| Mathematics | 237 | `math_processes` |
| Chemistry | 123 | `chemistry_processes` |
| Biology (discipline) | 55 | `biology_processes` |
| Computer science | 50 | `computer_science_processes` |
| Physics | 21 | `physics_processes` |

### 4. OpenAI RAG stack (Cloud Run)
- `cloud-run-backend/services/rag_service.py`: OpenAI chat (`gpt-4o-mini`) → Vertex fallback → retrieval-only
- Embeddings via factory (OpenAI preferred)
- Deployed: `copernicus-podcast-api` (builds `83396e87`, `63adc2dc`, …)

### 5. Knowledge Map fixes
- **Root causes:** 30s frontend timeout; stale React state on Quick Examples; backend scanned 20k docs + per-paper vector queries
- **Fixes:** `_seed_papers_by_vector` in `knowledge_map_service.py`; keyword-only similarity edges; discipline aliases; 120s timeout; prominent search box in `KnowledgeMapView.tsx`
- Verified: `nilpotent group` + mathematics → ~10s, 10 papers + concept nodes
- Deployed frontend build `8daf2236`

### 6. Frontend deploy fix
- `.gitignore` excluded `lib/` → broke `lib/auth.ts`; added `!/lib/` exception; restored auth module

### 7. Paper updates (`papers/knowledge_engine_vision.md`)
- 594 processes, 100% embeddings, OpenAI RAG, Knowledge Map §5 subsection, §3.2 single-provider note, §7 dense-retrieval disclaimer, GLMP footnote
- **Unchanged intentionally:** Table 4 lexical metrics, 30-query SHA256, corpus SHA256, Zenodo DOI, nDCG@10 = 0.545

### 8. GLMP prune (executed 2026-06-07)

**Problem (audit):** Firestore had **115** docs; canonical `glmp-v2/metadata.json` has **108**. Only **4** doc IDs matched canonical; **111** used legacy prefixed IDs from `sync_glmp_processes.py` (`ecoli-ecoli_aerobic_respiration` instead of `ecoli_aerobic_respiration`).

**Actions:**
1. Added `cloud-run-backend/scripts/prune_glmp_processes.py`
2. **Pass 1:** Deleted **111** legacy docs; re-synced from GCS via `process_sync_common.py` (uses JSON `id` field correctly)
3. GCS bucket lists **221** JSON blobs under `glmp-v2/processes/` (includes legacy duplicates); sync wrote docs with non-canonical IDs from orphan files
4. **Pass 2:** `--apply --skip-resync` deleted **6** remaining non-canonical IDs:
   - `ecoli_e._coli_dna_replication_elongation`
   - `ecoli_e._coli_envelope_stress_response`
   - `process_DNA Repair_e.-coli-sos-response`
   - `process_Gene Regulation_arabinose-operon-and-arac-dual-regulation`
   - `process_Gene Regulation_lac-operon-regulation`
   - `process_Signal Transduction_two-component-signal-transduction-(envz-ompr-paradigm)`

**Result:** `glmp_processes` = **108 / 108** canonical IDs, **0 missing** from metadata.

**Follow-up required (software, not paper):**
- **104 / 108** GLMP docs lack `embedding` field (only 4 pre-existing bacillus docs embedded). Run:
  ```bash
  cd ~/copernicus-web-public
  source venv_embeddings/bin/activate
  export OPENAI_API_KEY='...'
  python backfill_embeddings.py --submit --collection glmp_processes
  # then --check / --write
  ```
- **GCS cleanup:** prune ~113 orphan JSON files under `glmp-v2/processes/` so future syncs cannot reintroduce stray IDs (use `prune_orphans.py` extended for GLMP, or metadata-driven sync only)
- **Deprecate** `sync_glmp_processes.py` path-derived ID logic; use `process_sync_common.py` + metadata IDs

---

## Live Firestore audit (2026-06-07)

| Collection | Total | Embedded | Notes |
|------------|------:|---------:|-------|
| `research_papers` | 59,499 | 59,499 | ✅ |
| `math_processes` | 237 | 237 | ✅ matches canonical |
| `biology_processes` | 56 | 56 | ✅ (canonical 55 + 1 index/metadata doc — verify) |
| `glmp_processes` | **108** | **4** | ⚠️ embedding backfill needed |
| `chemistry_processes` | 173 | 173 | canonical 123 — **50 Firestore orphans** |
| `computer_science_processes` | 72 | 72 | canonical 50 — **22 orphans** |
| `physics_processes` | 28 | 28 | canonical 21 — **7 orphans** |

### Corrections to stale handoff claims

| Stale claim (old handoffs) | Actual |
|-----------------------------|--------|
| Math top-up ~200 new docs needed | **False** — math is 237/237 embedded |
| `math_processes` ~254 | **237** |
| GLMP “7 duplicate IDs” | **111 legacy prefixed IDs + 6 GCS orphan JSONs** — now pruned to 108 |
| Biology embeddings missing | **56/56 embedded** |
| Process families = 7 | **6 families** in Table 3 (+ GLMP footnote) |

---

## Deployed URLs

| Service | URL |
|---------|-----|
| Knowledge Engine UI | https://copernicus-frontend-phzp4ie2sq-uc.a.run.app/knowledge-engine |
| API | https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app |

GCP project: `regal-scholar-453620-r7` · Firestore DB: `copernicusai`

---

## What Claude should do next (priority)

1. **Review** Cursor-drafted §6 dense prose + Table 4 column after Gary pastes metrics and draft
2. **Optional:** Zenodo deposit description, abstract sentence polish, interpretation
3. **Verify Reference 17** Zenodo DOI https://doi.org/10.5281/zenodo.18463441 (2026 v2) — already checked by Cursor
4. **Do not** change frozen lexical Table 4 or reword existence-proof framing without Gary’s approval

---

## What remains for Cursor / infrastructure (lower priority)

| Task | Status |
|------|--------|
| GLMP embedding backfill (104 docs) | Pending |
| GCS orphan prune: chem, CS, physics, GLMP JSON | Pending |
| `prune_orphans.py` — generalize beyond `math_processes` | Pending |
| Add GLMP to `sync_all_process_families.py` | Pending |
| Videos/podcasts vector indexing | Not started |
| Knowledge Map: process/video/podcast backend nodes | UI checkboxes only |

---

## Key file index

| Topic | Path |
|-------|------|
| Paper | `papers/knowledge_engine_vision.md` |
| Dense benchmark protocol | `papers/dense_retrieval_benchmark_handoff.md` |
| Colab bundle | `papers/retrieval_pilot_colab_bundle.ipynb` |
| Judgments | `papers/judgments.csv` |
| Lexical manifest | `papers/manifest.json` |
| GLMP prune script | `cloud-run-backend/scripts/prune_glmp_processes.py` |
| Process sync | `cloud-run-backend/scripts/process_sync_common.py` |
| RAG | `cloud-run-backend/services/rag_service.py` |
| Knowledge map | `cloud-run-backend/services/knowledge_map_service.py` |
| Eval freeze | `docs/EVAL_FREEZE.md` |
| Status JSON | `huggingface-space/knowledge-engine-status.json` |

---

## Scripts added/modified this session

- **New:** `cloud-run-backend/scripts/prune_glmp_processes.py` — canonical-ID prune + optional GCS re-sync
- **Updated:** `papers/knowledge_engine_vision.md`, handoff docs, Knowledge Map components, RAG service, `.gitignore`

---

*End of handoff. Questions on infrastructure → Cursor; paper voice and benchmark interpretation → Claude + Gary.*
