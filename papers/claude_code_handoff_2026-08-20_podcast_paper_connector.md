# Handoff — 20 August 2026 (Knowledge Engine paper → podcast connector, Phase 1)

**From:** Claude Code (this session)
**To:** Cursor and Claude Chat
**Repo:** `copernicus-web` @ `dc53eb8bd` (`origin/main`)
**Regenerate from a fresh fetch before acting.**

Share this file as-is. New, unrelated topic from the day's GLMP-paper threads — this is the
CopernicusAI.fyi podcast generation workflow, not the E. coli decoder or the synthesis-paper work.

---

## What happened

Gary wants researchers (himself and Prof. Lents) to generate podcast episodes sourced from
specific papers already in the GLMP/ATAP Knowledge Engine collections, instead of only the
existing open PubMed/arXiv topic-research path. Asked whether the current podcast generator
supports this.

**Found the backend already mostly supported it.** `models/podcast.py`'s `PodcastRequest` already
had `paper_content`/`paper_title`/`paper_abstract`/`paper_doi` fields, and
`services/podcast_generation_service.py` already branches into a dedicated paper-analysis pipeline
when they're populated, skipping the generic topic-research path entirely. What was missing was the
connector — resolving "a link, title, or description" against the GLMP/ATAP Firestore corpus and
populating those fields. (Also found `components/PodcastGenerator.tsx`, the one existing frontend
piece nominally for podcast creation, is unused — nothing imports it, and its fields don't even
match the paper-driven backend model. Not touched; a real UI for this still needs building, Phase 3
below.)

## What's built and committed (`copernicus-web@dc53eb8bd`)

**New file `cloud-run-backend/services/paper_resolver.py`** — resolves a query through three paths,
in order:
1. **DOI/PMID/arXiv identifier** (link or bare id) — exact Firestore field lookup. Confirmed this is
   what a paper's Knowledge Engine title link already resolves to — checked
   `lib/knowledge-engine-links.ts` directly: papers have no internal KE detail page, unlike processes
   or podcasts; the title link goes straight to `doi.org`/`pubmed`/`arxiv.org`.
2. **Exact title match** — added after a live test found that searching for a real GLMP paper using
   its own verbatim title still failed to surface it via semantic search alone (see below). Cheap,
   single equality query, not a scan.
3. **Free-text semantic search** — fallback, filtered client-side on `citations[].cited_project`
   (GLMP/ATAP tagging lives inside a `citations[]` array of citation events, not a flat field, so it
   can't be a Firestore `.where()` filter directly — same shape of problem `question_scope_ids` was
   built to solve for question-level scoping; documented in the module, not silently worked around).

**New endpoints in `endpoints/podcast/routes.py`:**
- `POST /resolve-paper` — preview lookup, no side effects.
- `POST /generate-podcast-from-paper` — requires an explicit `paper_id` (from a prior resolve call)
  or a query that resolves unambiguously (identifier or single exact-title match). A fuzzy free-text
  query is rejected here on purpose — this never silently generates a real, cost-incurring podcast
  episode about a paper the caller didn't confirm.

**Everything was live-tested read-only against production Firestore**, not just written and
assumed correct:
- Identifier path: found Stormo & Hartzell 1989 (one of Lents' 10 CRP-lac papers) by DOI; correctly
  reported `identifier_wrong_project` when scoped to `atap` instead of `glmp`; correctly reported
  `identifier_not_found` for a nonexistent DOI.
- Free-text path, first attempt: searched "DNase footprinting protein-DNA binding sites" (genuinely
  on-topic for Galas & Schmitz 1978, another of Lents' 10) scoped to GLMP — **zero candidates**. The
  paper exists and is correctly tagged; it just didn't rank in the top 60 broad-similarity results,
  because the corpus has many legitimately-relevant general molecular-biology method papers on the
  same topic that aren't GLMP-specific.
- Followed up with the paper's own **exact, verbatim title** as the query — **still didn't surface
  it**, semantically. That's what justified building the exact-title fallback rather than accepting
  the limitation as unavoidable. With the fallback added: same exact-title query now correctly
  resolves the right paper in one candidate.

## Not done

- **Not deployed.** This is Cloud Build/Cursor's step whenever Gary wants to move on it — should get
  a code review first since it's new backend surface, not just a content/copy change.
- **Phase 2 (real end-to-end generation test)** — everything tested so far is read-only against
  Firestore; `/generate-podcast-from-paper` itself hasn't actually been invoked, since that creates a
  real job and spends real generation API credits. Gary chose to stop here for today rather than run
  that test.
- **Phase 3 (a real UI for Gary/Lents)** — not started. `PodcastGenerator.tsx` is the wrong shape to
  repurpose; something new and small, gated on Phase 2 looking good first.

## Known, accepted limitation (not a bug)

The free-text/description path can still miss a real GLMP/ATAP paper if it doesn't rank within the
search's candidate window — confirmed live, not hypothetical. The identifier path (an actual link)
has no such limitation and is the one to recommend to Gary/Lents as the reliable way to use this.
A proper fix (a flat `cited_project` mirror field at ingest time, matching the `question_scope_ids`
pattern) was considered and deliberately deferred — that's an ingest-pipeline schema change, closer
to Cursor's lane than a v1 connector.

---

## Key paths

- `cloud-run-backend/services/paper_resolver.py` — the resolver, new
- `cloud-run-backend/models/podcast.py` — `ResolvePaperRequest`, `GeneratePodcastFromPaperRequest`
- `cloud-run-backend/endpoints/podcast/routes.py` — `POST /resolve-paper`, `POST /generate-podcast-from-paper`
- `cloud-run-backend/services/podcast_generation_service.py` — untouched; the existing paper-analysis
  pipeline this connector feeds into
- `components/PodcastGenerator.tsx` — unused frontend component, not the shape needed for Phase 3
- `lib/knowledge-engine-links.ts` — confirms papers have no internal KE detail-page URL
