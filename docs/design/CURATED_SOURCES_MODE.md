# Design: curated-sources mode for the podcast generator

**Status: PROPOSAL. Nothing here is built or deployed, and nothing in it is approved until Gary says so.** This pull request carries one file and no code. The first line of code is written only after Gary approves this design, and then as the separately reviewed pull requests in §9.

**Author:** Claude Code (Core lane), at Gary's request, 2026-10-29 · **Rules in force:** `governance/AGENT_ROLES.md` v2.9 · **Read with:** the current generation code (`cloud-run-backend/services/podcast_generation_service.py`, `podcast_research_integrator.py`, `paper_confirmation.py`, `relevance_gate.py`, `named_work_check.py`, `attribution_check.py`, `reference_sections.py`) and `docs/design/ENGINE_ONBOARDING_FORM.md` (same conventions: draft PRs, gated deploys, private-first). **Pinned source for the first series:** `github.com/openai/math` at commit `7ef5c0cc5ca4b0e072b7a050fca09ab24bc6fa3a`.

---

## 0. In one page

**What it is.** A second generation mode, admin-only, for public-channel episodes ("CopernicusAI · Frontiers of Science") built from **sources Gary chooses** instead of sources the engine discovers. The existing mode (registry-confirmed papers only, naming and attribution checks, relevance gate, three-paper minimum, code-built reference lists) is unchanged; the new mode reuses every one of those checks and adds the things a curated series needs: source classes with labels, per-result status taken from a pinned repository, a path for commentary that sites will not let us fetch, and a review step before anything reaches the feed.

**Decided by Gary (2026-10-29).** Sources can be chosen both ways: Gary pastes links, or names a topic, the engine proposes sources and Gary approves the final list. The ElevenLabs Pro plan's last month (Nov 7 to Dec 7) is the burst month, so the first episode should be possible by about Nov 10. The first series is OpenAI's mathematics release (§8), run order: overview, then ETH, then the rest.

**What I propose.**
1. **A frozen, approved source list is the input.** Generation never discovers anything in this mode; it reads the list Gary approved (§3). A list has a hash, the pinned commit, and every confirmation record.
2. **Four source classes** (§2): `peer_reviewed`, `preprint`, `company_release`, `commentary`. Each is labelled in the script, the description and the web page; the reference list is still built by code. **At least three confirmed non-commentary sources** per episode; commentary can support reactions and context, never a claim that a result is true.
3. **Each named result carries a status** taken from the pinned commit (§4): `has a Lean formalization` (never "verified"), `checked by experts` (only when a cited commentary source says so), `unverified`, or `withdrawn`. The withdrawal list is re-checked at publish time.
4. **Commentary** that cannot be fetched is supplied by Gary as pasted text or an excerpt, and the refused fetch is recorded as a marked limit (§5). Scripts paraphrase and attribute; a code check refuses verbatim runs.
5. **Corpus:** only manuscripts an episode uses are ingested, as `source_type: company_release` (§6).
6. **Publishing:** generate private, Gary reviews, then the existing gated publish (§7). The run record gains the TTS character count.
7. **Build:** eight pull requests (§9). **The smallest build that can make episode 1 is about 8 to 10 agent days** (C0, C1, C2, a reduced C3 and a paste-only C4), which puts the first episode at **about Nov 11 to 14**, not by Nov 10; §9.2 says exactly what is cut to get there. **There is no dependency on the onboarding build's PR 1**; the two compete only for the same agent's time (Q6).

**What is still open:** the questions in §10, each with a default that **stands unless Gary says otherwise**.

---

## 1. What this design rests on (read-only inspection, 2026-10-29)

