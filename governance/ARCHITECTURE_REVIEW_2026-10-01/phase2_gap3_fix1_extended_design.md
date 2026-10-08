# Gap 3, upstream fix 1 (extended): the script names only confirmed papers — design proposal

*Core lane (Claude Code), 2026-10-08. For Gary's review before anything is built. **Design only:** no code
changed, no episode generated, no provider called to write this; the only writes are this file and its draft PR.
Requirements: Gary's decisions of 2026-10-08 on the baseline evaluation (BULLETIN entry 021). Every file:line
below was read on 2026-10-08 on `main` after the PR #45 merge. Numbers from Firestore were read the same day,
read-only.*

---

## 0. Summary

**What changes.** Today the model writes the reference list, and the research stage mixes registry records with
model-written citation strings. The evaluation found the serious defect is papers **named in the script that are
not in the list** (8 of 60 sampled flags, plus 21 of 124 reference lines with no identifier and 5 of 20 episodes
with no list). This design replaces the pipeline's citation handling with four mechanisms, all in code:

1. **Confirm** every candidate paper against its registry (PubMed, arXiv with version, Crossref DOI) before the generator
   sees it. Nothing else reaches the generator. No model-written citation string survives anywhere.
2. **Number** the confirmed papers `P1…Pn`; the generator may name only those, and **a post-generation check** finds any
   author, title or paper named in the script that is not on the list. Policy on a hit: **regenerate with the hits fed
   back (up to 2 times), then fail the episode. Never publish it, never auto-delete sentences.**
3. **Build the reference list in code** from the confirmed papers the script names, deduplicated, each with its stable
   identifier and cited version. "The link is in the description" may appear only for papers in that list.
4. **Fewer than 3 confirmed papers: fail with a clear failure email** (already decided).

The `P` numbers are stable and stored with the episode, so fix 3 (inline markers) attaches to them with no rework.

**Evidence on how many topics could now fail** (section 5): of the 32 past jobs that stored their sources, **none** had fewer
than 3 sources carrying a registry identifier (minimum 3; 28 had 10). That counts identifiers, not confirmed existence,
and 35 older jobs stored nothing, so the real rate is unmeasured; the sandbox test (section 6) measures it. The larger
risk is **the naming check firing on first attempts**; the old generator named an unlisted work in roughly 2 of 5 episodes,
so regeneration with feedback is built in.

**Cost** (section 6, estimates): the sandbox test is about **$1.5 to $2.5** for 10 topics, ceiling $4. The ongoing cost is
small: a few registry calls (free) and one short extraction call per episode (about $0.005).

**Prerequisite found on the way** (section 7.5): the failure email only reaches anyone once the Gmail app password from
the proposal's section 13 is set up, and one recipient setting must be fixed first or failure emails can go to the sender
address instead of you.

---

## 1. Requirements and the evidence behind each

| # | Requirement (Gary, 2026-10-08) | Evidence |
|---|---|---|
| R1 | Every paper available to the generator is retrieved and confirmed by identifier (PubMed, arXiv incl. version, Crossref DOI); no model-written citation strings anywhere | Citation integrity 82% (102 of 124 reference lines); 21 lines with no identifier; model-written citation strings are pooled into the evidence (section 2) |
| R2 | The script may name only confirmed papers; a post-generation check detects any named work not on the list; propose the remedy; never publish | 8 sampled real flags were papers named in the script with a promised link and absent from the list; the extractor found unmatched named works in 8 of 20 episodes (roster A) |
| R3 | The reference list is built by code from every confirmed paper the script names, with identifier and version; "link in the description" only for listed papers | 5 of 20 episodes had no list; 1 duplicate in 124 lines; two title mismatches were version differences (the cited `v1` was right) |
| R4 | Fewer than 3 confirmed sources: fail with a clear failure email | decided |
| R5 | Numbered list ready for fix 3 | items 7 and 80: a listed paper was not connected to the claim naming it |
| R6 | Test plan: sandbox, nothing published, adopted checker, compare with the baseline | section 6 |
| R7 | Per change: file:line, effort, risks, gated deploy path | sections 4 and 7 |

---

