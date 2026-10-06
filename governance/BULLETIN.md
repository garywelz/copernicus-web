# Suite Bulletin

*Canonical home: `copernicus-web/governance/BULLETIN.md`. Append-only notice board for the
humans and AI agents of the CopernicusAI suite. Every agent session reads the newest
entries at start (see `PROJECT_HEADERS.md`).*

**What goes here:** changes that affect how someone else works — lane changes, new rules,
new agent surfaces, retired documents, and **what is waiting on whom**.
**What doesn't:** status feeds, run logs, or restated content. Each entry *links* to the
commit or PR that is the record; it announces, it does not duplicate.

**How to add an entry:** propose it in the same PR as the change it announces (agents),
or ask an agent to draft it (humans). Newest first. Never edit a past entry's substance;
correct it with a new entry that references it. Humans are notified by one Slack post
linking to the entry — no automated posting.

Entry format:

    ## NNN — YYYY-MM-DD — title
    - From: who proposed it
    - Record: commit / PR links
    - Affects: which agents or people
    - Summary: two or three sentences
    - Waiting on: who must do what (or "nobody")

---

## 019 — 2026-10-06 — Gap 3 (verification loop) scope split between Core and Methods & Tools

- **From:** Claude Chat (architecture review), decided by Gary 2026-10-05
- **Record:** this entry; no other repo change
- **Affects:** Core, and the Methods & Tools project; anyone building verification for the engines (GLMP, ATAP, TDAP)
- **Summary:**
  - **Core builds verification layers 1 and 2.**
    - **Layer 1, faithfulness:** whether generated text (podcast scripts, RAG answers) says what its cited sources say, measured against the NSF proposal targets: grounding of at least 90% and citation integrity of at least 95%.
    - **Layer 2, cross-checking by independent models:** using the multi-model checking that exists but is switched off.
  - **Layer 3, domain verification, is method development and belongs to Methods & Tools.**
    - Lean formalization for ATAP and other mathematics work.
    - Evo-class and virtual cell models (run on Colab) as computational evidence for GLMP and other biology work.
    - **Lean results count as verification; model predictions count as evidence, not proof.**
  - **Core will prepare to receive layer 3 results:** a place to store each verification result, linked to the paper, claim or process document it concerns, and a way to show it in the engines. A shared result-record format should be agreed before either side builds.
- **Waiting on:**
  - **Gary:** the gap 3 interview, 2026-10-06.
  - **Core:** a result-record proposal, after the interview.
  - **Methods & Tools:** scope a Lean pilot on ATAP material, and an Evo experiment protocol for GLMP.

## 018 — 2026-10-04 — glmp-service closed to the public; stale revision tags removed; entry 009 corrected

- **From:** Claude Code (Core lane), approved by Gary
- **Record:** changes made in Google Cloud, not in a repo; reversals below. Filed privately until the fix was live (rule 17); published now that it is.
- **Affects:** the GLMP lane, and anyone who deploys `glmp-service` or `copernicus-podcast-api`
- **Summary:**
  - **What was exposed.** The Cloud Run service `glmp-service` accepted unauthenticated calls on every route, and its code has no authentication. One route, `GET /api/secrets/list`, returns the names of every secret in the project's Secret Manager: names only, no values (from the source). Several POST routes call paid providers with keys held server-side.
  - **What the logs show.** The 30-day request log (2026-09-04 to 2026-10-04) holds 10 requests and no POSTs. Nine were probes of POST-only routes (`405`). On 2026-09-21 one `GET /api/secrets/list` returned the list of secret names to a caller we could not identify, and nothing indicates it was one of ours. Older logs were not available.
  - **Fix.** Public access was removed on 2026-10-04 and anonymous requests now get `403` (verified 2026-10-05 00:43 UTC; a first check six seconds after the change still got `200`, because IAM changes take a short time to take effect). No caller in any repo, Hugging Face Space, public page or other service needs it public. The previous policy and configuration are saved in the private internal bucket. To reverse: `gcloud run services add-iam-policy-binding glmp-service --region=us-central1 --member=allUsers --role=roles/run.invoker`.
  - **Revision tags removed** from `copernicus-podcast-api`: `fixes0930`, `test` and `lockdown`. A tag gives a revision its own URL with the service's public access, so revisions older than the lockdown in entry 014 were reachable by URL. Rollback goes by revision name and is unaffected; `step2` (`-00268-muc`) and `gap1-engine` stay. To reverse: `gcloud run services update-traffic copernicus-podcast-api --region us-central1 --update-tags=fixes0930=copernicus-podcast-api-00264-sug,test=copernicus-podcast-api-00097-xal,lockdown=copernicus-podcast-api-00266-nav`.
  - **Correction to entry 009.** It named "revision -00262-kfx and the fixes0930 tag" as the rollback path. The tag was on `-00264-sug`; `-00262-kfx` never carried one. The tag is gone, and rollback is by revision name.
  - **A redeploy would have undone the first fix, and cannot now.** The glmp repo's build file and seven documents beside it passed `--allow-unauthenticated`. [glmp#23](https://github.com/garywelz/glmp/pull/23) (commit ae1de18) switched them to `--no-allow-unauthenticated` and added a [RETIRED.md](https://github.com/garywelz/glmp/blob/main/glmp-cloud-service/RETIRED.md) note beside the service's code. No Cloud Build triggers exist in the project, so nothing redeploys the service automatically.
