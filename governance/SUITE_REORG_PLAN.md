# Suite Reorganization & Maintenance Plan

*Proposed canonical home: `copernicus-web/governance/SUITE_REORG_PLAN.md`.
Per the Constitution §4, the record of truth is GitHub — this file is written
to be committed there, not to live in a chat. Every Project's knowledge base
holds a copy; when this changes, re-sync. If a copy and the GitHub master
disagree, GitHub wins.*

*Status date: 2026-07-25. This plan emerged across two working sessions and
was previously undocumented — reconstructing it from conversation was the risk
this file exists to close.*

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
class of defect is itself unfinished work (Part 5).

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
- **Reclassify the CopernicusAI podcast collection** from Resources to
  Products (its authored home), registered into Resources for consumption.
- **sciencevideodb Gradio vestige** — `app.py` + `requirements.txt` present but
  `sdk: static`; the app is inert. Small cleanup.

### Part 2 — Asset migration — **decided, not started**

**Option B chosen:** `copernicus-web` stays canonical for deploy-coupled
content; the ATAP repo (`github.com/garywelz/atap`) holds papers, focus file,
docs. Conceptual ownership and physical location may differ (e.g. `math_processes`
in Firestore is ATAP data operated by Core).

Blocked on:
- **Git-history depth check** on `copernicus-web/.../mathematics-processes-database/`
  (664-file ATAP corpus): substantive history vs. bulk import → decides
  subtree-split vs. fresh-commit. A provenance defect in
  `flowchart-source-papers.tsv` this month makes history-preservation matter.

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
- **ATAP focus file** — Gary's ten minutes in the schema, then commit.
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

### Part 5 — The findability defect class — **instances fixed, detection not built**

Three instances found and fixed; both leak sources now close automatically.
But **nothing would catch the fourth instance.** A findability check — one that
asks "is this retrievable?" rather than "does this exist?" — does not exist.

This is the durable fix and it is not yet on any queue. Minimum viable version:
a periodic probe that (a) confirms every embedded collection's live
`find_nearest` returns sensible hits for a fixed query set, and (b) flags any
collection where `count(docs)` and `count(findable docs)` diverge. It belongs
in the nightly chain's verification stage and its output belongs in the morning
report.

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

1. **Commit this plan** to `copernicus-web/governance/` so the record of truth
   stops being a conversation.
2. **Create the Resources and Products projects; add the fetch-live header to
   all projects; retitle and re-scope ATAP.** (Manual, web app — not
   agent-doable.)
3. **Add the Part 5 findability check** to the queue — the one durable fix the
   month's work implies but never scheduled.
4. **ATAP focus file** — Gary's edit + commit (small, unblocks ATAP's brief).
5. **Git-history depth check** (unblocks Part 2 migration planning).
6. Then, in whatever order suits: remaining `sync_*` hardcodes, TSV provenance
   diagnostic, venv untracking, IAM narrowing (alert only — it can break the
   Jetson).

---

*This plan is descriptive of decisions already made and prescriptive only where
marked "open" or "recommended." It does not authorize execution — the
Constitution's propose-before-executing rule still governs each step.*
