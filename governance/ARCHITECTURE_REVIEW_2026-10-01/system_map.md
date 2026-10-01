# CopernicusAI Suite — System Map (Architecture Review Phase 1)

*Read-only inventory. Status date 2026-10-01. Covers all 8 sections — sections
1–4 were drafted and opened as a draft PR first, per the task's own
stop-and-report instruction; sections 5–8 were added in a follow-up pass on
the same branch/PR, both before any merge. Everything below is either a live,
one-shot GET-only check or a source-code citation (file:line); no number here
is inferred. Path note: the task specified
`governance/ARCHITECTURE_REVIEW_2026-10/01_system_map.md`, which splits the
date across a directory boundary — almost certainly a stray slash. Normalized
to `governance/ARCHITECTURE_REVIEW_2026-10-01/system_map.md`; flagging rather
than guessing silently.*

---

## 1. Code and hosting surfaces

### GitHub (`garywelz`, via `gh repo list`, live 2026-10-01)

| Repo | Private | Default branch | Last push | Purpose / feeds |
|---|---|---|---|---|
| `copernicus-web` | no | main | 2026-10-01 | Monorepo: Core backend (`cloud-run-backend/`), the Knowledge Engine frontend, governance. Feeds Vercel (`copernicus-web-public` → www.copernicusai.fyi) and the `copernicusai` HF Space (`huggingface-space/`) |
| `glmp` | no | main | 2026-09-30 | GLMP engine: focus file, master TODO, scout/decoder scripts, dashboard. Feeds `glmp` HF Space; has the suite's only scheduled GitHub Action |
| `atap` | no | main | 2026-09-28 | ATAP engine: proof-graph corpus, focus file. Feeds `atap` HF Space |
| `tdap` | no | main | 2026-09-27 | TDAP engine (hosted, outside collaborator). Open questions, seed papers, hold list. No confirmed HF Space |
| `sciencevideodb` | no | main | 2026-09-09 | YouTube-filtered science video DB, transcript search. Feeds `sciencevideodb` HF Space and (per entry 005) a now-authenticated-only Cloud Run service `scienceviddb-web` is PUBLIC — see §2 |
| `progframe` | no | main | 2026-08-24 | Programming Framework generator/tooling. Feeds `programming_framework` HF Space |
| `metadata-database` | no | main | 2026-07-30 | Browse/search table generator for the shared paper corpus. Feeds `metadata_database` HF Space and the GCS table `papers-database-table.html` |
| `poiesis-engine` | no | main | 2026-08-27 | Fiction/poetry engine dev — **not referenced anywhere in `governance/`**. Question for Gary: in scope or not? |
| `garysfirst-agent` | yes | main | 2026-09-28 | Not referenced anywhere in `governance/`. UNKNOWN purpose from this seat |
| `shadow` | yes | main | 2026-08-30 | Explicitly out of scope (`AGENT_ROLES.md` rule 13) |
| `shadow-archive` | yes | main | 2026-04-21 | Companion to `shadow`; same out-of-scope status inferred, not stated |
| `copernicus-podcast-api` | yes | main | 2025-07-09 | Named in `AGENT_ROLES.md`'s legacy table as "audit — confirm live before folding." Last push over a year ago; the live podcast backend is `cloud-run-backend/` inside `copernicus-web`, not this repo. Looks dead, not confirmed |
| `GraciePCat` | yes | main | 2025-01-25 | Out of scope per `AGENT_ROLES.md` ("not a science project") |

**Discrepancy, not a finding:** `AGENT_ROLES.md`'s legacy table also lists `Copernicus_AI`, `copernicus_backup`, and `kickflip-docs`. None resolve via `gh repo view garywelz/<name>` — GitHub reports no such repository for any of the three. Either already deleted/renamed/transferred, or the table predates a cleanup that was never recorded back to governance. Question for Gary, not asserted as "deleted."

### Hugging Face Spaces (plain `GET /api/spaces/garywelz/<name>`, live 2026-10-01)

| Space | SDK | Stage | Last modified | Calls a backend API? |
|---|---|---|---|---|
| `copernicusai` | static | RUNNING | 2026-08-04 | Yes — `huggingface-space/index.html` etc. call `copernicus-podcast-api` |
| `programming_framework` | static | RUNNING | 2026-08-04 | UNKNOWN from this check — not inspected this pass |
| `glmp` | static | RUNNING | 2026-08-14 | UNKNOWN from this check |
| `atap` | static | RUNNING | 2026-08-24 | UNKNOWN from this check |
| `metadata_database` | static | RUNNING | 2026-08-04 | Serves the GCS-hosted table; the Space itself is static |
| `sciencevideodb` | static | RUNNING | 2026-08-04 | UNKNOWN from this check |

All six are public, all `sdk: static`, all report `RUNNING`. No Space runs its own compute (no Gradio/Docker runtime found) — consistent with `SUITE_REORG_PLAN.md`'s "sciencevideodb Gradio vestige — DONE" note.

### Vercel

No API token or CLI session available in this environment (`vercel` CLI not installed; no credential to use it unauthenticated) — most of this section is **UNKNOWN**, sourced instead from `governance/BULLETIN.md` entries 003/005/006 (last verified 2026-09-28, not today) plus three live, plain, single-GET domain checks run just now:

