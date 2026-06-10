# CopernicusAI Knowledge Engine — Agent Task Organization

**Date:** February 11, 2025  
**Purpose:** Organize long-running agents to populate Research Paper Database and Scientific Video Database, and meld them into Knowledge Engine tools.

**Reference:** [Public Project Interface](https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/copernicusai-public-reviewer.html)

---

## Current State Summary

| Component | Current Count | Target | Status |
|-----------|---------------|--------|--------|
| Research Papers | 54,509 | 100,000 | Firestore; **11,746** with embedding (**21.55%** of total); see `/api/content/stats` |
| Scientific Videos | 753 | 2,000 | From status publish (Cloud SQL); not yet on `/api/content/browse`; plan batch/daily ingest similar to papers |
| Processes (Firestore GLMP) | 115 | 1,000 | `glmp_processes` only — used by Content API `content_type=processes`. |
| PF processes (GCS metadata sum) | **472** | 1,000 | [GLMP v2](https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/glmp-database-table.html) **108** + math **217** + bio **20** + chem **56** + physics **21** + CS **50** — from public `metadata.json` per family (see `knowledge-engine-status.json` → `process_databases`). |
| Podcasts | 86 | 500 | Firestore; separate pipeline |

*Live totals: Cloud Run `GET /api/content/browse` (papers, processes, podcasts) and `GET /api/content/stats` (embeddings); **as of 20 April 2026** — resync with `scripts/generate_status_page.py --source api` (adds `process_databases` from GCS).*  
**108 vs 115:** The [GLMP table](https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/glmp-database-table.html) reads [`glmp-v2/metadata.json`](https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/glmp-v2/metadata.json) (`totalProcesses` = **108**). Firestore has **115** documents: **four** are duplicate Bacillus rows (two ID styles, e.g. `bacillus-bacillus_*` vs `bacillus_*`), **two** are extra *E. coli* variant IDs (`ecoli_e._coli_*`), and **one** is a stray `metadata` document — not Krampis V1–V6 demo slots and not the mathematics / other discipline DBs (those are separate rows in the **472** sum).*

