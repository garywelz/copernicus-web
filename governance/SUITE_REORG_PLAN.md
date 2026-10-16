# Suite Reorganization & Maintenance Plan

## Status as of 2026-10-16

*Added 2026-10-16 by Core (Claude Code). The plan below is unchanged and is dated 2026-07-25 (last edited 2026-08-04). "Done" is claimed here only where a BULLETIN entry or a PR is cited, or where the item was re-checked on 2026-10-16 as stated. Anything not confirmed is "unknown", not guessed. Items recorded as done only in the plan's own 2026-08-04 pass, or in another repo's to-do, are "unknown" here because this check could not confirm them. Jetson facts come from the GLMP lane's read-only report of 2026-10-16 ([GLMP-lane comment](https://github.com/garywelz/copernicus-web/pull/131#issuecomment-6215827185)); I did not touch the Jetson, and I re-read `scheduler_status` in Firestore myself.*

| Item | Status | Evidence |
|---|---|---|
| **Part 1** Engine/discipline architecture settled; governance shows engines apart from demonstrations | done | BULLETIN 001, 002, 017 (engine model, onboarding, engine scoping); the repo↔Space map in `governance/AGENT_ROLES.md` lists glmp, atap and tdap as engines |
| Part 1: ATAP renamed from `mathematics-database` | done | `garywelz/atap` exists (2026-10-16 GitHub API check); manifest ATAP row |
| Part 1: four discipline stub repos deleted | done | `biology-database`, `chemistry-database`, `computer-science-database`, `physics-database` each return 404 on the GitHub API (2026-10-16 check) |
| Part 1: fetch-live header on all projects | done | BULLETIN 004 (headers in all four Cursor Projects and all seven of Gary's Claude Projects, 2026-09-28) |
| Part 1: podcast collection listed under Products | done | `governance/RESOURCE_MANIFEST.md`, "Products" section (2026-10-16 check) |
| Part 1: Resources and Products Claude Projects created; ATAP retitled and re-scoped | unknown | Claude Project state cannot be read from the repo (plan §6, item 2) |
| Part 1: `huggingface-space/DISCIPLINE_DATABASES_PLAN.md` rewritten against the engine/discipline distinction | unknown | recorded done in this plan on 2026-08-04; not re-read on 2026-10-16 |
| **Part 2** Option B (copernicus-web stays canonical for deploy-coupled content) | done (decision) | AGENTS.md, "This repo" |
| Part 2: git-history depth check; the asset migration itself | unknown | depth check recorded in glmp `GLMP_MASTER_TODO.md` item 16 (2026-07-30), no BULLETIN entry or PR cited; no entry records any content moving |
| **Part 3** Ordering: embed `--auto`, then status publish, then findability, then MASTER_TODO | done | [GLMP-lane comment](https://github.com/garywelz/copernicus-web/pull/131#issuecomment-6215827185): hook chain and logs (2026-10-16T01:22Z to 01:26Z); ordering holds |
| Part 3: acquire as a dependency chain | open | still six clock-scheduled scout lines (PubMed, bioRxiv, arXiv, each AM and PM); ingest is also clock-scheduled (10:30 and 20:15) — [GLMP-lane comment](https://github.com/garywelz/copernicus-web/pull/131#issuecomment-6215827185) |
| Part 3: overnight relocation | open | only the GLMP batch decoder (02:00) runs between 00:00 and 07:00 ET — [GLMP-lane comment](https://github.com/garywelz/copernicus-web/pull/131#issuecomment-6215827185) |
| Part 3: morning report | open | none on the Jetson (no cron line, script or status file) — [GLMP-lane comment](https://github.com/garywelz/copernicus-web/pull/131#issuecomment-6215827185) |
| Part 3: `scheduler_status` heartbeat for every stage | open | the six scout jobs have documents; ingest and post-ingest stages have none (Firestore re-read 2026-10-16: scout_arxiv/biorxiv/pubmed AM and PM, phase1_smoke, _schema only) — [GLMP-lane comment](https://github.com/garywelz/copernicus-web/pull/131#issuecomment-6215827185) |
| Part 3: production stages (podcast, flowchart, video) in the chain | unknown | not covered by the GLMP-lane report |
| **Part 4** ATAP focus file | done | BULLETIN 004 (`atap/docs/research_focus.json` has existed since July) |
| Part 4: date-forward mode | open | no date-forward or posted-since-last-run mode in the scout config or code; arXiv still uses rolling `submittedDate` windows — [GLMP-lane comment](https://github.com/garywelz/copernicus-web/pull/131#issuecomment-6215827185) |
| Part 4: ATAP (mathematics) scout section | open | none; the four arXiv queries are q-bio and ML-for-biology only — [GLMP-lane comment](https://github.com/garywelz/copernicus-web/pull/131#issuecomment-6215827185) |
| Part 4: TDAP scout section | open | none anywhere in the scout config or code — [GLMP-lane comment](https://github.com/garywelz/copernicus-web/pull/131#issuecomment-6215827185) |
| Part 4: arXiv reliability | open (counts) | 8 rate-limit (429) lines and 14 timeout lines in the 14 days since 2026-10-02 (28 dated log files); several arXiv runs report success with 0 documents — [GLMP-lane comment](https://github.com/garywelz/copernicus-web/pull/131#issuecomment-6215827185) |
| Part 4: daily brief; production selection | unknown | agent-shaped work; nothing recorded in a BULLETIN entry |
| **Part 5** Findability probe | done (built and running) | tracked at `cloud-run-backend/scripts/findability_probe.py`; `glmp/scripts/build_master_todo.py` has `read_findability_status` (checked 2026-10-16); runs as post-ingest hook 3 after every successful ingest, twice daily — [GLMP-lane comment](https://github.com/garywelz/copernicus-web/pull/131#issuecomment-6215827185) |
| Part 5: latest probe run | ALERT, under diagnosis | 2026-10-16T01:26:15Z: overall ALERT, one anchor miss in the `episodes` collection; no cause is recorded here — [GLMP-lane comment](https://github.com/garywelz/copernicus-web/pull/131#issuecomment-6215827185) |
| Part 5: an anchor for every collection created later | open | plan, Part 5 |
| **§6.1** Commit the plan | done | BULLETIN 001 (governance moved into this repo, PR #10) |
| §6.2 Create Resources and Products projects; add headers; retitle ATAP | partly done | headers: BULLETIN 004; the rest: unknown (see Part 1) |
| §6.3 Part 5 findability check | done (built and running) | see Part 5; latest run ALERT, under diagnosis |
| §6.4 ATAP focus file | done | BULLETIN 004 |
| §6.5 Git-history depth check | unknown | see Part 2 |
| §6.6 `sync_*` hardcodes, TSV provenance diagnostic, venv untracking | unknown | recorded done in this plan on 2026-08-04; not re-checked |
| §6.6 IAM narrowing | open (in progress) | public access removal is done (BULLETIN 005, 006, 014, 018); service-account role narrowing is under way and tracked privately, with no public entry yet |

**Open items recorded since the plan was written**
- Gap 1b: 58.7% of `research_papers` carry no engine tag (auto-tagging not built) — BULLETIN 012. Not on the Jetson ingest path: nothing in the nightly ingest writes `question_scope_ids` (the only write path found, `huggingface-space/scripts/acquire_papers/researcher_cited_intake.py`, is not in the cron chain) — [GLMP-lane comment](https://github.com/garywelz/copernicus-web/pull/131#issuecomment-6215827185).
- Duplicates from two ingest paths: 136 documents across 68 shared DOIs and 64 across 32 arXiv IDs — BULLETIN 012.
- Missing publication year: 43.8% of documents (52,279) — BULLETIN 012.
- Fix 3, inline citation markers for the podcast generator (design only until approved) — BULLETIN 021.
- Part 5 findability probe: built and running after each ingest ([GLMP-lane comment](https://github.com/garywelz/copernicus-web/pull/131#issuecomment-6215827185)); latest run ALERT, under diagnosis; open is an anchor for every collection created later.
- Other users opening their own private episodes needs the subscriber session design — BULLETIN 024.

---

*Proposed canonical home: `copernicus-web/governance/SUITE_REORG_PLAN.md`.
Per the Constitution §4, the record of truth is GitHub — this file is written
to be committed there, not to live in a chat. Every Project's knowledge base
holds a copy; when this changes, re-sync. If a copy and the GitHub master
disagree, GitHub wins.*

*Status date: 2026-07-25. This plan emerged across two working sessions and
was previously undocumented — reconstructing it from conversation was the risk
this file exists to close.*

*Last verified against reality: 2026-08-04 (Claude Code) — five items marked
"open" below had actually been completed without this file being updated —
the plan itself had gone stale, the exact "presence is not findability"
failure Part 5 describes, applied to a planning document. Each is marked
below with what was checked, the commit hash, and the verification date, so
the next reader inherits the proof rather than re-doing the chase.*

---

## 0. Why this document exists

The suite is being reorganized around a single realization: **the operating
knowledge engines are projects with frontiers (GLMP, ATAP), not disciplines
(Biology, Mathematics).** A discipline is a shelf; an engine is a vehicle
aimed at an open question. Everything below follows from that distinction.

A second theme runs through the maintenance work: **the suite has repeatedly
checked that things *exist* without checking that they are *findable*.** Three
separate silent failures this month — junk vectors polluting retrieval, papers
present-but-unembedded, podcast embeddings stranded in the wrong collection —
all passed every count-based check. Presence is not findability. Detecting that
class of defect is now built and running (Part 5) — including having caught,
via this exact section going stale without anyone noticing, an instance of the
same failure applied to this plan itself.

---

## 1. The organizing test

**An engine is the scope over which one `research_focus.json` makes sense** — a
real frontier belonging to a real researcher, with active questions the
literature can answer and frontier questions where the engine must hand off.

- **GLMP** qualifies: Class II reachability is a live frontier.
- **ATAP** qualifies: whether the algorithm-capsule regularity is real or a
  selection artifact (n=3) is a live frontier.
- **"Biology" / "Mathematics" do not**: ten thousand frontiers belonging to
  ten thousand people; no single focus file could be honestly maintained.

Disciplines remain a valid taxonomy for **outputs** (podcasts shelved by
discipline, because listeners browse that way) but not an architecture for
**engines**.

### The six categories

The test that separates the two most-confused pairs:
- **Resources vs. Products** — Resources are *inputs the engine consumes*
  (gathered externally); Products are *outputs the engine creates* (authored
  within). Different claim types: Resources carry a citation/provenance claim,
  Products carry an authorship/honesty claim, and the honesty guardrail applies
  hardest to Products.
- **Methods & Tools vs. Core** — Methods & Tools answers *"how do we understand
  this?"* (a method is a way of seeing; a tool applies a method). Core answers
  *"how do we make and serve things?"* A generator is a making-machine, not an
  understanding-method — it is Core infrastructure, not a Method or Tool.

| Category | Holds | Test |
|---|---|---|
| **Knowledge Engine Core** (umbrella) | Shared plumbing and production infrastructure every engine uses: corpus, embeddings, retrieval, ingest, cron, status — **and the generators** (podcast, video, image/graph rendering: MatPlotLib, Mathematica, DALL-E, etc.) | "Would every engine need this?" |
| **Engine projects** (GLMP, ATAP, future) | Per-vehicle: focus file, frontier, scout vein, domain graphs, domain instruments (e.g. GLMP's DNA decoder), project papers | "Does one `research_focus.json` cover it?" |
| **Methods & Tools** | The Programming Framework (method), the tools that apply it (text→graph converter), the Methods Catalog, and the discipline flowchart collections as demonstration that the method generalizes | "Is this about *how* to understand, not *what* was made?" |
| **Resources** | External inputs the engine consumes: sciencevideodb, research-paper metadata database, other externally-gathered collections | "Do engines read from it, and did it come from outside?" |
| **Products** | Engine-authored outputs: CopernicusAI podcast collection, original papers (human-in-the-loop), videos, and output forms not yet imagined | "Did the engine author it?" |

**Two lifecycles connect these categories** (arrows, not merges):
- **Products → Resources.** A product the engine authored today (a podcast) can
  be substrate the engine ingests tomorrow — but it enters that second life *as
  a resource*, by being registered into a Resources collection, not by leaving
  Products. Its authored home stays Products; its consumable role is a
  registration. This is the engine's "read your own instruments" mode (Part 2,
  mode 2) made concrete: Products is what mode 2 reads from.
- **Domain instrument → shared method.** When an engine's instrument (GLMP's
  DNA decoder) embodies a general method, the *method* is extracted to Methods &
  Tools while the *instrument* stays in the engine — exactly as the Programming
  Framework generalizes while ATAP's proof-graphs stay in ATAP. Generalizing is
  not "move the instrument"; it is "extract the method, leave the instrument."

**Products organized by output form** (podcast / paper / video / …) as a
dimension, so a fourth form drops in without restructuring. Do not hard-code
three.

**Claude Projects are flat** — the nesting is conceptual, enforced by the
Constitution copy each project's knowledge base carries, not by a folder tree.

---

## 2. Operating model (the vehicle metaphors, made precise)

Three metaphors converged into design constraints. Recorded because they shape
what gets built, not as decoration.

- **Bison grazing the plains.** The *users* roam and graze; the engine keeps the
  terrain navigable — fields stocked, mapped, passable — and keeps a sightline
  to the next ridge. Serving only what a researcher already asks for fences the
  herd in (the `horizons` field exists against this).
- **Mining a vein.** Following a signal toward increasing concentration, always
  seeking the mother lode and connections to other veins. Implies an *assay* —
  feedback on what each haul yields — which the suite does not yet have
  (nothing records which papers proved valuable). `flagged` is the crude first
  version of that signal.
- **Full self-driving to the frontier, then handoff.** The engine drives
  autonomously over mapped ground (synthesize settled literature — the `active`
  mode) and hands the wheel to the human at the frontier (surface what exists,
  state what's unresolved, do **not** pretend to an answer — the `frontier`
  mode). A clearly marked frontier is itself a finding (Constitution §5).

**Three engine modes** fall out of this, and belong in the Constitution:

1. **Drive the mapped road** — synthesize external literature (`active`).
2. **Read your own instruments** — query/compute over the suite's own artifacts.
   This is the Copernican operation mechanized: same data, new reference frame.
   Made available as a standing property of the brief, not a declared field.
   The collection mode 2 reads from is Products — the engine's own authored
   outputs, queryable as substrate.
3. **Hand over the wheel** — the frontier, where the engine must not pretend.

**Telescope, not oracle:** the engine makes vantage points cheap to try; the
choosing stays with the researcher. This is what keeps mode 2 from quietly
eating the frontier.

---

## 3. Part status

### Part 1 — Architecture clarification — **mostly done**

Done: four destinations settled; the engine test validated against every case;
ATAP renamed on HF and GitHub (from `mathematics-database`); four discipline
stub repos deleted; `DISCIPLINE_DATABASES_PLAN.md` rewritten against the
engine/discipline distinction; governance tables no longer flatten engines and
demonstrations into peer rows; the 50-process mathematics scheme archived
(`glmp/archive/mathematics-50-processes-2025-01.md`) rather than deleted.

Open:
- The ATAP, Methods & Tools, GLMP, and Core projects **already exist** (predate
  the reorg; created ~Jul 18, ATAP ~Jul 23). They do NOT yet carry the
  fetch-live governance header or current scope notes.
- **Create the Resources project** (new) — holds sciencevideodb,
  research-paper metadata database.
- **Create the Products project** (new — this session's addition).
- **Add the fetch-live header to all projects** so each reads canonical
  governance from GitHub rather than stale uploads. This is the highest-value
  item: it stops any project from drifting, which is the record-of-truth
  discipline applied to the projects themselves.
- **Retitle ATAP** to include the acronym ("ATAP — Axiomatic Theories,
  Algorithms and Proofs") and **update its scope note** from the current
  library description to the engine framing.
- ~~**Reclassify the CopernicusAI podcast collection** from Resources to
  Products (its authored home), registered into Resources for consumption.~~
  — DONE. Confirmed 2026-08-04: `RESOURCE_MANIFEST.md` already lists it under
  "Products," with a note at the old Resources location pointing there.
- ~~**sciencevideodb Gradio vestige** — `app.py` + `requirements.txt` present
  but `sdk: static`; the app is inert. Small cleanup.~~ — DONE (2026-07-30,
  part of the `sciencevideodb` quality pass, commit `6d452b4`). Confirmed
  2026-08-04: both files absent from `hf-spaces/sciencevideodb`.

### Part 2 — Asset migration — **decided, not started**

**Option B chosen:** `copernicus-web` stays canonical for deploy-coupled
content; the ATAP repo (`github.com/garywelz/atap`) holds papers, focus file,
docs. Conceptual ownership and physical location may differ (e.g. `math_processes`
in Firestore is ATAP data operated by Core).

Blocked on:
- ~~**Git-history depth check** on `copernicus-web/.../mathematics-processes-database/`
  (664-file ATAP corpus): substantive history vs. bulk import → decides
  subtree-split vs. fresh-commit.~~ — DONE (`glmp` `GLMP_MASTER_TODO.md` item
  16, 2026-07-30). Zero substantive history found — one bulk-import root
  commit, nothing to preserve — so the decision is **fresh-commit, not
  subtree-split**. This unblocks migration *planning*; the migration itself
  hasn't started (see below).

No content has moved.

### Part 3 — The nightly chain — **the hard half is built**

**Dependency ordering is real in production.** Status publish and MASTER_TODO
fire on ingest *completion* (not a guessed clock time), and the `--auto` embed
stage runs ahead of them. `acquire → enrich → publish` works today, verified
2026-07-25: embed_auto filled a 13-paper gap, *then* publish reported a true
100.0%.

Done: ordering fix shipped and validated over PM + AM cycles; standalone
10:40/10:45 cron removed; `--auto` embed live and non-blocking; both leak
sources (papers, episodes) now close automatically.

Open:
- **Acquire is still six clock-scheduled cron lines**, not a dependency chain.
- **Overnight relocation** (midnight–07:00, once daily) not done. Gary's stated
  preference; frees the daily boundary and keeps work off interactive hours.
- **Production stages** (podcast, flowchart, video) not in the chain. Inventory
  established these are **agent-shaped** (selection is judgment) with
  **script-shaped** pipelines — so a cron owns generation, an agent owns "which
  5 papers deserve a podcast today."
- **Chain shape** should stay a shell orchestrator reading/writing the existing
  `scheduler_status` heartbeat — not Airflow. Per-stage timeouts and a
  continue-or-abort policy per stage; a morning report written last is what
  makes once-daily-unattended safe.

### Part 4 — Researcher relevance — **specified, barely built**

The `research_focus.json` spec exists. GLMP's file is committed
(`9bb8bd9`→edited); ATAP's draft v2 is ready for Gary's hand-edit.

Open:
- ~~**ATAP focus file** — Gary's ten minutes in the schema, then commit.~~ —
  DONE. Confirmed 2026-08-04: committed at `atap/docs/research_focus.json`.
- **Date-forward scout** — the scout re-samples a fixed multi-year window and
  takes top-N; it does not scan "what's new since yesterday." That's a new
  selection mode (`edat`/posted-date since last run), not a schedule change. It
  is the actual engine of "keeping researchers abreast." Reads `terms`,
  `graze`, `mute` from the focus file. **Note:** a mathematics scout section in
  `daily_scout_config.json` does not exist yet, and arXiv acquisition was
  failing (429s/timeouts) — both prerequisites for ATAP's vein.
- **The daily brief** — three specified jobs: keep current on settled ground
  (mode 1), point at the frontier (mode 3 handoff), keep one sightline to an
  adjacent ridge (anti-paddock). Depends on the focus file + new query paths.
- **Production selection** — agent-shaped; not a cron.

### Part 5 — The findability defect class — **built and running** (was:
"instances fixed, detection not built" — corrected 2026-08-04, see below)

Three instances found and fixed; both leak sources now close automatically.
This section originally said nothing would catch a fourth instance and that
the check "does not exist... not yet on any queue." **That was wrong by the
time it was checked, not just later** — confirmed 2026-08-04:

- The probe exists: `copernicus-web/cloud-run-backend/scripts/findability_probe.py`,
  commit `403e0b4c0`, "Add findability probe (v1) — Gate 3 proven, not yet
  integrated."
- It's integrated, not just built: `glmp/scripts/build_master_todo.py` reads
  its report into AUTO-STATUS (`glmp` commit `073be02`, `read_findability_status()`
  following the same `SourceResult` contract as every other reader — missing
  or malformed input degrades to a stale cell rather than crashing the
  assembler).
- It's live in production: `GLMP_MASTER_TODO.md` item 21 records a Gate-3
  acceptance test against production (14 anchors, no false alarms), an
  automated overnight render witnessed writing a "### Findability" section
  into the published doc, and a same-day ALERT that was traced to ground
  truth rather than assumed benign (item 21's follow-up diagnosis) —
  confirming the probe surfaces real signal, not noise.

Minimum-viable design as originally specified — (a) confirms every embedded
collection's live `find_nearest` returns sensible hits for a fixed query set,
(b) flags any collection where `count(docs)` and `count(findable docs)`
diverge — matches what got built. ~~**Open, not done:** whether coverage
extends past the original anchor set as new collections (`atap_graphs`,
etc.) come online is unverified.~~ — Also stale, corrected 2026-08-04:
`atap_graphs` (the plan's own example of an uncertain case) already carries
real anchor queries ("field extension degree" → `abstract_algebra-field-theory-extensions`,
"diagonalization" → `cantor-diagonal-proofs`), and so does every other
current collection — `research_papers`, `glmp_processes`,
`chemistry_processes`, `physics_processes`, `computer_science_processes`,
`biology_processes`, `episodes`. Full coverage has existed since close to
the probe's original commit, not added later. **Genuinely open, not yet
checked:** whether coverage keeps pace automatically as *new* collections
are created after this point — nothing currently forces an anchor to be
added when a collection is; that's a process gap, not a current coverage
gap.

**A second, distinct defect class, worth naming separately.** This section's
original text wasn't a stale pointer — it was a false claim: it asserted the
probe "does not exist" when it existed, was committed, and was already wired
into `glmp`'s AUTO-STATUS. `RESOURCE_MANIFEST.md` had the same failure mode
the same day, in the opposite direction — a citation that resolved to a real
file while asserting something about that file's contents (a superseded DOI
under an old title) that wasn't true. `check_citations.py` catches dead
pointers; it cannot and does not catch either of these — a claim can be false
while every citation near it resolves perfectly. Two instances in one day is
a pattern, not a coincidence: read this doc's "done" markers as claims to
re-verify when they matter, not as settled once written, this correction pass
included.

---

## 4. Cross-cutting: collaboration & shared context

- **Collaboration model (Principal Investigator control).** Each Knowledge
  Engine is owned by a Principal Investigator who writes and manages its
  backend. This control is structural, not incidental: any PI creating a
  Knowledge Engine project holds the same authority the GLMP/Core PI holds —
  they own the record of truth, gate every change, and decide what
  collaborators may see and do. Collaborators receive read-only views (static
  GitHub Pages briefs; public repos and Spaces consumed via the
  clone-the-project fetch-live pattern) and contribute through suggestions
  (Slack/email) and occasional code pushes accepted through the PI's normal
  review gate. There is no shared Chat↔Code state, no GitHub Issues/Projects
  write integration, and no collaborator write access to the record of truth.
  The collaborator-facing surface is a static, fetchable brief — not an
  interactive board. This keeps onboarding additive rather than
  architectural: bringing collaborators aboard points them at read-only
  surfaces and a suggestion channel; it does not restructure the engine or
  dilute PI control. The pattern scales to a federation of engines, each
  PI-owned, rather than one project with helpers.
- **Records of truth stay in GitHub/GCS/Firestore/Zenodo** (Constitution §4).
  Project knowledge bases hold snapshots that go stale — as the Resource
  Manifest copy did this month.
- **Preferred sharing pattern (works on any plan today):** collaborators clone
  the project rather than share state — each creates their own Claude project,
  and project instructions **fetch canonical governance live** from raw GitHub
  URLs at the start of work rather than relying on uploaded copies. Push a
  change once; everyone's next session reads it. No coordinated re-upload.
- **Enterprise path (CUNY):** Me-Me, Krampis, Lents have institutional Claude
  access through CUNY; Gary is plausibly eligible (CUNY Graduate Center — New
  Media Lab). Team/Enterprise adds shared projects and Claude Tag (Slack) on
  top of the fetch-live pattern, not instead of it. Open questions for CUNY IT:
  external-collaborator eligibility, whether connectors/web-fetch are permitted
  (the fetch-live pattern needs them), data-retention/admin-visibility policy
  given personal GCP/GitHub assets.
- **Slack** is the human layer that *links to* records, not a place to duplicate
  them (Constitution §4). A collaborator-facing status page (GitHub Pages, not
  GCS — it can't drift from the repo) is worth building, and is **not** the
  MASTER_TODO: researchers need current research state, what changed, links to
  artifacts they'd open, and — highest value — **what's waiting on them.**

---

## 5. Working practices affirmed this month

Recorded because they were learned the hard way and should bind future work:

- **Blob-pin every script review:** review blob X, commit blob X, verify blob X
  on the box (`git hash-object` = worktree = HEAD). Caught paste-drift that
  changed a function's meaning by two characters.
- **Deploy-gap check:** after commit+push, confirm the box pulled and the hash
  matches before treating a fix as live.
- **Canary-then-full** for anything destructive or rebuild-triggering (bulk
  deletes, HF Space pushes).
- **Never select or clean by label** where the label is the untrustworthy field
  (embedding-model mislabel); select by measured property (vector dimension).
- **Credential handling** (`AGENT_ROLES.md` v1.2): never `cat`/`od`/`head`
  credential-shaped files; `grep -c` / `tail -c N` only; flag immediately if
  one leaks to output.
- **A read-only task that produces commits is a process failure** even when the
  commits are good — scope discipline over eager helpfulness.
- **Cross-agent completions don't appear in any one agent's history** — when
  status is uncertain, ask rather than assume in either direction.
- **Accurate-and-unflattering beats wrong-on-time:** publish true state even
  when a stage stumbled; don't suppress a status to preserve a rounder number.

---

## 6. Recommended next actions (priority order)

1. ~~**Commit this plan** to `copernicus-web/governance/` so the record of
   truth stops being a conversation.~~ — DONE (`8d694df1a`).
2. **Create the Resources and Products projects; add the fetch-live header to
   all projects; retitle and re-scope ATAP.** (Manual, web app — not
   agent-doable.) **Still open** — no way to verify Claude Project state from
   a repo checkout.
3. ~~**Add the Part 5 findability check** to the queue — the one durable fix
   the month's work implies but never scheduled.~~ — DONE and beyond queued:
   built, integrated, live in production. See Part 5 above.
4. ~~**ATAP focus file** — Gary's edit + commit (small, unblocks ATAP's
   brief).~~ — DONE, `atap/docs/research_focus.json`.
5. ~~**Git-history depth check** (unblocks Part 2 migration planning).~~ —
   DONE, decided fresh-commit. Migration itself still not started.
6. Then, in whatever order suits: ~~remaining `sync_*` hardcodes~~ (done),
   TSV provenance **diagnostic** (done — the *full re-harvest* it recommends
   is separately tracked and still open, `GLMP_MASTER_TODO.md` item 25),
   ~~venv untracking~~ (done), **IAM narrowing** (alert only — it can break the
   Jetson) — **still open**, `GLMP_MASTER_TODO.md` item 10.

---

*This plan is descriptive of decisions already made and prescriptive only where
marked "open" or "recommended." It does not authorize execution — the
Constitution's propose-before-executing rule still governs each step.*
