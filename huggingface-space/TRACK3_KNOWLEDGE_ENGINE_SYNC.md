# Track 3: Knowledge Engine sync (papers / videos / Firestore)

**Goal:** Keep **local JSON** (Daily Scout) and the **public Knowledge Engine** (Firestore, embeddings, RAG) aligned.

---

## 1) Papers: JSON → Firestore

**Script:** `copernicus-web-public/cloud-run-backend/scripts/ingest_papers_from_metadata_json.py`  

**Reads:** `huggingface-space/metadata-database/papers/**/*.json` (same files Daily Scout writes).  
**Writes:** Firestore `copernicusai` → collection **`research_papers`**.  
**Design:** Batched writes, **`--skip-existing`** by default (safe to re-run).

**Run (from repo, with Google credentials for the project):**

```bash
cd /home/gdubs/copernicus-web-public/cloud-run-backend
# Use backend venv if you have one; ensure google-cloud-firestore is installed
export GOOGLE_CLOUD_PROJECT=regal-scholar-453620-r7
export FIRESTORE_DATABASE=copernicusai   # if your DB id differs, adjust

python3 scripts/ingest_papers_from_metadata_json.py \
  --root /home/gdubs/copernicus-web-public/huggingface-space/metadata-database/papers \
  --skip-existing
```

**After large backfills:** use **`--limit`** and **`--checkpoint-file`** for resume (see `python3 .../ingest_papers_from_metadata_json.py -h`).

**Embeddings / vector search** for RAG are a **separate** pipeline in `cloud-run-backend` (e.g. `utils/auto_embedding.py` and deploy jobs). Ingesting metadata does not by itself re-embed; plan embedding refresh per your `CONTENT_INGESTION_*.md` docs when needed.

---

## 2) Videos: Cloud SQL → Firestore (+ embeddings)

**Script:** `cloud-run-backend/scripts/sync_videos.py`  

**Requires:** `SCIENCEVIDDB_DATABASE_URL` or Secret `scienceviddb-database-url`, plus backend deps (`psycopg2`, embedding service, etc.).

**Run:** from `cloud-run-backend` with venv and env vars (see script header and `docs/planning/VIDEO_DATABASE_SETUP.md` if present).

Use this when you want the **Science Video DB** in Firestore for the **Knowledge Engine**, not for the file-only `metadata-database/papers` flow.

---

## 3) Status page numbers (Track 3 + #4)

**Local generator:** `huggingface-space/scripts/generate_status_page.py`  

- **`--source api` (default):** uses **`GET /api/content/browse?...&limit=1`** on the public API for **papers, podcasts, processes** totals (same order of magnitude as the live [papers table](https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/papers-database-table.html)).  
- **`--source local`:** counts JSON files on disk (good offline; can differ from Firestore).  
- **Videos** are not on that browse API; set **`KSTATUS_VIDEO_COUNT`** or **`--videos N`** when publishing.

**Publish JSON to GCS** (so `knowledge-engine-status.html` shows fresh numbers):

```bash
cd /home/gdubs/copernicus-web-public/huggingface-space
chmod +x scripts/publish_knowledge_engine_status.sh
# optional: export KSTATUS_VIDEO_COUNT=753
./scripts/publish_knowledge_engine_status.sh
# or: ./scripts/publish_knowledge_engine_status.sh -- --videos 800
```

**When to run:** after a big **ingest** or when you want the **Status** card to match production. For **daily automation** after the paper scout, install the **10:45 Eastern** job:

```bash
cd /home/gdubs/copernicus-web-public/huggingface-space
chmod +x scripts/install_cron_1045_status_publish_ny.sh
bash scripts/install_cron_1045_status_publish_ny.sh
```

This runs **`publish_knowledge_engine_status.sh`** every day at **10:45** (same `CRON_TZ=America/New_York` as your 10:10/10:15 block). Log: `paper_acquisition_logs/daily_scout/status_publish_cron.log`.

---

## 4) Quick verification

- **API totals:** same base as the app —  
  `https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app/api/content/browse?content_type=papers&page=1&limit=1` → `pagination.total`.  
- **Generated file:** `huggingface-space/knowledge-engine-status.json`  
- **Public:** `https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/knowledge-engine-status.json`

---

## Related

- `AGENT_TASK_ORGANIZATION.md` — full plan  
- `DAILY_PAPER_AGENT_RALPH_WIGGUM.md` — Daily Scout (fills JSON on disk)  
- `DAILY_SCOUT_VERIFICATION.md` — cron / logs  

---

*CopernicusAI Knowledge Engine*
