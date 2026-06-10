# Knowledge Engine Updates — Handoff Note for Claude

**Date:** 2026-06-07 (updated)  
**Author:** Cursor agent session (for Gary Welz)  
**Purpose:** Context for continuing work on `papers/knowledge_engine_vision.md` and the live CopernicusAI Knowledge Engine. Share this note together with the revised paper.

---

## Executive summary

Between May and June 2026, the CopernicusAI Knowledge Engine moved from a partially embedded, Vertex-dependent prototype to a **unified OpenAI stack** (embeddings + RAG chat) with **100% paper embedding coverage**, **594 JSON-canonical process charts** across six discipline families, an updated **Knowledge Engine dashboard**, and an **evaluation corpus freeze** that preserves the paper's lexical retrieval pilot while allowing infrastructure to advance.

The revised `knowledge_engine_vision.md` reflects these changes. The **published empirical benchmark remains lexical-only** (nDCG@10 = 0.545 on 30 queries); dense retrieval is live in production but not yet formally evaluated on the frozen query set.

**Post-handoff (2026-06-07):** Knowledge Map tab fixed for performance and usability — vector-seeded graph builds (~10s), prominent topic search box, node-click OpenAI RAG explanations. Frontend and backend both redeployed to Cloud Run.

---

## 1. Evaluation corpus freeze

- **When:** 2026-05-26  
- **What:** Scheduled paper ingest crons disabled; corpus export frozen at **59,499 papers**  
- **SHA256:** `3dd5e019fca5f8e823bd71020a80c534b2e1a9e7199272b27c0b13da40ee8065`  
- **Zenodo:** https://doi.org/10.5281/zenodo.18463303  
- **Runbook:** `docs/EVAL_FREEZE.md`

**Important distinction:** The freeze applies to the **evaluation export artefact**, not to all Firestore activity. Embedding backfill, process catalog rollout, and UI deploys continued afterward without invalidating the frozen export used in Section 6.

---

## 2. Embedding backfill (papers)

- **Before:** ~11,746 papers embedded (~20%)  
- **After:** **59,499 / 59,499 (100%)**  
- **Model:** OpenAI `text-embedding-3-small` (1536 dimensions)  
- **Script:** `backfill_embeddings.py` (paginated scan, OpenAI batch API, checkpoint file)  
- **Provider decision:** **Do not mix Vertex AI embeddings (768d) with OpenAI (1536d)** — single provider for index consistency

---

## 3. JSON-canonical process catalog pipeline

**Location:** `huggingface-space/scripts/process_catalog/`

| Tool | Purpose |
|------|---------|
| `schema.py` | Canonical JSON schema for process charts |
| `publish.py` | Generate `metadata.json` + `process-index.json` per family |
| `html_to_json.py` | Migrate legacy HTML to canonical JSON |
| `upload_to_gcs.py` | Publish to GCS |
| `prune_orphans.py` | Remove stale GCS/Firestore documents |
| `audit_archive.py` | Archive superseded files |

**Per-family canonical counts (June 2026):**

| Family | Count |
|--------|------:|
| GLMP v2 (biology) | 108 |
| Mathematics | 237 |
| Chemistry | 123 |
| Biology (discipline charts) | 55 |
| Computer science | 50 |
| Physics | 21 |
| **Total** | **594** |

- Legacy count in paper was **582**; migration + deduplication brought canonical total to **594**
- Superseded HTML/flat-path files archived under `huggingface-space/_archive/superseded/`
- Math family: 237 canonical JSON in `mathematics-processes-database/`

**Firestore sync scripts:**
- `cloud-run-backend/scripts/sync_math_processes.py`
- `cloud-run-backend/scripts/sync_all_process_families.py`
- Shared helpers: `process_sync_common.py`

**Firestore vector collections:**
- `glmp_processes`, `math_processes`, `chemistry_processes`, `physics_processes`, `computer_science_processes`, `biology_processes`

**Process embeddings:** OpenAI batch backfill run per family (chemistry ~117, physics ~22, CS ~51, biology ~56, math ~254 earlier).

---

## 4. Media catalogs

| Catalog | Count | Source |
|---------|------:|--------|
| `episodes-catalog.json` | 90 | Firestore episodes |
| `videos-catalog.json` | 753 | GCS `videos-metadata.json` via `--from-gcs` |

Videos and podcasts are **JSON-canonical** and surfaced in the dashboard stats. **Not yet fully in vector search** — noted as limitation in revised paper.