- **Waiting on:**
  - **Gary:** check OpenAI, OpenRouter and other provider usage since 2025-10 for unexplained spend (the logs cover only 30 days); decide whether to delete `glmp-service` (nothing calls it, and glmp#23 marked it retired).
  - **GLMP lane:** nothing; glmp#23 is merged.
  - **Key review:** the Jetson's credential was identified and is not the disabled key.
  - **Collaborators:** nobody.

## 017 — 2026-10-04 — Engine scoping live: GLMP, ATAP and TDAP toggles now scope Browse, Search and Ask Questions

- **From:** Claude Code (Core lane), approved by Gary
- **Record:** `copernicus-web` PR [#32](https://github.com/garywelz/copernicus-web/pull/32) (engine registry + `engine` param on `/api/content/browse`), PR [#33](https://github.com/garywelz/copernicus-web/pull/33) (`engine` param on `/api/rag/answer` and `/api/vector-search/semantic`), and PR [#34](https://github.com/garywelz/copernicus-web/pull/34) (frontend wiring) — all merged
- **Affects:** anyone using the Knowledge Engine's GLMP/ATAP/TDAP project toggle, or relying on its retrieval scope
- **Summary:**
  - Entry 012 flagged the toggle as chrome-only — framing copy and placeholders, with no effect on what Search/Ask Questions actually retrieved. That gap is closed: selecting a project now sends `engine=<glmp|atap|tdap>` on Browse, Search, and Ask Questions, strictly scoping paper retrieval to that engine's tagged `question_scope_ids` (`array_contains_any`). "All projects" still sends no `engine` param — fully unscoped, unchanged.
  - A new Firestore composite index (`research_papers`: `question_scope_ids` array-contains + `embedding` vector) lets scoped search use native `find_nearest()` with an `array_contains_any` pre-filter, in place of the old in-memory cosine rerank. Measured (warm-connection medians): TDAP-scoped 0.222s, GLMP-scoped 0.892s, versus 3.662s unscoped — scoped search is faster, not slower.
  - Live backend revision: `copernicus-podcast-api-00270-puh` (rollback kept: `copernicus-podcast-api-00268-muc`, tag `step2`).
  - Live frontend revision: `copernicus-frontend-00054-rud` (rollback kept: `copernicus-frontend-00052-zif`, tag `lockdown`).
  - The Knowledge Map stays unscoped this release (deliberate, not an oversight) — it shows a visible note when a project is selected: "Knowledge Map shows all projects -- the \<Project\> scope applied on Browse, Search, and Ask Questions doesn't narrow this map yet."
  - Drift check: `cloud-run-backend/scripts/check_engine_registry_drift.py` compares the registry's claimed tags against live `question_scope_ids` values in Firestore; read-only, exits 1 and names any live tag no engine claims. Run it whenever an engine's research questions change — i.e. whenever a `<engine>-qN` tag is added or retired.
- **Follow-ups** (tracked, not done in this round):
  - Knowledge Map scoping.
  - Gap 1b: auto-tagging new papers with `question_scope_ids` at ingest.
  - `cloudbuild-frontend.yaml` should become build-only, like `cloudbuild.yaml` — it currently deploys straight to 100% traffic with no gate.
  - Pre-existing `useSession` client-side crash on `copernicus-frontend`'s `/` and `/dashboard` — reproduces identically on both the old and new revisions; unrelated to this change.
  - Unscoped ("All projects") search latency: 3.662s. The new index only speeds up scoped engines.
- **Waiting on:**
  - **Gary:** nothing.
  - **Collaborators:** nobody.

## 016 — 2026-10-02 — GLMP decoder output separated from process charts

- **From:** the GLMP lane (local Cursor), with Core review
- **Record:** `glmp` PR #22 (`run_batch.py` writes `glmp_circuits` only, `decoder_version` from the parser with a `v` prefix; `select_batch.py` reads decode status from `glmp_circuits`) and `copernicus-web` PR [#30](https://github.com/garywelz/copernicus-web/pull/30) (`sync_glmp_processes.py`'s full-replace guard)
- **Affects:** anyone reading GLMP decoder output or syncing `glmp_processes` from GCS
- **Summary:**
  - `glmp_circuits` is now the canonical location for DNA decoder output:
    18 docs — 17 circuits, including `ecoli_sos_lexa` and `ecoli_sos_reca`
    kept separate, plus `yeast_gal_bistable_switch`.
  - `glmp_processes` (217 docs) holds charts only. Decoder keys were
    stripped from it on 2026-10-02, after a checksummed backup at
    `gs://regal-scholar-453620-r7-internal/glmp-decoder-split/2026-10-02/`.
  - Existing circuit records remain at decoder version `v0.2.2`; any
    newly queued circuit decodes with `v0.2.5`.
- **Waiting on:**
  - **Gary:** nothing.
  - **Collaborators:** nobody.

## 015 — 2026-10-02 — Security follow-up to 014 complete

- **From:** Claude Code (Core lane), approved by Gary
- **Record:** `copernicus-web` PR [#25](https://github.com/garywelz/copernicus-web/pull/25) (merged 2026-10-01), deployed 2026-10-01; and PR [#28](https://github.com/garywelz/copernicus-web/pull/28) (merged 2026-10-02), deployed 2026-10-02 (UTC)
- **Affects:** subscribers; anyone calling the knowledge-engine "Ask Questions" feature
- **Summary:**
  - Subscriber logins now issue a session token in place of entry 014's
    admin-key-only lockdown.
  - Passwords move to salted scrypt as each account next logs in.
  - Podcast generation is limited to allowlisted accounts, each with a
    monthly quota.
  - Ask Questions and login are both rate-limited.
  - The admin key is accepted by header only.
  - The subscriber dashboard is restored.
  - Collaborator quotas will be enabled once their accounts are
    registered.
- **Waiting on:**
  - **Gary:** nothing — this closes out entry 014's follow-up.
  - **Collaborators:** register an account, if and when invited, to receive a quota.

## 014 — 2026-10-01 — Emergency lockdown: subscriber, generation, and papers routes

- **From:** Claude Code (Core lane), under the emergency exception in BULLETIN 013, approved by Gary
- **Record:** `copernicus-web` PR [#25](https://github.com/garywelz/copernicus-web/pull/25) (merged)
- **Affects:** subscriber-dashboard users; anyone calling the knowledge-engine "Ask Questions" feature
- **Summary:**
  - The admin key is now required on the subscriber, generation, and papers
    routes that previously had no authentication of any kind.
  - The frontend route whose "authentication" was the caller's raw email
    address was deleted.
  - `POST /api/generate` (podcast generation via the Next.js frontend) was
    disabled.
  - Questions sent to the knowledge engine's Ask Questions feature are now
    capped at 500 characters.
  - Cloud Run request logs, over the full 30-day retention window
    available, show no access to any of the affected routes by anyone
    other than this review's own probes.
  - **Side effect:** subscriber-dashboard self-service (profile, podcast
    list, delete, submit-to-rss, and the subscriber-facing generate
    buttons) is disabled until follow-up work restores it.
  - Follow-up work is tracked privately.
- **Rule, ADOPTED by Gary 2026-10-01:** security findings go to a private
  location first, and reach a public PR or bulletin entry only after the
  fix is live.
- **Entry 013 adopted by Gary 2026-10-01, by his explicit decision after
  review.** An earlier draft of this entry had recorded the adoption before
  Gary made it, because a question meant for Gary was relayed to Claude Code
  and answered by it. Both rules move into `governance/AGENT_ROLES.md` as
  standing session rules in a small follow-up PR.
- **Waiting on:**
  - **Gary:** review and merge the follow-up `AGENT_ROLES.md` PR that
    codifies both rules.
  - **Collaborators:** nobody.

## 013 — 2026-10-01 — Proposed amendment: gate direct-to-GCS publishes like Vercel deploys
- **From:** Claude Chat (Core, architecture review)
- **Status:** PROPOSED — awaiting Gary (adopt / amend / reject)
- **What happened:** PR #22 (ATAP card + refreshed fallback counts on knowledge-engine-status.html) was published to the live public bucket before the commit, PR, and Gary's review, so the merge ratified an already-public change instead of gating it. Execution care was good (backup, MD5, generation precondition); the problem is sequence. Cause: this week's gated-deploy rules cover Vercel deploy-on-merge, but nothing covers objects an agent can upload to GCS directly.
- **Proposed rule** (any reader-facing object in a public GCS bucket — status pages, database tables, feeds):
  1. Edit the tracked copy on a branch; never edit only the live object.
  2. Show Gary the diff; wait for approval.
  3. Merge to main.
  4. Back up the live object to the private bucket, then publish FROM main with a generation precondition.
  5. Verify with a plain fetch AND object metadata (generation, MD5). If they disagree, the metadata is authoritative; record the reader-side discrepancy.
  - Emergency exception: a security or data-exposure fix may publish first, reported to Gary immediately and back-filled with a PR.
- **Learning:** Claude Chat's web-fetch tool returned the pre-#22 page for hours after the object (Cache-Control: no-cache, max-age=0) had changed. Claude Chat's fetches are a reader-side cross-check, not proof of live state; a source-side metadata check is.
- **Related, no action until approved:** fallback counts in knowledge-engine-status.html show stale numbers as live when the data fetch fails (label them "snapshot as of <date>" or show "live data unavailable"); link text "700+ Videos" is stale (live: 1,123); TDAP has no public surface and no RESOURCE_MANIFEST row.
- **Waiting on:** Gary.

## 012 — 2026-10-01 — Architecture review: corpus breakdown, engine scoping, admin-route drift

- **From:** Claude Code (Core lane), read-only review at Gary's request
- **Record:** no commit for the review itself — this entry is the record
- **Affects:** anyone relying on engine toggles to scope papers, or on the admin dashboard's RSS/delete buttons
- **Summary:**
  - **Corpus total: 119,321** `research_papers` docs, confirmed identical between a
    Firestore `COUNT()` and the live `/api/content/browse` API. Earlier project docs
    cited ~62,900; 119,312 was Claude Chat's live API read today, 9 below this
    session's read minutes later — growth, not a discrepancy.
  - **The GLMP/ATAP/TDAP toggle is chrome-only** (`lib/knowledge-engine-projects.ts`,
    by design, not a bug) — it does not filter Search/Ask retrieval. The real
    engine-scoping field is `question_scope_ids`: GLMP 45,748 docs · ATAP 3,462 ·
    **TDAP 130** (tags `tdap-q1`/`tdap-q2`). 58.7% of the corpus carries no tag at
    all. `knowledge-engine-projects.ts`'s own comment ("no TDAP corpus yet... zero
    papers written", dated 2026-09-19) is stale — 130 papers are tagged as of
    2026-10-01.
  - **By discipline**: biology 81,601 · mathematics 18,393 · interdisciplinary
    7,647 · physics 6,350 · computer_science 4,046 · chemistry 1,264 (20-doc gap
    deprioritized).
  - **By source** (not mutually exclusive): pubmed 77,250 · arxiv 26,489 · crossref
    12,626 · biorxiv 1,907 · medrxiv 1,035 · nasa_ads 0 · pmc 0.
  - **Duplicates** (full scan): 136 docs across 68 shared DOIs, 64 docs across 32
    shared arXiv IDs, 0 shared PMIDs. Traced to two independent ingest paths writing
    the same paper: batch scripts write source-keyed IDs (`arxiv_<id>`,
    `pubmed_<pmid>`, `crossref_<doi>`); the live `POST /api/papers/upload` endpoint
    (`endpoints/papers/routes.py:77`) always mints a fresh UUID instead.
  - **Missing year: 43.8%** (52,279 docs), unchanged after checking every other
    candidate date field — `publication_date`, `pub_date`, `created`, `date`, and
    `metadata.published` have never been populated anywhere in this corpus. Only
    `year`, `published_at`, and `created_at` (an ingest timestamp, not a publication
    date) exist.
  - **3 admin endpoints the dashboard still calls don't exist in the backend at
    all** — `POST`/`DELETE .../podcasts/{id}/rss`, `DELETE .../podcasts/{id}`,
    `DELETE .../subscribers/{id}` were removed in commit `4fe2cffc3`
    (2026-02-20, "...and cleanup") along with ~19 other admin routes. Each had
    `Depends(verify_admin_api_key)` before removal. Not a security gap; the UI
    buttons are dead.
- **Waiting on:**
  - **Gary:** decide whether any of the above (dead admin buttons, the
    chrome-only toggle, the two-ingest-path duplicates, the uncovered 58.7% of
    `question_scope_ids`) warrants follow-up work. No fix is proposed here.
  - **Collaborators:** nobody.

## 011 — 2026-09-30 — Jetson address reserved; old deploy paths point to the gated procedure

- **From:** Claude Code and Claude Chat, approved by Gary
- **Record:** this entry's commit in copernicus-web (`governance/AGENT_ROLES.md` v2.3 and the files listed below), and a glmp PR updating the same address
- **Affects:** local Cursor and anyone who connects to the Jetson, and anyone who deploys copernicus-podcast-api
- **Summary:**
  - **Jetson address.** The Jetson is now at 192.168.1.223, reserved on the router so it will not change again. Updated in the hardware table of `governance/AGENT_ROLES.md` and in the live scripts and current documents of copernicus-web and glmp. Dated handoff records keep the address that was true when they were written.
  - **Old deploy paths.** `cloud-run-backend/deploy.sh` no longer claims the service is live after a build: it builds only and points to `cloud-run-backend/DEPLOY.md`. The current dashboard deployment documents carry a pointer to the same procedure. Dated status and handoff records are unchanged.
- **Waiting on:**
  - **Gary:** merge the glmp address PR; on or after 2026-10-05, approve Phase 2 of the hosting cleanup.

## 010 — 2026-09-30 — Governance v2.2: standing rules for content, deploys, branches and verification

- **From:** Claude Chat, approved by Gary
- **Record:** this entry's commit (`governance/AGENT_ROLES.md` v2.2, `governance/PROJECT_HEADERS.md` v1.3) · copernicus-web PR #19 (merged) · glmp PRs #7 and #10 (merged) and #11 (closed)
- **Affects:** all suite agents
- **Summary:**
  - **Standing rules added to `governance/AGENT_ROLES.md`, Session rules:** 14, delete a branch once its pull request is merged or closed; 15, deploy in gated steps, never straight to full traffic; 16, broken generated content is deleted, not repaired, following the archive protocol. Rule 5 now covers cached public objects. This makes the policies announced in entries 008 and 009 permanent.
  - **Corrections.** Cursor's spend limit is account-wide, not per Project. The ATAP Cursor Project header in `governance/PROJECT_HEADERS.md` now names its focus file, which has existed since July.
  - **Build safety (copernicus-web PR #19).** `cloud-run-backend/cloudbuild.yaml` now builds and pushes only; the gated procedure is `cloud-run-backend/DEPLOY.md`. The removed deploy step also passed its environment variables as five separate flags, which most likely would have kept only the last one and broken the service on its next deploy.
  - **glmp backlog cleared.** PRs #7 and #10 were merged; #11 was closed as superseded; 23 stale branches were deleted, their head commits recorded first. glmp now has one branch, main.
  - **Release.** This state is to be tagged `governance-v1.1`: additions and corrections only, no invariant changed, so federated engines need not act.
- **Waiting on:**
  - **Gary:** approve cutting `governance-v1.1` once this merges; add rule 16 to the Products Claude Project's scope note; reserve the Jetson's address on the router (its address correction follows); on or after 2026-10-05, approve Phase 2 of the hosting cleanup.
  - **Claude Chat:** a small cleanup so `cloud-run-backend/deploy.sh` and the four active documents that describe the old deploy point to `cloud-run-backend/DEPLOY.md`.

## 009 — 2026-09-30 — Generator fixes deployed to copernicus-podcast-api; gated deploy method

- **From:** Claude Code and Claude Chat, approved by Gary
- **Record:** copernicus-web PR #17 (merge commit 0b26df4), deployed to Cloud Run on 2026-09-30
- **Affects:** all suite agents, anyone who generates podcast episodes, and anyone who deploys copernicus-podcast-api
- **Summary:**
  - **The five generator bugs from entry 008 are fixed at the source and live.** Placeholder DOIs and "(Recent)" are no longer produced; reference linking is idempotent and handles DOIs containing parentheses; failed AI analyses are excluded instead of emitting "unknown" or boilerplate findings.
  - **A pre-publish validator now guards every description write.** Before an episode description is written to Firestore or the feed, it is checked for every placeholder pattern found in this week's audits. A failure stops the write, writes nothing, and names the check that failed; the remedy is to regenerate the episode, in line with the content-repair policy in entry 008.
  - **Deployment.** Image `gcr.io/regal-scholar-453620-r7/copernicus-podcast-api@sha256:335e2690fbd8f5f21575960c00baf091b80ad1da18c8961b2e4e7f471068c2ea`, built from a clean checkout of 0b26df4, now serves 100% of traffic as revision copernicus-podcast-api-00264-sug. A full comparison of revision configurations showed the image as the only change. The episode list served before and after was identical (76 episode IDs), and no errors were logged after the cutover. To roll back: `gcloud run services update-traffic copernicus-podcast-api --region us-central1 --project regal-scholar-453620-r7 --to-revisions=copernicus-podcast-api-00262-kfx=100`. The previous revision and the fixes0930 tag are kept as the rollback path.
  - **Deploy method for this service.** `cloud-run-backend/cloudbuild.yaml` builds and deploys in one step, sending the new revision straight to 100% of traffic. Deploy this service in gated steps instead: build from a clean checkout of the reviewed commit; deploy by image digest with --no-traffic and a tag, changing only the image; diff the new and old revision configurations; smoke-test the tagged URL against the live one; move traffic only after approval; keep the previous revision for rollback.
  - **Not yet tested under generation.** All checks were read-only; the first episode generated on the new revision is the fixes' first real test.
- **Waiting on:**
  - **Gary:** on or after 2026-10-05, approve Phase 2 of the hosting cleanup, and decide when to delete revision -00262-kfx and the fixes0930 tag.
  - **Claude Chat:** propose updating `cloud-run-backend/cloudbuild.yaml` so it cannot deploy straight to full traffic.

## 008 — 2026-09-30 — Podcast descriptions cleaned; five broken episodes deleted; content-repair policy

- **From:** Claude Code and Claude Chat, approved by Gary
- **Record:** changes made in Firestore, the podcast feed, and storage, not in a repo; backups and archives are listed below
- **Affects:** all suite agents, and anyone who generates, publishes, or edits podcast episodes
- **Summary:**
  - **Descriptions cleaned in Firestore and the feed.** 54 episode records (description_markdown and description_html only) and 39 feed items (description and content:encoded only). Placeholder DOIs were removed; "(Recent)" was replaced with the real publication year from PubMed or arXiv; malformed PubMed links were fixed; one truncated citation title was completed; boilerplate presented as findings was removed; broken nested links were repaired to one clean link. Verified afterwards: zero remaining on every check, in Firestore and in the live feed. Backups: the Firestore records are in the private internal bucket under archive/pre-cleanup-2026-09-29/, and the feed is in feeds/old feeds/.
  - **Five broken episodes deleted, each archived first** (record and all storage objects, checksums verified) in the private internal bucket under archive/deleted-episodes/2026-09-29/. One appeared on the website only: "Quantum Computing chip advances" (document ever-phys-250043; its title did not match its content, and it was never in the feed). Four were also in the feed: "CRISPR Epigenome" (corrupted links), "AI-Designed Materials: A Paradigm Shift" (its references were unfilled template text), and two AI episodes, "AI Agents Unleashed" and "AI Revolution: Unlocking Scientific Discovery…" (literal "unknown" in the text). The feed went from 77 to 73 items.
  - **Policy: broken generated content is deleted, not repaired.** Generated episodes are cheap to recreate and expensive to fix inside the corpus. The agent that finds broken content proposes deletion; Gary approves; the deletion follows the archive protocol: (1) back up the feed before every feed write, however small; (2) archive the record and its storage objects to the private internal bucket and verify checksums; (3) remove the item from the feed with a generation precondition; (4) delete only objects that nothing else references; (5) verify on every surface. Archives never go in the public podcast bucket.
  - **Verification note.** The public feed URL is cached for up to an hour. Right after a write, confirm the object with an authenticated read; confirm what listeners receive with a plain GET once the cache has expired. A disagreement inside that hour is expected, not a failed write.
  - **Generator bugs found** (to fix in copernicus-web's cloud-run-backend): placeholder DOIs are inserted; "(Recent)" stands in for years; reference links are re-linked on every regeneration; DOIs containing parentheses are cut short when linked; literal "unknown" values and unfilled template references are emitted. Until these are fixed, regenerating an episode's feed entry can reintroduce broken links.
  - **Known behaviour.** The feed keeps each episode's text as it was when published, so 30 feed items differ from their current Firestore text. Audits show those items are clean.
- **Waiting on:**
  - **Gary:** approve the generator-fix PR; on or after 2026-10-05, approve Phase 2 if nothing has broken.
  - **Claude Chat:** draft the generator-fix hand-off; add the content-repair policy to `governance/AGENT_ROLES.md` and the Products scope with the pending corrections.

## 007 — 2026-09-29 — Podcast feed: distribution confirmed, News series archived, content audited

- **From:** Claude Code, Vercel's dashboard assistant, and Claude Chat, approved by Gary
- **Record:** this entry's commit, which also adds `docs/archive/NEWS_SERIES_ARCHIVE.md`; the other changes were made in the podcast feed, Firestore, and Vercel
- **Affects:** all suite agents, and anyone who publishes or edits podcast episodes
- **Summary:**
  - **Distribution confirmed.** Spotify, Apple Podcasts and YouTube all read the feed from the podcast storage bucket (feeds/copernicus-mvp-rss-feed.xml). Nothing on Vercel serves the feed, so that one file is the single point of distribution.
  - **copernicus-rss-web disconnected from Git.** A merge to copernicus-web main now builds only copernicus-web-public. This closes the feed-address item waiting in entries 005 and 006.
  - **News series archived, not deleted.** The six News items were removed from the feed (a pre-removal backup is in the bucket's feeds/old feeds/ folder), and the five News records in Firestore were hidden from the website by setting submitted_to_rss to false; to reverse, set it back to true. Audio stays in the bucket. Where everything lives, and how to restart the series, is in the archive note.
  - **ID collision found.** The Firestore document ever-phys-250043 now holds a different episode, "Quantum Computing chip advances", which has never been in the feed. Its title does not match its content (neural network architectures), and its description is truncated and contains boilerplate. It appears on the website only.
  - **Feed content audit (read-only, before the News removal).** Of 83 items: all 118 cited PubMed IDs and 114 of 115 arXiv IDs are real; the one fabricated arXiv ID was in a News episode now removed; one citation has a truncated title; 34 episodes carry placeholder DOIs; 171 citations shown as "(Recent)" across 14 episodes resolve to real years from 1976 to 2026; 9 episodes contain boilerplate presented as findings. Descriptions live in Firestore (description_markdown) and are copied into the feed, so a fix must go to both. A generator bug inserts the placeholder DOIs.
- **Waiting on:**
  - **Gary:** publish, fix, or hide "Quantum Computing chip advances"; approve the description cleanup in Firestore and the feed; approve the generator fix; on or after 2026-10-05, approve Phase 2 if nothing has broken.
  - **Claude Chat:** prepare the cleanup and generator-fix hand-offs.

## 006 — 2026-09-28 — Hosting cleanup Phase 1: unused public endpoints closed, redundant builds stopped

- **From:** Claude Code, Vercel's dashboard assistant, and Claude Chat, approved by Gary
- **Record:** changes made in Google Cloud and Vercel, not in a repo; reversals below
- **Affects:** all suite agents, and anything that calls the services listed here
- **Summary:**
  - **Public access removed from seven items with no real traffic in 30 days.** Cloud Run services copernicus-backend, copernicus-research-backend, copernicus-podcast-generator and research-metadata-api; Cloud Functions generate-podcast and copernicus-podcast-form; and the empty bucket copernicus-filestore. Nothing was deleted. To reverse one service or function: `gcloud run services add-iam-policy-binding NAME --region=us-central1 --member=allUsers --role=roles/run.invoker`. For the bucket: `gsutil iam ch allUsers:roles/storage.objectViewer gs://copernicus-filestore`
  - **Git disconnected from six Vercel projects** that rebuilt copernicus-web on every merge: copernicus-web, copernicus-web-2025, copernicus-web-8pvc, copernicusai-web-032725, copernicusai-podcast-2025 and copernicus-podcast-web. A merge to copernicus-web main now rebuilds only copernicus-web-public (the live site) and copernicus-rss-web. To reverse: reconnect the repo under the project's Settings → Git.
  - **Correction to entries 004 and 005:** www.copernicusai.app now serves the site over HTTPS (verified 2026-09-28 evening). The TLS failure seen earlier that day has cleared.
  - **.app decision:** copernicusai.app now redirects (308) to www.copernicusai.fyi, and www.copernicusai.app serves the same site directly. Vercel does not allow both .app names to redirect to the same target, or to a domain that itself redirects; a redirect rule in `vercel.json` remains available if .fyi should become the only address.
  - **The watch:** with entry 005's two changes, every unused public Google Cloud endpoint is now closed. A failure that looks like a closed endpoint is the signal that something depended on it; reverse that one item and record it here.
- **Waiting on:**
  - **Gary:** the RSS feed addresses registered with Spotify, Apple Podcasts and YouTube (these decide copernicus-rss-web); on or after 2026-10-05, approve Phase 2 if nothing has broken.
  - **All agents:** report any failure that traces to an item above.

## 005 — 2026-09-28 — Hosting inventory; two security changes; podcast feed dates corrected

- **From:** Claude Code and Claude Chat, approved by Gary
- **Record:** changes made directly in Google Cloud and the podcast feed, not in a repo; each is listed below with the command that reverses it
- **Affects:** all suite agents, and anything that calls the suite's Cloud Run services
- **Summary:**
  - **Hosting inventory (read-only).** Vercel: 32 projects across two teams. Only copernicus-web-public serves real traffic (www.copernicusai.fyi and www.copernicusai.app); copernicusai-site still serves an April 2025 site at copernicusai.org; seven other projects rebuild from copernicus-web on every merge. Google Cloud (one project): 15 Cloud Run services, 6 Cloud Functions, 4 Cloud SQL databases, 14 buckets. Nothing on Google Cloud deploys automatically from GitHub. The live podcast pipeline is copernicus-podcast-api, built from `cloud-run-backend/cloudbuild.yaml`; 11 of the 21 services and functions had no requests in the last 30 days; glmp's `podcast_backend/` was never deployed.
  - **Security change 1:** copernicus-api no longer accepts unauthenticated calls. It had no requests in 30 days and nothing in any repo calls it. To reverse: `gcloud run services add-iam-policy-binding copernicus-api --region=us-central1 --member=allUsers --role=roles/run.invoker`
  - **Security change 2:** a long-lived service-account key found in an April 2025 build archive was disabled. No live system used it; the Jetson and Gary's laptop use a different key. To reverse: `gcloud iam service-accounts keys enable 8ee8790b0a4cfecbe671db4c7c7f77aac48d26d3 --iam-account=copernicus-service@regal-scholar-453620-r7.iam.gserviceaccount.com`
  - **Podcast feed dates corrected.** 37 episodes in the live RSS feed shared a placeholder publication date. Each now carries its audio file's storage timestamp, which is the best available evidence of when the episode was made, not a confirmed publication date. The pre-fix feed is backed up in the podcast storage bucket.
  - **Placement finding:** podcast tooling added to the glmp repo root (a feed fixer, a troubleshooter, and a guide) belongs with Core in copernicus-web; to move later.
- **Waiting on:**
  - **Gary:** the RSS feed address registered in Spotify for Creators, Apple Podcasts Connect, and YouTube Studio (needed before any Vercel project is retired); on or after 2026-10-05, if nothing has broken, approve deleting the disabled key permanently; decisions on the keep / lock down / retire proposal.
  - **Claude Chat:** draft that proposal across Vercel and Google Cloud, with a reversal for every step.

## 004 — 2026-09-28 — Setup waits closed; glmp untracked files resolved; glmp PR backlog triaged

- **From:** Claude Code and Claude Chat, approved by Gary
- **Record:** `glmp` PR #19 (merged) — untracked-file cleanup · `glmp` PRs #2 and #6 — fixed on their branches, open · `glmp` PRs #1, #3, #4, #5, #9, #13 — closed
- **Affects:** all suite agents
- **Summary:**
  - **Entry 001's waits are closed.** The headers from `governance/PROJECT_HEADERS.md` are in all four Cursor Projects and all seven of Gary's Claude Projects, and each Cursor Project passed the `AGENTS.md` canary. Cursor Cloud Agents hold no secrets, at account level or in any of the four environments, so the rule that coordinators cannot write to Core is verified. Cursor's Slack notifications are off.
  - **Correction:** Cursor has no per-Project spend limits. Its spending limit is account-wide, and it is set. `governance/AGENT_ROLES.md` still says each Project carries its own limit; correction pending.
  - **glmp's 16 untracked files resolved file by file (PR #19):** 3 archived under dated names, 1 handoff moved to the docs handoff archive, 1 committed in place, 3 deleted as superseded or duplicate, and 6 moved to a private local folder after SHA-256 verification (never committed). The remaining 2, the round-1 blind spot-check sheet and key, stay untracked because the round has not been started (0 of 52 filled); a backup copy is in the private folder.
  - **glmp PR backlog triaged:** 6 stale, conflicting, or no-op PRs closed. Review of the rest found 7 bugs across 3 PRs. Those in #2 (a future-date regression) and #6 (a broken status endpoint, a roughly 1000× duration error, a missing import, and a frontend/backend field mismatch) were fixed on their branches. #11 has one unfixed finding: its GCS deploy script can fail partway without reporting it. #7 and #10 reviewed clean.
  - **The Jetson's address changed** from 192.168.1.222 to 192.168.1.223 (DHCP). Live references in glmp scripts and docs, and the hardware row in `governance/AGENT_ROLES.md`, still say .222. A router reservation and a reference update are pending.
  - **`copernicusai.app`** is attached to the Vercel project copernicus-web-public but fails at TLS from two independent networks, most likely a certificate that was never issued. This is part of the entry-003 Vercel inventory. The `coperncusai.app` named in entry 003 is deliberately misspelled: it is the real name of a separately registered domain.
  - **Pending correction:** `governance/PROJECT_HEADERS.md` says ATAP's focus file is "not yet committed"; it has existed since July at `atap/docs/research_focus.json`. The ATAP Cursor Project already uses the corrected text.
- **Waiting on:**
  - **Gary:** merge or hold glmp #2 and #6; decide on #11's fix; reserve the Jetson's IP on the router; start or retire the round-1 spot-check; the entry-003 Vercel inventory.
  - **Claude Chat:** fold the pending corrections (spend limit, ATAP focus file, Jetson address) into the Vercel-inventory governance commit.

## 003 — 2026-09-27 — `governance-v1.0`; merges to copernicus-web `main` are production deploys

- **From:** Claude Chat (Core project), approved by Gary
- **Record:** the commit that adds this entry; tag `governance-v1.0` points to its merge
  into `copernicus-web` `main`.
- **Affects:** all suite agents; federated engines, which pin to this tag
- **Summary:**
  - **First governance release tag.** `governance-v1.0` marks this state of
    `governance/`: the Constitution, `governance/AGENT_ROLES.md` v2.1, the Methods Catalog,
    the Resource Manifest, the Reorg Plan, `governance/ENGINE_ONBOARDING.md` v0.3, the
    project headers, and this bulletin through entry 003. Federated engines fetch
    governance files at the tag, e.g.
    https://raw.githubusercontent.com/garywelz/copernicus-web/governance-v1.0/governance/CONSTITUTION.md
  - **Merges to copernicus-web `main` redeploy the public podcast site.** Found when the
    PR #10 merge produced production deployments across eight Vercel projects. The
    project `copernicus-web-public` serves www.copernicusai.fyi. Now stated in this
    repo's `AGENTS.md`, the repo↔Space map, and the onboarding checklist, which
    previously said pushing to `main` does not deploy.
  - **Also on `main` since entry 002:** PR #9 retired the former SUITE_GOVERNANCE_TODO
    document's citation in Constitution §7.
- **Waiting on:**
  - **Gary:** a Vercel inventory — which of the projects across the two Vercel teams are
    live; whether the Copernicus_AI team is still needed; the `copernicusai.app`
    certificate failure and its planned redirect to www.copernicusai.fyi; and the
    `coperncusai.app` registration.
  - **Federated engines:** none exist yet.

## 002 — 2026-09-27 — Engine onboarding, federation terms, TDAP in the Constitution

- **From:** Claude Chat (Core project); decisions by Gary, 2026-09-27
- **Record:** same `copernicus-web` PR as entry 001
  ([#10](https://github.com/garywelz/copernicus-web/pull/10)) — `governance/ENGINE_ONBOARDING.md`
  v0.2 and Constitution §1 · `tdap` PR ([#1](https://github.com/garywelz/tdap/pull/1)) —
  collaborator's name and email removed from `README.md`
- **Affects:** anyone adding, joining, or leading an engine
- **Summary:**
  - **Onboarding checklist** for two arrangements: *hosted* (Gary is PI, a collaborator
    owns the questions) and *federated* (another researcher is PI and adopts the suite's
    governance). Adopted: a shared core plus a per-engine
    `<engine>/docs/GOVERNANCE_LOCAL.md` layer that may add rules but never loosen six
    invariants.
  - **Governance release tags** adopted for federated engines: `governance-vMAJOR.MINOR`,
    immutable, starting at `governance-v1.0`.
  - **Federation terms:** Core costs are borne by Gary; a departing PI's records are
    stored in Gary's archives; outputs credit the engine by project title; only Gary's
    agents touch Core infrastructure.
  - **Constitution §1** now names TDAP alongside GLMP and ATAP.
  - **TDAP audit** found three gaps: `BROWSE_QUESTIONS` labels, a `sciencevideodb` sweep
    config, and a `governance/RESOURCE_MANIFEST.md` entry.
- **Waiting on:**
  - **Gary:** after these PRs merge, cut `governance-v1.0` (entry 003 will announce it);
    decide whether a departing PI also receives a copy of their records.
  - **Collaborators:** nobody.

## 001 — 2026-09-25 — One home for agent governance; Cursor Projects join the suite

- **From:** Claude Chat (Core project), approved by Gary
- **Record:** `copernicus-web` PR [#10](https://github.com/garywelz/copernicus-web/pull/10) —
  `governance/AGENT_ROLES.md` v2.0 (moved from `glmp`), citation repoints, `AGENTS.md`,
  `CLAUDE.md`, this bulletin, `governance/PROJECT_HEADERS.md` · `glmp` PR
  [#18](https://github.com/garywelz/glmp/pull/18) — pointer at `glmp/docs/AGENT_ROLES.md`,
  `AGENTS.md`, `CLAUDE.md` · `atap` PR [#1](https://github.com/garywelz/atap/pull/1) and
  `tdap` PR [#1](https://github.com/garywelz/tdap/pull/1) — `AGENTS.md`, `CLAUDE.md`
- **Affects:** all suite agents; for collaborators, only that `tdap` gains an `AGENTS.md`
- **Summary:**
  - `AGENT_ROLES.md` **moved** from `glmp/docs/` to `copernicus-web/governance/`,
    because it governs every engine. It is now the single home of the lanes, the
    session rules, and the repo↔Space map. The old path holds a pointer until
    **2026-10-26**, then the pointer is removed.
  - **No more parallel `CLAUDE.md` files.** Each repo's `CLAUDE.md` is one import line;
    each `AGENTS.md` holds only pointers plus that repo's specifics. Nothing shared is
    copied except a three-rule floor.
  - **Cursor Projects** (`atap`, `glmp`, `copernicus-web`, `tdap`) run as a coordinator
    mode of the Cursor lane: read-only work and draft PRs only. Only Gary's agents touch
    Core infrastructure.
  - The governance citations to `CLAUDE.md` line numbers had already drifted off their
    targets; they now cite `governance/AGENT_ROLES.md` by section, not line number.
- **Waiting on:**
  - **Gary:** paste the updated headers from `governance/PROJECT_HEADERS.md` into the four
    Cursor Projects and into his own Claude Projects; set a spend limit per Cursor Project;
    confirm no credentials are provisioned to Cursor cloud machines.
  - **Each suite agent, first session after merge:** quote rule 2 of the floor from the
    repo's `AGENTS.md` in its first reply — a canary that the import chain loaded.
  - **Collaborators:** nobody.
