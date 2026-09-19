# TDAP Backfill Recon — 2026-09-19

Read-only recon. No writes made anywhere except this file.

## Summary

GLMP and ATAP are not distinguished by a Firestore "initiative" field — there is no such field. Process/chart records (flowcharts) are separated by **Firestore collection** (`glmp_processes` vs `atap_graphs`), while paper records in the single shared `research_papers` collection carry soft, non-enum-validated tags: `question_scope_ids` (array of ids like `glmp-q1`/`atap-q2`), `acquisition_channel`, and per-citation-event `cited_project` (free-text, lowercased at intake). GLMP and ATAP deliberately **share one corpus** — a paper can and does belong to both. Acquisition is driven by each project's `research_focus.json` (canonical copies live in the separate `glmp` and `atap` sibling repos, not in `copernicus-web`), consumed by a documented-but-partially-implemented "standing acquisition contract" (A2) plus one-off backfill/expansion scripts under `huggingface-space/scripts/acquire_papers/`. Citation-graph expansion already exists — a gated, one-hop, capped pilot (`citation_expansion_pilot.py`) using Crossref + OpenAlex from seed papers (chart-named, researcher-cited, flagged), explicitly **not** a general bibliography crawl. Embedding backfill is a single parameterized script, `cloud-run-backend/scripts/backfill_research_paper_embeddings.py`, run from the Yoga laptop (manual pin/dry-run/pilot/run) or unattended via `--auto` on the Jetson (`/media/sdcard/logs`), fully idempotent per-document via `embedding_model` re-check, with hard-stop-on-structural-error and checkpoint/resume. The frontend/backend toggle is unusually well-factored for reuse: nearly everything routes through `lib/knowledge-engine-projects.ts` (`KE_PROJECTS`, `KEProjectId`), but a handful of genuine hardcodes remain (the `'glmp'|'atap'` union type itself, an icon ternary, and backend `PROCESS_FAMILY_COLLECTIONS`/`ALL_PROCESS_CONTENT_TYPES` maps). The one concrete hazard confirmed by reading the code: `batch_*.json` acquisition-summary sidecars are explicitly excluded from per-paper ingest by filename glob (already guarded, not a live footgun). The Jetson production tree is known and repeatedly documented to drift from git (`SCOUT_ARCHITECTURE.md`, `STUB_GATE_PR_DRAFT_NOTES_2026-07-17.md`) — I could not verify current Jetson state directly since I have no SSH/filesystem access from this machine. The May eval-freeze artifact `research_papers_20260526.jsonl.gz` is an external, already-exported GCS/Zenodo snapshot (not a file in this repo); it cannot be touched by any live Firestore backfill by construction — only a fresh, separately-named export could equal or reference it.

---

## Q1 — Acquisition