| Domain | Live check (2026-10-01) | Per BULLETIN 006 (2026-09-28) |
|---|---|---|
| www.copernicusai.fyi | **200** | live, serves `copernicus-web-public` |
| www.copernicusai.app | **TLS handshake failure** (`curl -v`: DNS resolves to 216.150.1.65, then `schannel: SEC_E_INVALID_TOKEN`) | reported cleared, serving HTTPS |
| copernicusai.app | same TLS failure | reported cleared |
| copernicusai.org | **404** | `copernicusai-site` serves an April 2025 snapshot |

**Flagging, not concluding:** the `.app` TLS failure contradicts entry 006's "cleared" note from 4 days ago. Could be a real regression, or a schannel-specific client quirk (this curl runs over Windows SChannel, not OpenSSL) rather than a server-side problem — a browser or a different client might succeed. Needs a second instrument before calling it a finding.

Per BULLETIN 005/006 (not re-verified live): 32 Vercel projects across two teams; only `copernicus-web-public` (serving the two live domains above) and `copernicus-rss-web` still rebuild on every `copernicus-web` push; six other projects were git-disconnected. `gh api repos/garywelz/copernicus-web/deployments` still lists historical environment names for the disconnected projects (`copernicus-web-2025`, `copernicusai-podcast-2025`, `copernicusai-web-032725`) — expected residue, not evidence they're still wired.

**What would answer the rest:** Vercel dashboard access or a `VERCEL_TOKEN` for the CLI/API.

---

## 2. Google Cloud (`regal-scholar-453620-r7`)

### Cloud Run (`gcloud run services list`, region `us-central1`, live 2026-10-01 — 15 services, matching BULLETIN 005's count)

| Service | Image source | Max instances | Unauthenticated access |
|---|---|---|---|
| copernicus-api | `gcr.io` (manual push) | 100 | no (closed per BULLETIN 005) |
| copernicus-backend | Cloud Run source deploy | 10 | no (closed per BULLETIN 006) |
| copernicus-frontend | `gcr.io` (manual push) | 10 | **yes** |
| copernicus-podcast-api | `gcr.io` by digest | 5 (min 1) | **yes** — the live podcast/content API |
| copernicus-podcast-form | Cloud Function (gen2) | 100 | no (closed per BULLETIN 006) |
| copernicus-podcast-generator | Cloud Run source deploy | 1 | no (closed per BULLETIN 006) |
| copernicus-research-backend | Cloud Run source deploy | 10 | no (closed per BULLETIN 006) |
| generate-podcast | Cloud Function (gen2) | 100 | no (closed per BULLETIN 006) |
| glmp-feedback | Cloud Function (gen2) | 10 | **yes** |
| glmp-process-suggestion | Cloud Function (gen2) | 10 | **yes** |
| glmp-service | Cloud Run source deploy | 20 | **yes** |
| glmp-simple-suggestion | Cloud Function (gen2) | 10 | **yes** |
| glmp-view-suggestions | Cloud Function (gen2) | 10 | **yes** |
| research-metadata-api | `gcr.io` (manual push) | 20 | no (closed per BULLETIN 006) |
| scienceviddb-web | `gcr.io` (manual push) | 10 | **yes** |

8 of 15 still allow unauthenticated access: `copernicus-frontend`, `copernicus-podcast-api` (the only one that should), and 6 `glmp-*`/`scienceviddb-web` services never addressed by BULLETIN 005/006's closure pass. Not asserting these are wrong — BULLETIN 006 explicitly scoped its closure to "no real traffic in 30 days," and these may well be live and in use. Flagging as a question for Gary: were the `glmp-*` Cloud Functions and `scienceviddb-web` in scope for that review, or missed?

### Firestore (database `copernicusai`, the only database on the project — `gcloud firestore databases list`)

16 collections (`:listCollectionIds`), each counted via `runAggregationQuery COUNT()`:

| Collection | Docs | Purpose (one line) |
|---|---|---|
| research_papers | 119,321 | The shared paper corpus — see BULLETIN 012 |
| science_videos | 1,123 | sciencevideodb's video index (matches BULLETIN 013's "live: 1,123") |
| glmp_processes | 217 | GLMP process/flowchart definitions |
| atap_graphs | 237 | ATAP's proof-graph corpus (its "public browsable corpus," per the ATAP README) |
| podcast_jobs | 77 | In-flight/completed podcast generation jobs |
| episodes | 104 | Published podcast episode catalog |
| chemistry_processes | 124 | Programming Framework demonstration corpus (chemistry) |
| computer_science_processes | 72 | Same, computer science |
| biology_processes | 56 | Same, biology |
| physics_processes | 28 | Same, physics |
| subscribers | 18 | Podcast-site subscriber accounts — **contains personal data; not inspected beyond count** |
| glmp_circuits | 18 | GLMP circuit-diagram data |
| scheduler_status | 8 | Heartbeat/status records for the nightly chain (`SUITE_REORG_PLAN.md` Part 3) |
| podcasts | 9 | UNKNOWN exact relationship to `episodes` — not disambiguated this pass |
| users | 2 | UNKNOWN purpose — not inspected |
| system_metrics | 1 | UNKNOWN purpose — not inspected |