**Knowledge Engine Tools:** [Research Tools Dashboard](https://copernicus-frontend-phzp4ie2sq-uc.a.run.app/knowledge-engine) — Knowledge Map, RAG, Vector Search

## Ingest-first and embedding A/B (background plan)

**Last updated:** April 20, 2026

- **Metadata ingest:** Keep running at the current rate using the **Daily Scout cron** (and the metadata → Firestore ingest path you use with it). As volume grows, revisit **mix** by **source** (PubMed, arXiv, NASA ADS, Crossref, etc.) and **subject/discipline** so the corpus stays useful for a future **stratified** comparison, not just a single big count.
- **Embeddings / vectors:** **Defer** large-scale bulk embedding until a defined **eval window** (on the order of **~100k+ papers** with a planned stratification, plus a **query + relevance** plan for a fair **Vertex vs OpenAI**-style A/B). Until then, growing **metadata only** is fine for tables, counts, and browse.
- **If ingest feels too slow:** Use **larger batch** backfills and/or run them **overnight** (`acquire_*_batch.py` and related scripts, checkpoints in `paper_acquisition_logs/`) so daytime quotas stay comfortable; prefer **idempotent** / resumable runs.
- **Priority:** This is **not urgent**—the pipeline can run **in the background for a few weeks** while other work takes focus; check counts or mix on a **weekly** cadence if helpful.
- **Rough timeline (illustrative):** At about **1,000 papers per day**, **~7 weeks** adds on the order of **~49,000** papers, which (from a **~55k** current baseline — see *Current State Summary*) approaches **>100,000** total. **Mid-June 2026** is a reasonable time to start **scoping** embedding A/B (dual fields or indexes, same text to both providers, reported cost/latency and retrieval metrics). Exact dates depend on the live count when you read this.

### Process & podcast growth (batched, collaborative)

- **Process charts (PF):** Increase toward the **1,000** target with **prompted batches** that you specify, **spread across subjects** (GLMP, biology, chemistry, physics, mathematics, computer science) so the catalog stays balanced rather than one family running ahead.
- **Podcasts:** Increase toward the **500** target in part through **CUNY students** supplying prompts for **additional episodes**—treat as a parallel, human-curated expansion path alongside automated or staff-driven generation; document review and quality expectations in the podcast workflow as volume grows.

---

## Task Organization: Three Agent Tracks

### Track 1: Research Paper Database Population Agent

**Goal:** Scale from current Firestore total (~55k+; see *Current State Summary*) toward **100,000** papers (reset milestone); feed into Knowledge Engine (embeddings, knowledge graph, RAG).

**Daily volume (cron + Ralph Wiggum):** See **`DAILY_PAPER_AGENT_RALPH_WIGGUM.md`** — tune `papers_per_source_per_day` and `total_papers_per_day` in `daily_scout_config.json`.

#### 1.1 Existing Infrastructure (Leverage)

- **Daily Scout** (`scripts/acquire_papers/daily_scout_runner.py`)
  - Runs PubMed, arXiv, NASA ADS
  - ~100–200 papers/source/day via `daily_scout_config.json`
  - Designed for Ralph Wiggum / cron (e.g., 2:00 AM UTC)
- **Batch Acquisition Scripts**
  - `acquire_pubmed_batch.py` — Biology/medicine
  - `acquire_arxiv_batch.py` — Physics, CS, math, q-bio
  - `acquire_nasa_ads_batch.py` — Astronomy/astrophysics
  - `acquire_crossref_batch.py` — Multi-publisher, DOI-based
- **Post-processing:** `deduplicate_papers.py`, `validate_metadata.py`
- **Metadata generation:** `generate_papers_metadata.py` → `papers-metadata.json`

#### 1.2 Agent Tasks (Long-Running)

| Task | Description | Schedule | Output |
|------|-------------|----------|--------|
| **Paper Scout Agent** | Run Daily Scout (PubMed, arXiv, NASA ADS) | Daily 2 AM UTC | `metadata-database/papers/daily_scout/` |
| **Paper Backfill Agent** | Run batch scripts for large historical backfills (e.g., 5K–10K per source) | Weekly or on-demand | `metadata-database/papers/{discipline}/` |
| **Paper Deduplication Agent** | Deduplicate across sources | After each Scout run | `metadata-database/papers_deduplicated/` |
| **Paper Metadata Sync Agent** | Regenerate `papers-metadata.json`, upload to GCS | After dedup or daily | GCS + papers-database-table.html |
| **Paper → Knowledge Engine Sync Agent** | Push new papers to Firestore/Vertex AI for embeddings & graph | After metadata sync | Knowledge Engine backend |

#### 1.3 Suggested Workflow

```
Daily Scout (cron) → Deduplicate → Metadata Sync → Knowledge Engine Sync
     ↑                      ↑              ↑                  ↑
  Agent 1               Agent 2         Agent 3            Agent 4
```

**Backfill (parallel, on-demand):**
- Run `acquire_pubmed_batch.py`, `acquire_arxiv_batch.py`, etc. in separate processes
- Each can run for hours; use checkpoints (`.ckpt` files in `paper_acquisition_logs/`)

---

### Track 2: Scientific Video Database Population Agent

**Goal:** Grow video collection; unify DB (753) and web (106) sources; integrate with Knowledge Engine.

#### 2.1 Current State

- **PostgreSQL (Cloud SQL):** 753 videos — primary source
- **Web app:** 106 videos — subset or different collection
- **Export script:** `scienceviddb/scripts/export_videos_metadata.ts` (needs DB connection)
- **Viewer:** `videos-database-table.html` — ready, needs `videos-metadata.json`

#### 2.2 Agent Tasks (Long-Running)

| Task | Description | Schedule | Output |
|------|-------------|----------|--------|
| **Video Export Agent** | Export 753 videos from PostgreSQL → JSON | Weekly or after DB updates | `videos-metadata.json` |
| **Video Ingestion Agent** | Ingest new videos (YouTube API, manual lists, etc.) | Daily or on-demand | PostgreSQL + JSON |
| **Video Metadata Sync Agent** | Regenerate metadata, upload to GCS | After export/ingestion | GCS + videos-database-table.html |
| **Video → Knowledge Engine Sync Agent** | Push video metadata to Knowledge Engine (embeddings, RAG) | After metadata sync | Knowledge Engine backend |

#### 2.3 Suggested Workflow

```
Video Ingestion (YouTube, etc.) → PostgreSQL
         ↓
Video Export Agent → videos-metadata.json → GCS
         ↓
Video → Knowledge Engine Sync Agent
```

**Immediate next steps (from VIDEO_DATABASE_ENHANCEMENT_PLAN.md):**
1. Run export script (Cloud SQL Proxy or Cloud Shell)
2. Generate `videos-metadata.json`
3. Upload HTML + JSON to GCS
4. Add video ingestion pipeline (YouTube Data API, curated lists)

---

### Track 3: Knowledge Engine Integration (Meld)

**Goal:** Ensure Papers and Videos flow into the Research Tools Dashboard and Public Interface.

**How-to (ingest, videos, status JSON):** see **`TRACK3_KNOWLEDGE_ENGINE_SYNC.md`**.  
**Papers (JSON → Firestore):** `cloud-run-backend/scripts/ingest_papers_from_metadata_json.py`.  
**Status JSON (API-backed counts + GCS upload):** `scripts/generate_status_page.py`, **`scripts/publish_knowledge_engine_status.sh`**.

#### 3.1 Integration Points

- **Knowledge Engine Dashboard:** https://copernicus-frontend-phzp4ie2sq-uc.a.run.app/knowledge-engine
- **Data sources:** Firestore, Vertex AI embeddings, GCS
- **Public Interface:** https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/copernicusai-public-reviewer.html

#### 3.2 Sync Agent Tasks

| Task | Description | Trigger |
|------|-------------|---------|
| **Papers → Firestore/Vertex** | Ingest new papers, generate embeddings, update knowledge graph | After Paper Metadata Sync |
| **Videos → Firestore/Vertex** | Ingest video metadata, generate embeddings (transcripts, descriptions) | After Video Metadata Sync |
| **Status Page Update** | Update `knowledge-engine-status.json` with current counts | After any sync |
| **Cross-Modal Linking** | Link papers ↔ videos ↔ processes (shared concepts, citations) | Periodic batch |

#### 3.3 Data Flow (End-to-End)

```
Papers (PubMed, arXiv, NASA ADS, Crossref)
    ↓
metadata-database/papers/ → Dedup → papers-metadata.json
    ↓
Firestore + Vertex AI Embeddings → Knowledge Graph
    ↓
Research Tools Dashboard (RAG, Vector Search, Knowledge Map)

Videos (PostgreSQL, YouTube)
    ↓
videos-metadata.json
    ↓
Firestore + Vertex AI Embeddings
    ↓
Research Tools Dashboard
```

---

## Implementation Options for Long-Running Agents

### Option A: Ralph Wiggum / Cron (Current)

- **Pros:** Already set up for Daily Scout; simple
- **Cons:** Single machine; no built-in retries or orchestration

### Option B: Google Cloud Scheduler + Cloud Run Jobs

- **Pros:** Serverless, scalable, no machine to maintain
- **Cons:** Need to containerize scripts; cold starts

### Option C: Cloud Workflows / Cloud Tasks

- **Pros:** Orchestration, retries, chaining
- **Cons:** More setup

### Option D: Cursor / MCP Task Agents

- **Pros:** AI-assisted, flexible, good for exploratory work
- **Cons:** Not ideal for 24/7 unattended runs

**Recommendation:** Use **Option A** for Daily Scout (already working). Add **Option B** for backfill and sync jobs when ready. Use **Option D** for development and one-off runs.

---

## Suggested Priority Order

1. **Paper Scout Agent** — Ensure Daily Scout runs reliably (cron/Ralph Wiggum)
2. **Paper Backfill** — Run batch scripts to reach 50K–100K papers (parallel, resumable)
3. **Video Export** — Run export script, generate `videos-metadata.json`, upload to GCS
4. **Paper Metadata Sync** — Regenerate `papers-metadata.json`, upload; verify papers-database-table.html
5. **Knowledge Engine Sync** — Wire new papers (and videos) into Firestore/Vertex AI
6. **Video Ingestion Pipeline** — Add YouTube/curated ingestion to grow video DB
7. **Status Page** — Run **`scripts/publish_knowledge_engine_status.sh`** after ingests (or on a schedule) so GCS `knowledge-engine-status.json` matches API/Firestore totals; see `TRACK3_KNOWLEDGE_ENGINE_SYNC.md` §3

---

## File Locations Reference

| Item | Path |
|------|------|
| Daily Scout Runner | `scripts/acquire_papers/daily_scout_runner.py` |
| Daily Scout Config | `scripts/acquire_papers/daily_scout_config.json` |
| Run Script | `scripts/acquire_papers/run_daily_scout.sh` |
| Paper Logs | `paper_acquisition_logs/daily_scout/` |
| Papers Metadata | `metadata-database/papers/` |
| Papers Metadata JSON | `papers-metadata.json` (generated) |
| Papers Database Viewer | `papers-database-table.html` |
| Videos Database Viewer | `videos-database-table.html` |
| Video Export Script | `scienceviddb/scripts/export_videos_metadata.ts` |
| Status Page | `knowledge-engine-status.html` |
| Status JSON | `knowledge-engine-status.json` (GCS) |

---

## Next Steps

1. **Choose starting track:** Papers or Videos (or both in parallel)
2. **Verify Daily Scout:** See **`DAILY_SCOUT_VERIFICATION.md`** (cron, logs, NASA ADS toggle). Run `run_daily_scout.sh` manually when testing.
3. **Paper backfill:** Run `acquire_pubmed_batch.py --recent 5000` (or similar) as first backfill
4. **Video export:** Set up Cloud SQL Proxy; run `export_videos_metadata.ts`
5. **Document sync API:** Identify how Knowledge Engine backend ingests new papers/videos (Firestore schema, API endpoints)

---

*Part of the CopernicusAI Knowledge Engine*
