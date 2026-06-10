eir.# CopernicusAI Software Handoff — Cursor Agent
**Date:** 2026-06-07  
**Repo:** `~/copernicus-web-public`  
**For:** Cursor agent continuing infrastructure work

---

## Current system state (as of 2026-06-07)

### What's working
- **59,499 research papers** in Firestore (`research_papers` collection), 100% embedded with OpenAI `text-embedding-3-small` (1536d)
- **594 JSON-canonical process diagrams** across 6 discipline families in Firestore and GCS
- **Vector search** operational via `/api/vector-search/semantic`
- **RAG** operational via `/api/rag/answer` using `gpt-4o-mini`
- **Knowledge Map** tab working (~10s build time, vector-seeded)
- **Frontend** deployed: https://copernicus-frontend-phzp4ie2sq-uc.a.run.app/knowledge-engine
- **Backend** deployed: https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app

### Key config
| Parameter | Value |
|-----------|-------|
| GCP Project | `regal-scholar-453620-r7` |
| Firestore database | `copernicusai` |
| Embedding model | `text-embedding-3-small` (1536d, OpenAI only) |
| RAG model | `gpt-4o-mini` (override via `OPENAI_RAG_MODEL`) |
| Vertex AI | **DISABLED** (`DISABLE_VERTEX_AI=1` in cloudbuild.yaml) |

### Firestore collections
| Collection | Count | Embedded |
|------------|------:|---------|
| `research_papers` | 59,499 | ✅ 100% |
| `glmp_processes` | 108 | ⚠️ 4/108 embedded — backfill 104 after 2026-06-07 prune |
| `math_processes` | 237 | ✅ 100% |
| `chemistry_processes` | 173 | ✅ embedded (123 canonical; ~50 Firestore orphans) |
| `physics_processes` | 28 | ✅ embedded (21 canonical; ~7 orphans) |
| `computer_science_processes` | 72 | ✅ embedded (50 canonical; ~22 orphans) |
| `biology_processes` | 56 | ✅ 100% embedded |
| `episodes` | 90 | ❌ Not yet in vector search |
| `podcast_jobs` | varies | ❌ Not indexed |

---

## Open tasks (priority order)

### 1. GLMP embedding backfill (104 docs) — after 2026-06-07 prune
Firestore `glmp_processes` is **108 canonical IDs** (pruned via `prune_glmp_processes.py`).
Only 4 docs retain embeddings; re-embed the collection:
```bash
cd ~/copernicus-web-public
source venv_embeddings/bin/activate
export OPENAI_API_KEY='sk-...'
python backfill_embeddings.py --submit --collection glmp_processes
python backfill_embeddings.py --check && python backfill_embeddings.py --write
```

### 2. GCS/Firestore orphan prune (chem, CS, physics, GLMP JSON)
Canonical counts < Firestore totals for chemistry (123 vs 173), CS (50 vs 72), physics (21 vs 28).
Extend `prune_orphans.py` beyond math-only or run family-specific prunes before next sync.

### 3. ~~Math processes top-up~~ — NOT NEEDED
Audit 2026-06-07: `math_processes` = **237/237 embedded**, matches `mathematics-processes-database/metadata.json`.

### 4. Wire biology into frontend search — ✅ DONE (verify only)
`SearchInterface.tsx`, `ContentBrowser.tsx`, `constants.ts`, and `KnowledgeMapView.tsx` already include `biology` / `biology_processes`. No code change needed unless search API regressions appear.

### 5. Dense retrieval benchmark (track A) — **Claude task**
Full protocol: `papers/dense_retrieval_benchmark_handoff.md`
Session context: `papers/cursor_session_handoff_for_claude.md`

### 6. Embed and index videos/podcasts
753 videos and 90 podcasts are cataloged but not in vector search.
- Source: `huggingface-space/knowledge-engine-status.json`
- Add `videos` and `episodes` to `backfill_embeddings.py` ALL_COLLECTIONS
- Wire into `vector_search.py` (add `COLLECTION_VIDEOS`, `COLLECTION_EPISODES`)
- Wire into Knowledge Map graph builder

### 7. Knowledge Map: wire process/video/podcast nodes
UI checkboxes exist in `KnowledgeMapView.tsx` for content types beyond papers.
Backend `knowledge_map_service.py` is paper-only today.

---

## Do NOT do
- **Do not re-enable Vertex AI** — would require re-embedding entire corpus in 768d space
- **Do not mix embedding providers** — all embeddings must be OpenAI 1536d
- **Do not change the frozen evaluation corpus** — `research_papers_20260526.jsonl.gz` is citable
- **Do not delete `embedding_checkpoint.json`** until backfill is fully verified
- **Do not commit `.env` files, API keys, or `venv_embeddings/`**

---

## Key files
| File | Purpose |
|------|---------|
| `backfill_embeddings.py` | Embedding backfill (paginated, batch API, checkpoint) |
| `cloud-run-backend/mcp_server/config.py` | All collection names and GCP config |
| `cloud-run-backend/services/rag_service.py` | RAG pipeline (OpenAI primary) |
| `cloud-run-backend/mcp_server/tools/vector_search.py` | Vector search across all collections |
| `cloud-run-backend/services/knowledge_map_service.py` | Knowledge Map graph builder |
| `components/knowledge-engine/SearchInterface.tsx` | Frontend search |
| `components/knowledge-engine/KnowledgeMapView.tsx` | Knowledge Map UI |
| `huggingface-space/scripts/process_catalog/` | JSON-canonical process pipeline |
| `cloud-run-backend/scripts/sync_all_process_families.py` | Firestore sync for all process families |
| `docs/EVAL_FREEZE.md` | Evaluation freeze runbook |

---

## Deployment
```bash
# Backend
cd cloud-run-backend
gcloud builds submit --config cloudbuild.yaml

# Frontend  
cd ..
gcloud builds submit --config cloudbuild-frontend.yaml
```

