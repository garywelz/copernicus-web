# Evaluation corpus freeze — runbook

Operational notes for freezing the **`research_papers`** metadata corpus while running the **Discover AI manuscript** retrieval pilot (`papers/knowledge_engine_vision.md` §6, Table 4 placeholders; Colab **`papers/retrieval_pilot_colab_bundle.ipynb`**).

---

## Freeze boundary (authoritative statement)

**Ingest automation disabled (host crontab, 2026‑05‑26):**

| Schedule | Job | Status |
|---------|-----|--------|
| 10:15 AM | `run_daily_scout_with_ingest.sh` | **Disabled** (`# DISABLED 2026-05-26:` prefix; re-enable by uncommenting) |
| 10:15 PM | `run_daily_scout_with_ingest.sh` | **Disabled** (`# DISABLED 2026-05-26:` prefix) |

**Still scheduled (non–research-paper ingest):**

| Schedule | Purpose |
|---------|---------|
| 10:10 AM | Coffee reminder |
| 10:45 AM / 10:45 PM | Status publish |

A backup of the pre-change crontab should live under **`/tmp/`** from the disable operation (confirm on host).

---

## GCP `daily-rss-sync` (02:00 UTC)

**Verified behaviour (code trace, 2026‑05‑26):**

- Cloud Scheduler invokes **`POST /api/admin/episodes/sync-rss-status`**.
- That route may **not exist** in the deployed backend (`main.py` / `cloud-run-backend/endpoints/`); refactoring docs list it as pending — invocations may return **404** until restored.
- Intended behaviour (archived script `archive/one_off_scripts/root/sync_rss_status.py`): updates **podcast episode** RSS flags in Firestore **`episodes`** only (`submitted_to_rss`, `visibility` vs GCS RSS XML). **Does not** read, write, enrich, or enqueue **`research_papers`**.

**Runbook line:** `daily-rss-sync` is **not** a research-paper ingest pathway. Safe to leave enabled for corpus freeze. **Optional hygiene:** pause or fix the job if nightly **404** clutter or alerts are undesirable.

---

## Scope limits (do not over-claim)

1. **Freeze for the paper = frozen export artefact**, not “Firestore can never change.” Manual scripts, one-off jobs, future deploys, or other projects can still mutate `research_papers` until you take an **export + SHA‑256 + UTC timestamp** and cite it in **`META` / Zenodo**.
2. The “only automated pathways” claim applies to **the two disabled cron lines** as the **scheduled** writers we identified; enumerate any **other** schedulers (CI, Cloud Functions) if they exist.

---

## Next steps for the evaluation bundle

1. **Export** corpus slice for Colab contract: **`firestore_id`** (Firestore document id = canonical join key used by ingest) + **`combined_text`** (built from **`title`** + **`abstract`**, matching `ingest_papers_from_metadata_json.py`). Paginator script: **`huggingface-space/scripts/export_research_papers_jsonl.py`** (`FIRESTORE_DATABASE=copernicusai`, **`GOOGLE_CLOUD_PROJECT=regal-scholar-453620-r7`**). Embedding vectors omitted by default (add `--include-embedding-vectors` only if needed); Vertex coverage in UI matches non‑empty **`embedding_model`**, see `cloud-run-backend/endpoints/content/routes.py`). Example:

   ```bash
   cd huggingface-space && export GOOGLE_CLOUD_PROJECT=regal-scholar-453620-r7 FIRESTORE_DATABASE=copernicusai
   python3 scripts/export_research_papers_jsonl.py --out ~/exports/research_papers_YYYYMMDD.jsonl --batch-size 500 \
     --checkpoint-file ~/exports/research_papers_YYYYMMDD.cp --projection minimal
   ```
   Long runs: each page uses **`order_by('__name__').limit(N).stream()`** (not a single **`get()`** over the full collection). **`--resume`** appends to the JSONL and resumes after the **`doc_id`** saved in **`--checkpoint-file`**.