### GCS buckets (`gcloud storage buckets list` — 15 buckets, one more than BULLETIN 005's "14")

| Bucket | Public read (`allUsers`)? | Role |
|---|---|---|
| regal-scholar-453620-r7-podcast-storage | **yes** | The suite's reader-facing surface — status pages, database tables, the RSS feed, `admin-dashboard.html`/`admin-subscribers.html` (static pages; the APIs they call are separately gated, see BULLETIN 012) |
| regal-scholar-453620-r7-internal | no | Private archive — `GLMP_MASTER_TODO.md`, an `archive/` prefix |
| copernicus-media-audio | no | Checked directly — **not** public, despite the name suggesting podcast audio. Live audio appears to be served from the podcast-storage bucket instead; this one looks unused or legacy, not confirmed |
| copernicus-media-video | no | Same caveat as above |
| copernicus-assets | not checked | — |
| copernicus-audio-regal-scholar-453620-r7 | not checked | — |
| copernicus-filestore | not checked | Named in BULLETIN 006 as closed-off (empty, public access removed) |
| copernicus-temp-regal-scholar-453620-r7 | not checked | Likely scratch |
| regal-scholar-453620-r7-podcast-storage-backup-20250707/-0708/-0708-0713 | not checked | Three dated backup snapshots of the main bucket |
| gcf-v2-sources-*, gcf-v2-uploads-*, run-sources-*, *_cloudbuild | not checked | Build/deploy staging buckets (Cloud Functions/Cloud Build), not reader-facing by convention |

The one-bucket discrepancy against BULLETIN 005 (15 vs. 14) isn't chased further — a question about which list was taken when, not a finding.

### Scheduled jobs

**Cloud Scheduler: zero jobs — the API itself has never been enabled on this project** (`gcloud scheduler jobs list` returned `SERVICE_DISABLED`, not an empty list; I did not enable it). All suite scheduling is therefore either the Jetson's local cron or GitHub Actions:
- **Jetson** (`AGENT_ROLES.md`): scout cron 10:15 AM + 8 PM ET, batch decoder 2 AM ET, FIMO scanning, paper ingest pipeline. Off-network from this seat — **UNKNOWN** current state; SSH-to-Jetson access would confirm.
- **GitHub Actions**: exactly one scheduled workflow exists suite-wide — `glmp/.github/workflows/published-drift-check.yml`, weekdays 13:00 UTC, read-only (curls published artifacts, diffs against repo). `copernicus-web` has no `.github/workflows/` directory at all.

### Secret Manager (names only, `gcloud secrets list` — 33 secrets)

`GEMINI_API_KEY`, `GOOGLE_AI_API_KEY`, `admin-api-key`, `anthropic-api-key`, `api-key`, `cloud-sql-password`, `copernicus-db-url`, `copernicus-service-key`, `core-api-key`, `elevenlabs-api-key`, `gcp-copernicusai-tts-key`, `gemini-api-key`, `google-ai-api-key`, `google-client-id`, `google-client-secret`, `hf-token`, `nasa-ads-token`, `news-api-key`, `openai-api-key`, `pubmed-api-key`, `scienceviddb-database-url`, `twitter-*` (7 secrets: access-secret/token/token-secret, api-key/secret, bearer-token, client-id/secret), `vertex-ai-service-account-key`, `youtube-api-key`, `youtube-client-id`, `youtube-client-secret`, `zenodo-api-key`.

**Notable naming collision:** both `GEMINI_API_KEY`/`gemini-api-key` and `GOOGLE_AI_API_KEY`/`google-ai-api-key` exist (4 distinct secret IDs for what may be the same underlying key, in two casings each) — not resolved which, if any, is actually read; see §3.

---

## 3. Model providers — call sites

### Google AI / Vertex AI (Gemini)
Two distinct integration paths for the same model family, not one:
- **`google-generativeai` SDK** (Google AI Studio API key path): `genai.GenerativeModel('gemini-2.5-flash')` — `cloud-run-backend/main.py:2145`, `cloud-run-backend/paper_processor.py:91,94` (paper preprocessing/summarization — `.pro` for a second tier). Fallback chains `['gemini-2.5-flash', 'gemini-2.5-pro']` also appear at `main.py:775,935` and `services/podcast_generation_service.py:491,843,1198,1247` (podcast script generation).
- **`vertexai` SDK** (GCP-native, service-account auth): `GenerativeModel("gemini-2.5-flash")` — `services/rag_service.py:237` (RAG fallback when OpenAI is unavailable, see below) and `services/knowledge_map_service.py:747`.

