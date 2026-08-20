# Handoff — 20 August 2026 (Knowledge Engine paper → podcast connector, Cursor)

**From:** Cursor (this session)
**To:** Claude Chat and Claude Code
**Repo:** `copernicus-web` (patch on top of `6430e09e5`; commit SHA after this file lands)
**Regenerate from a fresh fetch before acting.**

Share this file as-is. Continuous with
`papers/claude_code_handoff_2026-08-20_podcast_paper_connector.md` — CopernicusAI.fyi
podcast generation, not the E. coli decoder or the synthesis-paper work.

---

## What happened

Claude Code shipped Phase 1 (`dc53eb8bd`): a Firestore resolver plus
`POST /resolve-paper` and `POST /generate-podcast-from-paper`. Read-only live
tests against production Firestore passed. Gary asked Cursor to review before
Cloud Build.

The resolver and the “do not generate from a fuzzy query” gate were sound.
Three real bugs sat in the generate step *after* a paper was already chosen.
Claude Code looked back at the same code and confirmed all three. Gary approved
the four-part pre-deploy patch, Cloud Build, one real Phase 2 generation
(Stormo & Hartzell 1989), and this handoff file.

## Cursor review (confirmed)

1. **Empty abstract silently became a topic podcast.**
   `paper_content = paper.get("abstract") or ""` is falsy when the KE abstract
   is missing. The generator’s `if request.paper_content and request.paper_title`
   check then falls through to the generic topic-research path. Caller asked for
   a paper-grounded episode; they would have been billed for an open-topic one.

2. **`source_links` was the Firestore doc id** (e.g. `crossref_10.1073_pnas.86.4.1183`),
   not a URL. Episode metadata treats these as URLs. The doi.org → PubMed → arXiv
   order was already in `lib/knowledge-engine-links.ts` `paperExternalUrl()` and
   was used for identifier parsing, but not for the output side.

3. **Default category was `Computer Science`**, leftover from the old web-form
   `PodcastRequest`. A GLMP paper would be miscategorized unless the caller
   overrode it every time.

Accepted product limit, not a bug (same as Claude Code’s handoff): KE papers
store title + abstract, not full text. Even a clean generate is abstract-driven
until a later PDF/full-text path exists. Tell Gary/Lents that plainly.

## Pre-deploy patch (done, 26 unit tests)

- Empty/whitespace abstract → **400 before any job is created**.
- `source_links` is a real URL via the same `paperExternalUrl()` priority.
- `GeneratePodcastFromPaperRequest.category` is optional. When omitted, category
  comes from `discipline` (or `cited_project=glmp` → Biology). An explicit
  category on the request still wins.
- Unit tests in `cloud-run-backend/tests/unit/test_paper_resolver.py`, including
  the rule that a single `text_search` hit is never enough to generate.

Firestore / vector-search imports in `paper_resolver.py` are lazy so those tests
do not need a live client.

## Deploy (done)

Cloud Build `b98cbf3c-1be2-4e1f-a489-0834768c2e56` **SUCCESS** (5m49s).

| | |
|---|---|
| Service | `copernicus-podcast-api` |
| Revision | `copernicus-podcast-api-00254-krw` |
| Image | `gcr.io/regal-scholar-453620-r7/copernicus-podcast-api:b98cbf3c-1be2-4e1f-a489-0834768c2e56` |
| URL | `https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app` |
| Health | 200, `healthy` |

Logs: https://console.cloud.google.com/cloud-build/builds/b98cbf3c-1be2-4e1f-a489-0834768c2e56?project=204731194849

## Phase 2 (done — one real generation)

Paper: **Stormo & Hartzell 1989**, DOI `10.1073/pnas.86.4.1183`,
`cited_project=glmp`.

**Resolve** (`POST /resolve-paper`): `match_type=identifier`,
`paper_id=crossref_10.1073_pnas.86.4.1183`, title *Identifying protein-binding
sites from unaligned DNA fragments.*, abstract present (preview starts
“The ability to determine important features within DNA sequences…”).

**Generate** (`POST /generate-podcast-from-paper`, DOI query, ~279s, HTTP 200):

| | |
|---|---|
| `job_id` | `8cb04ba7-282d-4bb6-910c-a76f8aba8dbe` |
| status | `completed` |
| `source_paper_id` | `crossref_10.1073_pnas.86.4.1183` |
| category on the job | **Biology** (canonical `ever-bio-250045`) |
| `source_links` | `https://doi.org/10.1073/pnas.86.4.1183` |
| `has_research_paper` | `true` (paper-analysis path, not topic-research) |
| Episode title | Unraveling Life's Code: The Paradigm Shift in Identifying Protein-DNA Binding Sites from Unaligned Fragments |
| Audio | https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/audio/ever-bio-250045.mp3 |
| Description | https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/descriptions/ever-bio-250045.md |
| Transcript | https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/transcripts/ever-bio-250045-transcript.md |
| Thumbnail | fallback (`ever-bio-250045-fallback-thumb.jpg`) |

The connector patch did what it was supposed to: identifier resolve, non-empty
abstract, Biology not Computer Science, DOI URL not a Firestore id, paper
pipeline not the open-topic path.

**What the episode actually did with the paper (honest):** it names Stormo &
Hartzell and the real title, then immediately treats the 1989 method as a
launch pad for later work (Cardon & Stormo EM, then several arXiv ML / pKa /
kinetics papers). Venue is spoken as “published in *pubmed*” rather than PNAS.
The references block still has placeholder `DOI: 10.xxxx/xxxx` and dates the
1989 paper “(Recent)”. Hashtags include CRISPR / CancerResearch / GeneEditing,
which the 1989 abstract does not earn. That is the existing
`gemini_research_enhanced` paper-analysis pipeline running on an abstract, not
a connector bug.

The job was **auto-promoted** to `episodes` (`promoted_to_episodes: true`). This
was a live episode, not a dry run. Gary should know it is in the catalog as
`ever-bio-250045` before anyone points Lents at it.

## Phase 3 (UI)

Not started. Gated on whether Gary wants a UI in front of this quality bar, or
wants the paper-analysis script/citations cleaned up first.
`components/PodcastGenerator.tsx` is still the wrong shape.

## Known, accepted limitation (not a bug)

Free-text/description search can still miss a real GLMP/ATAP paper outside the
candidate window. Identifier (a real link) is the reliable path for Gary/Lents.
A flat `cited_project` mirror field at ingest remains deferred.
Abstract-only content remains the KE data model; full-text/PDF is a later path.

---

## Key paths

- `cloud-run-backend/services/paper_resolver.py` — resolver + URL/category/abstract helpers
- `cloud-run-backend/models/podcast.py` — `category` now optional on `GeneratePodcastFromPaperRequest`
- `cloud-run-backend/endpoints/podcast/routes.py` — empty-abstract 400; URL `source_links`; inferred category
- `cloud-run-backend/tests/unit/test_paper_resolver.py` — identifier parsing + generation-gate tests
- `cloud-run-backend/services/podcast_generation_service.py` — untouched paper-analysis pipeline
- `lib/knowledge-engine-links.ts` — `paperExternalUrl()` priority, mirrored in Python
