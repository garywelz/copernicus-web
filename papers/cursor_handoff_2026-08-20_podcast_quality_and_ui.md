# Handoff — 20 August 2026 evening (podcast quality + Phase 3 UI, Cursor)

**From:** Cursor (this session)
**To:** Claude Chat and Claude Code
**Repo:** `copernicus-web` @ `5b3145512` (`origin/main`)
**Regenerate from a fresh fetch before acting.**

Share this file as-is. Continuous with
`papers/cursor_handoff_2026-08-20_podcast_paper_connector.md` and
`papers/claude_code_handoff_2026-08-20_podcast_paper_connector.md`.
This is CopernicusAI.fyi podcast generation, not the E. coli decoder or the
synthesis-paper work. Gary stopped here for the night.

---

## Status (stop here)

Phases 1–3 of the Knowledge Engine paper → podcast path are **done and on
`main`**. Gary reviewed the new Stormo episodes (“these look good”), approved
ungating the UI, then said this is enough for today.

Do **not** generate more Stormo episodes. Do **not** publish or unpublish
anything unless Gary asks. Do **not** Cloud Build unless there is a new backend
change — the live API already has the quality fixes.

---

## What shipped today (all pushed to `origin/main`)

| Commit | What |
|---|---|
| `fd180991f` | Real journal/year instead of “published in pubmed”; no title-fragment hashtags; DALL-E attempts before geometric fallback |
| `1ef60aca1` | Drop OpenAI `style` param (`Unknown parameter: 'style'` → HTTP 400) |
| `116709a08` | Thumbnails: `dall-e-3` is gone on this account; use `gpt-image-1` / `gpt-image-1-mini`, quality `medium`/`low`, handle `b64_json` |
| `5b3145512` | Phase 3 UI: paper lookup on the subscriber dashboard |

**Live API:** `copernicus-podcast-api-00259-dr2` (100% traffic), no-cache Cloud
Build after `116709a08`. URL
`https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app`.

**There is no GitHub Cloud Build trigger.** Deploy is `gcloud builds submit`
from `cloud-run-backend/` with `--no-cache`. First cached submit of the day
shipped stale code as revision `00255`. Always `--no-cache` until proven
otherwise. A reusable config lived at
`C:\Users\garyw\AppData\Local\Temp\cloudbuild-nocache.yaml`.

**Frontend:** `public/subscriber-dashboard.html` pushed to GitHub (Vercel /
copernicusai.fyi) and copied to
`gs://regal-scholar-453620-r7-podcast-storage/subscriber-dashboard.html`.

---

## The quality bugs (and what actually fixed them)

Gary reviewed `ever-bio-250045` and wanted pipeline cleanup before UI:

1. **Venue.** Live path is `generate_content_from_research_context` →
   `podcast_research_integrator.build_2_speaker_research_prompt`, which labeled
   sources `Source: pubmed` / `Published: Recent`. `format_citation` on
   `PodcastRequest` never reached that prompt. Fixed by parsing journal/year in
   `research_pipeline.py`, passing the KE paper as the first `ResearchSource`,
   rewriting venues, and never saying “published in PubMed”.
2. **Hashtags.** `generate_relevant_hashtags` minted tags from arbitrary title
   words (`#Identifying`) and unrelated CRISPR/cancer. Now: category + matched
   scientific terms only (`#Biology #Biotech #Proteins` plus the suite tags).
3. **Thumbnail.** HD DALL-E + long “living tissue” prompt → fail →
   `*-fallback-thumb.jpg`. Then `style: vivid` 400. Then
   `The model 'dall-e-3' does not exist.` Now `gpt-image-1` with a short
   abstract prompt; success uploads `*-thumb.jpg`.

Key files: `cloud-run-backend/content_fixes.py`,
`podcast_research_integrator.py`, `research_pipeline.py`,
`services/podcast_generation_service.py`,
`tests/unit/test_content_fixes.py`.

---

## Stormo episodes (DOI `10.1073/pnas.86.4.1183`)

Paper: Stormo & Hartzell 1989, `paper_id=crossref_10.1073_pnas.86.4.1183`,
`cited_project=glmp`, collection `research_papers`. Generate via
`POST /generate-podcast-from-paper`. Admin subscriber
`gwelz@gc.cuny.edu` /
`7e16babf99eb30e20c32b7dca9e9610da7644fe00e03e999382e4c25b6c2690b`.