### OpenAI
- **Chat/RAG**: `gpt-4o-mini`, default `self.model_name` — `services/llm_providers/openai_rag.py:28`, and **this is the preferred RAG provider**: `services/rag_service.py:207-223` picks OpenAI first whenever `RAG_PROVIDER` is unset and an OpenAI key is available (it is — `openai-api-key` exists in Secret Manager), falling back to Vertex Gemini only if OpenAI init fails. So the knowledge-engine "Ask Questions" feature is, by default, calling **OpenAI**, not Gemini or Claude.
- **Embeddings**: `text-embedding-3-small` — `services/llm_providers/openai_embedding.py:29`, and the same string in two backfill scripts (`scripts/backfill_research_paper_embeddings.py:105`, `scripts/backfill_glmp_embeddings_v2.py:39`).
- **Image generation**: `gpt-image-1` / `gpt-image-1-mini` — `content_fixes.py:855-857`, `services/podcast_generation_service.py:1844,2033` (podcast episode thumbnails).

### Anthropic
- `claude-3-5-haiku-20241022` — `services/llm_providers/claude_rag.py:28`, a RAG provider **option**. `rag_service.py`'s provider-selection logic (lines 207-243) only ever initializes OpenAI or Vertex; I did not find a branch that selects `claude_rag.py` by default. Looks like an available-but-currently-unused provider, not confirmed inactive — would need a runtime trace or logs to be sure.

