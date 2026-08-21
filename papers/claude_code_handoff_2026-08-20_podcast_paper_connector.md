# Handoff — 20 August 2026 (Knowledge Engine paper → podcast connector, Phase 1)

**From:** Claude Code (this session)
**To:** Cursor and Claude Chat
**Repo:** `copernicus-web` @ `dc53eb8bd` (`origin/main`)
**Regenerate from a fresh fetch before acting.**

Share this file as-is. New, unrelated topic from the day's GLMP-paper threads — this is the
CopernicusAI.fyi podcast generation workflow, not the E. coli decoder or the synthesis-paper work.

**Follow-up, same day: Cursor reviewed Phase 1, found three real pre-deploy bugs, Gary approved the
fix.** Cursor read the resolver, models, routes, generation service, ingest shape, and
`lib/knowledge-engine-links.ts`, and would not have Cloud Built this as-is:

1. **Empty-abstract silent fallback.** `paper_content = paper.get("abstract") or ""` — an empty
   abstract is falsy, so the generation service's paper-analysis branch never triggers and the job
   silently falls through to the generic topic-research path instead. Billed the same either way;
   just not the episode the caller asked for.
2. **`source_links` held a Firestore doc id, not a URL.** Episode metadata expects a real link;
   `crossref_10.1073_pnas.86.4.1183` isn't one.
3. **Default `category` was still `"Computer Science"`** — a leftover from the old generic web-form
   model, unfixed in the new paper-driven request. A GLMP paper would get miscategorized unless the
   caller remembered to override it.

Checked all three directly against the code I'd written — all confirmed real, not nitpicks. Gary
approved Cursor's proposed four-part patch (reject empty abstract; fix `source_links` via the same
`paperExternalUrl()` priority order — doi.org, PubMed, arXiv; derive category from
discipline/`cited_project` instead of the CS default; add unit tests for identifier parsing and the
unambiguous-generation gate) and told Cursor to go ahead.

**Status as of this note:** Cursor's patch is applied in the shared local `copernicus-web` checkout
— new helpers `paper_abstract_text()`, `paper_external_url()`, `podcast_category_for_paper()`,
`is_unambiguous_generation_match()` in `paper_resolver.py`, `category` now `Optional[str] = None`
("inferred from the paper when omitted") in the request model — **but not yet committed or
deployed**. Sequencing after that, per Cursor's plan: Cloud Build the deploy, then one real Phase 2
test (Stormo & Hartzell 1989 by DOI, `cited_project=glmp` — already confirmed to resolve cleanly),
then Phase 3 UI only once that episode looks right. Not touched or committed by Claude Code — this
is Cursor's in-progress work in the shared checkout, left alone per the usual convention.

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

## Follow-up, same day: Gary reviewed the live episode, wants a pipeline cleanup pass before Phase 3

Gary got the admin dashboard API key (pre-existing infrastructure, `admin-api-key` in Secret
Manager — unrelated to today's deploy, just needed re-entering since it lives in browser
localStorage and his had been cleared) and looked at `ever-bio-250045` directly.

**Decision: leave `ever-bio-250045` live, do not unpublish.** Confirmed: it's a working episode,
true to the topic, not the generic-topic-research fallback. Good sign for the connector itself.

**But two more concrete quality gaps found on top of Cursor's citation/venue findings**, both in the
same pipeline, worth fixing together rather than as separate passes:

3. **Thumbnail fell back to the generic placeholder** (`ever-bio-250045-fallback-thumb.jpg`,
   already noted in Cursor's handoff) rather than generating a real one. Worth checking whether
   `generate_and_upload_thumbnail`/`generate_fallback_thumbnail` in
   `podcast_generation_service.py` is failing silently on the paper-driven path specifically, or
   whether it's a more general issue that just happened to surface here.
4. **The description page renders badly formatted.** Separate issue from thumbnail generation, same
   general area of the pipeline (`upload_description_to_gcs`) — worth checking what the actual
   markdown/HTML output looks like versus what the renderer expects.

**Gary's explicit sequencing, confirmed:** clean up the paper-analysis pipeline first — citation
accuracy, venue attribution (Cursor's items: "published in *pubmed*" instead of the real venue,
placeholder `DOI: 10.xxxx/xxxx`, mis-dated "(Recent)", unrelated hashtags), plus these two — **then**
move on to Phase 3 (the UI). Not before. This is squarely pipeline-internals work
(`podcast_generation_service.py`, 2912 lines, the core generation service) — Cursor's lane, not a
single-file edit.

## Known, accepted limitation (not a bug)

The free-text/description path can still miss a real GLMP/ATAP paper if it doesn't rank within the
search's candidate window — confirmed live, not hypothetical. The identifier path (an actual link)
has no such limitation and is the one to recommend to Gary/Lents as the reliable way to use this.
A proper fix (a flat `cited_project` mirror field at ingest time, matching the `question_scope_ids`
pattern) was considered and deliberately deferred — that's an ingest-pipeline schema change, closer
to Cursor's lane than a v1 connector.

---

## Closing status, evening of 2026-08-20: all three phases shipped, Gary stopped for the night

Cursor's evening handoff (`papers/cursor_handoff_2026-08-20_podcast_paper_connector.md`,
`copernicus-web@5b3145512`) closes out the day. Full pipeline-cleanup scope from the section above
— citation accuracy, venue attribution, thumbnails, description formatting — is done and live, not
just the connector. Confirmed by episode `ever-bio-260008`: real PNAS citation/year (not "published
in pubmed"), a real generated thumbnail (not the fallback), clean category-matched hashtags (not
title-fragment or CRISPR/cancer junk). Root causes, briefly: venue was being read from a prompt path
(`podcast_research_integrator`/`research_pipeline`) that never saw `PodcastRequest.format_citation`;
hashtags were minted from arbitrary title words; thumbnails failed because `dall-e-3` is retired on
this OpenAI account and an unrelated `style` param 400'd before that was found — now on `gpt-image-1`.
Phase 3 UI also shipped: a "Generate from a paper" block on `subscriber-dashboard.html`, GLMP-default
corpus, DOI/URL path recommended in the copy itself, episodes private until RSS.

**Gary reviewed the new episodes and approved shipping** ("these look good"), then stopped for the
night. Two decisions Cursor explicitly left open, not made themselves — still open, not decided
here either:
- Publish `ever-bio-260008` (or `260005`) as the live Stormo episode, or restore `ever-bio-250045`
  (still up, still has the old flaws — pubmed venue, fallback thumb, junk hashtags)?
- Keep `ever-bio-260003`–`260007` as unpublished test episodes (Cursor's recommendation), or clean
  some up?

Nothing else outstanding on this thread as of tonight. Do not generate more Stormo episodes, publish/
unpublish anything, or Cloud Build without a new backend change — per Cursor's own explicit stop
note, still standing until Gary picks up the two decisions above.

---

## Key paths

- `cloud-run-backend/services/paper_resolver.py` — the resolver, new
- `cloud-run-backend/models/podcast.py` — `ResolvePaperRequest`, `GeneratePodcastFromPaperRequest`
- `cloud-run-backend/endpoints/podcast/routes.py` — `POST /resolve-paper`, `POST /generate-podcast-from-paper`
- `cloud-run-backend/services/podcast_generation_service.py` — untouched; the existing paper-analysis
  pipeline this connector feeds into
- `components/PodcastGenerator.tsx` — unused frontend component, not the shape needed for Phase 3
- `lib/knowledge-engine-links.ts` — confirms papers have no internal KE detail-page URL