| Canonical | Notes |
|---|---|
| `ever-bio-250045` | First Phase 2 live test. Gary said **leave published**. **Currently private / `submitted_to_rss=False`, no `subscriber_id`** — RSS restore via the subscriber API will 400. Cursor did not republish it. Quality: pubmed venue, fallback thumb, junk hashtags. |
| `ever-bio-250046` | Stale `00255`. Private test. Leave unpublished. |
| `ever-bio-260001` | Private test. Leave unpublished. |
| `ever-bio-260002` | Private test after `00256`. Naming + admin attribution worked; venue/thumb/hashtags still wrong. Leave unpublished. |
| `ever-bio-260003` | Venue + hashtags good; **fallback thumb** (`style` 400). Private. |
| `ever-bio-260004` | Venue + hashtags good; **fallback thumb** (`dall-e-3` missing). Private. |
| `ever-bio-260005`–`260007` | Original thumbs after `00259`; extras from interrupted/retried generates. All private. |
| `ever-bio-260008` | **Check episode that passed.** Script: *Proceedings of the National Academy of Sciences*, 1989. Thumb: `ever-bio-260008-thumb.jpg` (~1.2 MB, not fallback). Hashtags: `#CopernicusAI #SciencePodcast #ResearchInsights #Biology #Biotech #Proteins`. DOI in description. Private / not RSS. |

Next Biology evergreen would be `ever-bio-260009`. Naming:
`ever-{bio\|chem\|compsci\|phys\|math}-{YY}{NNNN}` with YY = creation year
and NNNN per-category **that year only**. Ignore `25xxxx` when allocating
2026. News stays `news-{cat}-{YYYYMMDD}-{serial}`. No rename/backfill of
`25xxxx`.

Gary liked the new episodes. Open product questions (do not decide):

- Publish `260008` (or `260005`) as the live Stormo, vs restore `250045`?
- Keep `260003`–`260007` as unpublished tests (recommended).

---

## Phase 3 UI (done)

Not a feature flag — it had not been built. `components/PodcastGenerator.tsx`
is still unused and the wrong shape (open topic, not a confirmed paper). Left
alone.

**What shipped:** on
https://www.copernicusai.fyi/subscriber-dashboard.html
(sign in), a **Generate from a paper** block above the old topic form.

- `POST /resolve-paper` then user confirms a candidate
- `POST /generate-podcast-from-paper` with `paper_id` + `subscriber_id`
- Default corpus **GLMP**; ATAP / all papers available
- Copy states: DOI/URL is the reliable path; free-text can miss; episode is
  from the stored **abstract**, not a PDF; stays **private until RSS**
- Category inferred by the backend (do not default Computer Science)

Hard-refresh if the old form is still cached.

---

## Deploy notes (Windows / Cursor lane)

- Cloud Run timeout 900s; generation ~4–8 minutes.
- Verify a new revision actually has the code before generating: job
  `request` should include `paper_journal` / `paper_year`; API response should
  include `subscriber_id`. Missing those = stale image again.
- PowerShell heredocs break JSON posts; use `curl.exe` or a Python
  `urllib` script.
- `gcloud builds submit --async` then wait; logs are `CLOUD_LOGGING_ONLY`.

---

## Known limits (not bugs)

- KE papers are title + abstract, not full text.
- Free-text/`text_search` is never enough to generate; identifier (a real
  link) is the path to recommend to Gary/Lents.
- Description can list the source paper twice (KE citation + research-source
  line). Minor; not cleaned tonight.
- `dall-e-3` is retired on this OpenAI account. Do not switch back.

---

## Out of scope / do not touch

- `shadow` (Shadow of Lillya)
- Unrelated untracked local files (nsf resumes, reorg markdown,
  acquire_papers jsonl, `tsconfig.tsbuildinfo`, etc.)
- E. coli decoder / synthesis-paper threads

---

## Key paths

- `cloud-run-backend/content_fixes.py` — venue rewrite, hashtags, image attempts
- `cloud-run-backend/services/podcast_generation_service.py` — live generate + thumbs
- `cloud-run-backend/podcast_research_integrator.py` — script prompt sources
- `cloud-run-backend/research_pipeline.py` — PubMed XML journal/year/DOI
- `cloud-run-backend/endpoints/podcast/routes.py` — `/resolve-paper`, `/generate-podcast-from-paper`
- `public/subscriber-dashboard.html` — Phase 3 UI
- `components/PodcastGenerator.tsx` — do not repurpose