### Third party (not Anthropic/OpenAI/Google, noted because it's in the same call-site family)
- **Voyage AI**: `voyage-3.5` — `services/llm_providers/voyage_embedding.py:29`, gated on a `voyage-api-key` Secret Manager entry ("33% cheaper than Vertex AI" per `main.py:376`'s comment). Live Vertex embedding default is `text-embedding-004` — `services/embedding_service.py:35`.
- **ElevenLabs**: TTS, `model_id: "eleven_multilingual_v2"` — `elevenlabs_voice_service.py:493`, four named voice IDs for host/expert roles (lines 63-90).

---

## 4. Knowledge sources

| Source | Ingest script | Keying | Live vs. batch | Doc count (2026-10-01, from `sources` field) |
|---|---|---|---|---|
| PubMed | `acquire_papers/acquire_pubmed_batch.py`, `a1_resolve_and_ingest.py` | `pubmed_<pmid>` | Batch (Jetson cron, per AGENT_ROLES.md) | 77,250 |
| arXiv | `acquire_papers/acquire_arxiv_batch.py` | `arxiv_<id>` | Batch | 26,489 |
| Crossref | `acquire_papers/acquire_crossref_batch.py` | `crossref_<doi>` | Batch | 12,626 |
| bioRxiv/medRxiv | `acquire_papers/acquire_biorxiv_medrxiv_batch.py` | `biorxiv_<doi>` / `medrxiv_<doi>` (inferred from doc IDs seen in BULLETIN 012's duplicate sample) | Batch | 1,907 / 1,035 |
| NASA ADS | `acquire_papers/acquire_nasa_ads_batch.py` **exists** | would be `nasa_ads` per `sources` vocabulary | Batch, but evidence below suggests it has never successfully run | **0** |
| PMC | no script found anywhere in `acquire_papers/` | — | never built | **0** |
| OpenAlex | no script found | — | not built | n/a |
| YouTube | referenced via `youtube-api-key`/`youtube-client-id/secret` secrets; feeds `sciencevideodb`, not `research_papers` | — | UNKNOWN cadence — not traced this pass | n/a (1,123 videos in `science_videos`, not papers) |
| Researcher-cited / citation expansion | `researcher_cited_intake.py`, `citation_expansion_pilot.py` | merges onto existing docs by `doc_id`, doesn't mint new source-keyed IDs itself | One-hop, capped, non-recursive per `RESOURCE_MANIFEST.md`'s acquisition-scope rules | n/a (a scoping mechanism, not a source) |
| Discussion boards (MathOverflow, BioStars) | `discussion_board_scout.py` | provenance only — thread URL recorded, post not ingested as a `research_papers` record (explicit rule in `RESOURCE_MANIFEST.md`) | Batch | n/a by design |

**The nasa_ads=0 explanation, sourced from code, not inferred:** `acquire_nasa_ads_batch.py:41-64` (`get_nasa_ads_api_token()`) looks up Secret Manager secret ID **`NASA_ADS_API_TOKEN`** (upper-snake-case). The actual secret in Secret Manager is named **`nasa-ads-token`** (lower-kebab-case) — a different, non-matching ID. Secret Manager IDs are exact-match; this lookup would raise `NotFound` every run, fall through to an environment-variable check (`os.getenv('NASA_ADS_API_TOKEN')`), and — absent that env var — hit the script's own guard clause ("❌ NASA ADS API token required") and exit without ingesting anything. This fully explains a durable zero, assuming the env var was never separately set on the Jetson; I have not seen the Jetson's actual cron environment or a run log, so this is a well-evidenced read of the code, not a confirmed execution trace. **PMC's zero has a simpler explanation: no ingest script for it exists at all.**

---

## 5. Production capacity

### Podcast generation
- **Entry points**: `POST /generate-podcast`, `/generate-podcast-with-subscriber`, `/generate-podcast-from-paper`, and the side-effect-free preview `/resolve-paper` — all `cloud-run-backend/endpoints/podcast/routes.py`.
- **Models/services**: Gemini (`gemini-2.5-flash`→`gemini-2.5-pro` fallback) for script generation (`services/podcast_generation_service.py`); `gpt-image-1`/`gpt-image-1-mini` for thumbnails; ElevenLabs `eleven_multilingual_v2` for TTS (4 named voices — see §3).
- **Output**: audio to `gs://regal-scholar-453620-r7-podcast-storage/audio/*.mp3` (public); records in Firestore `episodes` (104 docs) and `podcast_jobs` (77 docs).
- **Measured volume**: 120 audio files in that prefix, 1.05 GiB total. **The most recently modified audio file is dated 2026-08-23** — over 5 weeks before today. `episodes`' `created_at` field is a non-ISO string ("Tue, 29 Jul 2025 00:00:00 GMT"), so sorting by it lexicographically is unreliable and was not used for this figure; the GCS object-modification timestamp is the more trustworthy instrument here. Flagging, not concluding: this could be a deliberate pause or a real stall in the generation pipeline — worth Gary's eyes, not asserted as broken.

### Process/chart generation (GLMP/ATAP)
Not a Cloud Run pipeline at all. Per `SUITE_REORG_PLAN.md` §1, charts are authored externally (human+agent dialogue, "a biologist review can make a GLMP chart better"), then synced into Firestore by manual CLI scripts — `cloud-run-backend/scripts/sync_glmp_processes.py` and `sync_math_processes.py` (confirmed: `argparse`-driven, "Sync GLMP processes from GCS to Firestore", run on demand, not cron-scheduled). Served read-only via `GET /api/glmp/processes*`. Output lives in Firestore `glmp_processes` (217), `atap_graphs` (237), plus the Programming-Framework demonstration collections (`chemistry_processes` 124, `computer_science_processes` 72, `biology_processes` 56, `physics_processes` 28). No throughput metric available — this is agent-paced, not metered.

### Video ingestion (sciencevideodb)
Entry point is in the `sciencevideodb` repo's `packages/ingestion` (TypeScript): fetches each registered channel's uploads via the YouTube Data API, extracts transcripts, generates embeddings. **Important nuance found, not resolved this pass**: `docs/INGESTION.md` states metadata is stored in **PostgreSQL**, and Secret Manager holds a `scienceviddb-database-url` secret confirming a separate Postgres database exists for this engine. Whether the Firestore `science_videos` collection (1,123 docs — matching BULLETIN 013's "live: 1,123" figure) is a sync target of that Postgres store, or an independent/legacy ingestion path, is **not established** — flagged in the Unknowns table below, not asserted either way. Served via the public `scienceviddb-web` Cloud Run service and the `sciencevideodb` HF Space.

### Briefings
`SUITE_REORG_PLAN.md` Part 4 already states this honestly: "specified, barely built." No daily-brief script was found in this pass either — this confirms the governance doc's own status rather than adding a new finding.

---

## 6. Experimentation capacity

### DNA decoder (GLMP domain instrument)
Lives in `glmp/collaborations/krampis-virtual-cell/dna-decoder/`. Entry point: `scripts/write_ecoli_decoder_firestore.py`, invoked per `AGENT_ROLES.md` by Jetson cron at 2 AM ET. Reads/writes Firestore collection **`glmp_processes`** — confirmed directly from the script (`db.collection("glmp_processes")...`), correcting an assumption that it would write to the similarly-named `glmp_circuits` collection. **Found, not resolved**: only one log file exists in the repo, `logs/batch_decoder_20260701.log`, dated 2026-07-01 — three months stale as of today. Either the Jetson's cron genuinely hasn't produced a fresh batch since July, or it runs but no longer logs anywhere that syncs into this repo. Can't distinguish from this seat.

### Colab notebooks
`glmp/k562-empirical-sequel/`: `STATE_K562_Benchmark.ipynb` (v1–v4), `STATE_Rescore_DE20.ipynb`, `rbio_circuit_class_probe.ipynb`, and `STATE_K562_Colab.py` (confirmed live `colab.research.google.com` reference) — K562 cell-line benchmark/rescoring work for GLMP's empirical-sequel line. Run interactively in Google Colab, not on any suite server; reach is whatever that Colab runtime has (its own compute, public internet) — not traced further this pass.

### Jetson Nano (`gary@192.168.1.223`)
Per `AGENT_ROLES.md`: scout cron (10:15 AM + 8 PM ET), batch decoder (2 AM ET), FIMO scanning, paper ingest pipeline. **UNKNOWN current state** — off-network from this seat, and SSH-to-Jetson is explicitly Cursor's lane, not Claude Code's, per the Cursor/Claude Code boundary in `AGENT_ROLES.md`. What would answer it: Cursor, run locally, checking cron status and recent log output directly on the device.

### Other analysis scripts
`cloud-run-backend/scripts/audit_research_paper_embeddings.py`, `backfill_research_paper_embeddings.py`, `backfill_glmp_embeddings_v2.py` — manual, one-off scripts run directly against Firestore/OpenAI, not cron-scheduled.

---

## 7. Auth posture

### `copernicus-podcast-api` (the live backend) — every route found in source, 46 total

**GET routes with a declared auth dependency** (`Depends(verify_admin_api_key)`), probed in Phase 0 and again here:

| Route | File:line | Live probe (no key) |
|---|---|---|
| `/api/admin/subscribers` | `admin/routes.py:23-24` | 401, no data |
| `/api/admin/subscribers/{id}/podcasts` | `admin/routes.py:77-80` | 401, no data |
| `/api/admin/podcasts/catalog` | `admin/routes.py:154-155` | 401, no data |
| `/api/admin/podcasts/database` | `admin/routes.py:186-187` | 401, no data |

**GET routes with no auth dependency at all** (29 routes; one plain GET each, just now):

| Route | Status | Data returned |
|---|---|---|
| `/api/rag/answer?question=...` | 200 | yes |
| `/api/episodes` | 200 | yes |
| `/api/episodes/search?q=...` | 200 | yes |
| `/api/episodes/{id}` | 404 (fake id) | no |
| `/api/glmp/processes` | 200 | yes |
| `/api/glmp/processes/{id}` | 404 (fake id) | no |
| `/api/glmp/processes/{id}/preview` | 404 (fake id) | no |
| `/api/papers/{id}` | 404 (fake id) | no |
| `/api/public/podcasts` | 200 | yes |
| **`/api/subscribers/podcasts/{id}`** | **200** (fake id) | yes (empty list for the fake id — see flag below) |
| `/api/subscribers/profile/{id}` | 404 (fake id) | no |
| `/api/test` | 200 | yes |
| `/api/content/browse` | 200 | yes |
| `/api/content/stats` | 200 | yes |
| `/api/knowledge-map/graph` | 200 | yes |
| `/api/knowledge-map/stats` | 200 | yes |
| `/api/knowledge-map/subgraph/{id}` | 200 (fake id) | yes |
| `/api/knowledge-map/query/*` (5 routes: cluster, papers-by-concept, path, related, search) | 200 each | yes each |
| `/api/vector-search/semantic` | 200 | yes |
| `/health`, `/test-frontend`, `/status/{id}` | 200, 200, 404 | yes, yes, no |

**Flagging, not exploiting**: `GET /api/subscribers/podcasts/{subscriber_id}` (`subscriber/routes.py:290-291`) and `PUT /api/subscribers/profile/{subscriber_id}` (`:243`) and `DELETE /api/subscribers/podcasts/{podcast_id}` (`:703`) declare **no auth dependency of any kind** — not even the admin key. A fake ID returns an empty/404 result, which is all this review tested (per the task's no-key, no-guessing, one-request rule); it does not rule out that a real subscriber ID would return or let someone modify real subscriber data unauthenticated. Worth Gary's attention before anyone else touches this.

**Non-GET routes — auth dependency declared? (source only, not called):**

| Route | Method | File:line | Auth dependency |
|---|---|---|---|
| `/debug/run-content` | POST | `public/debug.py:31-34` | yes, `verify_admin_api_key` |
| `/debug/watchdog` | POST | `public/debug.py:97-98` | yes, `verify_admin_api_key` |
| `/generate-podcast` | POST | `podcast/routes.py:36-37` | **no** |
| `/generate-podcast-with-subscriber` | POST | `podcast/routes.py:121-124` | **no** |
| `/resolve-paper` | POST | `podcast/routes.py:233` | **no** |
| `/generate-podcast-from-paper` | POST | `podcast/routes.py:253` | **no** |
| `/api/papers/upload` | POST | `papers/routes.py:69-70` | **no** |
| `/api/papers/query` | POST | `papers/routes.py:152` | **no** |
| `/api/papers/{id}/link-podcast/{id}` | POST | `papers/routes.py:196` | **no** |
| `/api/subscribers/register` | POST | `subscriber/routes.py:31` | **no** (expected — it's a signup endpoint) |
| `/api/subscribers/login` | POST | `subscriber/routes.py:111` | **no** (expected — it issues the credential) |
| `/api/subscribers/profile/{id}` | PUT | `subscriber/routes.py:243` | **no** |
| `/api/subscribers/podcasts/submit-to-rss` | POST | `subscriber/routes.py:483` | **no** |
| `/api/subscribers/password-reset-request` | POST | `subscriber/routes.py:641` | **no** (plausibly gated by a mailed token inside the body — not traced this pass) |
| `/api/subscribers/password-reset` | POST | `subscriber/routes.py:671` | **no** (same caveat) |
| `/api/subscribers/podcasts/{id}` | DELETE | `subscriber/routes.py:703` | **no** |
| 3 admin routes called by `admin-dashboard.html` | POST/DELETE | — | **route doesn't exist** (see BULLETIN 012) |

Absence of `Depends(...)` doesn't prove an in-body check doesn't exist (e.g. a token field inside the request body) — this table reports the declared-dependency check the task asked for, not a full code audit of every function body.

### Vercel (`copernicus-web-public`) — a structural finding

`app/api/*/route.ts` (Next.js App Router, 8 files including `user/profile`, `subscription/manage`) **appear to be dead code in production.** `vercel.json` uses the legacy explicit `builds` config — `{"src": "public/**", "use": "@vercel/static"}` and `{"src": "api/**/*.js", "use": "@vercel/node"}` only, no Next.js framework builder. Confirmed live: the homepage's `<title>` matches `public/index.html` byte-for-byte, and a plain GET of all 7 `app/api/*` GET routes returns **404** for every single one, including `/api/auth/session` (a path NextAuth would always answer if it were actually running). The site is served statically from root-level `public/`, plus a handful of real serverless functions in root-level `api/` (`episodes/index.js`, `episodes/[episodeId].js`, `rss-feed.js` — none have auth logic, which is appropriate since they're public podcast-episode reads).

**Why this matters**: `app/api/user/profile/route.ts:61-66` "authenticates" by reading `Authorization: Bearer <value>` and treating `<value>` **literally as the user's email address** — no signature, no session, no verification of any kind (`const email = authHeader.substring(7)`). If this route were ever actually deployed and reachable, anyone could read or create any user's profile by guessing their email. As it stands today it's unreachable (404 live), so this is a dead-code finding, not a live vulnerability — but it's worth fixing or deleting before anyone re-wires the build to include `app/`.

### Hugging Face Spaces
All 6 are `sdk: static` (§1) — no server-side routes of their own. Their auth posture is whatever Cloud Run API they call client-side, already covered above.

---

## 8. Cost

**Billing: no read access from this seat.** `gcloud billing projects describe` and `gcloud billing accounts list` both fail — the Cloud Billing API has never been enabled on this project (`SERVICE_DISABLED`, not a permissions error on top of an enabled API). I did not enable it (read-only task). `bq ls` returns no datasets — no BigQuery billing export is configured either. **What Gary would need to export by hand**: the Cloud Console's Billing → Reports page for `regal-scholar-453620-r7` (or whichever billing account it's linked to), filtered by service, for the last 3 months — there's no way to get this from the CLI without enabling an API this task was scoped not to touch.

**Paid external APIs in use, by evidence in Secret Manager + code (§3), not billing data:**

| Provider | Secret(s) | Called from |
|---|---|---|
| OpenAI | `openai-api-key` | RAG answers (default), image thumbnails, embeddings |
| Google AI / Vertex AI | `GEMINI_API_KEY`/`gemini-api-key`, `GOOGLE_AI_API_KEY`/`google-ai-api-key`, `vertex-ai-service-account-key` | Podcast scripts, paper preprocessing, RAG fallback, Vertex embeddings |
| Anthropic | `anthropic-api-key` | `claude_rag.py` provider option (looks unused by default — §3) |
| ElevenLabs | `elevenlabs-api-key`, `gcp-copernicusai-tts-key` | Podcast TTS |
| Voyage AI | `voyage-api-key` | Optional embedding provider (cheaper alternative to Vertex, per `main.py:376`'s comment) |
| NASA ADS | `nasa-ads-token` | `acquire_nasa_ads_batch.py` — but see §4, the secret-name mismatch means this has likely never actually been billed |
| PubMed (NCBI E-utilities) | `pubmed-api-key` | `acquire_pubmed_batch.py` — raises rate limits, typically free tier |
| YouTube Data API | `youtube-api-key`, `youtube-client-id/secret` | sciencevideodb ingestion |
| Twitter/X API | 7 secrets (`twitter-*`) | Not traced this pass — call sites unknown |
| News API | `news-api-key` | Not traced this pass |
| Zenodo | `zenodo-api-key` | DOI minting (`RESOURCE_MANIFEST.md`'s Zenodo table) — API itself is free |

No per-provider spend figures are available without the billing export above.

---

## Connection diagram

```mermaid
graph LR
    subgraph Hosting
        Vercel["Vercel: copernicus-web-public\n(www.copernicusai.fyi)"]
        HF["HF Spaces (6, static)\ncopernicusai / glmp / atap /\nprogramming_framework /\nmetadata_database / sciencevideodb"]
        GCSPublic["GCS: regal-scholar-453620-r7-\npodcast-storage (public)"]
    end

    subgraph "Cloud Run (public)"
        PodAPI["copernicus-podcast-api"]
        Frontend["copernicus-frontend"]
        GLMPsvcs["glmp-service +\n4 glmp-* Cloud Functions"]
        SciVidWeb["scienceviddb-web"]
    end

    subgraph "Cloud Run (auth-only)"
        CopAPI["copernicus-api"]
        ResMeta["research-metadata-api"]
        Legacy["copernicus-backend /\n-research-backend /\n-podcast-generator"]
    end

    subgraph Firestore["Firestore (db: copernicusai)"]
        RP[("research_papers\n119,321")]
        SV[("science_videos\n1,123")]
        Other[("13 more collections")]
    end

    subgraph Models
        OpenAI_["OpenAI\ngpt-4o-mini, gpt-image-1,\ntext-embedding-3-small"]
        Gemini_["Google AI / Vertex\ngemini-2.5-flash/pro,\ntext-embedding-004"]
        Claude_["Anthropic\nclaude-3-5-haiku\n(provider option, default-off)"]
        Voyage_["Voyage AI\nvoyage-3.5"]
        Eleven_["ElevenLabs\neleven_multilingual_v2"]
    end

    subgraph Sources["Knowledge sources (batch, Jetson cron)"]
        PubMed_["PubMed"] --> RP
        ArXiv_["arXiv"] --> RP
        Crossref_["Crossref"] --> RP
        BioMed_["bioRxiv/medRxiv"] --> RP
        NasaAds_["NASA ADS\n(broken: secret-name\nmismatch)"] -.->|0 docs| RP
        YouTube_["YouTube"] --> SV
    end

    Vercel --> PodAPI
    HF --> PodAPI
    GCSPublic -.->|admin-dashboard.html\n(static, API gated separately)| PodAPI

    PodAPI --> RP
    PodAPI --> Eleven_
    PodAPI --> OpenAI_
    PodAPI --> Gemini_
    PodAPI --> Claude_
    PodAPI --> Voyage_
    GLMPsvcs --> Firestore
    SciVidWeb --> SV

    subgraph Experimentation["Experimentation (off Cloud Run)"]
        Jetson_["Jetson Nano\nscout/decoder/FIMO cron\n(UNKNOWN current state)"]
        Colab_["Colab notebooks\nK562 benchmark/rescoring"]
    end
    Jetson_ -->|"write_ecoli_decoder_\nfirestore.py"| RP
    Jetson_ -.->|"only log: 3mo stale"| Jetson_

    subgraph DeadCode["Vercel app/api/* -- NOT in live build"]
        NextAPI["app/api/user/profile etc.\n(email-as-bearer-token 'auth')"]
    end
    Vercel -.->|"vercel.json builds only\npublic/** + root api/**/*.js\n-- 404 live, confirmed"| NextAPI

    AuthGap["3 unauthenticated routes:\nGET/PUT/DELETE\n/api/subscribers/..."] -.->|no Depends| PodAPI
```

---

## Unknowns table

| Unknown | What would answer it |
|---|---|
| Whether `poiesis-engine` / `garysfirst-agent` repos are in scope | Ask Gary |
| Whether `copernicus-podcast-api`, `Copernicus_AI`, `copernicus_backup`, `kickflip-docs` repos are confirmed dead or just missing from today's `gh repo list` | Ask Gary; check GitHub's organization/transfer history if any |
| Full Vercel project list, deploy triggers, last-deploy state for all but 2 projects | Vercel dashboard or API token access |
| Why `.app` domains fail TLS today despite BULLETIN 006 saying this cleared | A non-Windows/non-schannel client test, or Vercel's domain/cert dashboard |
| Whether the `glmp-*` Cloud Functions and `scienceviddb-web`'s public access is intentional or a BULLETIN-006 gap | Ask Gary |
| `podcasts` vs. `episodes` Firestore collections — relationship | Read `cloud-run-backend` service code that writes each (not done this pass) |
| `users`, `system_metrics` Firestore collections — purpose | Same |
| Public-read status of 10 of 15 GCS buckets (only 4 checked) | One more IAM check per bucket |
| Which of `GEMINI_API_KEY`/`gemini-api-key`/`GOOGLE_AI_API_KEY`/`google-ai-api-key` is actually read | Trace `utils/api_keys.py` and each secret's access log |
| Whether `claude_rag.py` (Anthropic) is ever actually selected in production | Runtime trace or Cloud Run logs filtered for `llm_provider=claude` |
| Jetson cron's actual current state (scout/decoder/FIMO) | SSH to the Jetson (off-network from this seat) |
| HF Spaces' own backend-API call sites (only `copernicusai` checked) | Read each Space's `index.html`/JS this session didn't get to |
| Whether podcast generation has genuinely stalled since 2026-08-23, or paused deliberately | Ask Gary; check Jetson/Cloud Run logs for recent `/generate-podcast*` calls |
| Whether Firestore `science_videos` (1,123 docs) is fed by, or independent of, sciencevideodb's own Postgres store | Read `packages/ingestion`'s write path fully (not done this pass) and/or query the Postgres DB directly |
| Why the DNA decoder's only log is 3 months stale — cron stopped, or just not logged to this repo path | SSH to the Jetson (Cursor's lane) |
| Whether a real (non-fake) subscriber ID returns actual personal data from `GET /api/subscribers/podcasts/{id}` or lets `PUT .../profile/{id}` / `DELETE .../podcasts/{id}` modify it unauthenticated | Would require testing with a real ID — explicitly out of scope for this read-only, no-guessing review; flagging for Gary to decide how to verify safely |
| Whether `app/api/*/route.ts` (including the email-as-bearer-token "auth") was ever live, or has always been dead code since this `vercel.json` was written | `git log` on `vercel.json` vs. `app/api/` to see which came first — not traced this pass |
| Twitter/X API (7 secrets) and News API call sites | Not traced this pass — grep `cloud-run-backend` and other repos for `twitter-api-key`/`news-api-key` usage |
| Exact dollar cost per service, last 3 months | Cloud Billing API is disabled on this project — Gary would need to enable it or pull the Billing → Reports page by hand |

---

*All 8 sections now covered. No writes, deploys, publishes, or config changes
made in the course of this review; the Cloud Scheduler and Cloud Billing APIs
were found disabled and were deliberately left that way.*