---

## 5. Backend: unified OpenAI RAG path

**Key file:** `cloud-run-backend/services/rag_service.py`

**LLM priority order:**
1. **OpenAI chat** (`gpt-4o-mini`, override via `OPENAI_RAG_MODEL`) when `OPENAI_API_KEY` or Secret Manager `openai-api-key` is available  
2. **Vertex Gemini** (`gemini-2.5-flash`) only if OpenAI unavailable and Vertex not disabled  
3. **Retrieval-only excerpts** if no chat model configured

**Embeddings:** Always via `get_embedding_service()` factory → OpenAI preferred (no longer gated on Vertex being enabled).

**Cloud Run config:** `DISABLE_VERTEX_AI=1` in `cloud-run-backend/cloudbuild.yaml`

**Secret Manager:** `openai-api-key` bound to compute service account — no env var required at deploy time.

**RAG metadata returned to frontend:**
```json
{
  "model": "gpt-4o-mini",
  "llm_provider": "openai",
  "retrieval_method": "vector_semantic",
  "context_items_used": 5
}
```

**Related files:**
- `cloud-run-backend/services/llm_providers/openai_rag.py` (standalone provider; main API uses `rag_service.py`)
- `cloud-run-backend/services/llm_providers/embedding_factory.py`
- `cloud-run-backend/mcp_server/tools/vector_search.py` (biology collection added; embedding gate removed)
- `cloud-run-backend/endpoints/vector_search/routes.py`
- `cloud-run-backend/endpoints/content/routes.py` (`process_family` browse support)

**Backend deployed:**
- OpenAI RAG path: `83396e87-6b58-48a5-a088-445062131465` (2026-06-06)
- Knowledge Map performance: `63adc2dc-cf0e-4c2f-b694-f1620faafff0` (2026-06-06)

---

## 6. Frontend: Knowledge Engine UI

**URL:** https://copernicus-frontend-phzp4ie2sq-uc.a.run.app/knowledge-engine

**Components:** `components/knowledge-engine/`

| Component | Updates |
|-----------|---------|
| `constants.ts` | GCS status URL, all content types, process DB links |
| `StatsDashboard.tsx` | Loads `knowledge-engine-status.json`, per-family counts |
| `SearchInterface.tsx` | All 6 process families in search |
| `ContentBrowser.tsx` | `process_family` tabs (glmp, math, chem, physics, CS, biology) |
| `KnowledgeMapView.tsx` | Prominent **Search the Knowledge Map** box; Quick Examples; RAG on node click with `focus_id`; 2-minute API timeout |
| `RAGInterface.tsx` | OpenAI provider label in banner; `llm_provider` in metadata |

**Status snapshot:** `huggingface-space/knowledge-engine-status.json` (also published to GCS)

**Frontend deploy:** SUCCESS — Cloud Build `5e93ac92-4ad8-4d01-83dd-671b26481474` (2026-06-07). Earlier builds failed because `.gitignore` rule `**/lib/` excluded Next.js `lib/auth.ts`; fixed with `!/lib/` exceptions.

---

## 6b. Knowledge Map (interactive graph)

**URL:** Knowledge Engine → **Knowledge Map** tab

**User flow:**
1. Enter a topic in **Search the Knowledge Map** → **Build Map** (or Enter)
2. Optional: discipline, date, source filters below
3. Click a paper node → OpenAI RAG explanation in the side panel (`focus_id` biases retrieval)

**Backend:** `cloud-run-backend/services/knowledge_map_service.py`
- Keyword queries **seed via vector search** (`_seed_papers_by_vector`) instead of scanning 20k Firestore docs
- Similarity edges use fast keyword overlap (not per-paper vector queries)
- Discipline aliases (`math` ↔ `mathematics`); case-insensitive source matching
- Sample query (`nilpotent group` + mathematics): **~10s**, 10 papers + concept nodes

**API:** `GET /api/knowledge-map/graph?keyword=...&max_papers=10&disciplines=mathematics&format=cytoscape&force_rebuild=true`

**Known gaps:** Process/video/podcast nodes in the map UI are not yet fully wired (content-type checkboxes exist; backend graph is paper-centric today).

---

## 7. Paper updates made (`knowledge_engine_vision.md`)