## 2. Where citations enter and leave the pipeline today (all under `cloud-run-backend/`)

| # | What happens | Where |
|---|---|---|
| 1 | Candidate sources come from PubMed, arXiv, bioRxiv, Zenodo, CORE, NASA ADS, YouTube and (optionally) a news API; `ResearchSource` has `doi` and `url` only: **no PMID, arXiv ID, version or confirmation field** | `research_pipeline.py:12-23`, `:84-148`; PubMed parse `:711-771`, arXiv parse `:773` |
| 2 | User-supplied links are turned into "sources" by **a model extracting title, authors and abstract from page text**; no DOI is read and nothing is checked against a registry | `research_pipeline.py:580-655` (`_extract_metadata_with_ai`, `:605`) |
| 3 | The per-paper analysis prompt asks the model for "properly formatted academic citations with DOIs where possible"; the answer is kept | `paper_processor.py:117`, `:165` |
| 4 | Those model-written citations are pooled into the research context | `podcast_research_integrator.py:190-194` |
| 5 | A second, template-built citation list is pooled from the sources (`format_real_citation_line`); it omits papers with neither DOI nor URL | `podcast_research_integrator.py:50-72`, `:196-203`, `:227` |
| 6 | The sources the generator sees are the top 8, numbered `1.`…`8.` in the prompt, with abstract cut to 300 characters (unchanged here; that is fix 2, deferred) | `podcast_research_integrator.py:468-495` |
| 7 | The prompt tells speakers to name "Author names, publication, and title" and to say "the link is in the description"; it asks the model to **write** a `## References` section and return `citations_used` | `podcast_research_integrator.py:383-388`, `:443`, `:449` |
| 8 | A sibling code path builds a separate script (`EnhancedPodcastScript`) with "citations" made from titles plus keywords | `enhanced_research_service.py:75`, `:322`, `:411-417` |
| 9 | If the model left out References, code adds up to 5 from the template-built list (two copies of this logic) | `services/podcast_generation_service.py:2400-2480`, `:1436-1458` |
| 10 | The job fails fast when fewer than 3 **sources** (any kind) are found | `podcast_research_integrator.py:137-143`; call `services/podcast_generation_service.py:2187` |
| 11 | Content generation is retried up to 2 times, only if the script is too short | `services/podcast_generation_service.py:2262-2318` |
| 12 | Any exception marks the job failed and sends the failure email to `ERROR_NOTIFICATION_EMAIL` | `services/podcast_generation_service.py:2850-2870`; `config/constants.py:54`; `email_service.py:120` |

---

## 3. The design

### 3.1 Step A: confirm the papers (new module, called at the end of the research phase)
Input: the ranked `ResearchSource` list. Output: `confirmed_papers`, a list of records, plus a `dropped` list with a reason.

For each candidate, in order:
1. **Extract an identifier from the registry-given fields, never from model output:** arXiv ID and version from the arXiv
   `<id>` URL (the parse at `research_pipeline.py:773` already receives it), PMID from the PubMed record, DOI from the
   record's DOI field. Candidates with none are dropped (`no_identifier`): this removes YouTube, news, CORE without a DOI,
   and Zenodo without a DOI.
2. **Look the identifier up:**
   - arXiv: one batched request for all arXiv IDs with their versions (`id_list=2603.28944v1,…`); keep the title,
     authors, abstract, and `v` of that version. A bare ID is pinned to the version retrieved.
   - PubMed: one batched `efetch` for all PMIDs.
   - Crossref: `works/{doi}`; if there is no abstract, try PubMed by DOI as the evaluation harness did.
3. **Check that the record matches what was retrieved** (title word overlap at least 0.6, and publication year within one
   year if both exist). A record that exists but is a different paper is dropped (`identifier_mismatch`).
4. **Assign `P1…Pn`** in current rank order, up to a maximum of 12 papers (the generator uses 8 today; the extra four are a
   reserve for dropped ones).

Stored record (also the unit fix 3 will cite):

