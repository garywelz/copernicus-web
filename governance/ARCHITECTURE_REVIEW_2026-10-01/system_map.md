# CopernicusAI Suite — System Map (Architecture Review Phase 1)

*Read-only inventory. Status date 2026-10-01. Covers sections 1–4 only; sections
5–8 (production capacity, experimentation capacity, full auth posture, cost)
are a follow-up per the task's own stop-and-report instruction. Everything
below is either a live, one-shot GET-only check or a source-code citation
(file:line); no number here is inferred. Path note: the task specified
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

## Connection diagram (sections 1–4 only)

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
```

---

## Unknowns table (sections 1–4 only)

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

---

*Sections 5–8 (production capacity, experimentation capacity, full auth-posture
sweep, cost) not yet started — stopping here per the task's own instruction to
check in before continuing if the work runs long.*
