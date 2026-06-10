# Daily paper agent (cron + Ralph Wiggum)

**Purpose:** Add a **predictable number of new paper metadata JSON files** every day (PubMed + arXiv; optional NASA ADS when enabled).

**Output folder:** `metadata-database/papers/` (see `AGENT_TASK_ORGANIZATION.md`).

---

## How many papers per day?

Edit **`scripts/acquire_papers/daily_scout_config.json`**, section **`limits`**:

| Field | Role |
|--------|------|
| **`papers_per_source_per_day`** | Maximum papers requested **per enabled source** in one run (PubMed, arXiv, …). |
| **`total_papers_per_day`** | **Daily budget** split **evenly** across **enabled** sources. The runner uses `min(papers_per_source_per_day, floor(total / n_sources))` for each. |

**Examples (2 enabled sources: PubMed + arXiv, NASA ADS off):**

- `total_papers_per_day: 500`, `papers_per_source_per_day: 200`  
  - `min(200, 250) = 200` each → up to **~400** targeted per day (capped by APIs / duplicates).
- `total_papers_per_day: 300`, `papers_per_source_per_day: 200`  
  - `min(200, 150) = 150` each → **~300** targeted per day.

**To add more per day:** raise **`total_papers_per_day`** and/or **`papers_per_source_per_day`** (respect PubMed / arXiv / NASA ADS rate limits; long runs are normal).

---

## 1) Cron (already supported)

**Eastern, 1,000 papers/day, 10:10 reminder + 10:15 run:** see **`PAPER_SCOUT_CRON_NY_1015.md`** and run:

`bash scripts/acquire_papers/install_daily_scout_cron_1015_ny.sh`

**Older installer (07:00 UTC only):**

```bash
cd /home/gdubs/copernicus-web-public/huggingface-space
bash scripts/acquire_papers/install_daily_scout_cron.sh
```

**Default schedule (that script):** `0 7 * * *` → **07:00 UTC** daily. Remove that line in `crontab -e` if you use the 10:15 Eastern job instead, so the scout does not run twice.

**Logs:** `paper_acquisition_logs/daily_scout/cron.log` and per-source `pubmed_YYYYMMDD.log`, `arxiv_YYYYMMDD.log`.

**Manual test:**

```bash
cd /home/gdubs/copernicus-web-public/huggingface-space
bash scripts/acquire_papers/run_daily_scout.sh
```

---

## 2) Ralph Wiggum (or any daily automation)

**Single command** (uses venv if `paper_acquisition_venv` exists):

```bash
cd /home/gdubs/copernicus-web-public/huggingface-space && bash scripts/acquire_papers/run_daily_scout.sh
```

**In Ralph Wiggum:** add a **System command** (or “run shell script”) with that line, set **Repeat daily** (or match your cron time so you don’t double-run—pick **either** cron **or** Ralph, unless you use Ralph only on a machine without cron).

**Duration:** allow **30–90 minutes**; PubMed and arXiv can be slow.

---

## 3) Manual backfill (larger “when I have time” runs, not Daily Scout)

**Do not** point `daily_scout_runner.py` at 10,000 — it is for **small** daily chunks. For **larger** jobs (hundreds to thousands+), use the **batch scripts** in the same folder; they are built for that pattern.

### Time expectations

The Daily Scout **felt fast** because it only requested **~200 per source** (a few hundred total). A **10,000**-paper run is a different class of work: PubMed in particular is **throttled** to NCBI (roughly a few requests per second; see [NCBI guidelines](https://www.ncbi.nlm.nih.gov/books/NBK25497/)). A **10k** backfill will usually take **much longer than 10–15 minutes** — think **tens of minutes to several hours** depending on source, network, and paging. It is a good “**start and walk away**” job, not a short coffee break, unless you try a **smaller** count first to see real wall clock on *your* machine.

**Practical approach:** run **1,000** (or **2,000**) once, note how long it took, then scale up. Run in a **tmux** / **screen** session or leave the machine awake if it is a long job.

### Commands (from `huggingface-space/`, venv if you use it)

**PubMed — e.g. 5,000 recent only, no classic**

```bash
cd /home/gdubs/copernicus-web-public/huggingface-space
source paper_acquisition_venv/bin/activate  # if you use venv
python3 scripts/acquire_papers/acquire_pubmed_batch.py --recent 5000 --classic 0
```

**arXiv — e.g. 5,000 recent, no classic**

```bash
python3 scripts/acquire_papers/acquire_arxiv_batch.py --recent 5000 --classic 0
```

**Example “~10k total” in two steps** (separate runs): e.g. **5,000 + 5,000** as above, or **10,000** on one source only:

```bash
python3 scripts/acquire_papers/acquire_pubmed_batch.py --recent 10000 --classic 0
```

(Still expect **long** runtime; same for arXiv at 10,000.)

Afterward: optional **`deduplicate_papers.py`**, then **`generate_papers_metadata.py`**, then your **Knowledge Engine / Firestore** ingest as in `AGENT_TASK_ORGANIZATION.md`.

---

## 4) After papers land (optional, not daily)

- **Deduplication:** `python3 scripts/acquire_papers/deduplicate_papers.py`
- **Consolidated JSON for static viewers:** `python3 scripts/generate_papers_metadata.py`
- **Knowledge Engine / Firestore:** your existing `cloud-run-backend` sync / ingest (separate from Daily Scout).

---

## 5) Related docs

- `DAILY_SCOUT_VERIFICATION.md` — NASA ADS flag, last verification  
- `scripts/acquire_papers/RALPH_WIGGUM_DAILY_SCOUT_SETUP.md` — longer Ralph walkthrough  
- `AGENT_TASK_ORGANIZATION.md` — full three-track plan  

---

*CopernicusAI Knowledge Engine*