```json
{"pid": "P3", "title": "<registry title of the cited version>", "authors": ["<full author list from the registry>"],
 "year": 2026, "venue": "<journal or null>",
 "ids": {"arxiv": "2603.28944", "arxiv_version": "v1", "pmid": null, "doi": null},
 "url": "https://arxiv.org/abs/2603.28944v1", "abstract": "<registry abstract>",
 "registry": "arxiv", "confirmed_at": "<UTC time>", "title_match": 0.93}
```

Rules that make the list trustworthy:
- **Titles and authors in the list always come from the registry**, never from a model and never from the search record's
  own text. The title is the **cited version's** title (the evaluation showed a later version can be retitled).
- **User-supplied links** (`:580-655`) become a candidate only if the page or URL yields a DOI, arXiv ID or PMID that
  passes step A; the model-extraction route is kept only to find that identifier, and its title and authors are discarded.
  Links that cannot be confirmed are dropped and listed in the job record.
- **A paper requested directly** (the paper-request flow, `services/podcast_generation_service.py:1078-1099`) must itself be
  confirmed by its DOI; if it cannot be, the job fails with a message that says so.
- **Registry outage is not "too few sources".** If a registry is unreachable after two retries, the job fails with a
  different, honest message ("could not reach arXiv/PubMed/Crossref; try again") so a transient outage is not misread as a thin topic.

### 3.2 Step B: the generator gets a numbered list and one rule
The evidence block (`podcast_research_integrator.py:468-495`) changes from `1. **Title**` to `[P1] Authors (year). Title.`,
using only fields from `confirmed_papers`. The model-written pieces are removed from the prompt: the "REAL CITATIONS" block
(`:517-521`), the paradigm-shift and key-finding lines stay but are tagged with the `P` number of the paper they came from (so
a finding can be traced), and the instruction at `:443` and the `citations_used` field at `:449` are replaced by:

> You may name only the papers in the list above, by their authors and year, in speech. Do not name, quote or allude to any
> other paper, author or study, even if you know it. If the list lacks something you need, say it is outside what was reviewed.
> Say "the link is in the description" only right after naming a paper from the list. Do not write a References section;
> it is added for you.

The output schema loses `citations_used`, and `description` no longer contains a References section.

### 3.3 Step C: the post-generation check (inside the existing retry loop)
Placed next to the word-count test at `services/podcast_generation_service.py:2262-2318`, before the pre-publish gate at `:2345`.

