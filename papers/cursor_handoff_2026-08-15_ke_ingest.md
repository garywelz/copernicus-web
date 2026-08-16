# Handoff — 15 August 2026 (Knowledge Engine ingest night)

**From:** Cursor (this session)  
**To:** Claude Code (publishing / quality) and Claude Chat (decisions, prose, next-session briefing)  
**Repo:** `copernicus-web` @ `main` (`b3196e666`)  
**Stopped for the night.** Do not start new ingest or cron work unless Gary asks.

Share this file as-is. Claude Code: read `CLAUDE.md` first. Claude Chat: the locked decisions and leftovers are the load-bearing parts.

---

## Who does what

| Agent | Do | Do not |
|---|---|---|
| **Claude Code** | Reader-facing copy, single-file polish, HF/GCS deploys, verify live KE after a hard refresh | SSH to Jetson, crontab, Cloud SQL proxy, paper-scout cron, full-repo refactors |
| **Claude Chat** | Hold decisions, draft Gary-facing notes, sequence the leftovers | Invent a third engine, elect a “canonical” chart source, treat bibliographies as an ingest queue |
| **Cursor** | Jetson, cron, Firestore indexes, Cloud Build, acquisition workers | `shadow` (out of scope) |

If a task looks like Cursor’s, say so rather than forcing it.

---

## Locked product decisions (do not reopen)

- One Knowledge Engine. GLMP and ATAP share backend and corpus. Toggle, not fork.
- ATAP = Axiomatic Theories, Algorithms and Proofs (`content_type=math` → `atap_graphs`). Not “mathematics as a second process collection.”
- Unique-file rule: every paper / podcast / process / video title opens **that item’s own file**.
- Charts are a **best current approximation**, not Lean-style verification. Lents/Me-Me review improves them; it does not certify them. Never elect a canonical chart source.
- Tokenizer floor: 3 characters.
- Discussion boards: **official APIs only**. No Reddit scrape. Do not ingest Q&A as papers — harvest paper IDs (DOI / PMID / arXiv) only.
- Bioinformatics Stack Exchange is the **locked GLMP fallback** when BioStars is Cloudflare-blocked (decided tonight).
- First-run adjacent MathOverflow papers (Kervaire, von Neumann, measure theory, etc.) **stay in the corpus**. Gary said leave them. The tightened gate applies to later runs only.
- Production PubMed / bioRxiv / arXiv cron is **untouched**.
- Media never goes in git.

---

## What shipped tonight (on `main`)

| Commit | What |
|---|---|
| `6536ad408` | Videos wired through Search / Ask / Browse / Map; Ask citation IDs passed through `/api/rag/answer` |
| `386a92640` | A2 §8 gated citation-expansion rule; A1 harvest/resolve as candidate evidence |
| `a3465ea2f` | A1 title-match gate; stripped mismatched PMID `named_by_charts` stamps |
| `1f586e6e1` | 50-seed one-hop citation-expansion pilot (`cited_by_collection`) |
| `1e3d43ef3` | MathOverflow + BioStars worker; BioSE fallback; tightened MO tags |
| `4ab57a0ed` | Recent-video cron wrapper (backend venv + Cloud SQL Auth Proxy) |
| `b3196e666` | Search HTTP handler now returns `videos`; index note |

**Live**

- KE: `https://copernicus-frontend-phzp4ie2sq-uc.a.run.app/knowledge-engine`
- API: `https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app`
- Backend Cloud Build tonight: `b94f9f93-2edc-4a50-b7e2-2f12d0ad72d6` **SUCCESS**
- Firestore `science_videos`: **753** docs, embeddings `text-embedding-3-small` (1536-d), **0 transcripts**
- Vector index `science_videos`: `CICAgLiT6IEK` **READY**
- Gary confirmed videos in Map and Browse; Search/Ask were empty until the index + the Search response fix. He should hard-refresh and re-check.

**A1 (GLMP chart-named papers)**

- Calendar wait lifted 15 Aug. Ingest as candidate evidence only. Do not rewrite chart JSON.
- First pass: 98 created, 128 DOI-merged. PMID fallback had attached 76 charts to the **wrong** papers; those stamps were stripped. 21 title-matching PMID resolves kept.
- **66 remain**: DOI-only, Crossref miss (old Cell / JBC / Annual Reviews / Science). Biopython does not help. Next pass is title/OpenAlex, not Entrez.

**A2 citation-expansion pilot**

- 50 seeds (33 researcher-cited, 17 chart-named). Local `research_focus.json` in this checkout is **ATAP** with empty `flagged`, so GLMP flagged papers were not in the seed set.
- 93 admitted (83 two-seed, 10 top-in-seed); 78 new, 14 already in corpus, 1 title-mismatch, 0 unresolved.
- Channel: `cited_by_collection`. Not a scout-cron change. Bibliography is Map metadata, not an ingest queue.

**Discussion-board harvest**

- Worker: `huggingface-space/scripts/acquire_papers/discussion_board_scout.py`
- Channel: `discussion_board`. Thread URL in `parent_thread_urls`. Q&A is not a corpus item.
- First write: 20 MO + 20 Bioinformatics SE threads (BioStars 403 from Windows); 24 IDs; 21 created, 2 merged, 1 unresolved.
- Tags then tightened: dropped `ct.category-theory`; thread-title keep/drop; ATAP paper-title gate.

**Videos**