**GLMP corpus:**
- Bulk/batch acquisition scripts: `huggingface-space/scripts/acquire_papers/acquire_pubmed_batch.py`, `acquire_arxiv_batch.py`, `acquire_biorxiv_medrxiv_batch.py`, `acquire_crossref_batch.py`, `acquire_nasa_ads_batch.py`, `acquire_pubmed_batch.py` (targets/usage documented in `huggingface-space/scripts/acquire_papers/README.md:11-140`).
- Standing daily cron (production, split workers, not the monolithic runner): `huggingface-space/scripts/scheduler/SCOUT_ARCHITECTURE.md:1-30` — cron calls `scout_pubmed.py`/`scout_biorxiv.py`/`scout_arxiv.py` on the Jetson, reading `scripts/acquire_papers/daily_scout_config.json` (`SCOUT_ARCHITECTURE.md:148-156`), a hand-maintained, GLMP-biased (not project-focus-driven) config (`A2-standing-acquisition-contract.md:33-46`).
- One-off backfill for GLMP's own flowchart-cited sources: `huggingface-space/scripts/acquire_papers/A1-glmp-source-backfill-plan.md` (handoff/session doc) + `a1_harvest_chart_sources.py` (harvests unique DOI/PMID from in-repo `glmp-processes-database/processes/*.json` `sources` arrays) + `a1_resolve_and_ingest.py` (resolves via the acquirers above, stamps `acquisition_channel: "glmp_chart_source_candidate"` and `named_by_charts`, `cited_project = "glmp"` — `a1_resolve_and_ingest.py:35,154,158,240`). First run 2026-08-15: 389 harvested papers, 108 charts (`A1-glmp-source-backfill-plan.md:171-177`).
- Researcher-cited intake (#43): `huggingface-space/scripts/acquire_papers/researcher_cited_intake.py` — takes `--input` (DOI/PMID/arXiv/bibcode/URL/free text), `--cited-by`, `--cited-date`, `--cited-context`, `--cited-project`, `--cited-for-question` (lines 494-513).
- Discussion-board harvest: `discussion_board_scout.py` — MathOverflow + BioStars/Bioinformatics SE official APIs, harvests paper IDs from scoped threads only, `acquisition_channel: "discussion_board"` (`discussion_board_scout.py:573,597-598`); ATAP local-scratch focus file at `discussion_board_scout.py:39-41` (`atap_research_focus.json`, since this checkout carries ATAP's local copy).

**ATAP corpus:**
- Same acquirer scripts, routed via `research_focus.json` `categories` (`atap_research_focus.json:59`: `["math.LO","cs.LO","cs.PL","math.CT","cs.DM"]`).
- A2 documents that **ATAP had zero standing acquisition** as of 2026-08-05 (`A2-standing-acquisition-contract.md:44-45`) — "not an untuned scout: zero queries." ATAP's first-pass acquisition ran as a citation-expansion/discussion-board pilot rather than a daily cron.
- Citation expansion pilot ran with a mix of GLMP+ATAP seeds (33 researcher-cited, 17 chart-named; `A2-standing-acquisition-contract.md:391-394`).

**Session/handoff docs describing this work** (not exhaustive): `huggingface-space/scripts/acquire_papers/A1-glmp-source-backfill-plan.md`, `A2-standing-acquisition-contract.md`, `43-researcher-cited-intake.md`, `papers/cursor_handoff_2026-08-15_ke_ingest.md`, `papers/claude_code_handoff_2026-08-22_atap_diagonalization_papers.md`.

**Inputs the scripts take:** keyword/term lists (`daily_scout_config.json` — 10 PubMed + 4 arXiv queries, `A2-standing-acquisition-contract.md:35-36`), arXiv category lists (`atap_research_focus.json:59`), DOI/PMID/arXiv-ID lists (`--doi-file`, harvested-sources lists), and free-form researcher citations (`researcher_cited_intake.py --input`). No purely author-list-driven acquisition script was found (see Q5).

---

## Q2 — Initiative membership

**There is no `initiative` field on `research_papers` documents.** Confirmed by an exhaustive grep for `"initiative"` across `.py/.ts/.tsx/.js/.json` (no hits outside this recon).

Membership is instead a composite of several looser mechanisms:
1. **`question_scope_ids`** (array of strings, e.g. `"glmp-q1"`, `"atap-q2"`) — a flat, Firestore-`array_contains`-queryable mirror of `acquisition_matches[].question`/`cited_for_question`, built in `cloud-run-backend/scripts/ingest_papers_from_metadata_json.py:401-424` and used for filtering in `cloud-run-backend/endpoints/content/routes.py:135,173,212,247`, `cloud-run-backend/content_browse_filters.py:55-126`, `cloud-run-backend/services/knowledge_map_service.py:339,1045`, and `cloud-run-backend/mcp_server/tools/vector_search.py:409-526`. Question ids are free-text-prefixed (`glmp-*`/`atap-*`), not a validated enum.
2. **`cited_project`** — a per-citation-event free-text field (`researcher_cited_intake.py:458,540`; `citation_expansion_pilot.py:321,348`; `a1_resolve_and_ingest.py:35,158,240`), lowercased at intake but **not schema-validated** — a 2026-08-08 incident split GLMP-vs-glmp casing across 33 vs 4 records before the lowercasing fix (`researcher_cited_intake.py:531-537`).
3. **`acquisition_channel`** — records *how* a paper entered (`glmp_chart_source_candidate`, `researcher_citation`, `cited_by_collection`, `discussion_board`), not which project it belongs to per se, though channel + provenance together often imply a project.
4. **Firestore collection itself, for process/chart records** — GLMP charts live in collection `glmp_processes`, ATAP charts in `atap_graphs` (`cloud-run-backend/endpoints/content/routes.py:99-100`, `cloud-run-backend/services/knowledge_map_service.py:135-136`). For charts, the collection *is* the initiative marker — a hard partition, unlike papers.

**Can one record belong to more than one initiative?** Yes, explicitly by design for papers: "The two projects share one corpus" (`A2-standing-acquisition-contract.md:420-429`) — GLMP and ATAP foundational papers cite each other (73 shared references across three GLMP papers mixing homotopy type theory with *E. coli* network motifs). `question_scope_ids` is an array and can hold both `glmp-*` and `atap-*` entries on the same document. Process/chart records cannot straddle both — they live in one collection or the other.

---

## Q3 — Toggle mechanics

The toggle is centered on **`lib/knowledge-engine-projects.ts`**, a per-project config map (`KE_PROJECTS: Record<KEProjectId, KEProjectConfig>`, lines 76-138) consumed by every UI component. Every place `'glmp'`/`'atap'`/`GLMP`/`ATAP` is hardcoded and would need a `tdap` entry:

**Frontend:**
- `lib/knowledge-engine-projects.ts:22` — `export type KEProjectId = 'glmp' | 'atap'` (the type itself; must become `'glmp' | 'atap' | 'tdap'`).
- `lib/knowledge-engine-projects.ts:76-138` — the `KE_PROJECTS` object literal (`glmp: {...}`, `atap: {...}`) — needs a third `tdap: {...}` entry (label, fullName, framingLine, processContentType, searchPlaceholder, askExamples, quickExamples).
- `lib/knowledge-engine-projects.ts:140` — `KE_PROJECT_IDS: KEProjectId[] = ['glmp', 'atap']`.
- `lib/knowledge-engine-projects.ts:142-144` — `isKEProjectId()` type guard (`v === 'glmp' || v === 'atap'`).
- `components/knowledge-engine/constants.ts:11-12` — `ALL_PROCESS_CONTENT_TYPES` includes `'glmp'`, `'math'` (ATAP's process content type).
- `components/knowledge-engine/constants.ts:31-32` — `PROCESS_FAMILIES` array (`{id:'glmp',...}`, `{id:'math', label:'ATAP',...}`).
- `components/knowledge-engine/constants.ts:51-65` — `BROWSE_QUESTIONS` hardcodes every `glmp-q*`/`atap-q*` id/label pair.
- `components/knowledge-engine/constants.ts:73-74` — `PROCESS_DATABASE_LINKS` (GLMP/ATAP GCS table URLs).
- `components/knowledge-engine/KnowledgeMapView.tsx:965` — `proj.id === 'atap' ? '📐' : '🧬'` icon ternary (binary; breaks for a third project — always falls to 🧬).
- `components/knowledge-engine/ContentBrowser.tsx:78` — default `processFamily` state falls back to `'math'` when no project selected.
- `app/knowledge-engine/page.tsx:12,64,74,127-140` — imports `KE_PROJECTS`/`KE_PROJECT_IDS`/`isKEProjectId`; the toggle buttons themselves are rendered by `.map()` over `KE_PROJECT_IDS` (line 127) so **no additional hardcode needed there** if `KE_PROJECT_IDS` gains `'tdap'`.
- `components/knowledge-engine/RAGInterface.tsx:78-79` — explicit `KE_PROJECTS.glmp.askExamples.slice(0,2)` / `KE_PROJECTS.atap...` concatenation for the "both selected" case — a third project must be added to this list manually or the concat logic generalized.

**Backend:**
- `cloud-run-backend/endpoints/content/routes.py:99-100` — `PROCESS_FAMILY_COLLECTIONS = {"glmp": "glmp_processes", "math": "atap_graphs", ...}`.
- `cloud-run-backend/endpoints/content/routes.py:352` — default `process_family` fallback `"glmp"`.
- `cloud-run-backend/services/knowledge_map_service.py:135-136` — same `PROCESS_FAMILY`→collection map, second copy.
- `cloud-run-backend/services/knowledge_map_service.py:1259` — `process.get("process_family") or "glmp"` default.
- `cloud-run-backend/endpoints/glmp/routes.py` and `cloud-run-backend/endpoints/rag/routes.py` reference GLMP/ATAP in module names/docstrings but no `grep` hits for hardcoded `'glmp'`/`'atap'` string literals were found inside those two files themselves (they were empty on this search — likely reference the shared constants instead; **not independently verified line-by-line**, see Limits).

**Note (important for TDAP's design):** `lib/knowledge-engine-projects.ts:12-19`'s own header comment warns explicitly that **GLMP ≠ "biology discipline"** and **ATAP ≠ "mathematics discipline"** — project identity is `question_scope_ids`-scoped papers + a dedicated process-chart Firestore collection, not a `discipline` filter. TDAP (topology/persistent cohomology) will likely want the same shape: a `tdap-*` question-id prefix plus (if TDAP grows chart/diagram artifacts later) its own process collection — not a repurposed `discipline: "mathematics"` filter.

---

## Q4 — Embedding backfill

**Script:** `cloud-run-backend/scripts/backfill_research_paper_embeddings.py` (single script, parameterized by `--collection {research_papers, episodes}` via a `PROFILES` dict, lines 164-179). A GLMP-process-specific legacy variant also exists: `cloud-run-backend/scripts/backfill_glmp_embeddings_v2.py` (embeds `glmp_processes` docs specifically, written 2026-06-30 "replaces lost backfill_embeddings.py" — lines 1-8,36-38).

**Model/dims:** `text-embedding-3-small`, 1536 dimensions, written to Firestore field `embedding` (Firestore `Vector` type) + `embedding_model` + `embedding_updated` (lines 105-106, 626-631). Explicitly does **not** pass `dimensions=` to the API to match the original corpus request path (line 29, 516-517).

**Batch API flow:** one document → one `embeddings.create()` call per request (line 506-513) — deliberately **not** a multi-input batch, to avoid response-index/doc-id mismatch risk (documented rationale at lines 511-514). Structural response checks (single result, model-name prefix match, exact 1536-length vector) raise `StructuralError` and hard-stop immediately, bypassing the transient-retry loop (lines 519-544, 552-554). Transient errors (429/5xx/timeout) retry up to 3x with linear backoff (lines 237-250, 555-565).

**Where it runs:**
- Manual/pin/pilot/run modes: "Yoga, system Python 3.12 + ADC" laptop (docstring lines 53-64).
- `--auto` unattended gap-fill mode: designed for the Jetson — default `--log-dir` is `/media/sdcard/logs` (line 112, `DEFAULT_LOG_DIR`), writes dated JSONL run logs (`_append_auto_run_log`, lines 798-804). `SCOUT_ARCHITECTURE.md:22-24,28-29` shows an "embed --auto before publish" slot reserved in the post-ingest cron chain but not yet wired in as of the doc's 2026-07-23 last-update — **could not confirm from this checkout whether `--auto` is actually cron-scheduled on the Jetson today** (see Limits).

**Idempotency:** per-document re-check of `embedding_model` immediately before embedding and again immediately before write (`process_one_doc`, lines 598-605; pre-write re-assert lines 621-625) — safe to rerun; already-embedded docs are skipped. `--pin`/`--dry-run`/`--pilot`/`--run` modes use a `manifest.json` (frozen census) + `checkpoint.json` (remaining/completed/failed ids) that hard-stops if the checkpoint's pin timestamp doesn't match the current manifest (lines 490-503), preventing silent partial-state corruption across re-pins.

**Cost per 1000 records:** **not found in this repo.** No cost/dollar figures, token-cost logs, or `embed_auto_*.jsonl` run logs are present in this checkout (searched `papers/*.md`, `cloud-run-backend/services/EMBEDDING_SERVICE_README.md`, `papers/dense_retrieval_benchmark_handoff.md`) — the script does log `tokens_total` per run (lines 470-481, 918-931) but those logs live under `/media/sdcard/logs/` on the Jetson, unreachable from this machine. I did not compute a cost estimate from external pricing knowledge to avoid presenting an unverified number as a repo finding — see Limits.

---

## Q5 — Citation-graph expansion

**Yes, this exists**, but it is deliberately narrow, gated, and separate from the daily scout cron — not general bibliography ingestion.

- Script: `huggingface-space/scripts/acquire_papers/citation_expansion_pilot.py`. Docstring (lines 1-12): "A2 §8 — 50-seed one-hop citation-expansion pilot... Channel: `cited_by_collection`. Production scout cron is not touched."
- Sources used: **Crossref** (`CROSSREF = "https://api.crossref.org/works"`, line 37) is preferred when the seed has a deposited reference list; **OpenAlex** (`OPENALEX = "https://api.openalex.org/works"`, line 38) is the fallback (used for `cited_by_count`/most-cited-reference ranking) — confirmed by `A2-standing-acquisition-contract.md:343-346`: "Crossref is enough when the seed has a deposited `reference` list. OpenAlex or Semantic Scholar is the fallback." **Semantic Scholar** is also present as a service (`cloud-run-backend/services/semantic_scholar_service.py`) but was not observed wired into the citation-expansion pilot itself in this pass. **NASA ADS** exists only as a batch *acquirer* (`acquire_nasa_ads_batch.py`), not as a citation-graph expander.
- Rules (governance-level, `A2-standing-acquisition-contract.md:307-352`): one hop only, never re-expand from a paper the hop just admitted; keep a candidate only if ≥2 seeds cite it or it's `isInfluential`/top-cited-in-seed; capped per-seed (≤8) and per-batch (~50 seeds → "a few hundred new papers at most"); seeds are restricted to trusted classes only — chart-named papers (A1), `research_focus.json` `flagged` + researcher-cited papers (#43), later a small attributed scout slice — **never the whole corpus**. Explicitly ruled out in `governance/RESOURCE_MANIFEST.md:127-132`: "Ungated bibliography ingest... A stored reference list is Map metadata, not an acquisition queue."
- First (and apparently only) run: 2026-08-15, 50 seeds (33 researcher-cited, 17 chart-named) → 93 admitted, 78 new papers written, 14 already-in-corpus (attributed), 1 title-mismatch skipped (`A2-standing-acquisition-contract.md:391-395`).

Everything else in Q1 (daily PubMed/bioRxiv/arXiv scout, batch acquirers) is **keyword/category scouting**, not citation- or author-graph expansion. No author-works-based expansion (e.g., "pull everything by this author") script was found anywhere in this repo.

---

## Q6 — Reuse

**Already parameterizable (reuse directly for TDAP):**
- Frontend chrome: `lib/knowledge-engine-projects.ts`'s `KE_PROJECTS` config object — adding a `tdap` key with its own `label`, `framingLine`, `processContentType`, `searchPlaceholder`, `askExamples`, `quickExamples` is the documented, designed-for extension point (its own header comment calls it "chrome-first v1," designed to be config-driven).
- Embedding backfill: `backfill_research_paper_embeddings.py`'s `PROFILES` dict is already collection-parameterized; TDAP papers land in the same `research_papers` collection and are picked up by the *existing* `research_papers` profile automatically — no code change needed there at all, only a large `question_scope_ids`/`cited_project` tag distinguishing them.
- Acquisition contract: A2's `research_focus.json` contract (`terms`, `since`, `flagged`, `frontier`, `mute`, `categories`, `horizons`, `seeds`) is explicitly designed to be per-project and reusable (`A2-standing-acquisition-contract.md:59-206`) — TDAP would add its own `tdap/docs/research_focus.json` (or an analogous local scratch copy) and set `categories` to arXiv topology/algebra codes (e.g. `math.AT`, `math.CO`, `cs.CG`).
- Citation expansion pilot: `citation_expansion_pilot.py` is seed-class-driven, not GLMP-hardcoded in its *mechanism* (only its default `cited_project = "glmp"` literal, see below) — reusable for a TDAP seed set with a parameter change.
- Ingest pipeline: `ingest_papers_from_metadata_json.py` is source/discipline-agnostic; `_infer_discipline()` (line 229) and the stub gate (`_reject_stub_reason`, line 174) apply uniformly.

**Hardcoded (must change for TDAP), minimal concrete list:**
1. `lib/knowledge-engine-projects.ts:22` — widen `KEProjectId` union to include `'tdap'`.
2. `lib/knowledge-engine-projects.ts:76-138` — add a `tdap: {...}` entry to `KE_PROJECTS` (mirroring the `atap` shape: `processContentType` — decide whether TDAP gets its own process-chart family now or stays `null`/papers-only initially, since TDAP is metadata-first per the task brief).
3. `lib/knowledge-engine-projects.ts:140` — add `'tdap'` to `KE_PROJECT_IDS`.
4. `lib/knowledge-engine-projects.ts:142-144` — extend `isKEProjectId()`.
5. `components/knowledge-engine/KnowledgeMapView.tsx:965` — replace the binary icon ternary with a lookup (e.g., an `icon` field added to `KEProjectConfig` and read from `KE_PROJECTS[proj.id].icon`, rather than three-way-`if`ing inline).
6. `components/knowledge-engine/RAGInterface.tsx:78-79` — generalize the hardcoded `.glmp`/`.atap` concat for the "no project selected" combined-examples case (currently a fixed 2-slice-per-project concat that silently omits a third project).
7. If/when TDAP gets its own process/chart family: `cloud-run-backend/endpoints/content/routes.py:99-100` and `cloud-run-backend/services/knowledge_map_service.py:135-136` need a `"tdap": "tdap_graphs"` (or similar) entry in both copies of `PROCESS_FAMILY_COLLECTIONS`, plus `components/knowledge-engine/constants.ts:11-12,30-37,72-79` (`ALL_PROCESS_CONTENT_TYPES`, `PROCESS_FAMILIES`, `PROCESS_DATABASE_LINKS`).
8. `components/knowledge-engine/constants.ts:51-65` — add `tdap-q1..N` entries to `BROWSE_QUESTIONS` once TDAP's `research_focus.json` questions are drafted (mirrors the `glmp-q*`/`atap-q*` id convention already established).
9. `huggingface-space/scripts/acquire_papers/citation_expansion_pilot.py:321,348` and `a1_resolve_and_ingest.py:35` — these hardcode `cited_project = "glmp"`; a TDAP-equivalent seed script (if built by A1's pattern) would set `"tdap"` instead, or the constant should become a CLI/config parameter rather than copy-pasting a third hardcoded script.
10. New `tdap_research_focus.json` (local scratch, mirroring `atap_research_focus.json`'s pattern) with `active_questions`/`frontier`/`flagged`/`categories`/`horizons`/`mute`, and (per Gary's plan) a `tdap-biomed` sub-tag — the existing schema has no native "sub-tag" concept; the cleanest fit is either (a) a second-level `terms`/`categories` split inside one `active_questions` entry, or (b) treating `tdap-biomed` as its own `frontier`/`active_questions` entry with a distinguishable question id prefix (e.g. `tdap-biomed-q1`) so it rides the existing `question_scope_ids` array mechanism without schema changes.

**Governance note (not a code hardcode, but relevant):** `CLAUDE.md:45-50` currently states "`glmp` and `atap` are the suite's only two engines." `governance/SUITE_REORG_PLAN.md:72` already anticipates this — "Engine projects (GLMP, ATAP, **future**)" — so adding TDAP as a third engine is consistent with the governance design, but `CLAUDE.md`'s summary table itself would need a one-line update to stay accurate; this is a documentation-consistency item, not a blocker.

---

## Q7 — Hazards

**1. `batch_*.json` manifests fed into per-paper ingest — mechanism and footguns.**
Acquisition batch scripts write per-batch summary sidecars (e.g. `huggingface-space/metadata-database/papers/biology/classic/batch_0001.json`, containing `{"batch_number":1,"papers_count":0,"pmids":[],"acquired_date":...}` — not a paper record). The ingest script's file walker, `_iter_json_files()` in `cloud-run-backend/scripts/ingest_papers_from_metadata_json.py:445-457`, explicitly globs `*.json` recursively (line 447) but then **filters out `batch_*.json` by fnmatch** (lines 448-453: "Manifest side-cars (`batch_*.json`) are acquisition summaries, not [papers]"). **This footgun is already closed in the current ingest script.** The residual risk is narrower: (a) any *other* or *future* ingest path that globs `*.json` without importing this same filter (e.g., a hand-rolled TDAP ingest script) would need to reimplement the same exclusion — this is a "copy the pattern, don't reinvent it" risk, not a live bug; (b) the stub gate (`_reject_stub_reason`, line 174) is a second independent safety net for genuinely bad records (no title AND no identifier) — a `batch_*.json` sidecar would likely fail that gate too if the filename exclusion were ever removed, since it has no `title` field, so the two guards are partially redundant/defense-in-depth.

**2. Divergence between the repo and executed Jetson/sdcard trees.**
This is a documented, known, ongoing risk — not something I could independently re-verify (no SSH/filesystem access from this Windows machine to the Jetson at `gary@192.168.1.222` / `/media/sdcard/...`).
- `huggingface-space/scripts/scheduler/SCOUT_ARCHITECTURE.md:104-128` states plainly: the git tree (`huggingface-space/scripts/scheduler/scout/`) is "source of truth," `/media/sdcard/scheduler/scout/` on the Jetson is a "**live production copy — outside git**," and `sync_to_jetson.sh` ships only `scheduler/scout/*.py` + `scout_ingest.sh` — it explicitly does **not** ship `ingest_metadata_to_firestore.sh`, `run_post_ingest_hooks.sh`/`publish_knowledge_engine_status.sh`, or `cloud-run-backend/scripts/ingest_papers_from_metadata_json.py` (those reach the Jetson only via a full-tree `git pull`, a separate and easy-to-forget step).
- `papers/STUB_LEAK_PHASE12_FINDINGS_2026-07-17.md:19-24` documents a concrete historical instance of this drift causing a real defect: the production entrypoint `scout_ingest.sh` "is not in the repo," and pinned reject-log arguments on `main` were "inert" on Jetson because the sync script never shipped the wrapper that would have used them.
- `papers/STUB_GATE_PR_DRAFT_NOTES_2026-07-17.md:32-57` further documents that an *unversioned* Jetson `scout_ingest.sh` makes "sync... a silent no-op" possible, and gives a specific diagnostic (absent GCS reject-log signal ⇒ "old code; executed path not synced").
- Given this, **any TDAP acquisition/backfill script that needs to run on a cron on the Jetson must go through the same `sync_to_jetson.sh` + `git pull` two-step**, and should not assume that pushing to `main` alone makes new code live. I could not confirm from this checkout whether the Jetson tree today (2026-09-19) is currently in sync or currently drifted — that requires the SSH access this task explicitly told me not to assume and I do not have.

**3. Risk to the May eval-freeze file `research_papers_20260526.jsonl.gz`.**
- **Location:** This is **not a file in this repository** (confirmed: no `find`/grep hit for the literal filename anywhere under the checkout). It is an already-exported artifact living at `gs://regal-scholar-453620-r7-podcast-storage/research_data/snapshots/research_papers_20260526.jsonl.gz` and archived permanently at Zenodo DOI `10.5281/zenodo.18463303` (`papers/knowledge_engine_vision.md:267`, `papers/manifest.json:7-33`, `papers/dense_retrieval_benchmark_handoff.md:15,28,36`). It is a **frozen gzip snapshot**, n=59,499 documents, SHA-256 `3dd5e019fca5f8e823bd71020a80c534b2e1a9e7199272b27c0b13da40ee8065` (`papers/manifest.json:8`, `papers/meta_partial.json:8`).
- **What depends on it:** the Discover-AI-manuscript dense-retrieval evaluation pipeline — `papers/retrieval_pilot_colab_bundle.ipynb`, `papers/run_dense_track_a.py`, `papers/rankings_lexical.csv`/`rankings_openai_dense.csv`, `papers/table4_metrics_lexical_vs_openai.csv`, and the manuscript's §6/Data-availability citation of this exact SHA-256 and Zenodo DOI.
- **Could a TDAP backfill disturb it?** No, not directly or by accident — the frozen file is a point-in-time export, already uploaded and hashed; nothing in the live ingest/backfill/embedding pipeline reads from or writes to that GCS object or its Zenodo mirror. `docs/EVAL_FREEZE.md:39-42` states the scope limit explicitly: "Freeze for the paper = frozen export artefact, not 'Firestore can never change.' ... Infrastructure improvements after the freeze (embedding backfill, process catalog rollout) did not modify this export artefact" (also stated verbatim in `papers/knowledge_engine_vision.md:267`). The only way a TDAP effort could touch this is indirectly and non-destructively: if someone later re-exports a *new*, differently-named snapshot of the live (now TDAP-enlarged) `research_papers` collection and conflates it with the frozen one in a citation — a documentation/process risk, not a data-overwrite risk. `docs/EVAL_FREEZE.md:9-15` also notes the crontab lines that disabled ingest for this freeze (`run_daily_scout_with_ingest.sh`, disabled 2026-05-26) were meant to be **re-enabled after the eval archive shipped** — I could not confirm from this checkout whether that re-enable already happened or whether TDAP acquisition would need to coordinate around it (see Limits).

---

## Limits

- **No Jetson/SD-card filesystem or SSH access from this machine.** All Jetson-related claims above are sourced from in-repo documentation (`SCOUT_ARCHITECTURE.md`, `STUB_GATE_PR_DRAFT_NOTES_2026-07-17.md`, `STUB_LEAK_PHASE12_FINDINGS_2026-07-17.md`, `cursor_handoff_2026-08-27_jetson_cron_check.md`) rather than direct observation of `/media/sdcard/...` or the live crontab. Current (2026-09-19) Jetson sync state is unverified.
- **Cost-per-1000-records for embedding backfill is not documented anywhere in this checkout.** `backfill_research_paper_embeddings.py` logs `tokens_total` per run, but those run logs live under `/media/sdcard/logs/embed_auto_*.jsonl` on the Jetson (unreachable). I deliberately did not substitute an unverified external OpenAI list-price estimate for a repo-sourced figure.
- **Whether `--auto` embedding backfill is actually cron-scheduled on the Jetson today** could not be confirmed — `SCOUT_ARCHITECTURE.md:22-24` shows an "embed --auto before publish" slot as reserved/planned (as of the doc's 2026-07-23 last-update), not confirmed installed.
- **`cloud-run-backend/endpoints/glmp/routes.py` and `cloud-run-backend/endpoints/rag/routes.py`** were confirmed to reference GLMP/ATAP in filenames/module context but returned no direct string-literal hits for `'glmp'`/`'atap'` in my targeted grep; I did not read either file in full line-by-line, so there could be additional hardcodes inside them I did not enumerate.
- **Canonical `glmp`/`atap` sibling repos** (`C:\Users\garyw\glmp`, `C:\Users\garyw\atap`) exist locally and were confirmed to hold the canonical `research_focus.json` files (`glmp/docs/research_focus.json`, `atap/docs/research_focus.json`), but I did not do a full audit of those repos' own acquisition/backfill code — this recon focused on `copernicus-web` per the task's explicit repo scope. If TDAP's canonical `research_focus.json` is meant to live in a new sibling `tdap` repo (mirroring GLMP/ATAP's pattern), that repo does not yet exist locally.
- **Whether the 2026-05-26 crontab disable (`run_daily_scout_with_ingest.sh`) has since been re-enabled** is not confirmed from this checkout — `docs/EVAL_FREEZE.md` describes it as a runbook/plan, and later handoffs (e.g., `SCOUT_ARCHITECTURE.md`, dated 2026-07-23) describe a *different*, currently-live cron path (the split `scout_*.py` workers + `scout_ingest.sh`) that appears to run regardless — I could not fully reconcile whether the specific `run_daily_scout_with_ingest.sh` freeze-disable is still in effect on top of that newer architecture, or superseded by it.
- **No execution of any script was performed** (per instructions) — all `--dry-run`/`--pin` behavior described above is read from source, not observed running.

---

# TDAP run proposal — 2026-09-19 addendum

Read-only source review of `huggingface-space/scripts/acquire_papers/citation_expansion_pilot.py` (393 lines, read in full), plus the relevant sections of `ingest_papers_from_metadata_json.py` and `researcher_cited_intake.py` it depends on. No script was executed. No Firestore/GCS writes. Nothing below has been run — this is a proposal for review.

## Q1 — Direction: references only, or also citing papers?

**References only (backward, seed → what the seed cites). No citing-papers (forward) direction exists anywhere in this script or its dependencies.**

- `crossref_refs()` (`citation_expansion_pilot.py:101-121`) hits Crossref `works/{doi}` and reads the `reference` array from the response `message` — Crossref's own bibliography for that work.
- `openalex_refs()` (`:124-167`) hits OpenAlex `works/doi:{doi}` and reads `referenced_works` — same direction, OpenAlex's copy of the work's own reference list.
- `fetch_seed_refs()` (`:170-177`) tries Crossref first, falls back to OpenAlex only if Crossref returns nothing (`if not refs:` at `:173`).
- No code path queries "what cites this DOI" (OpenAlex's `filter=cites:<id>` or Crossref's `is-referenced-by-count` expansion) anywhere in this file or in `researcher_cited_intake.py`/`a1_resolve_and_ingest.py`.

**This directly bears on the flood concern**: because expansion only walks a seed's *own* reference list (bounded — a paper's bibliography is typically tens to ~150 entries) and that list is further capped to the top 5 by `cited_by_count` per seed (`TOP_N_IN_SEED = 5`, `:41`, applied at `:208`), a highly-cited seed like Zomorodian–Carlsson or Otter et al. cannot flood the corpus through this mechanism *as built* — the flood risk you're worried about (thousands of papers citing a hub paper) only exists in the citing-papers direction, which this script doesn't implement. If a forward-direction mode is added later, that is exactly where a per-seed opt-out would become load-bearing (see Q4).

## Q2 — Seeds: input format, and the no-DOI case

**Not an external seed list.** `collect_seeds()` (`:66-98`) queries Firestore `research_papers` directly for docs where `acquisition_channel == "researcher_citation"` (`:83`) or `== "glmp_chart_source_candidate"` (`:89`), sorts the chart-source group by `named_by_charts` count descending (`:92-93`), dedupes by normalized DOI (`_norm_doi`, `:56-63`), and caps at `--seed-cap` (default `SEED_CAP = 50`, `:39,235`). There is no `--seed-file` or `--seed-doi` argument today.

**A seed with an arXiv ID but no DOI is silently dropped.** `add()` (`:71-81`) requires `doi = _norm_doi(data.get("doi")); if not doi or doi in seen: return` (`:72-74`) — a doc with no `doi` field never enters the `seeds` list, so it's never walked for references. This isn't a crash or a warning, it's a silent skip.

Separately verified: an arXiv-only paper **can** already be intake'd into `research_papers` without a DOI — `researcher_cited_intake.py`'s `resolve_arxiv()` (`:225-253`) queries the arXiv Atom API directly by arXiv ID, no DOI required, and the resulting record is written with `acquisition_channel: "researcher_citation"` (`:570`). So a DOI-less seed *can* exist in the corpus under exactly the channel `collect_seeds()` queries — but `collect_seeds()`'s own DOI filter (`:72-74`) still excludes it from becoming an active expansion seed, because Crossref/OpenAlex reference-lookup is DOI-keyed throughout this script (there's no arXiv-ID-based reference-fetch path). **This is a real gap, not a config knob**: at least one of your six seeds may hit it, and the fix isn't "pass it in differently" — the reference-walk mechanism itself has no DOI-less path. See minimal change list, item 1, and Limits.

## Q3 — Authors: can it expand by author works?

**No.** Nothing in `citation_expansion_pilot.py`, `researcher_cited_intake.py`, or `a1_resolve_and_ingest.py` queries by author — every lookup here is DOI-keyed (seed collection, Crossref/OpenAlex reference fetch, candidate resolution).

**Smallest addition — OpenAlex author works:** a new function mirroring `openalex_refs()`'s shape (`:124-167`), e.g. `openalex_author_works(author_openalex_id, per_page=50)` calling `GET https://api.openalex.org/works` with `filter=author.id:<id>` (or `filter=author.orcid:<orcid>`), `select=doi,title,cited_by_count,publication_year`, reusing the existing `UA` header (`:36`) and `_norm_doi()` (`:56-63`) for dedup. Placement: a new seed-source function parallel to `collect_seeds()` (`:66-98`), returning the same seed-dict shape (`doc_id`/`doi`/`title`/`kind`) with `kind="anchor_author"` so it flows through `admit()` unchanged, or — cleaner given the different signal type — as its own candidate pool merged into `admit()`'s output with a distinct `reason` (e.g. `"anchor_author_work"`) so it's auditable separately from `cited_by_2plus_seeds`/`top_cited_in_seed` in the report. Requires an OpenAlex author ID per anchor author first (resolvable by name+affiliation search, not yet attempted here — see Limits).

## Q4 — Filtering: relevance filter, per-seed cap, and config-vs-fork for the two proposed rules

**Existing filter (`admit()`, `:180-226`):** a candidate DOI is kept if either (a) **≥2 distinct seeds** reference it (`cited_by[rd]`, checked `len(parents) >= 2` at `:197`, hardcoded literal `2`), or (b) it's among the **top 5** references of a single seed by `cited_by_count` (`TOP_N_IN_SEED = 5` at `:41`, sliced at `:208`). There's also a per-run cap of `BATCH_NEW_CAP = 200` new Firestore writes (`:42`, enforced at `:360-362`) — a total-run cap, not per-seed.

**Bug worth flagging while I'm in this code:** `PER_SEED_CAP = 8` (`:40`) is checked at `:211` (`if added >= PER_SEED_CAP: break`) but `scored` is already sliced to `TOP_N_IN_SEED = 5` items at `:208` before that loop runs — so the `PER_SEED_CAP` check can never trigger; the real per-seed ceiling today is 5, not 8. Not a TDAP-specific issue, just noted since I read the line.

**Could the two proposed rules be config instead of forks? Yes, for both:**
- **"Linked to ≥2 seeds"** — already a single hardcoded int at `:197`. Lifting it to a `--min-parents` CLI arg (default 2) is a one-line change plus one argparse entry; no fork needed.
- **"References only" per-seed flag** — moot in the current script since references-only is the *only* direction implemented (Q1). If a forward (citing-papers) mode is added later, `collect_seeds()` already returns one dict per seed (`:76-81`); adding a `direction` key there (default `"references"`) and branching on it inside a future forward-fetch call is a natural extension of the existing per-seed dict shape, not a structural fork. I'd design it this way now, even before forward-direction exists, so the flag has somewhere to live.

## Q5 — Tagging: which fields, parameter or hardcoded?

Today, on every admitted candidate (`:317-322`, and again on merge into an existing doc at `:348`):

| Field | Value written | Parameterized? |
|---|---|---|
| `acquisition_channel` | `"cited_by_collection"` | **No** — string literal at `:317` |
| `cited_project` | `"glmp"` | **No** — string literal at `:321` (new doc) and `:348` (merge event) |
| `cited_by` | `"citation_expansion_pilot"` | No — literal at `:319`, but this one is accurate/generic as-is |
| `cited_context` | templated from module-level `CITED_CONTEXT` (`:43-46`) + `reason` | No, but content is fine as-is |
| `cited_for_question` | **never set** | N/A — field doesn't appear anywhere in `record` |

No CLI arg exists for any of these — the `argparse` block (`:234-238`) only defines `--seed-cap`, `--write`, `--report`.

**`question_scope_ids` is not written by this script at all.** It's derived downstream, in `ingest_papers_from_metadata_json.py`'s `_to_firestore_paper()` (`:417-424`), purely from `acquisition_matches[].question` or a `cited_for_question` field on the record — and the pilot never sets `cited_for_question` (confirmed against the exact field list the pilot does set, `:317-322`). So today, a pilot-admitted paper gets `acquisition_channel`/`cited_project` but **no `question_scope_ids`** — that's a gap against your requirement (`tdap-q1`/`q2`/`q3` tagging), not something that happens automatically once `cited_project` is parameterized.

## Q6 — Gate and dedup

**Gate:** the file-based stub gate (`_reject_stub_reason`, `ingest_papers_from_metadata_json.py:174-189`) is **not applied** to pilot-created records — it's only invoked from the main file-ingest loop at `ingest_papers_from_metadata_json.py:642`, and the pilot calls `_to_firestore_paper()` directly (`citation_expansion_pilot.py:364`), bypassing that loop entirely. The pilot's actual gate is the combination of: `admit()`'s ≥2-seeds/top-5-in-seed rule (`:195-226`); successful DOI resolution via `resolve_doi`/`resolve_doi_encoded` (`:298-300`, itself requiring a Crossref or bioRxiv/medRxiv hit — `researcher_cited_intake.py:151-188`); a title-match check unless the harvested title is short/blank (`:305-315`, using `a1_resolve_and_ingest.titles_match`); and the `BATCH_NEW_CAP = 200` total-writes cap (`:42,360-362`). In practice this is stricter than the stub gate, not looser — every admitted record already has a Crossref/OpenAlex-resolved title and DOI by construction.

**Dedup — this is exactly how it avoids duplicating already-in-corpus ATAP computational-topology papers:** the pilot first checks Firestore for a doc at the *computed* id (`ingest._doc_id_for_paper()`: pmid > arxiv_id > bibcode > provided id > sha256-of-identity-core, `ingest_papers_from_metadata_json.py:259-277`; checked at `citation_expansion_pilot.py:325-326`). If that misses, it falls back to `researcher_cited_intake.check_firestore_duplicate()` (`researcher_cited_intake.py:314-347`), which queries `research_papers` directly by `doi`, then `pmid`, then `arxiv_id`, then `bibcode` (`:327-334`) — **regardless of which project or acquisition channel originally created that doc.** So a Zomorodian–Carlsson reference already sitting in the corpus from ATAP's acquisition would be found by this check and is not re-created.

**On a match it does not skip — it merges** (`citation_expansion_pilot.py:333-354`): `parent_paper_ids` gets `firestore.ArrayUnion(cand["parents"])`, and a new citation event (`cited_by`, `cited_date`, `cited_context`, `cited_project`) is appended to the doc's existing `citations` array if not already present (`:343-352`). Today that event's `cited_project` is hardcoded to `"glmp"` (`:348`) even when merging onto an ATAP-tagged doc — i.e., an ATAP paper picked up this way would silently gain a `cited_project: "glmp"` tag. This needs the same parameterization as Q5 (→ `"tdap"`), and confirms the merge path is exactly where your ATAP-overlap concern gets resolved correctly *once* that literal is a parameter — not skipped, but correctly additively tagged.

## Q7 — Dry run: does a no-write, scored-candidate-list mode already exist?

**Yes, and it's the default, not an opt-in flag.** `--write` is `action="store_true"` with no default-true anywhere (`:236`); every Firestore mutation in the file — `col.document(doc_id).create(doc)` (`:365`) and `col.document(doc_id).update(update)` (`:353`) — sits inside an `if args.write:` / `elif args.write:` branch. Without `--write`, the run performs only: Firestore **reads** (seed collection, existence checks, dup checks), external API reads (Crossref/OpenAlex/bioRxiv, all read-only), and writes a local JSONL report (`--report`, default `citation_expansion_pilot_report.jsonl`, `:34,237`) — one line per candidate with `status` (`would_create`/`would_merge`/`unresolved`/`title_mismatch`/`capped`), `doi`, `title`, `reason`, `parents`, `cited_by_count` (`:373-381`). That already satisfies "a candidate list with scores and no Firestore writes" exactly as asked.

**So the minimal change isn't adding a dry-run mode — it's making the currently-hardcoded seed source and tags parameterizable (Q2, Q5, Q6) so a TDAP dry run has somewhere to put `tdap`-specific values before you ever touch `--write`.**

## Minimal change list (proposed edits to `citation_expansion_pilot.py`, none applied)

1. **Seed source** — add `--seed-doi-file PATH` (one DOI per line) as an alternative to `collect_seeds()`'s Firestore-channel query, so the six known seeds don't need to pre-exist in Firestore under a matching `acquisition_channel` first. Construct seed dicts directly from the file, still deduped via `_norm_doi()`.
   - **Does not solve the DOI-less seed.** If a seed genuinely has no DOI (not "not yet looked up" but structurally absent, e.g. an unpublished arXiv-only preprint), there is no reference-list-fetch path for it in this script at all (Q2) — it can be intake'd as a corpus member via `researcher_cited_intake.py` (no DOI required there), but it cannot itself be walked for one-hop expansion until/unless a DOI exists or an arXiv-native reference-fetch path is built (larger change, not proposed here).
2. **`--cited-project`** CLI arg, replacing the literal `"glmp"` at `:321` and `:348`; default `"glmp"` to preserve existing callers.
3. **`--acquisition-channel`** CLI arg, replacing the literal `"cited_by_collection"` at `:317`; default unchanged.
4. **`--cited-for-question`** CLI arg, threading a value into `record["cited_for_question"]` (new — this field is never set today) so `question_scope_ids` populates via the existing, unmodified logic in `ingest_papers_from_metadata_json.py:417-424`. A single value per run is consistent with how `researcher_cited_intake.py` already does this (one `--cited-for-question` per invocation); tagging three different `tdap-q1`/`q2`/`q3` scopes across one seed set would mean either three separate runs (grouped by which seeds map to which question) or extending this to accept a per-seed question mapping — flagging the choice for you rather than assuming.
5. **`--min-parents`** CLI arg (default 2), replacing the literal `2` at `:197`.
6. *(Optional, pre-existing bug, independent of TDAP)* fix the dead `PER_SEED_CAP`/`TOP_N_IN_SEED` mismatch (`:40-41,208`) if an actual per-seed cap of 8 (rather than the de facto 5) is wanted.

None of these are structural forks — all are literal-to-parameter changes or one new optional seed-input path, consistent with the script's existing shape.

## Exact dry-run command (proposed — NOT run)

Requires changes 1–5 above to exist first; shown here as the target invocation once they do, using the default (no `--write`) mode on the Yoga box with ADC as you specified:

```
python huggingface-space/scripts/acquire_papers/citation_expansion_pilot.py \
  --seed-doi-file tdap_seed_dois.txt \
  --cited-project tdap \
  --acquisition-channel tdap_seed_expansion \
  --cited-for-question tdap-q1 \
  --min-parents 2 \
  --report papers/tdap_citation_expansion_pilot_report_2026-09-19.jsonl
```

No `--write`. Output is a local JSONL candidate report only; Firestore is touched read-only (seed/dup lookups).

## Limits (this addendum)

- **The six seed papers' actual DOI status is unknown to me** — I don't have Jordan's seed list, only "some possibly arXiv-only, no DOI." I can't say which specific seed(s) hit the no-reference-path gap in Q2 until the list exists; flagging the mechanism, not the specific paper.
- **Anchor authors' OpenAlex author IDs are not resolved** — Vejdemo-Johansson confirmed as a person, but no author-ID lookup was attempted (would need name+affiliation disambiguation, ideally by ORCID); the Q3 addition can't actually run until that exists.
- **Reference-list coverage for the real six seeds is unverified** — Crossref's `reference` field is only as complete as what the publisher deposited; the script already falls back to OpenAlex when Crossref is empty (`:173-175`), but whether either source has usable reference data for these specific seeds is unknown until tried.
- **`validate_metadata.validate_paper()` schema validation is not called anywhere in `citation_expansion_pilot.py`** — only `researcher_cited_intake.py`'s standalone `main()` calls it (`:576`). I did not check whether pilot-created records could fail schema validation at some later point in the pipeline (e.g. embedding backfill or the frontend); not verified in this pass.
- **Semantic Scholar** remains uninvestigated as a possible third reference source beyond noting its existence (per the original recon) — not re-checked here.
- **No script was executed to confirm any of the above behaviorally** — everything above is read from source, per the read-only/propose-only instruction.

---

# Task 2 — citation_expansion_pilot.py diff (2026-09-19, implemented in working tree, NOT committed)

Implemented the minimal change list from the addendum above, amended per Claude Chat's domain review: `--seed-doi-file` (CSV, columns `doi,question_ids`, `|`-separated question ids) replacing the originally-proposed single `--cited-for-question`; `--cited-project`, `--acquisition-channel`, `--min-parents`, `--top-n-in-seed` as CLI params; a `direction` key on every seed (fixed to `"references"`, no forward mode implemented); dead `PER_SEED_CAP` removed (chose removal over fixing, since `top_n_in_seed`/formerly `TOP_N_IN_SEED` was already the real, tighter cap). All new-arg defaults reproduce prior literals exactly (`--cited-project glmp`, `--acquisition-channel cited_by_collection`, `--min-parents 2`, `--top-n-in-seed 5`) — no `--seed-doi-file` means `collect_seeds()` runs unchanged and `question_ids` is `frozenset()` for every seed, so the new `question_scope_ids` write path is inert (empty union) for any existing GLMP invocation.

**Verification performed:** `python -m py_compile` only — confirms syntax, not behavior. The script was **not run** (per the no-execution constraint), so the "defaults preserve existing GLMP behavior exactly" claim is a read-through-the-code guarantee (every new branch is gated on `args.seed_doi_file`/`qids` being truthy, both empty by default), not an observed regression test.

**Limits (this task):**
- Seeds loaded via `--seed-doi-file` are **not** themselves written to `research_papers` by this script — it only ever writes admitted *candidates*. If the seed papers themselves need to be discoverable TDAP corpus members (not just reference-walk hubs), they need separate intake (e.g. `researcher_cited_intake.py` per seed) — this is a Task 3/4 dependency, not something Task 2's change addresses.
- The `doi,question_ids` CSV format is new — I designed it for this change; it doesn't mirror an existing convention elsewhere in the repo, so it's worth Chat/Jordan explicitly signing off on the shape before Task 3 builds a real file against it.
- Multi-question seeds (a seed cited for more than one question) are supported by the format (`tdap-q1|tdap-q2`) but untested — no seed in the draft mapping needs it yet (each seed maps to exactly one question), so this path is unexercised.

---

# Task 3 — seed file (2026-09-19)

`papers/tdap_seed_dois.csv`, 6 rows. Every DOI verified live against Crossref/OpenAlex (not from memory) — see commands run in-session. Reference-list availability checked for all six against both sources ahead of any pilot run, since that directly determines whether a seed can produce any citation-expansion candidates at all:

| Seed | Question | DOI | Crossref refs | OpenAlex refs |
|---|---|---|---|---|
| de Silva, Morozov, Vejdemo-Johansson — *Persistent Cohomology and Circular Coordinates* (Discrete Comput. Geom. 2011) | tdap-q1 | `10.1007/s00454-011-9344-x` | 19 | 12 |
| Perea — *Sparse Circular Coordinates via Principal ℤ-Bundles* (Abel Symposia 2020) | tdap-q1 | `10.1007/978-3-030-43408-3_17` | 24 | 24 |
| Scoccola, Gakhar, Bush, Schonsheck, Rask, Zhou, Perea — *Toroidal Coordinates: Decorrelating Circular Coordinates With Lattice Reduction* (SoCG 2023, LIPIcs) | tdap-q1 | `10.4230/lipics.socg.2023.57` | **404 — not registered on Crossref** | **0** |
| Zomorodian, Carlsson — *Computing Persistent Homology* (Discrete Comput. Geom. 2005) | tdap-q2 | `10.1007/s00454-004-1146-y` | **0** (falls back to OpenAlex per `fetch_seed_refs()`) | 19 |
| Otter, Porter, Tillmann, Grindrod, Harrington — *A roadmap for the computation of persistent homology* (EPJ Data Science 2017) | tdap-q2 | `10.1140/epjds/s13688-017-0109-5` | 179 | 205 |
| Nigmetov, Morozov — *Distributed Computation of Persistent Cohomology* (ALENEX 2026 / arXiv:2410.16553) | tdap-q2 | `10.1137/1.9781611978957.15` | **0** | **0** |

**Nigmetov–Morozov DOI confirmed** — Crossref record matches the arXiv preprint's title and authors exactly (verified both independently), so the DOI given in Chat's message is correct.

**Two of six seeds are structural dead ends for citation expansion, confirmed ahead of any run**: **Scoccola et al.** (DOI exists but isn't on Crossref at all, and OpenAlex's copy has zero `referenced_works`) and **Nigmetov–Morozov** (both sources empty — a very recent 2024/2026 paper, likely not yet fully indexed with references anywhere). This isn't a bug in the pilot script; it's a real gap in what Crossref/OpenAlex have indexed for these two specific works. Practical effect: **the effective reference-walking seed pool for this run is 4, not 6** — this directly bears on Chat's `--top-n-in-seed ≈15` reasoning ("six seeds at top-5 yields too few, too-generic") — the real base is 4 productive seeds, so the under-yield concern is somewhat stronger than stated, reinforcing (not undermining) the case for raising `--top-n-in-seed`.

This doesn't mean Scoccola et al. or Nigmetov–Morozov should be dropped as seeds — they're both directly on-topic and real anchor-author work (per Chat's mapping); they just can't be *expanded from* via this mechanism. Both should still become corpus members in their own right (see Task 2's note: seeds aren't auto-added to `research_papers` by the pilot — they need separate intake, e.g. `researcher_cited_intake.py`, if they're to be discoverable/taggable corpus members, not just expansion hubs).

**Limits (this task):** I did not attempt to independently verify the Perea or de Silva/Morozov/Vejdemo-Johansson/Scoccola papers' relevance beyond title/author/venue matching — I did not read full text or abstracts to confirm topical fit against `tdap-q1`'s wording; that's a domain judgment for Jordan/Chat, not something I can verify from metadata alone. I did not check for a possible published (non-preprint) venue for Nigmetov–Morozov beyond the ALENEX 2026 proceedings entry already found.

---

# Task 4 — dry run, executed with approval (2026-09-19)

**A bug in my own Task 2 diff, found only by running it.** `admit()` builds `question_ids` as a Python `set` (needed for union arithmetic across parents); the pre-existing "unresolved" report-line branch spreads the whole candidate dict (`**cand`) straight into `json.dumps`, which can't serialize a raw `set`. `py_compile` (Task 2's only verification) cannot catch this — it's a runtime type error, not a syntax error. First run crashed after 9 DOI resolutions, before any candidate was written to the report or to Firestore (`--write` was never passed, so only read calls had happened: seed-existence checks and the crash itself was in local JSONL writing, not Firestore). **Fix**: convert `question_ids` to a sorted list once, at the single point `admit()` returns its rows, rather than at each call site (`citation_expansion_pilot.py`, end of `admit()`) — closes the bug for every write branch at once, not just the one that crashed. Re-ran the identical approved command after the fix; it completed clean. This is exactly the kind of thing "a clearly marked limit is a finding" is for: my own diff had a real bug that only surfaced under execution, caught here rather than during a future `--write` run.

**Command actually run** (twice — first attempt crashed, see above; second succeeded), exactly as proposed and approved, no `--write`:
```
python huggingface-space/scripts/acquire_papers/citation_expansion_pilot.py \
  --seed-doi-file papers/tdap_seed_dois.csv \
  --cited-project tdap \
  --acquisition-channel tdap_seed_expansion \
  --top-n-in-seed 15 \
  --report papers/tdap_citation_expansion_pilot_report_2026-09-19.jsonl
```

**Candidate counts by status/reason:**

| status | count |
|---|---|
| would_create | 17 |
| unresolved | 1 |
| would_merge | **0** |
| already_in_corpus | 0 |
| title_mismatch | 0 |
| new_capped | 0 |
| created / merged | 0 / 0 (no `--write`) |

Admitted 18 total (6 by `cited_by_2plus_seeds`, 12 by `top_cited_in_seed`); one of the 18 (`10.2312/spbg/spbg04/157-166`, "Topological estimation using witness complexes," an OpenAlex-only hit with no Crossref record) failed DOI resolution and landed as `unresolved`, leaving 17 `would_create`.

**ATAP overlap (`would_merge`): zero.** None of the 18 admitted candidates matched an existing `research_papers` doc by doc-id or by doi/pmid/arxiv_id/bibcode dedup query. Contrary to the original worry that "many computational-topology papers may already exist via ATAP," this run found none — plausibly because ATAP's own corpus centers on proof-graph/logic topics (`math.LO`, `cs.LO`, `cs.PL`, `math.CT`, `cs.DM`), not computational-topology algorithmics, so the actual subject overlap with these Zomorodian–Carlsson-adjacent references turned out to be small. This is a live-data result, not a structural guarantee — a future TDAP run with different seeds could still hit real overlap.

**Seeds with empty reference lists from both Crossref and OpenAlex, confirmed live:** exactly the two predicted in Task 3 — **Scoccola et al.** (`10.4230/lipics.socg.2023.57`) and **Nigmetov–Morozov** (`10.1137/1.9781611978957.15`), both `source: none`, `0 refs`, in the actual run output. No new empty-list seeds beyond those two.

**A live-data structural finding not caught by static reading**: the `top_cited_in_seed` bonus path can only ever fire for a seed resolved via the **OpenAlex fallback**, because `crossref_refs()` always sets `cited_by_count: None` (`citation_expansion_pilot.py`, `crossref_refs()`) and `admit()`'s top-cited loop filters on `r.get("cited_by_count") is not None`. In this run, only **one** of the six seeds (Zomorodian–Carlsson) resolved via OpenAlex (`source: openalex`); the other three productive seeds (de Silva et al., Perea, Otter et al.) all resolved via Crossref. Confirmed in the actual output: **all 12 `top_cited_in_seed` candidates have Zomorodian–Carlsson as their sole parent** — none came from the other three productive seeds. Practical effect: raising `--top-n-in-seed` to 15 only deepened the Zomorodian–Carlsson branch; it did not, and structurally cannot, pull more top-cited candidates from de Silva et al., Perea, or Otter et al. This is worth Chat/Jordan knowing before relying on `--top-n-in-seed` to broadly widen the pool — it widens one seed's contribution, not all seeds'.

**`validate_metadata.validate_paper()` results** (checked separately — the pilot itself never calls this; re-resolved each `would_create` DOI and ran the same function `researcher_cited_intake.py` uses, no Firestore writes, full results in `papers/tdap_candidate_validation_2026-09-19.json`):

**16 of 17 pass.** The one failure — `10.1201/9780429493911`, "Elements of Algebraic Topology" (a Munkres-style textbook entry) — fails only the *soft* 85% quality threshold (83.3%), not a structural/required-field error; Crossref's metadata for this entry is thinner (no abstract) than a typical journal article. Not a blocker, just lower-quality metadata, consistent with it being a textbook rather than a paper.

**Limits (this task):**
- The re-resolution used for validation hit Crossref/bioRxiv APIs a second time per candidate (the dry run doesn't persist full resolved records, only report summaries) — mildly redundant network traffic, but necessary since nothing else retains the full record.
- `already_in_corpus`/`would_merge = 0` reflects this specific seed set and this specific moment in the corpus; it is not evidence that TDAP and ATAP will never overlap, only that this run didn't find any.
- I did not evaluate whether any of the 17 `would_create` candidates are actually *substantively relevant* to TDAP's questions beyond the mechanical admission gate (≥2-seed citation or top-cited-in-seed) — e.g. "Nonlinear Dimensionality Reduction by Locally Linear Embedding" and "A Global Geometric Framework for Nonlinear Dimensionality Reduction" (Isomap) are classic manifold-learning papers admitted because Perea's and de Silva et al.'s papers both cite them — plausibly relevant background, but a domain judgment for Jordan/Chat, not verified by me.
- No `--write` run was performed or requested; nothing above reflects a real corpus write.

---

# Task 5 — frontend toggle edits, applied (2026-09-19, working tree only, NOT committed)

Applied, after review, the four requested edits plus one necessary consequence and three necessary follow-on fixes discovered only by actually type-checking:

**Applied as proposed:**
1. `lib/knowledge-engine-projects.ts:22` — `KEProjectId` widened to include `'tdap'`.
2. `lib/knowledge-engine-projects.ts` — new `tdap` entry in `KE_PROJECTS` (icon `🍩`, `processContentType: null`, `askExamples`/`quickExamples` grounded in `tdap-q1`/`q2` — **not live-tested**, since no TDAP corpus exists yet; unlike GLMP/ATAP's examples, which this file's own comments say were verified against `/api/vector-search/semantic`).
3. `KnowledgeMapView.tsx:965` — `proj.id === 'atap' ? '📐' : '🧬'` ternary replaced with `proj.icon`, reading from the new config field (added to `KEProjectConfig`, backfilled onto `glmp`/`atap`'s existing entries too).
4. `RAGInterface.tsx:74-81` — the hardcoded `.glmp`/`.atap` two-line concat replaced with `KE_PROJECT_IDS.flatMap(...)`, generalizing to any number of projects.

**Necessary consequence, flagged before applying:** `KEProjectConfig.processContentType` had to become nullable (`'glmp' | 'math' | null`) since TDAP has no chart/process family in v1 (per your decision). This required a guard in `searchContentTypesForProject()` (`lib/knowledge-engine-projects.ts`) so a `null` doesn't get pushed into the content-types array.

**Found only by running `tsc --noEmit`, not by reading the diff**: three more call sites elsewhere in the codebase assumed `processContentType` was always a string and broke — `ContentBrowser.tsx:78,95` (`useState<string>`/setter typed for `string`, would have taken a raw `null` for TDAP) and `KnowledgeMapView.tsx:333` (`params.set('process_family', ...)` would have set the literal string `"null"` as a live URL query parameter). Fixed with the same guard pattern (`?? ''` / a null-check before `.set()`), shown to you and approved before applying. **Verified: `npx tsc --noEmit -p tsconfig.json` now reports 0 errors project-wide** (confirmed by full run, not just grep on the touched files).

**Known, non-blocking cosmetic gap, not fixed (out of the four-item scope)**: `SearchInterface.tsx:61,203` renders `"{label} process charts"` regardless of whether the project has a process family — selecting TDAP will show "TDAP process charts" heading text over an empty result, since TDAP has none. No crash, no data issue, just a misleading label; flagged for a future pass rather than fixed unilaterally here.

**Incidental**: running `tsc` regenerated `tsconfig.tsbuildinfo` (a tracked build-cache file); reverted with `git checkout -- tsconfig.tsbuildinfo` since it's noise unrelated to this task, not an intentional change.

**Final working-tree state**: 5 modified files (`citation_expansion_pilot.py`, `lib/knowledge-engine-projects.ts`, `KnowledgeMapView.tsx`, `ContentBrowser.tsx`, `RAGInterface.tsx`), 4 new untracked files (this recon doc, `tdap_seed_dois.csv`, the pilot-run report, the validation-results JSON). Nothing staged, nothing committed, no Firestore/GCS writes, no Jetson/cron changes at any point across all five tasks.

**Limits (this task):** I did not visually test the toggle in a running dev server (no `npm run dev` session was started) — verification here is limited to `tsc --noEmit` (type-correctness) and source reading, not a rendered-UI check. If you want a visual pass before committing, that's a separate step I haven't done.

---

# Task 5 follow-up — visual dev-server check (2026-09-19)

Started `npm run dev`, drove it with Playwright (installed locally via `npm install --no-save`, not added to `package.json`; `node_modules/` is gitignored so this left no trace in git status), clicked through the toggle, screenshotted, checked console/page errors. Stopped the server afterward (`taskkill` on the PID bound to :3000 — `lsof` isn't available in this Windows/Git-Bash environment).

**Confirmed working:**
- All three toggle buttons render (GLMP, ATAP, TDAP) and are independently clickable; clicking TDAP highlights it and un-highlights the others, same as GLMP/ATAP.
- TDAP's framing line renders correctly under the header when selected.
- Quick Examples section correctly filters to TDAP's three examples (with the 🍩 icon rendering, confirming the `proj.icon` fix works, not just compiles).
- Search tab: placeholder text updates to TDAP's exact configured string.
- Ask Questions tab: all three TDAP `askExamples` render as clickable example-question buttons.
- Switching back to GLMP and to ATAP after TDAP both restore their correct framing/content — no state leakage.
- **Zero console errors, zero page errors** across every interaction.

**One real, now visually-confirmed defect** — worse than the "cosmetic" read I gave it before actually seeing it rendered. Three hardcoded strings render **"TDAP process charts"** where TDAP has none:
- `SearchInterface.tsx:61` → Search tab's "Vector Search:" description line.
- `SearchInterface.tsx:203` → (same pattern, a second location in that file).
- `RAGInterface.tsx:146` → Ask Questions tab's "RAG:" description line.

Both visibly appeared in the actual rendered page: the Search tab shows a checkbox literally labeled **"TDAP process charts"** (alongside Research Papers/Podcasts/Videos, implying it's a real, checkable content type), and the Ask tab's description reads "Retrieves context from **TDAP process charts** plus papers and podcasts." Neither is true — TDAP has `processContentType: null`. This isn't just an aesthetic nit; it actively implies a content type that returns nothing. **Not fixed** — still out of the four-item Task 5 scope, and you hadn't approved touching these two files. Recommend a follow-up task if you want it fixed (three one-line changes, same pattern as the fixes already applied: guard on `KE_PROJECTS[project].processContentType` before using the "process charts" phrasing).

**Limits:** Did not test the "Build Map"/"Search"/"Ask Question" *submit* actions themselves (would hit live backend APIs, potentially with cost/side effects, and wasn't asked) — only that the UI renders and the toggle's config-driven text updates correctly. Did not test `Browse Content` or `Statistics` tabs with TDAP selected (not asked; likely fine given `KE_PROJECT_IDS.map()` is used generically there per earlier recon, but unverified). Playwright + Chromium (~115MB) now sit in `node_modules/` and `%LOCALAPPDATA%\ms-playwright\` on this machine — not committed, but present on disk; let me know if you'd like them removed.

---

# Task 5 follow-up fix, applied and visually re-verified (2026-09-19)

Fixed the three "TDAP process charts" mislabels, same guard pattern as everywhere else in this diff (check `KE_PROJECTS[project].processContentType` before claiming a process family exists):

- `SearchInterface.tsx` — new `processClause` derived value; `processLabel` (the checkbox text) now reads `"TDAP (no process charts yet)"` instead of `"TDAP process charts"`; the "Vector Search:" prose sentence drops the process-charts clause entirely for a project with none, rather than rendering an empty/awkward fragment.
- `RAGInterface.tsx:145-150` — same guard; the "RAG:" prose sentence now reads "Retrieves context from papers and podcasts..." for TDAP, omitting the false claim, while GLMP/ATAP keep their original wording exactly.

**Verified**: `tsc --noEmit` clean (0 errors). Re-ran the dev server + Playwright check: TDAP no longer shows "TDAP process charts" anywhere (Search tab checkbox now reads "TDAP (no process charts yet)", Ask tab prose omits the clause); GLMP's wording in both tabs is byte-for-byte unchanged ("GLMP process charts" still present, confirming the fix is additive/conditional, not a regression). Zero console errors. Dev server stopped afterward (`taskkill` on the port-3000 PID).

**Final state**: 6 modified files (adds `SearchInterface.tsx` to the 5 from before), 4 new untracked files, nothing staged or committed, no Firestore/GCS/Jetson/cron writes across all of Task 5 or its follow-up.

---

# Correction — video acquisition already exists (2026-09-19, post-commit)

**The original recon (Q1/Q5/Q6 above) is incomplete on video.** It never looked outside `copernicus-web`, and video acquisition lives entirely in a separate sibling repo this recon didn't scope: **`C:\Users\garyw\sciencevideodb`** (internal name "SciTV"). Gary flagged, correctly, that GLMP/ATAP searches already return videos and that "video sweep ingest runs" had already happened; my first answer (no YouTube acquisition exists, would be net-new work) was wrong. Corrected here rather than silently, since the original recon doc is what Chat and Jordan will read as the source of truth.

**What actually exists, confirmed by reading the code (not from memory):**
- `sciencevideodb/docs/INGESTION.md` documents a full pipeline: YouTube Data API search → transcript extraction (captions, manual-preferred/auto-fallback) → embedding → Postgres storage (`videos`, `channels`, `transcript_segments` tables).
- `sciencevideodb/cloud-run-backend`-equivalent sync happens via `copernicus-web/cloud-run-backend/scripts/sync_videos.py`, which pulls from that Postgres DB into Firestore for GLMP/ATAP to search — this is the script I misread earlier as "the suite's own self-generated podcast-videos"; it is not, it syncs real third-party YouTube content (the SQL join includes `channel_name`, `channel_url`, `youtube_channel_id`, `video_url`).
- **Question-scoped sweep configs already exist for both projects**: `sciencevideodb/packages/ingestion/sweeps/{atap-q1-q4,atap-q3,atap-thin-2026-09,glmp-next,glmp-q1-q8,glmp-q6-q11,glmp-thin-2026-09}.json`. Each config has `project`, `disciplines`, `perQuestionCap`, `minDurationSec`/`maxDurationSec`, a `mute` keyword blocklist, and per-question `{q, queries, keep}` (search queries + a keep-keyword relevance filter) plus an optional `seeds: [{youtubeId, questionIds, note}]` list for hand-picked known-good videos — structurally a close parallel to the paper citation-expansion seed file built earlier in this doc.
- **The runner script is already project-agnostic despite its name**: `sciencevideodb/packages/ingestion/src/scripts/sweep-glmp-videos.ts` takes `--config <path>` and is already invoked against both `glmp-*.json` and `atap-*.json` configs (see its own docstring usage examples). Defaults to dry-run (`dryRun = !ingest`, i.e. `--ingest` is required to write) — same safety pattern used throughout the paper pipeline.
- **These sweeps have actually run**, not just been configured: `sciencevideodb` git history — commit `cdf23ab`, "Add September GLMP/ATAP thin-question sweep configs so the 918-to-940 ingest is repeatable" — implies a real, counted ingest (918→940 videos). Not independently re-verified against live Firestore/Postgres in this session.

**Implication for a later TDAP video phase**: very likely just writing `sweeps/tdap-q1.json`/`q2.json`/`q3.json` (same shape as the ATAP/GLMP configs) and running the existing `sweep-glmp-videos.ts --config ... ` in its default dry-run mode first — probably no code changes, mirroring exactly the reuse story Task 2 already established for `citation_expansion_pilot.py`. This is a materially lower-effort estimate than my original "net-new work" answer.

**Limits of this correction**: `sciencevideodb` is a separate repo/stack (TypeScript/Node, its own Postgres DB, its own YouTube API credentials) that this session has only now looked at for the first time, briefly — I have not read `packages/ingestion/src/youtube/client.ts`, the embedding/search-indexing steps, or the `channels` table's current contents, and have not confirmed whether `SCIENCEVIDDB_DATABASE_URL`/YouTube API credentials are reachable from this machine (Yoga) the way Firestore ADC is. Nothing here was verified by running anything in `sciencevideodb` — read-only source/doc/git-log reading only, consistent with this whole recon's constraints. A real TDAP video phase would need its own recon pass into that repo before proposing sweep configs, not just this note.

---

# Production deploys and a scoping-gap finding (2026-09-19)

**Two production deploys performed with approval, both verified live:**

1. **Frontend Cloud Run deploy** (`gcloud builds submit --config cloudbuild-frontend.yaml .`), to ship the toggle from Tasks 5+follow-up. The service had **no CI/CD** — no GitHub Actions, no Cloud Build trigger (`gcloud builds triggers list` returned 0 items) — so pushing to `main` alone never would have deployed it; the prior revision (`copernicus-frontend-00049-nfs`) was three weeks stale (last deployed 2026-08-26). New revision `copernicus-frontend-00050-7qh` confirmed serving all three toggle labels via a live `curl`.

2. **Knowledge-engine status JSON republish**, after adding a genuinely new stat (below) — regenerated `huggingface-space/knowledge-engine-status.json` locally (`generate_status_page.py --source api`) and uploaded it to the public GCS bucket via ADC-based `google.cloud.storage.Client()` (the existing `upload_knowledge_engine_status_gcs.py` hardcodes a Jetson-only service-account file path that doesn't exist on this machine, so the same upload logic was run directly with this session's already-authenticated ADC instead of via that script). A second frontend deploy shipped the UI code that reads the new field. Confirmed live end-to-end: `curl` on the public GCS URL, then a Playwright check of the production Statistics tab.

## Finding: paper/podcast/video search has never been scoped by project — not a TDAP-specific gap

Gary reported "nice results" on Search/RAG/Knowledge Graph/Ask Questions with TDAP selected, which read as evidence TDAP was already working. It isn't. Live-tested:
- **Firestore, read-only, confirmed zero TDAP-tagged papers** on every field that could carry one (`cited_project == "tdap"`: 0; `acquisition_channel == "tdap_seed_expansion"`: 0; `question_scope_ids array_contains "tdap-q1"`/`"tdap-q2"`: 0 each). Consistent with the whole TDAP effort being dry-run only (Tasks 3-4).
- **Live `/api/rag/answer` call** with a TDAP quick-example query ("circular coordinates persistent cohomology") returned citations with `cited_project: None` on every item — general ATAP/math-corpus papers, podcasts, and lecture videos matched by loose keyword/semantic overlap (sharing words like "cohomology"), not real TDA content. The LLM's own answer explicitly said the provided context didn't address the question.
- **Root cause, in `lib/knowledge-engine-projects.ts`'s own pre-existing comment**: *"Project view scopes processes to that project's family only; papers stay unscoped until Layer B."* Confirmed by reading `RAGInterface.tsx`'s actual fetch call: the `content_types` param sent to the backend never carries a project/scope value for papers/podcasts/videos — only the (GLMP/ATAP-only) process-family string. This predates all of today's TDAP work; GLMP and ATAP have the identical limitation, just harder to notice with large existing corpora.
- **Not fixed, not in scope of anything asked today** — flagged here because it directly explains a real, surprising observation and should inform expectations: selecting a project currently changes only chrome (framing text, process-chart filtering) and, for TDAP, changes nothing else discoverable, since it has no chart family either. A real "Layer B" (scoping papers/podcasts/videos to project via `question_scope_ids`) would be a separate, larger backend+frontend change, not proposed or estimated here.

## Feature added: "Papers by initiative" stat (Statistics tab)

Gary asked for a TDAP number on the Statistics tab; there wasn't one for *any* project before this (only discipline-level biology/mathematics counts and process-chart-family counts existed — confirmed by reading `StatsDashboard.tsx` before writing anything).

- `generate_status_page.py`: new `INITIATIVE_QUESTION_IDS` constant (glmp-q1..11, atap-q1..4, tdap-q1..3 — snapshotted from each project's `docs/research_focus.json`; **tdap's repo is private, so unlike glmp/atap it cannot be live-fetched from a public raw.githubusercontent.com URL the way this file's other GCS-metadata fetches work** — all three are kept as static tuples for consistency rather than half-dynamic; refresh by hand if a project's question list changes). New `fetch_papers_by_initiative()`: one live Firestore `question_scope_ids array_contains_any <that initiative's question ids>` count query per initiative — deliberately *not* implemented as N separate `/api/content/browse?question=<id>` calls summed together, since a paper scoped to more than one question in the same initiative would be double-counted that way; a single `array_contains_any` avoids it exactly. No public-API equivalent exists for this (unlike `fetch_papers_by_discipline`), so this path requires live Firestore access and has no last-known-good fallback — on failure the field is omitted entirely (same reasoning as the existing `fetch_focus_fallback_metric`).
- `StatsDashboard.tsx`: new "Papers by initiative" section, rendered generically via `KE_PROJECT_IDS.map()` (a 4th future project needs no dashboard change either).
- **Live result, confirmed on production**: GLMP 45,456, ATAP 2,822, TDAP 0. The GLMP/ATAP numbers are also new information — this dashboard never showed per-initiative paper counts for them before today, only chart-family and discipline counts.

**Limits**: `INITIATIVE_QUESTION_IDS` is a hand-maintained snapshot, not derived from each repo's live `research_focus.json` — it will silently undercount (not error) if a project's question list grows and this constant isn't updated to match. Not verified against a second, independent counting method beyond the live Firestore query itself.

---

# Repo made public; outreach sent to Jordan (2026-09-19)

- **`github.com/garywelz/tdap` flipped from private to public** (Gary's decision, matching GLMP/ATAP's existing posture) so the "Using TDAP inside your own Claude" README pattern (added same day, mirroring `atap`'s) actually works — raw.githubusercontent.com fetches aren't authenticated, so this was blocked while the repo was private. Verified both raw URLs resolve (HTTP 200) after the flip.
- **Gary emailed Jordan** the repo link, the live-toggle URL, the three provisional questions, the six seed papers with their draft question mapping, and two onboarding options (a read-only Claude Project, or hands-on Claude Code/Cursor access against the public repo). Correctly frames Mikael Vejdemo-Johansson as Jordan's PhD advisor (not merely a contact), leaving Mikael's role, if any, to Jordan and Mikael to decide.
- **Current status: waiting on Jordan's (and possibly Mikael's) response.** Nothing is blocked on further engineering work — the full technical path (seed intake → `citation_expansion_pilot.py --write` → embedding backfill) is validated end-to-end via the dry run and ready to execute once the questions/seeds are confirmed. See the "Task 4" and "Correction" sections above for exactly what that sequence would run.
- No Firestore/GCS writes occurred in this step beyond the already-described production deploys and status-JSON republish earlier in this doc.

---

# Seed provenance resolved; three pilot-script improvements built (2026-09-19)

**Item 1 (seed choices) resolved — the gap was a hand-off gap, not a research gap.** Jordan's original email to Gary named exact titles for the six tdap-q1/q2 seeds ("Perea, Sparse Circular Coordinates via Principal ℤ-Bundles"; "Scoccola et al., Toroidal Coordinates..."). Claude Chat's hand-off to Claude Code relayed authors only ("Perea," "Scoccola et al."), not those titles — so Claude Code independently searched Crossref and picked the same papers Jordan had already named, by title/topic match, without knowing they were already confirmed. **The six seeds stand on Jordan's authority, not on that search** — recorded in `tdap/docs/seed_papers.md` with this provenance. The four tdap-q3 candidates remain Claude Chat's suggestions, DOI-verified, not yet confirmed by Jordan or Mikael.

**Three improvements built to `citation_expansion_pilot.py`, per Claude Chat's review, none committed yet (pending your review of the diff):**

1. **Semantic Scholar by arXiv ID, third fallback source** (`semanticscholar_refs_by_arxiv()`) — tried only when a seed has an `arxiv_id` (new optional seed-file column) and both Crossref and OpenAlex came back empty by DOI. Confirmed live for the two TDAP seeds that needed it: 32 references (Scoccola et al.) and 28 references (Nigmetov–Morozov), versus zero via DOI on either other source.
2. **`cited_by_count` backfilled from OpenAlex for every reference, regardless of source** (`_enrich_cited_by_count()`) — closes the gap found in the last round: the `top_cited_in_seed` admit path only ever fired for a seed resolved via `openalex_refs()` (the only source that natively carries citation counts), so 3 of 4 productive TDAP seeds structurally couldn't use that path no matter what `--top-n-in-seed` was set to. Batched via OpenAlex's `doi` filter (pipe-OR, verified live to support up to 50 DOIs per request, same pattern `openalex_refs()` already uses).
3. **Per-seed `admit_policy`** (new optional seed-file column, `strict` default / `all_references`) — `strict` keeps the existing min-parents/top-N gates (unchanged GLMP/ATAP behavior, still the default for every seed unless a seed file opts in). `all_references` admits every one of that seed's resolvable references outright, no gate. Assigned per Claude Chat's domain call: the six tdap-q1/q2 seeds (bibliographies already predominantly computational topology) get `all_references`; the four tdap-q3 candidates (bibliographies mostly non-TDA neuroscience, e.g. Gardner et al.'s) stay `strict`.

**Also**: `--batch-new-cap` is now a CLI param (was a hardcoded `BATCH_NEW_CAP = 200`), doesn't affect dry-run counts (the cap only ever applies inside the `--write` branch — confirmed by re-reading `main()`'s control flow, `new_writes` never increments in a dry run so the cap check is always false), and the report JSONL now includes each candidate's reference `source` (crossref/openalex/semanticscholar) and the admitted-by-`all_references_from_seed` reason, needed for the second dry run's fuller report.

**Verification**: `py_compile` clean. Live-verified the one new external API call this relies on — OpenAlex's `doi` filter does support pipe-OR batching (confirmed with a real 2-DOI request before writing the batching code, not assumed). Not yet run end-to-end — that's the second dry run, next.

**A real bug found by that first end-to-end run, not by review.** The first run of the round-2 dry run (10 seeds, `all_references` on six) completed (175 admitted, 167 would_create) but the seed-fetch log showed `[3/10] none 0 refs` and `[6/10] none 0 refs` — the two seeds the Semantic Scholar fallback exists specifically for. Checked live: `curl` on the exact same S2 endpoint, seconds later, returned HTTP 200 with 32 references. So `semanticscholar_refs_by_arxiv()`'s original silent `except Exception: return []` / `if resp.status_code != 200: return []` had almost certainly swallowed a transient 429 (S2's anonymous rate limit is strict and shared per-IP; this session had already hit one manually testing minutes earlier) as if it meant "no references" — exactly the kind of failure that looks identical to a real empty result unless you check. Fixed: retry with linear backoff (up to 3 attempts) on 429/exception, and a printed warning on final failure instead of silent `[]`. Re-running now with the fix before trusting any of round 2's numbers. This is the second time in this TDAP effort a bug in my own diff was only caught by actually running the code (the first was the `question_ids` JSON-serialization bug in the first dry run) — `py_compile` and code review cannot catch either class of failure.

## Second dry run, final (2026-09-19)

Re-ran after the fix. Semantic Scholar recovered 29 references for Scoccola et al. (close to the 32 found by hand — small run-to-run variance from S2's own index), but Nigmetov–Morozov's S2 call hit a **persistent** 429 that exhausted all 3 retries — genuine rate-limit exhaustion under this run's total request volume, not a bug. Did not chase a third run for one seed's marginal contribution; the numbers below already deliver what was asked for.

**Final counts** (`papers/tdap_citation_expansion_pilot_report_round2_2026-09-19.jsonl`): 198 admitted, **189 would_create**, 1 would_merge, 1 unresolved, 7 title_mismatch.

| Breakdown | |
|---|---|
| By reason | `all_references_from_seed` 84, `top_cited_in_seed` 74, `cited_by_2plus_seeds` 32 |
| By source | crossref 156, semanticscholar 24, openalex 10 |
| By question | tdap-q2 107, tdap-q3 59, tdap-q1 41 (candidates can carry more than one) |
| By seed | Otter et al. 96, Gardner et al. 26, Scoccola et al. 24, Kang-Xu-Morozov 23, Rybakken-Baas-Dunn 18, Perea-Harer 14, Zomorodian-Carlsson 12, Perea 10, de Silva et al. 9 |

**The one `would_merge`**, checked live in Firestore: `pubmed_28459448`, "Single-cell topological RNA-seq analysis reveals insights into cellular differentiation and development" — a real, existing GLMP paper (`question_scope_ids: ["glmp-q9"]`, `discipline: biology`), cited by Otter et al.'s survey as an application example. Legitimate overlap, not a bug — the merge path adds `tdap-q2` alongside the existing `glmp-q9` tag via `ArrayUnion`, doesn't touch anything else on the doc.

**Validation**: 183 of 190 pass (`papers/tdap_round2_candidate_validation_2026-09-19.json`). All 7 failures are the same soft 85%-quality-threshold miss as round 1 (textbooks/proceedings entries with no abstract in Crossref) — no structural errors.

**Quality finding, not resolved, needs a decision before `--write`**: Otter et al. alone contributes 96 of 189 candidates (>50%). Chat's stated assumption for the `all_references` policy ("nearly every reference is computational topology") holds well for the other five tdap-q1/q2 seeds (9-24 candidates each, predominantly on-topic in a manual scan) but measurably less well for Otter et al. specifically — it's a deliberately broad "roadmap" survey, and its bibliography includes real non-TDA background material: e.g. "Collective dynamics of 'small-world' networks" (general network science), "Novel Type of Phase Transition in a System of Self-Driven Particles" (a Vicsek flocking-model physics paper), "Generalized Linear Models" and "Finding Groups in Data" (general statistics/clustering texts) — all admitted because Otter's own survey cites them as background/comparison material, not because they're TDA papers. Full title list for spot-check, organized by seed with reason/source/citation-count: `papers/tdap_round2_candidate_titles_2026-09-19.md`.

**`--batch-new-cap` recommendation (task 5)**: default 200 is sufficient for this exact candidate set (189 would need creating) — no change needed to write this specific round. Flagging that it's close (189/200) in case a future round adds more.

**Nothing written** — no `--write`, no Firestore/GCS mutation beyond the read-only Firestore lookup used to verify the `would_merge` record's existing tags.

---

# Limits, recorded per Claude Chat's request (2026-09-19)

1. **Nigmetov–Morozov's references remain unfetched.** Semantic Scholar has them (confirmed manually: 28 refs by arXiv ID), but the round-2 dry run's automated attempt exhausted all 3 retries on a persistent 429 (S2's anonymous rate limit is strict and shared per-IP; this session had already made several manual S2 calls testing the mechanism). An S2 API key (free to request, raises the rate limit substantially) would very likely resolve this — not obtained in this session. Until then, this seed contributes zero expansion candidates, though it's still a valid seed/corpus member in its own right.

2. **`top_cited_in_seed`'s popularity bias is a real, structural limit for interdisciplinary seeds, not just a tuning question.** Ranking a seed's own references by raw `cited_by_count` systematically favors broadly-cited "hub" papers over narrowly-relevant specialized ones, for any seed whose bibliography spans more than one field. Confirmed in the round-2 data: Otter et al.'s (tdap-q2, `all_references` policy) top-cited references include general network-science and statistics classics it cites only as background (e.g. "Collective dynamics of 'small-world' networks," 43,633 citations); the four tdap-q3 candidate seeds' most-cited references skew toward general neuroscience rather than topology specifically, for the same reason. This isn't unique to TDAP — any future seed drawn from an applied/survey paper in any initiative would hit the same bias.

3. **Embedding-similarity relevance scoring is proposed for a future round, not built.** Instead of (or alongside) citation-count ranking, scoring each candidate reference by embedding similarity to the seed's own question text (or to a small set of known-good exemplar papers) would directly address the popularity-bias limit above — it would rank by topical relevance rather than raw citation count, and could apply uniformly regardless of whether a seed's bibliography is narrow or broad. No implementation exists yet; this is a design direction for round three, contingent on Jordan's/Chat's decision on how to handle the Otter et al. and tdap-q3 hold lists.

---

# Regression check found a real, unflagged behavior change for the GLMP default path (2026-09-19)

Chat asked for exactly this check, and it did its job: **default-args GLMP behavior is NOT unchanged.** Compared the pre-change (`528db05c5`, pushed) and current versions, both run with zero flags (`collect_seeds()` default path, no `--write`), via `git stash` on just this one file (isolated the comparison without disturbing any other uncommitted work):

| | before (`528db05c5`) | after (current) |
|---|---|---|
| admitted | 115 | 274 |
| would_create | 27 | 166 |
| would_merge | 85 | 103 |
| title_mismatch | 3 | 5 |
| `cited_by_2plus_seeds` | 97 | 97 |
| `top_cited_in_seed` | 15 | 172 |

**Root cause, confirmed by diffing the two candidate sets: `cited_by_2plus_seeds` is byte-identical (97/97, unaffected — that rule never touched `cited_by_count`) and every one of the 112 pre-change candidates still appears in the post-change set (0 lost).** The entire jump is 157 *new* `top_cited_in_seed` admissions, caused by `_enrich_cited_by_count()` (task 3, this session) backfilling `cited_by_count` from OpenAlex for every seed's references, including Crossref-resolved GLMP seeds that previously had no `cited_by_count` at all and so could never contribute to the top-cited path. **This is exactly the mechanism task 3 was built to fix — it just wasn't gated to TDAP, and I did not realize until running this check that it changes GLMP's default output too.**

**Correcting an earlier claim**: prior reports in this doc said "all new-flag defaults reproduce prior GLMP behavior exactly." That's true for every CLI argument's default value (`--min-parents 2`, `--top-n-in-seed 5`, `--cited-project glmp`, `--acquisition-channel cited_by_collection` are all unchanged) — but `_enrich_cited_by_count()` isn't behind a flag at all, so the claim was incomplete. Nothing was lost (0 pre-change candidates dropped, purely additive), but it's a real, unflagged expansion of what GLMP's own default runs would admit.

**Not remediated — needs your decision, not mine:**
- **Option A**: leave it. The change is strictly additive (finds more legitimately-top-cited references GLMP's own seeds already had, previously invisible only because of which source happened to resolve them) — arguably a genuine improvement that should apply everywhere, not just TDAP.
- **Option B**: gate `_enrich_cited_by_count()` behind a new opt-in flag (e.g. `--enrich-cited-by-count`, default off), restoring byte-for-byte GLMP default parity, with TDAP passing the flag explicitly.

Diagnostic reports kept for evidence: `papers/_regression_before.jsonl`, `papers/_regression_after.jsonl` (both `--write`-free, no Firestore mutation from generating them — read-only seed lookups plus external API calls only).