1. **Extract named works.** One short call to a cheap model (the checker's roster A model, about $0.005) reads the script
   and lists every place where a specific work or its authors are named or alluded to: author names tied to a paper, study
   or result; quoted titles; "a 2025 paper by …"; "according to …". It returns quotes, not judgments.
2. **Match deterministically** against the list: surname of any listed author **and** year or at least two title words. No
   model decides a match.
3. **Violations are:** a named work with no match; and a "link in the description" phrase not directly attached to a matched work.
   Not violations: a general scientific concept or person with no specific work attached (for example a named theory), and
   institutions. These rules matter because an over-eager check would fail good episodes; the test measures its false positives.
4. **What happens on a violation (recommendation, for your decision):**
   | Option | Verdict |
   |---|---|
   | **Regenerate the whole script with the violations fed back** ("you named X and Y; they are not on the list; name only P1…Pn"), up to 2 times in the existing loop, then **fail the episode** | **Recommended.** Uses machinery that exists, never publishes an unlisted name, and the failure email says exactly what was named |
   | Remove the offending sentences in code | Rejected for v1: deletes a turn from the middle of a dialogue, can leave a speaker answering nothing, and changes audio timing with no check of the result. Could be revisited as a repair of last resort only if tests show regeneration rarely succeeds |
   | Fail on the first violation | Rejected: wastes a good script over one stray name; regeneration costs about $0.01 |
   | Publish and flag after | Rejected by the requirement: never publish |
5. **If it still fails after the retries,** the episode fails (job status `failed`, nothing written to `episodes`, the feed or
   the audio bucket, since the check runs before any of that, as the pre-publish gate does).

### 3.4 Step D: the reference list is built by code
After the check passes, the matches from 3.3 say which confirmed papers the script names. The References section is generated
by a function, from those records only:

- one line per named paper, **deduplicated** by arXiv ID, PMID and DOI (and by title when ids differ), in order of first mention;
- format: `Authors (year). Title. Venue. arXiv:ID vN` or `PMID …` or `DOI …`, plus the canonical link; the **version** is shown
  and the link includes it (so `v1` stays `v1`);
- the source paper of a paper-request episode is always included;
- the list is written to the description, the RSS item (`services/rss_service.py:354-411`, which reads the same description)
  and the job record; it replaces both fallback blocks (`:2400-2480`, `:1436-1458`), which are deleted.

**Open point (question 1):** the requirement lists "every confirmed paper the script names". Papers on the list that the script
does not name are then not referenced, even though they informed the content. Fix 3 makes that distinction exact; until then I
recommend naming-only, with a note that this shortens some lists.

### 3.5 Step E: too few confirmed papers
If fewer than 3 papers survive step A, the job fails **before generation**, with a message that states how many candidates were
found, how many were confirmed, and the reasons for the drops (counts by reason). This moves the existing rule from
`podcast_research_integrator.py:137-143` (any 3 sources) to **3 confirmed papers**, evaluated after step A. The existing
failure path (`services/podcast_generation_service.py:2850-2870`) already marks the job failed and writes nothing to `episodes`.

### 3.6 Compatibility with fix 3 (inline markers)
- The `P` numbers exist from step A and are stored with the job (`confirmed_papers`) and the episode (`papers` plus
  `papers_named`), so a marker `[P3]` in a later `script_cited` field refers to the same record with no migration.
- The evidence block already presents each paper under a `[Pn]` label; fix 3 adds only the instruction "put the paper's
  number in brackets after each claim that rests on it" and a deterministic strip function before audio.
- The post-generation check then becomes mostly parsing: every `[Pn]` must be on the list, and every named work must carry a marker.
- The checker's primary flag ("no matched source") reads the markers instead of inferring the source, which is what
  items 7 and 80 needed.

### 3.7 What is stored (new fields, nothing existing is renamed)
| Where | Field | Content |
|---|---|---|
| `podcast_jobs` | `confirmed_papers`, `dropped_candidates` | the records above and the reasons |
| `podcast_jobs` | `named_work_check` | attempts, violations per attempt, final result |
| `podcast_jobs` and `episodes` | `references_built_by` | `"code@1"`, so old and new episodes can be told apart |
| `episodes` | `papers`, `papers_named` | the confirmed records and the `pid`s the script names |
Old fields (`real_citations`, `research_sources_summary`) stop being written by new jobs; old episodes keep theirs.

---

## 4. Changes: file:line, effort, risks

Effort is my estimate of Claude Code working time including tests (not calendar time). All files under `cloud-run-backend/`.

| # | Change | Where | Effort | Risks |
|---|---|---|---|---|
| C1 | New module: confirm papers (batched arXiv/PubMed/Crossref lookups, matching, `P` numbering, drop reasons) | new file; called from `podcast_research_integrator.py:99-230` after `:137` | 1.5-2 days | Registry rate limits and outages; slower research phase (batching keeps it to about 3 requests plus one per DOI; the research stage has a 300 s timeout at `services/podcast_generation_service.py:2189`); Crossref abstracts often missing; title-match threshold too strict drops real papers |
| C2 | Drop every model-written citation string | `podcast_research_integrator.py:190-194`, `:227`; `paper_processor.py:117` (remove from the requested schema), `:152`, `:165`; `enhanced_research_service.py:322`, `:411-417`; `research_pipeline.py:605-655` (keep only identifier discovery) | 0.5 day | A sibling script path (`EnhancedPodcastScript`) may still be used by other endpoints: grep for callers first; if used, stop emitting its citations rather than deleting the path |
| C3 | User-supplied links and requested paper confirmed by identifier or dropped | `research_pipeline.py:580-655`; `services/podcast_generation_service.py:1078-1099` | 0.5 day | A user link to a non-paper page is silently dropped (recorded in the job); paper-request episodes can now fail if their DOI is wrong |
| C4 | Prompt: numbered `[Pn]` evidence, naming rule, remove the References and `citations_used` instructions | `podcast_research_integrator.py:468-495`, `:517-521`, `:383-388`, `:443`, `:449` | 0.5 day | Prompt wording changes script style; a stricter rule may lengthen "outside what was reviewed" disclaimers; needs the test in section 6 |
| C5 | Named-work check (extraction call, deterministic match, "link in the description" rule) inside the retry loop; feedback to the regeneration prompt | `services/podcast_generation_service.py:2262-2318`; prompt feedback via `additional_instructions` at `:1078`, `:1111-1120` | 1.5-2 days | **False positives fail good episodes**; false negatives let a stray name through (the checker still catches those after publication); the extraction call is another model dependency; each regeneration adds about 1-2 minutes to a job the service runs synchronously |
| C6 | Reference list built by code; delete the two fallback blocks; dedupe; versioned link | `services/podcast_generation_service.py:2400-2480`, `:1436-1458`; description assembly at `:2613` area; `services/rss_service.py:354-411` reads the same text | 1 day | Existing validators (`content_fixes.py:635-679`) must still pass on the new format; a mistake here changes every future description and feed item |
| C7 | Fail early on fewer than 3 confirmed papers, with a clear message | `podcast_research_integrator.py:137-143`; `services/podcast_generation_service.py:2187` | 0.25 day | Topics now fail more often than today; see section 5 |
| C8 | Failure email: send to the requester too, with the reasons; initialise the subscriber address before the `try` so early failures can use it | `services/podcast_generation_service.py:2139-2154`, `:2850-2870`; `email_service.py:120` | 0.5 day | Today only `ERROR_NOTIFICATION_EMAIL` is notified (section 7.5); more recipients, more mail |
| C9 | Store the new fields; stop writing `real_citations` for new jobs | `services/podcast_generation_service.py:2199-2218`, episode record at `:2683-2756` | 0.25 day | Anything that reads `real_citations` (the two fallback blocks, admin pages) must be checked first |
| C10 | Tests: unit tests for matching and list building; a sandbox harness (section 6) | new test files and a script outside the service | 1 day | none to production |
| | **Total** | | **about 7-9 days** | |

Build order: C1, C2, C3 (the pipeline stops producing unconfirmed text) then C4, C7 (the generator) then C5, C6, C8, C9 (the check and the list), with C10 alongside. The sandbox test runs after C5.

---

## 5. How many topics might now fail

| Failure source | What I know | What I do not |
|---|---|---|
| Fewer than 3 confirmed papers (R4) | Of 32 past jobs that stored their sources, **0** had fewer than 3 with a registry identifier (min 3; 28 of them had 10). Sources were PubMed 134, arXiv 149, Zenodo 24 (all with DOIs); no YouTube or news in the stored top 10. With 32 jobs and no failures, the 95% upper bound on the failure rate is about 9-11% | Whether every identifier would pass step A (existence and title match); 35 older jobs stored no sources; topics with few papers (new or niche) may be underrepresented in what was generated |
| Registry unreachable | would fail with a different message and a retry | frequency |
| Named-work check still failing after 2 regenerations | In the baseline, the extractor found a named work with no matched source in 8 of 20 episodes (roster A), 14 of 20 (roster B); not all are real (items 7 and 80 were attribution failures), so the true old-generator rate is lower; Gary confirmed 8 genuine cases in his 60 sampled flags | the rate with the new prompt; the sandbox test measures first-attempt hits and final failures |
| Paper requests with a wrong DOI | fail with a clear message | frequency |

Planning figure for review: expect **a few percent of topics to fail honestly**, and **a larger share to need one regeneration**.
The sandbox test replaces this with a measurement; I recommend a go/no-go bar there (section 6.3).

---

## 6. Test plan (nothing published)

### 6.1 Set-up
- **Topics:** 10 of the 20 baseline topics, including the 5 episodes that had no reference list, the episodes with named-but-missing
  papers (from the judged items) and at least 2 topics with few papers. The topic text comes from the job record or title.
- **Harness:** a local script (not the service) that imports the changed research and generation functions from the branch
  and runs: research phase, step A, generation, the check with up to 2 regenerations, list building. **No audio, no
  transcript, no GCS write, no Firestore write, no email, no feed.** Output goes to local files in the same record format
  as the evaluation. Provider keys are read from Secret Manager into memory as before.
- **Adopted checker:** the 2026-10-08 configuration (roster A; script-alone pass on roster B's models for sourced claims,
  all three must agree; primary flag shows the nearest reference lines; reference-title check against the cited version).

### 6.2 Comparison with the baseline
| Measure | Baseline (old generator, 20 episodes) | New generator (10 topics) | Pass bar |
|---|---|---|---|
| Citation integrity (reference lines resolving to a stable identifier) | 82% (102 of 124) | measured the same way | at least 95% (the NSF target); expected near 100% by construction, so the real test is whether the list is complete |
| Papers named in the script but missing from the references | 24 of 61 attribution claims unmatched (A), in 8 of 20 episodes; 8 confirmed real in the judged sample | counted by the checker, after the check | **0** in published-candidate scripts; first-attempt hit rate reported separately |
| Claims with no matched source (primary flag rate) | 35% of checkable claims (154 of 443, A) | same measure | not higher than baseline; expected to stay similar until fix 3 |
| Episodes with no reference list | 5 of 20 | | 0 |
| Duplicate references | 1 in 124 lines | | 0 |
| Topics failing (insufficient confirmed papers, or naming failures) | not applicable | counted by reason | at most 1 of 10; more means rethinking before any deploy |
| Regenerations needed | not applicable | counted | reported, no bar |
| False positives of the naming check | not applicable | **Gary spot-checks every flagged violation (expected 10-20 items, about 20 minutes)** | no more than 1 in 5 violations a false alarm |

Also reported: runtime per topic (to see whether the 600 s content timeout and 300 s research timeout still hold), and the number
of papers dropped at step A and why.

### 6.3 Go/no-go
Proceed to a gated deploy of C1-C9 only if the pass bars hold. If the naming check's false-positive rate is too high, tune the
extraction prompt and re-run on the same topics (cached research makes re-runs cheap) before concluding anything.

### 6.4 Cost (estimates; prices as in the merged proposal, section 7, fetched 2026-10-06)
| Item per topic | Estimate |
|---|---|
| Research-phase analyses (about 13 Gemini calls, flash class) | $0.02-0.04 |
| Generation (`gemini-2.5-flash`, about 8k tokens in, 3-4k out), first attempt | $0.01-0.03 |
| Up to 2 regenerations if the check fires | +$0.01-0.06 |
| Named-work extraction (roster A model) | $0.005 per attempt |
| Adopted checker (roster A $0.056 plus the roster B script-alone pass instead of A's, about $0.024 more) | about $0.08 |
| Registry lookups | free |
| **Per topic** | **about $0.15-0.25** |
| **10 topics** | **about $1.5-2.5; hard ceiling $4.00, stop and report if exceeded** |

The model used by the generator on the live service is `gemini-2.5-flash` with `gemini-2.5-pro` as a fallback
(`services/podcast_generation_service.py:1198-1215`; Vertex AI is switched off on the live API), so the harness should call the
same models. Generation prices come from the same Google pricing page; I have not run a generation to measure tokens, which is why
the generation line is a range.

---

## 7. Gated deploy path

### 7.1 Before any deploy
1. Design approved (this PR), then code on a branch with the unit tests (C10) and a draft PR for the code.
2. The sandbox test (section 6) run and its report accepted by Gary.
3. The `DEPLOY.md` procedure for `copernicus-podcast-api` (`cloud-run-backend/DEPLOY.md:9-85`): build from a clean checkout of the
   reviewed commit; read the image digest; deploy by digest with only `--image`, `--no-traffic` and `--tag`; diff the revision
   specs; smoke-test the tagged URL against the live one; **move traffic only after Gary approves**; check logs for severity
   `ERROR` on the new revision; keep the previous revision as the rollback; remove the tag when its hold ends (step 9).
4. A tagged URL is public, so the tag is short-lived and the revision is removed from traffic if anything looks wrong (rule 18).

### 7.2 What the smoke test adds for this change
The generation endpoint runs the whole job synchronously and publishes to `episodes`, so a smoke test must not submit a real
request to the live path. On the tagged revision, run only the checks `DEPLOY.md` already requires (health and a read-only
endpoint). There is no way to exercise generation on the tagged revision without publishing, so the check of record is the
sandbox run from the reviewed commit. After traffic moves, the first real episode is generated on a topic Gary chooses and is held
as `private` until he has read its script and reference list; only then is it made public.

### 7.3 Rollback
Move traffic back to the previous revision. New fields are additions; old episodes are untouched, so there is nothing to migrate back.

### 7.4 Order relative to other work
Independent of the notification-email setup except for the failure email (7.5); independent of the rewritten source-support prompt
and the next judging package; precedes fix 3.

### 7.5 Prerequisite: the failure email
- **Email only works after the app password is set up** (the proposal's section 13): without it both email functions return
  without sending (`email_service.py:51-53`, `:129-131`). Until then a failed job is visible only as `status: failed` and an error text in
  the job record.
- **One setting must be fixed first.** The failure email goes to `ERROR_NOTIFICATION_EMAIL`, which defaults to the environment
  variable `NOTIFICATION_EMAIL` when its own variable is unset (`config/constants.py:54`). Section 13 sets `NOTIFICATION_EMAIL` to
  the **sender** address; unless `ERROR_NOTIFICATION_EMAIL` is set explicitly in the same revision, failure emails would go to the sender.
  The revision must set `ERROR_NOTIFICATION_EMAIL` explicitly.
- **Requester notification** (decided 2026-10-06: subscribers receive their own failure emails) needs C8: the failure path today sends
  only to `ERROR_NOTIFICATION_EMAIL`.

---

## 8. Limits and open questions

**Limits**
- The new check cannot know whether a claim is **true**; it ensures that what the script names is real and listed. The evaluation's
  other defect, unsupported claims, was not found (0 of 20 flags), so this design does not address it.
- The `P` list contains only papers whose abstract was retrieved; a paper confirmed by Crossref with no abstract is allowed
  but marked `metadata_only`, and the generator is told it may name it but not describe its findings. (This is a judgment call;
  question 3.)
- Confirmation proves the paper **exists and matches the retrieved title**; it does not prove the retrieved paper is on topic. The
  baseline's off-topic references are a source-selection problem and out of scope here.
- The naming check depends on a model to find named works; deterministic matching removes judgment from the decision but not from the
  finding. Fix 3 removes it.
- Sandbox results come from 10 topics and one generation each; generation is non-deterministic, so rates have wide intervals.
- Costs are estimates; generation tokens were not measured.

**Questions for Gary**
1. References: only papers the script **names** (as specified), or also papers the generator was given but did not name, in a
   separate "also reviewed" list? (Recommend: named only.)
2. Remedy on a naming violation: regenerate with feedback, up to 2 times, then fail (recommended)?
3. Allow a confirmed paper with no abstract (`metadata_only`) onto the list, with a "do not describe findings" rule, or require an
   abstract (fewer topics qualify)?
4. Maximum papers on the list: 12 (8 shown to the generator today, plus a reserve)?
5. Go/no-go bars in 6.2: at most 1 of 10 topics failing, at most 1 in 5 naming violations a false alarm?
6. Test scope: 10 topics, ceiling $4?
7. Failure email: also to the requester (C8), and fix `ERROR_NOTIFICATION_EMAIL` explicitly in the same revision?
8. The first real episode after deploy held as private for your read-through (7.2)?

---

## 9. Build order summary
| Step | What | Needs |
|---|---|---|
| 1 | Approve this design; answer section 8 | Gary |
| 2 | Code C1-C9 and C10 on a branch, draft PR | approval of design |
| 3 | Sandbox test (6), report | the code; Gary approves the spend (about $2.5, ceiling $4) |
| 4 | Gmail app password and `ERROR_NOTIFICATION_EMAIL` (7.5) | Gary creates the password (proposal section 13) |
| 5 | Gated deploy, then the first held episode (7) | Gary approves traffic |
| 6 | Fix 3 (inline markers) design, building on the `P` numbers | after step 5 |