### 1.1 The generation code today
| Fact | Where |
|---|---|
| Generation is started by `POST /generate-podcast` (and `-with-subscriber`, `-from-paper`), authorised by `authorize_generation`: the admin key (unmetered) or an allow-listed subscriber (metered). | `endpoints/podcast/routes.py:37`, `utils/auth.py:126` |
| A request carries `topic`, `category`, `duration`, `source_links`, `paper_*` fields, voices. `source_links` are processed by the research pipeline as hints, not as an approved list. | `models/podcast.py`, `research_pipeline.py:164` |
| The research stage is one function, `comprehensive_research_for_podcast`: discover, **confirm** (`confirm_sources`: a registry identifier is required; no identifier means the candidate is dropped as `no_identifier`; arXiv, PubMed, Crossref and DataCite are the registries), **relevance gate** (embedding similarity against the topic, threshold 0.25, Zenodo records never count toward the minimum), analyse, then fail closed on fewer than three confirmed papers. | `podcast_research_integrator.py:120-317`, `paper_confirmation.py:400`, `relevance_gate.py` |
| After the script is written: the **naming check** (every named work or author must match a confirmed paper; fails closed), the **attribution check** (a claim attributed to a paper is judged against that paper's abstract only; fails closed), word-count and notation checks, then references and further reading **built by code** (`code@2`) from registry records. | `named_work_check.py`, `attribution_check.py`, `reference_sections.py`, `podcast_generation_service.py:1896-2110` |
| A new episode is stored private: `submitted_to_rss=False`, media in the private bucket. Publishing is `POST /api/subscribers/podcasts/submit-to-rss` (the admin key is accepted), which promotes the files to the public bucket, verifies the copies and updates the feed, and demotes them again if the feed write fails. | `podcast_generation_service.py:2637`, `endpoints/subscriber/routes.py:~590-660`, `media_store.py` |
| Speakers are two named voices chosen by voice id (defaults Matilda and Adam); the names become the script's speaker labels. | `elevenlabs_voice_service.py:64-91`, `podcast_research_integrator.py:409-460` |
| **No TTS character count is recorded** anywhere in the job or episode record. | searched `characters`, `tts` in the service and the voice service |
| `ConfirmedPaper` has no class or label field and no notion of a pinned repository; `Dropped` reasons do not include a refused fetch. | `paper_confirmation.py:73-100` |
| The corpus is the `research_papers` collection (database `copernicusai`); a record's engine membership is `citations[].cited_project` (`glmp` or `atap`); ingest scripts live in `huggingface-space/scripts/acquire_papers/`; the post-ingest hooks (status publish, MASTER_TODO) run on the Jetson cron after the ingest job. There is no `source_type` field today. | `services/paper_resolver.py`, `researcher_cited_intake.py`, `SCOUT_ARCHITECTURE.md` |

### 1.2 The pinned repository (`openai/math` at `7ef5c0cc5`, read without cloning the working tree)
I fetched the repository's objects and read them directly (a normal checkout fails on Windows: the tree contains paths past the 260-character limit). Everything below is OpenAI's own statement, read at the pinned commit, not something I verified mathematically. Fetched 2026-10-29 (evening, US Eastern); `7ef5c0cc5` was the head of the default branch at that moment (merge of PR #3, 2026-10-26).

- **Size and layout:** 174,524 files. `README.md`, `CONTENTS.md` (the manuscript map, 641 KB), `history.md`, `overview.pdf` and `overview.tex`, `preprints/` (751 directories), `lean/`, `reasoning_traces/`. README: "721 manuscripts organized into 373 families", each family classified by discipline. The map lists exactly 721 manuscripts under 373 numbered families.
- **751 directories against 721 manuscripts:** the 30 not in the map are the **3 withdrawn manuscripts** and **27 older editions** of manuscripts that were revised (directory names end in the edition date).
- **Withdrawals:** `history.md` (October 7, 2026) withdraws three manuscripts: *Algebraicity of Weil classes on split abelian eightfolds*, *Algebraicity of Kuga-Satake Correspondences for K3 Surfaces* and *The rational Hodge conjecture for products of K3 surfaces*. Each directory holds a README that starts "Withdrawal notice" and explains the gap. **The withdrawn manuscripts are not in the manuscript map, so they have no family number at the pinned commit.** The withdrawal list therefore cannot be read from `CONTENTS.md`; it comes from the notices and `history.md`.
- **Lean:** `lean/formalization.yaml` (version v0.4) has `sources:` with **176** manuscript paths and `status.main_results` with **208** entries; its own metadata says `status.scope: "Partial progress."`, `review.status: unchecked` and `automation.methods: agent`. `history.md` says "300 / 719 = ~42%" of top-line results formalized; **that figure does not match the catalogue's 176 sources, and I have not reconciled them** (§10, Q9). The `status.main_results` entries name a Comparator configuration and a declaration, not a manuscript, so the link from a manuscript to its formalization is the `sources:` entry.
- **Provenance statements in the README:** produced by "an unnamed internal OpenAI model"; "Some of the unformalized results could have issues"; the manuscripts are "best understood as a form of raw research data, rather than polished academic papers"; abridged reasoning summaries exist for ten results (007, 017, 087, 102, 159, 197, 221, 271, 287, 362).
- **Quanta's report** that some formalizations prove weaker statements than the papers claim comes from Gary's brief; **I have not checked it**, and the design treats it only as a reason for the wording rule in §4.

---

## 2. Source classes

Every source in an approved list has exactly one class, assigned by code from evidence and approved by Gary. The class is carried through the script, the description and the web page.

| Class | Evidence required | Confirmed against | What an episode may say |
|---|---|---|---|
| `peer_reviewed` | A DOI or PMID whose registry record is a journal article | Crossref (record type `journal-article`) or PubMed; the journal version, with journal, year and DOI from the record | What the paper reports, as the paper's own claim |
| `preprint` | An arXiv id **with its version**, a bioRxiv or medRxiv DOI, or a Zenodo record | arXiv (version recorded), Crossref (record type `posted-content`) or DataCite; a Zenodo record counts only if DataCite's resource type is a text or preprint, not data or software | What the preprint reports, labelled as not peer reviewed |
| `company_release` | A manuscript that is in **no registry**. For the first series: `openai/math`, by family number or path, **at a recorded commit** | The company's own page or repository at the pinned commit: the file exists at that path and commit; its title and abstract are taken from the repository's own map at that commit; the blob identifier is recorded | What the company says the manuscript shows. Every episode naming one carries the label. Never "proved", never "verified" |
| `commentary` | A URL or a pasted text: journalism, a blog, a statement, a social post | Retrieval only: the outlet, author, date and URL, and that it was fetched or pasted (§5). "Confirmed" means retrieved, **not true** | Reactions and context: "X reported", "Y said". Never the basis for a claim that a result is true |

**Labels (wording is Gary's to approve, Q10; these are the defaults).** In the script, at the first mention of a work: "a preprint", "a company release that has not been peer reviewed", "reporting by [outlet]". In the description: a short **Sources** section built by code, one subsection per class, each line carrying its class and its registry or commit identifier. On the episode page: a badge per class beside each reference. The model never writes these; the code does (the existing `code@2` rule, extended to `code@3`).

### 2.1 How the existing checks extend
- **Confirmed list.** Today it holds registry records only. In this mode it holds one record per approved source, `ConfirmedPaper` extended with `source_class`, `pin` (repository, commit, path, blob id; empty for registry sources) and `evidence` (below). Registry sources keep their existing confirmation unchanged; `company_release` and `commentary` get their own confirmation records.
- **Naming check (fix 1).** Unchanged in logic. Because the confirmed list now includes the commentary entries (outlet or journalist as "authors", date, title words) and the company-release manuscripts (title words, "OpenAI" as author), a script that says "Quanta reported" or "OpenAI's manuscript on the Exponential Time Hypothesis" matches a list entry, and a mention that matches nothing is still a violation. A work in none of the classes cannot be named.
- **Attribution check.** Today a claim attributed to a paper is judged against that paper's abstract. Its **evidence text** is: the abstract (registry sources), the abstract from the repository's map at the pinned commit (`company_release`), and the **excerpt Gary pasted or the fetched summary window** (`commentary`). A claim attributed to commentary is judged against that excerpt only. A claim the evidence does not support is a reason to regenerate; after the allowed regenerations the episode fails, as today.
- **Three-source minimum.** I propose **at least three confirmed non-commentary sources** per episode. Commentary never counts toward the three, so an episode built on news coverage alone fails closed. Company-release manuscripts count, one each. The existing rule that three must come from outside Zenodo stays for engine-proposed lists only: in a Gary-chosen list the choice is his, and the class rules above already prevent a Zenodo dataset from standing in for a paper. (Q1.)
- **Relevance gate and Gary-pasted items.** I propose **report only** for items Gary pasted or named, and **block** (drop) for items the engine proposed. The score is computed for every item and **shown to Gary on the approval screen before any generation**, so a low score on something he pasted is a warning at the point where he can act on it, not a surprise after the episode exists. A Gary-pasted item is never silently dropped. Engine-proposed items below the threshold are dropped exactly as today. (Q2.)

---

## 3. Source intake

### 3.1 Where it sits
A new admin-only router, `endpoints/curated/routes.py`, beside `endpoints/podcast/routes.py`. Every route requires the admin key header (`X-Admin-API-Key`), with no subscriber path and no query-string fallback. It creates and freezes a **source list**; a new generation entry point, `POST /api/admin/curated/generate`, takes a list id instead of a topic and runs a sibling of `run_podcast_generation_job` (`run_curated_generation_job`) that **replaces only the research stage**: it builds the same `PodcastResearchContext` from the frozen list, then reuses `_generate_checked_content`, the naming and attribution checks, the reference builder and the audio steps unchanged. The existing routes and the existing mode are untouched, so a regression in one cannot reach the other.

### 3.2 Intake from Gary
Gary pastes any mix of: URLs; arXiv ids; DOIs; PMIDs; `openai/math` manuscripts given **by family number or by path**, at a recorded commit. The engine classifies each item by code and shows the proposal:

| Item | Proposed class | Confirmation |
|---|---|---|
| arXiv id or arxiv.org URL | `preprint` | existing arXiv confirmation; version recorded |
| DOI or doi.org URL | `peer_reviewed` or `preprint`, from the Crossref or DataCite record type | existing Crossref and DataCite confirmation |
| PMID or PubMed URL | `peer_reviewed` | existing PubMed confirmation |
| `github.com/openai/math` path, or "family 378" | `company_release` | repository confirmation at the pinned commit (§3.4) |
| any other URL | `commentary` | retrieval (§5) |

Gary can **override a proposed class** before approval; he cannot override a failed confirmation (a DOI no registry knows is refused, with the reason, exactly as `confirm_sources` reports it today).

### 3.3 Topic-proposed intake
Gary names a topic. The engine runs the **existing** discovery, confirmation and relevance gate (so every proposal is registry-confirmed and on-topic) and returns candidates ranked, each with its class, abstract and score. Gary approves or rejects each; nothing is generated until he approves the final list. **The engine proposes registry papers only.** It does not search for commentary or for company releases: model-driven web search for press coverage is unreliable, and a wrong "source" there is exactly the failure the system exists to prevent, so those two classes enter only by Gary's hand. A list may mix both kinds, and each item records `added_by` (`gary` or `engine`).

### 3.4 Intake from `openai/math`
- **Index at a pin.** A loader reads `CONTENTS.md` from `raw.githubusercontent.com/openai/math/<commit>/CONTENTS.md` (one 641 KB file) and builds a family index: number, title, description, and each manuscript's directory, title and abstract. The backend never clones the repository (174,524 files) and fetches individual files by commit only.
- **Pin.** The commit is recorded when the list is created (default `7ef5c0cc5ca4b0e072b7a050fca09ab24bc6fa3a`) and is part of the list's hash. Changing it re-runs every confirmation.
- **Confirmation of a manuscript** = at the pinned commit: the directory exists, it is one of the standing manuscripts in the map (an older edition or a withdrawn manuscript is refused as a source for a *standing* claim; see §4), its title and abstract come from the map, and its blob identifiers (`paper.pdf` or equivalent, `README.md`) are recorded. If two manuscripts in a family share a title (family 003 has two *The Quasi-Riemann Hypothesis* manuscripts, September 30 and October 5), the list **must name the directory**, and a bare family number that is ambiguous is refused (Q11).
- **A family number is shorthand for the family's standing manuscripts**, listed back to Gary for approval; he can strike individual manuscripts.
- **Untrusted text.** Everything fetched from the repository, a registry or a website is data. It reaches the model only inside clearly delimited blocks, the checks run on the output afterwards, and no fetched text is ever executed or treated as an instruction (the repository is written by a third party and can contain anything).

### 3.5 What a list stores
Firestore `curated_source_lists/{list_id}` (database `copernicusai`, admin-only; no public read):
`title`, `created_at`, `created_by` (admin), `status` (`draft`, `approved`, `used`), `pin` (`repo`, `commit`), `items[]` and `list_hash` (sha256 over the approved items and the pin, set at approval, never edited afterwards; a change is a new list). Each item: `item_id`, `class`, `added_by`, `identifiers`, `title`, `authors`, `year`, `venue`, `evidence_text` (abstract or excerpt; commentary excerpts are **private**), `confirmation` (the registry record or the repository confirmation, with `confirmed_at`), `relevance_score`, `result_status` (§4), `limits[]` (§5), `approved` (bool).

### 3.6 Safeguards on fetching
Gary-pasted URLs are fetched by the backend, so every fetch goes through one function that allows `http` and `https` only, refuses addresses in private, loopback and link-local ranges (checked after DNS resolution and on every redirect), caps the size (2 MB) and time (15 s), sends an honest user-agent, follows `robots.txt` (§5), and never sends a credential. Admin-only access reduces the exposure; it does not replace these.

---

## 4. Result status

Each **named result** (a manuscript, for the first series) gets exactly one status, computed by code at list approval from the pinned commit and **recomputed at publish time** (§4.3). The script receives the statuses as constraints, not as material to rephrase.

| Status | Taken from | Allowed wording | Never |
|---|---|---|---|
| `has_lean_formalization` | the manuscript's directory appears in `lean/formalization.yaml` `sources:` at the pinned commit | "OpenAI's catalogue lists a Lean formalization for this manuscript. The catalogue's own review status is 'unchecked'." | "verified", "proved", "machine-checked", "formally verified", "confirmed correct" |
| `checked_by_experts` | **only** when an approved commentary source in this episode says so; the item records which | "[Outlet] reported that [named people or group] checked it", always attributed | any claim the episode makes in its own voice |
| `unverified` | the default | "OpenAI's own manuscript, not independently checked" (or the plain "unverified") | anything that implies review |
| `withdrawn` | a "Withdrawal notice" README in the manuscript's `preprints/` directory, or a withdrawal in `history.md` | "withdrawn by OpenAI on [date from the notice], because [the notice's stated reason, paraphrased]" | presenting it as standing, citing it for a claim of fact, or listing it as a source for a standing result |

**Why "has a Lean formalization" and never "verified".** Gary's brief reports that Quanta found some formalizations prove weaker statements than the papers claim; I have not checked that report. The catalogue itself says `scope: "Partial progress."`, `review.status: unchecked`, and `automation.methods: agent`. A listed formalization shows that a Lean file exists; it does not show that the file states the paper's theorem. The wording rule holds either way.

**Precedence:** `withdrawn` over everything; then `checked_by_experts` (which needs a named, attributed source); then `has_lean_formalization`; then `unverified`. A manuscript can have a Lean entry and be listed as `unverified` for the expert question at the same time; the statement carries both facts ("has a Lean formalization; no expert check reported").

### 4.1 Checks added
- **Status wording check (code, fails the episode).** Scans the script for the forbidden words above within a window of a named result, and for any named `withdrawn` manuscript whose sentence does not say "withdrawn". Deterministic; it extends the naming check's mention matching rather than adding a model call.
- **Status constraints in the prompt.** For each named result: its status and the exact allowed wording. The prompt tells the model it may not state any other status.
- **Family versus manuscript.** A status belongs to a manuscript, not a family (family 240: the CH-obstruction manuscript has a Lean entry; *Eventual Categoricity for Abstract Elementary Classes* does not). The script may say "has a Lean formalization" only of the manuscript that has the entry.

### 4.2 The withdrawn manuscripts as content
A withdrawal is a story the series may tell (episode 1, and the number-theory episode). The three withdrawn manuscripts have no family number, so the list names them by directory. They enter the list with class `company_release` and status `withdrawn`; the check above makes any appearance as a standing result a failure, and the code-built Sources section prints them under a "Withdrawn" heading with the notice's date.

### 4.3 Re-check at publish time
Before the publish call, an attended step fetches `history.md` and the withdrawal notices at the **current head** of the repository, not the pin, and compares with the recorded statuses. **Any difference blocks publication and is shown to Gary** (a new withdrawal, or a Lean entry added or removed). If the difference appears after publication, it goes through the existing severity ladder (rule 16: a correction note, a prominent correction note, or withdrawal; Gary is the only approver at every level). A withdrawn paper is never presented as standing: if the pin is stale, the pin moves and the episode is regenerated or blocked, never published as written.

---

## 5. Commentary retrieval

Some sites refuse automated reading (Scientific American's `robots.txt` rule; a Nature fetch failure was reported to me).

1. **Fetch politely.** For each commentary URL the retrieval function reads `robots.txt` first and fetches only what it allows, within the limits in §3.6. Success records outlet, author, date, URL, retrieval time and a content hash.
2. **A refusal is a recorded limit, not an error.** Reasons: `robots_disallow`, `http_error` (status), `timeout`, `blocked`, `paywall`. The item is kept, marked `limits: [{type: fetch_refused, reason, at}]`, and cannot be used as evidence until Gary supplies text.
3. **Fallback: Gary pastes the text or an excerpt.** An admin form (or an authenticated request) attaches pasted text to the item, which then has `mode: pasted`. The pasted text is stored in the private store only (never in a public bucket, never in a public repository, never ingested into the corpus) with a content hash.
4. **A limit is shown to the listener.** For any commentary item that was pasted after a refused fetch, the code-built Sources section carries one line: "The publisher's site does not permit automated reading; this item was summarized from an excerpt supplied by the producer." The episode page repeats it. Nothing is hidden.
5. **Scripts paraphrase and attribute; they never reproduce an article's text.** Enforced three ways: the prompt says so; a **verbatim-run check** (code, fails the episode) refuses any run of **eight or more consecutive words** (normalised for case and punctuation) shared between the script and any pasted or fetched text, except a quotation Gary marked on the item as approved; and the attribution check judges attributed claims against the excerpt only. The excerpt is the evidence text; the full article is never stored in a record anyone but Gary can read. (Q3 for the eight-word limit.)
6. **What commentary may do.** Context, reactions and reception ("Quanta reported that some formalizations prove weaker statements", only if that is in an approved source), always with the outlet's name. The attribution check and the status rules keep it from becoming the basis for "this is true".

---

## 6. Corpus

Ingest **only the manuscripts an episode actually uses**, not the 721. After an episode is approved, an attended step writes one `research_papers` record per used `company_release` manuscript:

- `source_type: "company_release"` (new field; absent on every existing record), `source: "openai_math"`, `repo: "github.com/openai/math"`, `commit`, `path`, `family`, `title`, `abstract` (from the map at the pin), `result_status` as recorded, no DOI, `acquisition_channel: "curated_sources"`.
- Engine tag: `citations[].cited_project: "atap"` with `cited_by: "curated-sources"`, `cited_date`, `cited_context` naming the episode, using the same merge function the intake scripts use (`merge_citation`) so a second episode that uses the same manuscript adds a citation, not a duplicate. Document id: a stable slug of repo, commit-independent path and family, so a re-pinned manuscript updates the record instead of forking it.
- **Isolation by construction.** `confirm_sources` drops candidates with no registry identifier, so a `company_release` record can never be picked up as a "confirmed paper" by the ordinary mode; the field `source_type` also lets search results and the Knowledge Engine view label these records as not peer reviewed.
- **Embedding and hooks.** The record is embedded through the existing path; the **post-ingest hooks** (status publish, MASTER_TODO) run from the Jetson cron after the next ingest, so the status counts move on that schedule, not instantly. The status JSON's "papers in corpus" counts will include these records; I propose the status page footnote them as "includes N company releases" so the count is not read as registry-confirmed literature (Q12).
- Commentary excerpts, fetch logs and pasted text are **never** ingested.

---

## 7. Publishing

1. **Generate private.** Every episode from this mode is created with `submitted_to_rss=False` and its media in the private bucket, as today. Nothing in this mode can publish; `run_curated_generation_job` has no publish step.
2. **Review pack.** The run produces a record Gary reviews before anything else: the script; the source table (class, identifier or commit, status, limits, relevance score); the check results (naming, attribution, status wording, verbatim run, relevance report, minimum); the reference sections as built; and the audio through a signed link (the admin media-links route already exists; its links last up to seven days).
3. **Publish only on Gary's go.** Then the existing gated call (`submit-to-rss` with the admin key: promote, verify copies, update the feed, demote on failure), preceded by rule 16's backup of the feed before any feed write and by the §4.3 re-check. Each episode is its own go.
4. **Corrections.** After publication, a problem is handled by the severity ladder, never by silent repair (rule 16).
5. **TTS character count.** For every generation (both modes) the job and episode record gain `tts_characters` (the sum of the text actually sent to ElevenLabs, per voice and in total) and `tts_segments`. Counting happens where segments are synthesised (`synthesize_script_segments`). This lands first (C0) because it is useful today and costs almost nothing.
6. **Budget.** The plan's credit allowance and its exact unit cost per character are **not checked by me**; Gary reads them off the account page. With the count recorded, the run record shows each episode's cost, and a **per-episode warning threshold** set by Gary (Q7) turns an unexpectedly long script into a visible decision before the audio step runs.
7. **Voices and the channel.** The channel has no host name. The existing mode turns two voice names into speaker labels. In this mode the labels are internal (`HOST`, `EXPERT`), the prompt forbids any spoken personal name, and a code check refuses a script that speaks the voices' names (Q4). Audio only.

---

## 8. Appendix: the first series (OpenAI's mathematics release)

Gary's decisions: episode 1 is an overview; episodes 2 to 7 are one per area; episodes 8 to 13 are deep dives; **run order: the overview, then ETH, then the rest.** I checked every family number he gave against the pinned commit's manuscript map. **All 20 distinct family numbers exist and their titles match his labels** (the deep dives repeat six of them); nothing in the numbering is wrong. The things to know are flagged in §8.3.

### 8.1 Episodes
| Ep | Subject | Families (title at the pin) | Manuscripts at the pin | With a Lean entry |
|---|---|---|---|---|
| 1 | Overview: what the release is, how it was produced, the withdrawals, the Lean question, the reception | the README, `history.md`, `overview.pdf`; the three withdrawal notices; the ten reasoning summaries; commentary Gary supplies | n/a (the release itself) | see ep 2 to 7 |
| 2 | Number theory and arithmetic geometry | 003 *The quasi-Riemann hypothesis*; 002 *The full BSD formula from low Selmer corank*; 032 *The rational Hodge conjecture for CM abelian varieties*; plus the three **withdrawn** manuscripts (no family number) | 3 + 3 + 5 = 11 standing, 3 withdrawn | 003: 2 of 3; 002: 0 of 3; 032: 1 of 5 |
| 3 | Theoretical computer science | 378 *Disproof of the Exponential Time Hypothesis*; 102 *The Unique Games Conjecture and optimal approximation thresholds*; 107 *Matrix multiplication with exponent at most 9/4*; 109 *Integer multiplication below n log n* | 1 + 5 + 3 + 1 = 10 | 378: 1 of 1; 102: 3 of 5; 107: 3 of 3; 109: 0 of 1 |
| 4 | Combinatorics and discrete geometry | 157 *Graph coloring, clique minors, and Colin de Verdière invariants*; 087 *The Mahler conjectures, functional inequalities and polar-product symplectic width* | 3 + 3 = 6 | 157: 1 of 3; 087: 2 of 3 |
| 5 | Analysis and PDE | 376 *Universal computation in forced Navier–Stokes flows*; 079 *Local smoothing for the Euclidean wave equation*; 074 *Kakeya in three and four dimensions*; 362 *Global smoothness for relativistic Vlasov–Maxwell* | 9 + 2 + 2 + 1 = 14 | 376: 0 of 9; 079: 1 of 2; 074: 0 of 2; 362: 1 of 1 |
| 6 | Mathematical physics and probability | 221 *The Mézard–Parisi formula for diluted spin glasses*; 271 *Bloch's law, its lattice correction, and the spherical magnetization law* | 1 + 4 = 5 | 221: 0 of 1; 271: 0 of 4 |
| 7 | Algebra, logic, operator algebras, topology and geometry | 287 *Isomorphism of the free group factors*; 196 *A counterexample to Kaplansky's zero-divisor conjecture*; 304 *The Hilbert–Smith conjecture in every dimension*; 240 *Shelah's eventual categoricity and the prescribed-threshold obstruction*; 340 *A counterexample to the nearby Lagrangian conjecture* | 1 + 1 + 1 + 2 + 1 = 6 | 287: 0 of 1; 196: 1 of 1; 304: 0 of 1; 240: 1 of 2; 340: 0 of 1 |
| 8 | Deep dive: quasi-Riemann hypothesis | 003 | 3 | 2 of 3 |
| 9 | Deep dive: ETH | 378 | 1 | 1 of 1 |
| 10 | Deep dive: Unique Games | 102 | 5 | 3 of 5 |
| 11 | Deep dive: Hadwiger | 157 (the manuscript *A counterexample to Hadwiger's conjecture*) | 3 | 1 of 3 (that manuscript) |
| 12 | Deep dive: free group factors | 287 (it has a reasoning summary) | 1 | 0 of 1 |
| 13 | Deep dive: Shelah's categoricity conjecture | 240 | 2 | 1 of 2 (the CH-obstruction manuscript only) |

"With a Lean entry" means the manuscript's directory appears in `lean/formalization.yaml` `sources:` at the pinned commit. It is a catalogue fact (§4), not a statement that the result is verified.

### 8.2 Run order
**1 (overview), then ETH, then the rest.** The ETH deep dive carries the number 9 in Gary's list but runs second; I suggest it runs **before** the theoretical computer science area episode (3), since that episode then points back to it. After ETH, the order of the remaining eleven is not set by anything in the design; I propose areas before dives, in Gary's order, with the deep dive for each area following its area episode where the dependency reads naturally (Q13). Thirteen episodes at about three a week fits the burst month (Nov 7 to Dec 7, about 4.3 weeks) with little slack; the character budget (§7.6) is the binding constraint, not the calendar.

### 8.3 Flags from checking the numbers against the pin
1. **The withdrawn "Weil-class papers" have no family number.** The three withdrawn manuscripts are not in the map at all; they live in `preprints/` with notices. The standing manuscript *Weil classes and Hodge classes on abelian powers* (October 6) is in family 032, along with a manuscript on Kuga–Satake correspondences that is a *conditional* reduction. The series must not blur standing and withdrawn manuscripts that share vocabulary.
2. **Family 003 has two manuscripts with the same title** (*The Quasi-Riemann Hypothesis*, dated September 30 and October 5). Only the September 30 one has a Lean entry. Whichever the episode discusses must be named by directory (§3.4).
3. **Status is per manuscript, and varies inside a family.** 240's Lean entry covers the CH-obstruction manuscript, not *Eventual Categoricity for Abstract Elementary Classes*; 157's covers the Hadwiger counterexample, not the other two manuscripts; 032's covers the CM-abelian-varieties manuscript only. The status table in each episode's run record is per manuscript.
4. **ETH (378) is a single manuscript with a Lean entry**, dated October 25, and `history.md` says an independent working group (named there) "will examine and explain the proof". "Checked by experts" would be false unless a commentary source in the episode reports it; the wording rule in §4 handles this.
5. **Several areas have no Lean entry at all** (002, 109, 376, 074, 221, 271, 287, 304, 340), so those episodes' statuses are `unverified` unless commentary says otherwise.
6. **Count mismatches inside the repository's own text.** `history.md` says "300 / 719 = ~42%" formalized; the catalogue lists 176 manuscripts with a Lean source and 208 main-result entries. The README says 721 manuscripts (`history.md`'s 719 is presumably the count before the two October 26 additions). The withdrawal notice for the Weil-classes paper says "Withdrawn on October 6, 2026"; `history.md` records the withdrawals under October 7. An episode must not quote the percentage without attribution ("OpenAI says") and must not combine it with the catalogue.
7. **The pin is the head as of 2026-10-29.** If the repository moves before episode 1, the pin moves deliberately and every status is recomputed (§3.4, §4.3).

---

## 9. Build plan

Each item is a separate pull request, reviewed and gated on its own (rules 15, 18, 19, 20). Backend deploys follow `cloud-run-backend/DEPLOY.md`: a clean worktree of the reviewed commit, deploy by digest with no traffic, diff the revision specs, a smoke test, traffic only when Gary approves, the previous revision kept. A merge of the static pages is a production deploy of the public site and is treated as publishing. The new routes ship dark behind the admin key, so merging and deploying changes nothing a listener can reach until an episode is published.

| PR | Contents | Effort | Tests | In the smallest build |
|---|---|---|---|---|
| **C0** | Record `tts_characters` and `tts_segments` in the job and episode record, both modes; per-episode warning threshold hook | 0.5–1 day | counts equal the characters sent in a recorded fixture; unchanged output | yes |
| **C1** | Source lists and classes: the Firestore model, classification by code, class assignment from registry record types, the admin routes (create, add, override class, approve, freeze with hash), the repository confirmation at a pin, the minimum rule (three non-commentary), `ConfirmedPaper` extended | 2.5–3.5 days | each class confirmed or refused as specified; ambiguous family refused; list hash changes on any edit; admin key required; fetch guards (§3.6) | yes (company-release confirmation for `openai/math` only) |
| **C2** | The curated generation mode: `run_curated_generation_job` with the frozen-list research stage, class wording in prompt and code-built Sources (`code@3`), no spoken names, status constraints and the status wording check, the verbatim-run check, private by default, the review-pack record | 3–4 days | the failure cases: a commentary-only list fails; a withdrawn manuscript presented as standing fails; "verified" fails; a verbatim run fails; a spoken voice name fails; every existing check still runs; the ordinary mode is unchanged | yes |
| **C3** | Result status from the pin: the repository index at a pin (`CONTENTS.md`), the Lean flag from `formalization.yaml`, withdrawal notices and `history.md`, and the publish-time re-check against the current head | 1.5–2 days | each status from fixtures of the real files; precedence; a changed head blocks | reduced: pin, Lean flag and withdrawal notices; the publish-time re-check is run by hand by the agent on the day |
| **C4** | Commentary retrieval: the robots-aware, address-guarded fetch, refusal recording, the paste fallback and its private store, the visible limit line | 1.5–2 days | a refusal is recorded and shown; pasted text stays private; a guard refuses a private-network address and a redirect into one | reduced: **paste only**, no automated fetch |
| **C5** | Publishing surface: the review pack as an admin page, the class badges and limit lines on the episode page (a static-site change, rule 18) | 1.5–2 days | the page renders every class and limit; no script injection from stored text | no (labels already appear in the code-built description; Gary reviews from the record and the audio) |
| **C6** | Topic-proposed intake (§3.3): proposals through the existing discovery, with approval | 2–3 days | proposals are registry-confirmed and gated; nothing is generated before approval | no |
| **C7** | Corpus ingest of used manuscripts (§6) and the status page footnote | 1–1.5 days | one record per used manuscript, idempotent; the ordinary mode still refuses them | no |

### 9.1 Totals
Everything: about **13–19 agent days**. Smallest build for episode 1 (C0, C1, C2, reduced C3, paste-only C4): about **8–10 agent days**, plus Gary's review time on four pull requests and two attended backend deploys (two half-days).

### 9.2 What the smallest build leaves out, and the date
Left for later: the review-pack page and the page badges (C5), topic-proposed intake (C6), corpus ingest (C7), automated commentary fetching, and the automatic publish-time re-check. For episode 1 Gary supplies the commentary text by paste, the agent runs the re-check by hand on the day, and Gary reviews the script and listens through the existing signed link. **Realistic first episode: Nov 11 to 14.** The 8 to 10 agent days fit in the 11 calendar days to Nov 10 only if each pull request is reviewed and its deploy attended within about a day; each day of review delay moves the date a day, and a failed first generation (the checks fail closed by design) costs a day for the fix. The one further cut that saves time is C4 entirely (Gary names the commentary points himself and the first episode carries no commentary source), at the cost of the reception section in the overview; it saves about a day, so it moves the estimate to about Nov 10 to 13 and does not guarantee Nov 10.

### 9.3 Dependency on the onboarding build
**None.** The curated mode uses an admin-only router and its own Firestore collection; the private-episode access, per-episode publish, quota route and invitations that the onboarding build's PR 1 to PR 3 add are all subscriber-facing, and the admin path this mode needs (generate private, listen through admin media links, publish through `submit-to-rss`) already exists. The two builds touch different files; the only conflict is the same agent's time (Q6). One shared item: the admin route fix that moves an address out of a URL goes into the onboarding PR 1, as decided, and does not touch this work.

---

## 10. Questions for Gary

Each carries a default that **stands unless Gary says otherwise**.

1. **Minimum sources.** At least three confirmed non-commentary sources; company-release manuscripts count; commentary never counts; no per-episode override. **Default:** as stated.
2. **Relevance gate.** Report only for items Gary pasted or named (the score is shown on the approval screen); drop for engine-proposed items. **Default:** as stated.
3. **Verbatim limit.** No run of eight or more consecutive words from any pasted or fetched text appears in a script, except a quotation Gary marks approved. **Default:** eight words, no exceptions unless marked.
4. **Spoken names.** Speaker labels are internal (`HOST`, `EXPERT`); no personal name is spoken; a code check enforces it. **Default:** as stated.
5. **Evidence beyond the abstract for deep dives.** Abstract-only in v1 (the attribution check judges abstract-level claims). Later, add the first 6,000 characters of a company-release manuscript's introduction from its pinned TeX source as evidence for deep dives. **Default:** abstract only for the first episodes; revisit before the deep dives.
6. **Sequencing against the onboarding build.** Curated-sources first through the first episode, then PR 1 of the onboarding build resumes. **Default:** curated first.
7. **TTS budget.** Record the count and set a per-episode warning threshold that Gary chooses after reading the plan's allowance off the account page; no automatic cap. **Default:** record only until Gary names a threshold.
8. **Publish-time re-check.** A difference between the recorded statuses and the repository's current head blocks publication and goes to Gary. **Default:** block.
9. **The formalization percentage.** Episodes quote the repository's "300 / 719" only as "OpenAI says" and never alongside the catalogue's 176; the run record stores the catalogue's count. **Default:** as stated.
10. **Label wording.** "a preprint", "a company release that has not been peer reviewed", "reporting by [outlet]", and the status sentences in §4, as the default text. **Default:** as written here.
11. **Ambiguous manuscripts.** A bare family number whose manuscripts share a title is refused; Gary names the directory. **Default:** refused.
12. **Status page count.** The corpus count footnotes "includes N company releases". **Default:** yes, when C7 ships.
13. **Order after ETH.** Overview, ETH deep dive, then the area episodes in Gary's order with each deep dive after its area episode. **Default:** as stated.
14. **Robots rules.** The fetch obeys `robots.txt`; a disallowed site is never fetched around. **Default:** obey.

---

## 11. Not decided here, not built here

This document builds nothing, deploys nothing and changes no engine. It proposes. The pull request that carries it contains this file and no other change.