- One-time backfill already done (753/753). Cron is 14-day window only.
- ScienceVideoDB secret points at `localhost:5433`. Wrapper starts Cloud SQL Auth Proxy for `regal-scholar-453620-r7:us-central1:scienceviddb-db` if the port is free.
- Dry-run from Jetson: DB reachable, **0** videos published in the last 14 days. Daily job will often be a no-op until ScienceVideoDB itself gets new rows.

---

## Jetson (already installed — do not re-install)

Host: `gary@192.168.1.222`  
Tree: `/media/sdcard/copernicus-worker/copernicus-web` (= `/home/gdubs/copernicus-web-public`)  
Crontab `CRON_TZ=America/New_York`. Paper-scout AM/PM lines unchanged.

| When | Job | Log |
|---|---|---|
| 10:15–10:30 daily | Existing paper scouts + ingest | existing scout logs |
| 20:00–20:15 daily | Existing paper scouts + ingest | existing scout logs |
| **21:30 daily** | `sync_recent_videos.sh` (14-day) | `/media/sdcard/logs/video_sync_cron.log` |
| **Sunday 22:00** | `scout_discussion_boards.sh` | `/media/sdcard/logs/discussion_board_cron.log` |

Live wrappers (LF, not scp’d from Windows):

- `/media/sdcard/scheduler/scout/sync_recent_videos.sh`
- `/media/sdcard/scheduler/scout/scout_discussion_boards.sh`

Python for both new jobs: `cloud-run-backend/venv` (has Firestore). Proxy binary: `/media/sdcard/bin/cloud-sql-proxy`.

**Claude Code: do not SSH, do not edit crontab, do not `sync_to_jetson.sh` unless Gary sends you to Cursor.**

---

## Do not touch

- Production paper-scout cron (`scout_pubmed` / `biorxiv` / `arxiv` / `scout_ingest.sh`)
- Jetson crontab except to *read* it if Gary asks
- Chart JSON / “canonical source” election
- Recursive citation expansion; ungated bibliography ingest
- `shadow`
- Untracked junk in this checkout (resumes, `SUITE_REORG_PLAN (1).md`, generated JSONL reports, `tsconfig.tsbuildinfo`)

Generated reports (do not commit):

- `huggingface-space/scripts/acquire_papers/a1_*.jsonl`
- `huggingface-space/scripts/acquire_papers/citation_expansion_pilot_report.jsonl`
- `huggingface-space/scripts/acquire_papers/discussion_board_scout_report.jsonl`

---

## Leftovers (next session, not tonight)

1. **Gary hard-refresh KE** — confirm Search and Ask return videos; confirm Ask titles still link (DOI / podcast slug / process id).
2. **A2 for real** — production scout still does not read `research_focus.json`. Largest remaining acquisition gap. ATAP still has no standing scout of its own.
3. **A1 remainder** — 66 DOI-only chart papers. Title/OpenAlex, not Biopython.
4. **GLMP `flagged` seeds** — need the GLMP `research_focus.json` in this checkout (this tree’s file is ATAP, `flagged: []`).
5. **ScienceVideoDB recency** — cron works; the last-14-days query returned 0. If new YouTube rows are not landing in Postgres, the KE video corpus will freeze at 753.
6. **Optional:** strip `discussion_board` attribution from the first-run adjacent MO papers. Gary said leave them for now.

---

## Key files

- `lib/knowledge-engine-links.ts` — outbound unique-file resolver
- `cloud-run-backend/endpoints/rag/routes.py` — Ask citation pass-through
- `cloud-run-backend/endpoints/vector_search/routes.py` — must include `videos` in the HTTP JSON
- `cloud-run-backend/mcp_server/tools/vector_search.py` — `find_nearest` on `science_videos`
- `cloud-run-backend/scripts/sync_videos.py` — ScienceVideoDB → Firestore
- `cloud-run-backend/scripts/ingest_papers_from_metadata_json.py` — allowlist includes `named_by_charts`, `parent_paper_ids`, `parent_thread_urls`
- `huggingface-space/scripts/acquire_papers/A2-standing-acquisition-contract.md` — contract + tonight’s sequencing notes
- `huggingface-space/scripts/acquire_papers/discussion_board_scout.py`
- `huggingface-space/scripts/acquire_papers/citation_expansion_pilot.py`
- `huggingface-space/scripts/scheduler/scout/sync_recent_videos.sh`
- `huggingface-space/scripts/scheduler/scout/scout_discussion_boards.sh`
- `governance/RESOURCE_MANIFEST.md` — no ungated bibliography ingest; no dumping Q&A as papers
- `docs/planning/VECTOR_INDEX_CREATED.md` — `science_videos` index id

---

## Claude Code — first moves if Gary opens you next

1. Hard-refresh the live KE. Search a science-video topic with Videos checked. Ask the same question. Titles should link.
2. If Search is still empty for videos: the index is READY and the API now returns `videos`. Check you are hitting the new Cloud Run revision, not a cached response.
3. Do not propose Jetson work. Point Gary at Cursor.
4. Do not commit the JSONL reports or resumes.

## Claude Chat — how to talk about tonight

Tonight closed the video path (data, cron, index, Search JSON) and opened two bounded acquisition doors (chart-named papers as evidence; discussion-board paper IDs; one-hop citation expansion). The corpus got more *explicable*, not just larger. The standing scout still ignores `research_focus.json`; that is the next real A2 piece, and it is Cursor-sized.