| Section | Change |
|---------|--------|
| Abstract | 594 processes, 100% embeddings, OpenAI RAG, dense live vs formal eval distinction |
| Table 1 | OpenAI path, JSON-canonical digestion, Knowledge Engine dashboard, six-family search |
| §3.2 prose | Single OpenAI provider for embeddings + RAG (no mixed dimensions) |
| Table 3 | June 2026 stats, per-family process breakdown, 100% embeddings, freeze note |
| Figure 3 | OpenAI embedding retrieval + OpenAI chat synthesis; `focus_id` |
| Technology stack | Full OpenAI path, six Firestore collections, JSON-canonical catalogs, eval freeze |
| Known limitations | Removed "20% embeddings"; added dense-eval pending, media partial, discipline coverage |
| New §5 subsection | "JSON-Canonical Process Catalogs" |
| Programming Framework § | Extended with migration narrative |
| §6 pilot | Post-freeze infrastructure vs frozen export distinction |
| §6 interpretation | Dense live; formal benchmark next step |
| §6 roadmap (A) | OpenAI dense eval, not Vertex |
| §7 limitations | Dense + RAG quality unvalidated |
| §8 conclusion | Post-freeze infrastructure achievements |
| Data availability | Backend URL, status JSON, `EVAL_FREEZE.md` |

**What did NOT change (intentionally):**
- Lexical pilot metrics (Table 4) — still authoritative published benchmark
- 30-query list and SHA256 hashes
- Zenodo DOI for evaluation bundle
- Paper count 59,499 (matches frozen export)

---

## 8. Open evaluation tasks (for Claude or future sessions)

1. **Dense retrieval benchmark (track A):** Run OpenAI dense retrieval on frozen `research_papers_20260526.jsonl.gz` against 30 queries; compare nDCG@10 to lexical 0.545. Colab notebook: `papers/retrieval_pilot_colab_bundle.ipynb` (§6b for OpenAI dense).

2. **RAG quality evaluation:** No human assessor study yet; answers are live via OpenAI but unvalidated.

3. **Media vector integration:** Embed and index videos/podcasts for unified search.

4. **GLMP Firestore normalization:** `glmp_processes` count (115) vs canonical GLMP v2 (108) — duplicate IDs documented in `knowledge-engine-status.json` notes.

5. **Knowledge Map content types:** Wire processes/videos/podcasts into graph builder (UI checkboxes exist; backend is paper-only).

6. **Optional Zenodo update:** Only if a new corpus export is taken; current paper correctly cites May 26 freeze.

---

## 9. Key URLs and paths

| Resource | Location |
|----------|----------|
| Knowledge Engine (live) | https://copernicus-frontend-phzp4ie2sq-uc.a.run.app/knowledge-engine |
| Backend API | https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app |
| RAG endpoint | `GET /api/rag/answer?question=...&content_types=...` |
| Vector search | `GET /api/vector-search/semantic?query=...` |
| Knowledge map graph | `GET /api/knowledge-map/graph?keyword=...&max_papers=10` |
| Status JSON | `huggingface-space/knowledge-engine-status.json` |
| Eval freeze runbook | `docs/EVAL_FREEZE.md` |
| Paper (revised) | `papers/knowledge_engine_vision.md` |
| GCP project | `regal-scholar-453620-r7` |

---

## 10. Suggested prompts for Claude

When sharing with Claude, you might say:

> I've attached the revised `knowledge_engine_vision.md` and a handoff note (`KNOWLEDGE_ENGINE_UPDATES_FOR_CLAUDE.md`) documenting infrastructure work done in June 2026. Please:
> 1. Review the paper for internal consistency after these updates.
> 2. Help draft Section 6 track (A) — a dense OpenAI retrieval evaluation protocol using the frozen corpus and 30-query set.
> 3. Suggest any reviewer-facing language to clarify the distinction between "live dense retrieval operational" vs "formal benchmark not yet run."
> 4. [Add your specific ask here]

---

## 11. Architecture decision record (for reference)

| Decision | Rationale |
|----------|-----------|
| OpenAI embeddings (1536d) | Cost, batch API, consistency; avoid mixing with Vertex 768d |
| OpenAI chat for RAG | Same provider as embeddings; Vertex disabled on Cloud Run |
| JSON-canonical processes | Auditable, versioned, embeddable; replaces legacy HTML |
| Evaluation freeze | Preserve citable lexical pilot; allow infra to advance separately |
| No Vertex reinstatement | Would require re-embedding entire corpus in incompatible space |

---

*End of handoff note.*