2. **(Optional)** Mirror the frozen export to **GCS** (Colab handoff / Zenodo prep). Keep **evaluation artefacts** isolated from RSS-facing **`audio/`**, **`transcripts/`**, thumbnails, etc.

   Recommended layout on your existing podcast bucket (**replace `YOUR_BUCKET`**):

   ```
   gs://YOUR_BUCKET/
   ├── audio/                 # production RSS
   ├── transcripts/           # production RSS
   ├── research_data/         # evaluation & open-research artefacts
   │   ├── snapshots/        # dated JSONL.gz (e.g. 2026-05-26-papers.jsonl.gz)
   │   ├── embeddings/       # optional: openai_doc_embeddings.npz copies
   │   └── manifests/        # SHA-256 sums, META.json, Zenodo notes
   ```

   After `gzip -k ~/exports/research_papers_YYYYMMDD.jsonl`, upload with copy-time validation. **`gsutil cp`** performs **MD5 checksum validation** on upload by default (see `gsutil cp` help: “CHECKSUM VALIDATION”). Some **`gcloud storage cp`** versions do **not** support **`--checksum`**; use **`gsutil`** for this path, or plain **`gcloud storage cp`** and verify separately (e.g. re-download + **`sha256sum`**, or object metadata).

   ```bash
   gsutil cp ~/exports/research_papers_YYYYMMDD.jsonl.gz \
     gs://YOUR_BUCKET/research_data/snapshots/
   ```

   Alternatively (no automatic hash check): **`gcloud storage cp SOURCE gs://YOUR_BUCKET/research_data/snapshots/`**. Optionally scope **IAM** or **lifecycle** rules to **`research_data/`** so large snapshots can tier to colder storage without touching production audio.

   **Example lifecycle (Coldline → Archive, snapshots only):** see **`docs/gcs_research_data_lifecycle.json`** — transitions objects under **`research_data/snapshots/`** to **Coldline** at **30** days and **Archive** at **90** days. **Important:**
   - **`gcloud storage buckets update ... --lifecycle-file=...` replaces the entire bucket lifecycle.** Export the current rules with `gcloud storage buckets describe gs://YOUR_BUCKET --format="json(lifecycle)"`, merge manually with any existing `rule` entries, then apply one combined JSON file whose **top-level key is `"rule"`** (the shape `gcloud` documents). Some generators wrap rules in **`"lifecycle": { "rule": [...] }`**; **`gcloud` expects the wrapper omitted** (`{ "rule": [ … ] }` only).
   - **Coldline / Archive:** retrieval is slower and may incur minimum-duration storage economics if you churn objects early — fine for Zenodo-aligned “keep forever, rarely touch” snapshots.
   - Apply and verify (**replace bucket name**):

   ```bash
   gcloud storage buckets update gs://YOUR_BUCKET --lifecycle-file=docs/gcs_research_data_lifecycle.json
   gcloud storage buckets describe gs://YOUR_BUCKET --format="json(lifecycle)"
   ```

   **Collaborator sharing:** share one object without widening bucket IAM via a **signed URL** with a short TTL, e.g. **`gcloud storage sign-url gs://YOUR_BUCKET/research_data/snapshots/FILE.gz --duration=7d`** (requires signing credentials: impersonated service account with **`--impersonate-service-account`** or an account backed by a key; see **`gcloud storage sign-url --help`**).

3. **SHA‑256** the same bytes you treat as canonical (typically the **local** `.jsonl` / `.jsonl.gz` **before or after upload**, or re-download from GCS and hash that file so bytes match object) → **`corpus_sha256`** in Colab `META` and manuscript §6 placeholders; stash a **`*.sha256`** under **`research_data/manifests/`** if mirroring.

4. **Record UTC freeze time** and ingestion git commit or export job id → **`[INSERT_COMMIT]`** where applicable.
5. **Refresh §5 staging table** once from `knowledge-engine-status.json` aligned to that freeze narrative.
6. Upload **`papers/retrieval_pilot_colab_bundle.ipynb`** to Colab (or open locally): run **§5 load corpus**, then **§6 lexical TF‑IDF**; optionally **§6b OpenAI dense** (`OPENAI_API_KEY` in Colab secrets; first run saves **`openai_doc_embeddings.npz`** for replay).
7. Complete **`judgments.csv`** using union template (lexical + OpenAI columns when §6b ran), re-run metrics → **`table4_metrics_lexical_vs_openai.csv`** when dense is enabled.
8. Zip outputs + **`pip freeze`** + notebook → Zenodo → **`[INSERT_EVAL_ARCHIVE_DOI]`** in manuscript §6 / Data availability.

See notebook intro cell for filenames (`rankings_lexical.csv`, `rankings_openai_dense.csv`, etc.).

---

## Re-enable after v1 archive ships

1. Uncomment both `run_daily_scout_with_ingest.sh` crontab lines (remove `# DISABLED 2026-05-26:` block as appropriate).
2. Confirm no duplicate or conflicting ingest schedulers.

---

## Paste-ready one-liner (Zenodo README / email)

> Corpus freeze boundary: host crontab ingestion via **`run_daily_scout_with_ingest.sh`** (10:15 AM/PM) disabled **2026‑05‑26**. GCP **`daily-rss-sync`** adjusts podcast **`episodes`** RSS flags only—not **`research_papers`**; endpoint may 404 until reimplemented. Pilot corpus is defined by **this export file + SHA‑256 + UTC timestamp**, not live row counts.
