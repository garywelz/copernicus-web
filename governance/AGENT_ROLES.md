# Agent Roles and Division of Labor
## CopernicusAI Knowledge Engine suite — every engine, every agent

**Version:** 2.5 — October 4, 2026
**Lives in:** `copernicus-web` repo at `governance/AGENT_ROLES.md` (moved from
`glmp/docs/AGENT_ROLES.md`; see change log)
**Read alongside:** the rest of `governance/` — Constitution, Methods Catalog, Resource
Manifest, Reorg Plan, Bulletin, Project Headers. Each engine's own goals and to-do
lists stay in that engine's repo (e.g. `glmp/docs/GLMP_MASTER_TODO.md`).

---

## Purpose

This document defines who does what across the human and AI agents working across
the CopernicusAI Knowledge Engine suite, on which hardware, and against which repositories.
It exists so that any agent — or Gary — opening a session knows the division of labor and
the canonical repo↔Space map without re-deriving it, and so that handoffs between agents
are clean.

Roles and boundaries marked **(evaluating)** are not yet fixed. They describe how a tool
is currently being used and tested, and are expected to change as we learn what each tool
does best.

---

## The agents

| Agent | Role | Strengths |
|---|---|---|
| **Gary Welz** | Author, PI, decision-maker | Domain expertise, scientific judgment, strategic vision, final approval on all decisions |
| **Claude Chat** (claude.ai) | Consultant / strategy | Architecture design, strategy, document drafting, cross-session memory, handoff documents, paper editing, cross-project thinking |
| **Cursor** | Coding and task agent | Full codebase indexing, multi-file edits, SSH to Jetson, cron deployment, complex git operations, pipeline debugging. Gary's primary coding tool at present. |
| **Cursor Projects** (coordinator) | Long-running coding work **(evaluating)** | Cursor's lane at a larger unit of work: a cloud coordinator that plans, delegates to subagents, holds context across sessions, and can run recurring work. One Project each for `atap`, `glmp`, `copernicus-web`, `tdap`. See *Cursor Projects* below. |
| **Claude Code** | Publishing / quality agent **(evaluating)** | Autonomous file reading, targeted single-file edits, HuggingFace deployment, GCS uploads; finds deployment patterns autonomously. Currently the least-utilized tool and under active evaluation for a broader role (see below). |

### Gary + Claude Chat: the decision loop
High-level decisions — architecture, scope, publication strategy, what to build next —
are made by Gary in dialogue with Claude Chat. Claude Chat proposes and asks about goals
before proposing solutions; Gary decides. No significant work is executed before this
dialogue happens.

### Claude Code: current scope and evaluation
Claude Code is presently the underutilized tool. Its **proven** use so far is targeted,
self-contained deployment work (single-file HTML edits, HF Space pushes, GCS uploads).

Its **intended and under-evaluation** role is broader: improving the *quality* of the
science-suite HuggingFace Spaces — not just deploying them, but improving the writing,
presentation, and overall polish of each Space. Claude Code can participate in that
quality work even though high-level decisions remain with Gary and Claude Chat.

We may also discover or invent other functions for Claude Code as we go. Where its remit
is not yet settled, this document says **(evaluating)** rather than fixing a boundary
prematurely.

### Cursor / Claude Code boundary — **(evaluating)**
The working split, subject to revision as we learn:

- **Cursor** owns anything needing full-repo context or SSH-to-Jetson: multi-file
  refactors, cron deployment, pipeline debugging, complex git operations.
- **Claude Code** owns self-contained, per-Space work it can read and act on
  autonomously: quality improvements, presentation, single-file edits, HF/GCS deploys,
  and repeatable setup tasks (e.g. wiring a repo to a new Space).

This boundary is a starting hypothesis, not a rule. Overlap is expected while we evaluate
where each tool is strongest.

### CI / GitHub Actions ownership — **(evaluating)**
Established by precedent, not yet a settled rule: **Claude Code authors and maintains
GitHub Actions workflows** for repos it already does self-contained quality/deployment
work in — this fits the same "reads and acts autonomously on a single repo" profile as
its other work, and needs no Jetson/SSH access. First instance: `glmp`'s
`glmp/.github/workflows/published-drift-check.yml` (added 2026-08-03), a read-only check that curls each
published artifact and diffs it against the repo source.

This does **not** extend to workflows that touch Jetson, cron, or the ingest/decode
pipeline — that stays Cursor's, per the boundary above.

**Read-only vs. side-effecting CI is the load-bearing distinction, not "who wrote it":**
- A read-only check (drift detection, link validation, lint) can run unattended on a
  schedule or every push — no dialogue needed per-run, the same way a passing test suite
  doesn't need Gary's sign-off each time.
- Any workflow that would *deploy*, *publish*, or otherwise change GCS/HF/production state
  needs the same propose-then-wait approval as a manual deploy would, whether or not a
  human is literally typing the command. Nothing like this exists yet — flagging it now so
  the first one doesn't get waved through just because it's "just CI."

### Cursor Projects (coordinator mode) — **(evaluating)**
Added v1.9. Cursor Projects (beta, launched 2026-09-10) runs a coordinator agent on a
Cursor cloud machine. It plans work, dispatches subagents, keeps its own context across
sessions, and can run recurring work or react to Slack, schedule, and PR triggers. Four
exist, paralleling the repos of the same names: `atap`, `glmp`, `copernicus-web`,
`tdap` (created 2026-09-27). The `tdap` coordinator also follows the shared-engine
rules in `tdap/AGENTS.md`. They are **the Cursor lane at a larger unit of work, not a new lane** —
the Cursor / Claude Code boundary above still applies.

**Starting autonomy** (the most conservative setting; widen only by amending this section):
- **Without per-run approval:** read-only work only — repo analysis, audits, read-only
  probes of public endpoints, drafting plans. Same test as read-only CI above. Recurring
  or trigger-started runs are limited to this tier.
- **Output held for review:** open **draft** PRs on a branch. The draft PR *is* the
  proposal: its description carries the plan and the four-section report; Gary reviews
  the diff and decides the merge.
- **Never, from any trigger:** merge or push to `main`; force-push or rewrite history;
  HF Space pushes; GCS or Firestore writes; bulk deletes; cron edits; anything that
  deploys or publishes.
- **Fan-out does not waive canary-then-full or blob-pinning.** A multi-PR migration lands
  one reviewed PR at a time, the first as canary.

**Known limits** (recorded as findings, not worked around):
- The cloud coordinator is not on the home LAN. SSH-to-Jetson, cron, and the
  ingest/decode pipeline stay with Cursor run locally on the Yoga 9i.
- No service-account keys, `.env` files, or HF/GCS/Firestore write tokens are provisioned
  to Cursor cloud machines. The credential rule below binds coordinators and every
  subagent. This makes the permission boundary enforce the autonomy boundary.
- A Slack message may *trigger* a coordinator; coordinators do not *post* automated feeds
  to Slack (Constitution §4). Status goes in the PR or in `governance/BULLETIN.md`.
- A coordinator's learned context is private to Cursor — no other agent can read it. It
  does not bind anyone until written back to GitHub (see *Shared context contract*).
- Usage is metered. Cursor's spend limit is account-wide, not per Project; Gary sets it
  in the Cursor dashboard's Spending tab.

---

## Shared context contract

Added v1.9. No agent surface can read another's internal context: Claude Project
knowledge and memory, Claude Code sessions, and Cursor Project coordinator context are
separate stores. **GitHub is the one medium every agent and every human can read**, so it
is the shared context by construction.

1. **Read path.** Every session starts by fetching live, with plain fetches: the
   governance set in `copernicus-web/governance/` (this file included), the repo's
   `AGENTS.md`, and the newest entries of `governance/BULLETIN.md`. The session-header
   text pasted into each Claude Project and Cursor Project is versioned in
   `governance/PROJECT_HEADERS.md`; the pasted copies are snapshots.
   Headers list every URL literally, because Claude Chat can only fetch URLs that appear
   verbatim in its instructions or earlier results.
2. **Write path.** A decision or learning that should outlive a session is committed
   back — as a governance amendment, an `AGENTS.md` edit, or a bulletin entry. Context
   held only inside one tool (a coordinator's learned preferences, a Claude memory, a
   chat) is a snapshot and binds no other agent.
3. **Handoff path.** Work crosses between agents as a commit or PR, never as a pasted
   summary; the receiver regenerates from a fresh fetch (v1.5 rule).
4. **Bulletin.** `governance/BULLETIN.md` is the append-only notice board for changes that affect how
   others work: lane changes, new rules, new surfaces, and what is waiting on whom. Each
   entry links to the commit or PR that is the record — it announces, it does not
   restate. Humans get the same entry through a Slack post that links to it.
5. **One home per fact.** This file is the single home of the agent rules, the lanes
   (Claude Code's role included), and the repo↔Space map. Each repo's `AGENTS.md`
   holds only pointers here plus facts specific to that repo; each repo's `CLAUDE.md`
   is a one-line import of `AGENTS.md`, present only because Claude Code reads
   `CLAUDE.md`. Nothing is copied between repos except the three-rule floor in
   *Session rules*, duplicated deliberately (two hand-copied repo↔Space maps had
   drifted before v2.0).
6. **Collaborator workspaces are outside this contract.** An engine shared with an
   outside researcher (first case: `tdap`) gives that researcher a separate,
   researcher-owned instruction file in the engine repo (`tdap/docs/project_instructions.md`)
   for their own Claude. Its readers are not suite agents: the lanes here don't bind
   them, and their private work never enters the suite's records. They contribute to
   the shared engine only through issues and pull requests on its public repo, which
   reach `main` through Gary's review. How engines are added, and how an engine's PI
   adds local rules on top of this core, is in `governance/ENGINE_ONBOARDING.md`.
7. **Only Gary's agents touch Core infrastructure** — Firestore, GCS, Cloud Run, the
   Jetson, and the HF Spaces. No collaborator's or other PI's agents do, in any
   arrangement; their work reaches Core only as a request that Gary's agents carry out.

---

## Session rules — every agent, every session

The canonical text of the rules each repo's `AGENTS.md` points to. The first three are
the **floor**: they are also written into every `AGENTS.md`, so they hold even when a
live fetch of this file fails.

1. **Propose before executing.** Gary approves significant changes before they are made.
2. **Never force-push or rewrite history.** No autonomous or triggered run pushes to
   `main`.
3. **Never print credential-shaped files in full** (see *Credential handling*). If one
   reaches output, say so in the same turn.
4. **Review diffs before committing,** and blob-pin: review blob X, commit blob X,
   verify blob X.
5. **Verify live objects with plain fetches** (no cache-busters). A clean exit verifies
   pointers, not claims. For a cached public object (the podcast feed is cached for up
   to an hour), confirm a write with an authenticated read right away, and confirm what
   the public receives with a plain fetch once the cache has expired; a disagreement
   inside that window is expected, not a failed write.
6. **Regenerate anything handed across agents from a fresh fetch** before applying it.
7. **An empty or surprising result is a claim about the instrument** until the
   instrument is checked.
8. **Media never goes in git.** Audio, video, and large assets live in GCS.
9. **A clearly marked limit is a finding.** Report it plainly; don't work around it.
10. **Stay in lane.** When a task belongs to another agent, say so rather than forcing it.
11. **Write durable context back** to GitHub (governance amendment, `AGENTS.md` edit, or
    bulletin entry); context kept only inside one tool binds no other agent.
12. **Report in four sections:** what I found / what I did / what I'm uncertain about /
    what to discuss with Gary. Cursor Projects put this in the draft PR description.
13. **`shadow` is out of scope** — never touched as science-suite work.
14. **Delete a branch once its pull request is merged or closed.** Its commits stay
    recoverable from the pull request page ("Restore branch"); stray branches are how
    backlogs accumulate.
15. **Deploy in gated steps; never straight to full traffic.** Build from a clean
    checkout of the reviewed commit; deploy by image digest with no traffic and a tag,
    changing only the image; compare the new revision's configuration with the old one;
    smoke-test the tagged URL against the live one; move traffic only after Gary
    approves; keep the previous revision for rollback. For copernicus-podcast-api the
    procedure is `cloud-run-backend/DEPLOY.md`.
16. **Broken generated content is deleted, not repaired.** Generated episodes are cheap
    to recreate and expensive to fix inside the corpus. The agent that finds broken
    content proposes deletion and does not attempt repair; Gary approves; the deletion
    follows the archive protocol: (1) back up the feed before every feed write, however
    small; (2) archive the record and its storage objects to the private internal
    bucket and verify checksums; (3) remove the item from the feed with a generation
    precondition; (4) delete only objects that nothing else references; (5) verify on
    every surface. Archives never go in the public podcast bucket.
17. **A security finding goes to a private location first.** It reaches a public PR
    or `governance/BULLETIN.md` entry only after the fix is live, not while the gap is
    still open — a public repo discloses the finding to anyone the moment it's
    committed. Report to Gary immediately regardless; "private first" governs where it
    is written down, not when Gary is told. See `governance/BULLETIN.md` entry 014.
18. **A change to what the public can reach is gated like a Cloud Run deploy.** This covers
    (a) any reader-facing object in a public GCS bucket (status pages, database tables,
    feeds), and (b) Cloud Run access and addressing: an IAM binding on a service (granting or
    removing `allUsers` or `allAuthenticatedUsers`) and a revision tag (each tag is a URL with
    the service's own access, so tagging a revision of a public service publishes that
    revision). Steps: (1) propose it, with the exact command, the backup and the reversal; for
    a GCS object, edit the tracked copy on a branch and never the live object; (2) show Gary
    and wait for approval; (3) for a GCS object, merge to `main`; (4) back up first: the live
    object to the private bucket, or the current IAM policy or traffic-and-tag map saved to the
    private bucket; then apply with a precondition where the command allows (generation for
    GCS, etag for IAM); (5) verify: for GCS, a plain fetch *and* object metadata (generation,
    MD5), and if they disagree the metadata is authoritative; for Cloud Run, read the policy
    or traffic back, then, for a change meant to close access, make one unauthenticated request
    after waiting about two minutes and record the status code only, because IAM changes take a
    short time to take effect (a probe six seconds after a removal on 2026-10-04 still got
    `200`); (6) remove a tag when its hold ends and list any tag left in place.
    Emergency exception: a security or data-exposure fix that *narrows* access (removing a
    grant, removing a tag) may be applied first, reported to Gary in the same turn, and
    back-filled with a PR or bulletin entry once live (rule 17). Widening access never
    qualifies. See `governance/BULLETIN.md` entries 013, 014 and 018.

---

## The three hardware nodes

| Hardware | Primary role | What runs there |
|---|---|---|
| **Jetson Nano** (`gary@192.168.1.223`) | Edge compute | Scout cron (10:15 AM + 8 PM ET), batch decoder (2 AM ET), FIMO scanning, paper ingest pipeline |
| **Yoga 9i** (RTX 5060, 32GB) | Primary workstation | Cursor, Claude Code, all local repos, `gsutil`, `gcloud`, `gh`, git operations |
| **Yoga 730** | Mobile / secondary | Daily reading, email, remote access to Claude Chat and Cursor via browser. Travel machine. Not used for cron or pipeline work. |

### Mobile access
Gary accesses Claude Chat via iPhone and iPad (claude.ai app). Cursor and Claude Code are
desktop-only.

---

## Naming convention

**Naming has no single convention — consult the repo↔Space table below for each asset's
actual name.** Historically the aim was kebab-case for URL-facing names, but in practice:

- Single-token names (`copernicusai`, `glmp`, `sciencevideodb`, `atap`, `shadow`) have
  nothing to hyphenate.
- Two assets split repo and Space spelling: `progframe` (repo) / `programming_framework`
  (Space), and `metadata-database` (repo) / `metadata_database` (Space).
- The four discipline-database stub repos (`biology-database`, `chemistry-database`,
  `computer-science-database`, `physics-database`) were deleted in the suite reorg
  (`governance/SUITE_REORG_PLAN.md`, Part 1); the collections are Methods & Tools
  demonstration corpus.

**Never guess a name from the pattern — copy it from the table below.**

**License convention:** data/content collections use **CC0-1.0** (maximally reusable, no
attribution burden); code/tooling repos use **Apache-2.0** or **MIT**. This is why the five
discipline databases are CC0 while `metadata-database` (tooling-oriented) is Apache-2.0 —
a deliberate data/code split, not an inconsistency.

---

## The science suite: repo ↔ Space map

The canonical mapping. These are the repositories in scope for Claude Code quality work
and for the multi-agent workflow. GitHub (`garywelz`) is the source of truth.

| HF Space | GitHub repo | Status / notes |
|---|---|---|
| `copernicusai` | `copernicus-web` | **Monorepo.** Root = Eliza-framework AI-agent website (Python, MIT). Static `copernicusai` Space content lives in `copernicus-web/huggingface-space/` (`index.html`, `papers-database-table.html`). Claude Code must target that subfolder, not the root. **Merges to `main` deploy production (Vercel):** project `copernicus-web-public` (team "Gary Welz's projects") serves www.copernicusai.fyi, whose domain is registered in the separate Vercel team Copernicus_AI; seven other Vercel projects also build from this repo on every push (inventory pending). |
| `glmp` | `glmp` | Project home / dashboard (HTML). Exact-name match. |
| `programming_framework` | `progframe` | Generator/tooling repo for the discipline databases (HTML, MIT). Underscore/legacy naming — see exceptions. Discipline data is migrating out to per-discipline repos. |
| `sciencevideodb` | `sciencevideodb` | YouTube-filtered science video DB, searchable by transcript (TypeScript). |
| `metadata_database` | `metadata-database` | Renamed from `copernicusai-research-metadata`. **Repo≠Space naming exception** (like `progframe`/`programming_framework`): GitHub repo is kebab-case, HF Space is snake_case. Apache-2.0. Its public face is the GCS-hosted table `papers-database-table.html` — a browsable/searchable view of the **same** Firestore corpus (current count in the
generated knowledge-engine-status.json published to GCS) that `copernicusai` surfaces. Division of labor: `copernicusai` = knowledge engine + podcast front end; `metadata_database` = the browse/search table. Not overlapping databases — two views of one corpus. Table file rename to **metadata-database.html** (planned name) pending (see open items). |
| `atap` | `atap` | Renamed 2026-07-23 from `mathematics-database` (HF Space + GitHub repo, both live and no longer stubs). Algorithms, axiomatic theories, and proofs as dependency graphs. Math content continues to migrate out of `progframe`. |
| *(none known)* | `tdap` | Engine, created 2026-09 with an outside domain collaborator (a hosted engine; see `governance/ENGINE_ONBOARDING.md`). Persistent cohomology and circular/toroidal coordinates. Public repo holds open questions, seed papers, hold list, and the collaborator's Claude Project instructions; corpus lives in the shared Firestore `research_papers` collection. No HF Space confirmed. |

### Engines vs. everything else
`glmp`, `atap`, and `tdap` are the suite's **engines** — each has a frontier and a
`research_focus.json` (the organizing test in `governance/SUITE_REORG_PLAN.md` §1).
Everything else in the table above is infrastructure, a browse/search surface, or
Methods & Tools output, not an engine.

Biology, chemistry, computer science, and physics are not engines — the four
discipline collections are Programming Framework demonstration corpus, worked
examples of applying the method, not discipline databases — per
`copernicus-web/huggingface-space/DISCIPLINE_DATABASES_PLAN.md`. No standalone repos
or Spaces. If these collections are built, they belong under Methods & Tools /
`progframe`, not as standalone per-discipline repos.

### Out of scope
`garywelz/shadow` (**Shadow of Lillya**, a creative-writing completion of Audrey Berger
Welz's novel) is **not** part of the science suite and is **not** managed under this
workflow. No agent touches it as science-suite work.

---

## Legacy / support repos (not Space sources)

To be audited, consolidated, or archived. None of these back a science-suite Space.

| Repo | Visibility | What it is | Disposition |
|---|---|---|---|
| `Copernicus_AI` | Private | Eliza-framework AI agent (legacy) | Audit → fold anything worth keeping into `copernicus-web` → archive |
| `copernicus-podcast-api` | Private | Podcast generation system for CopernicusAI | Audit — **confirm whether it's a live deployed service before folding**; media artifacts stay in GCS, never in git |
| `copernicus_backup` | Private | Podcast-generator backup | Archive (read-only, reversible) |
| `GraciePCat` | Private | Virtuals.io creative agent (`GraciePCat`) | Ignore — not a science project |
| `kickflip-docs` | Public | Fork of an unrelated video-SDK docs project | Ignore |

### Copernicus consolidation (decided, pending execution)
`copernicus-web` becomes the single home for the Copernicus platform — Knowledge Engine,
podcasting and future media generation, the copernicusai.fyi site, and the `copernicusai`
static Space. **Hard rule:** media artifacts (audio, video, large assets) live in GCS
(`regal-scholar-453620-r7-podcast-storage`), never in the git repo. The repo holds code,
static HTML/CSS/JS, and configs only. This is what keeps the consolidation from bloating
the repo.

---

## Working preferences

- Gary prefers dialogue before execution on anything significant. Claude Chat proposes and
  asks about goals before proposing solutions; Gary approves before work begins.
- Cursor asks explicit questions before proceeding on ambiguous tasks.
- Cursor reports in a four-section format:
  **what I found / what I did / what I'm uncertain about / what to discuss with Gary.**
- GitHub (`garywelz`) is the canonical source of truth for all repositories.
- **Run `copernicus-web/governance/check_citations.py` after any cleanout that
  moves files out of the tree, and before committing governance edits.** Added
  2026-08-04 after a cleanout left two dead file-path citations in
  `RESOURCE_MANIFEST.md` (the underlying facts were correct; only the evidence
  pointers rotted). The cleanout is the actual trigger — it's the step that
  silently breaks a citation, not the governance edit itself.
- **Anything handed across between agents regenerates from a fresh fetch
  before it's applied — never trust the artifact in hand.** Added 2026-08-04
  after three instances of the same failure in one session: Claude Code's
  shallow clone gave a false "no conflicts" read; Claude Chat's own working
  copy had a blocked `git pull` that silently reverted a fix, briefly making
  a landed patch look unlanded; and a script patch was built on a pre-docstring
  base and would have silently dropped an unrelated addition if applied
  verbatim. All three cost nothing because the receiving side re-verified
  against live `main` before acting — that won't always happen unless it's
  the default, not a judgment call made fresh each time.
- **An empty or surprising result is a claim about the instrument until the
  instrument is checked.** Added 2026-08-06 after five instances in two
  days, all caught the same way — by someone asking whether the tool could
  produce that answer for a boring reason before believing the answer said
  something about the world: trp operon Greek letters dropped by an encoding
  step, peroxisome names failing a case-sensitive match, the SOS tokenizer
  splitting on the wrong boundary, a regex reporting zero DOIs because of an
  unescaped paren, and an arXiv feasibility sweep reporting "no literature"
  for several terms because every multi-word query was a single quoted
  phrase requiring exact word-adjacency (`GLMP_MASTER_TODO.md` item 50).
  Five in two days is a property of this kind of work, not a streak — a
  zero or an outlier is exactly as likely to be the measurement breaking as
  the thing being measured being empty, and it doesn't announce which.
  Check the instrument before writing the finding down as being about the
  world.
- **Agreement between instruments is only evidence if the instruments
  could have disagreed.** Added 2026-08-06, same day as the rule above,
  after the rule above wasn't enough on its own: ATAP's first-pass
  acquisition run had two independent checks both report zero overlap
  with the existing corpus — a sampled top-5-per-term check, and an
  ingest script's `--dry-run`. They agreed, which read as confirmation.
  It wasn't: the dry-run's skip count was structurally incapable of
  detecting overlap at all (`batch.create()` staged but never committed,
  so the existence check never ran), and the sample simply hadn't drawn
  the 0.2% of terms with pre-existing hits. Two blind spots produced the
  same wrong number by coincidence, not two measurements confirming each
  other. Before treating agreement across methods as corroboration, ask
  whether either method was actually capable of returning the other
  answer — if one of them couldn't have said "yes, overlap," its
  agreement with the one that could is not information.
- **Instrument failures run in both directions — discarding the right
  signal, and retaining the wrong one — and the fixes are not the same
  kind of fix.** Added 2026-08-08. Every catch through the ATAP work
  was normalization throwing away a discriminating token (trp's Greek
  letters, peroxisome names, the `SOS` tokenizer, a quoted 4-gram
  requiring exact adjacency). GLMP's retroactive-attribution pass found
  the opposite: an embedding scored "CRP binding-site sets" highest
  against papers about C-reactive protein — a real, dominant meaning of
  that string in the wider biomedical literature, correctly retained,
  just not the meaning intended. The first kind is a code bug; the
  second is a declaration-wording problem, and a wording fix is not
  guaranteed to work — tried rewording to "cAMP receptor protein (CRP) /
  catabolite activator protein (CAP)" and re-scored before trusting it:
  the contamination did not clear, and spelling out "receptor protein"
  pulled in a second, broader kind of noise instead. Measure a
  reword's effect the same way a code fix gets measured, rather than
  reasoning that spelling out the full term ought to obviously work.

---

## Credential handling — standing rule

**Never `cat`, `od`, `head`, or otherwise print the full contents of a file that may hold
credentials** — `*.env`, anything named `*credentials*`, `*-sa.json`, or anything under
`.config/`. This binds every agent (Cursor, Claude Code, Claude Chat), not just whoever is
in the current task — it's now been two different agents in as many days.

To check such a file, use a targeted read that reveals only what's needed and nothing that
could reconstruct the secret:
- Presence / shape check: `grep -c PATTERN file`, or match on the variable name only.
- Identifying suffix, to compare against a known-key table: `grep PATTERN file | tail -c 9`
  — enough characters to identify *which* key it is, never enough to be useful to anyone
  who shouldn't have it.

**If a credential reaches output anyway, say so immediately** in the same turn, the way
Claude Code did when it found a plaintext OpenAI key while grepping `copernicus-jetson.env`
for Cloud Run URL references (2026-07-23) — don't bury it, don't keep working past it
silently.

---

## Open items
1. **Rename the table file** — `papers-database-table.html` → **metadata-database.html** (planned name) for
   naming consistency. This is a *live* file: update every reference in one pass (the Space
   `index.html` links, the generated knowledge-engine-status.json (gitignored;
   published to GCS), and the GCS copy under
   `regal-scholar-453620-r7-podcast-storage/`), and keep the old name reachable briefly so
   no inbound links break. Good careful Claude Code / Cursor task.
2. **Copernicus legacy audit** — inventory `Copernicus_AI`, `copernicus-podcast-api`,
   `copernicus_backup`; report live vs. dead vs. worth-keeping before any move/archive.
   Candidate Claude Code read-only test.
3. **Delete the dead `GEMINI_API_KEY` secret** — a provider key check on 2026-10-06 found it
   rejected as invalid, while `GOOGLE_AI_API_KEY` works. Do it in the cleanup batches, after
   confirming no Cloud Run revision still mounts it. No action before then.
4. **Replace the retired default model in `cloud-run-backend/services/llm_providers/claude_rag.py:28`**
   — `claude-3-5-haiku-20241022` returns not-found on the Anthropic API (2026-10-06). Change it to
   a pinned, dated model ID through the gated deploy procedure in `cloud-run-backend/DEPLOY.md`.
   No action now.

---

## Change log
- **v2.5** (2026-10-04) — Rule 18 extended from public GCS objects to Cloud Run IAM
  bindings and revision tags, with a propagation wait before probing an access removal
  and an emergency exception limited to changes that narrow access. See
  `governance/BULLETIN.md` entry 018.
- **v2.4** (2026-10-01) — Added session rules 17 (a security finding goes to a
  private location first, public only after the fix is live) and 18 (gate
  direct-to-GCS publishes of reader-facing objects like a Cloud Run deploy, with
  an emergency exception for security/data-exposure fixes), both adopted by Gary
  the same day. See `governance/BULLETIN.md` entries 014 and 013.
- **v2.3** (2026-09-30) — Jetson address updated to 192.168.1.223, now reserved on the
  router so it no longer changes.
- **v2.2** (2026-09-30) — Added session rules 14 (delete branches after merge or close),
  15 (gated deploys), and 16 (broken generated content is deleted, not repaired, with
  the archive protocol), making bulletin entries 008 and 009 standing rules; extended
  rule 5 for cached public objects; corrected Cursor's spend limit to account-wide.
- **v2.1** (2026-09-27) — Recorded in the repo↔Space map that merges to
  `copernicus-web` `main` are Vercel production deploys of the public podcast site,
  found when the v2.0 merge redeployed it.
- **v2.0** (2026-09-25) — **Moved** from `glmp/docs/AGENT_ROLES.md` (last blob there:
  v1.8, `ab3efe6752cd120815c10f81fea0d346a3b238e1`) to `copernicus-web/governance/`,
  since the document governs every engine, not GLMP alone; the old path keeps a pointer.
  Git history cannot cross repos — prior history stays in `glmp`. Reframed as
  suite-wide; added *Session rules* as the single home of the rules each `AGENTS.md`
  points to; added `tdap` to the map and the engine list; recorded that collaborator
  workspaces sit outside the shared context contract; recorded that only Gary's
  agents touch Core infrastructure; added the `tdap` Cursor Project; removed the deleted discipline
  stub repos from the naming notes and the fixed corpus count from the map.
- **v1.9** (2026-09-25) — Added Cursor Projects as a coordinator-mode agent surface
  (read-only + draft-PR autonomy, cloud limits recorded as findings) and a *Shared context
  contract* making GitHub the one shared medium across Claude Chat, Claude Code, and
  Cursor, with `AGENTS.md` per repo, versioned project headers, and `BULLETIN.md`.
- **v1.8** (2026-08-08) — Added a working preference: instrument
  failures run in both directions (discarding the right signal vs.
  retaining the wrong one) and need different fixes, after GLMP's
  retroactive-attribution pass found a "CRP" ambiguity that a wording
  fix, tried and measured, did not actually clear.
- **v1.7** (2026-08-06) — Added a working preference: agreement between
  instruments is only evidence if the instruments could have
  disagreed, after two independent zero-overlap checks in the ATAP
  first-pass run turned out to be two unrelated blind spots agreeing
  by coincidence, not confirmation.
- **v1.6** (2026-08-06) — Added a working preference: an empty or surprising
  result is a claim about the instrument until the instrument is checked,
  after five same-shape catches in two days, the most recent being a
  feasibility sweep undercounting arXiv literature because of an overly
  strict phrase-query construction.
- **v1.5** (2026-08-04) — Added a working preference: regenerate anything
  handed across between agents from a fresh fetch before applying it, after
  three same-day instances of an out-of-date artifact silently producing a
  wrong verdict (a shallow clone, a blocked local `git pull`, a patch built
  on a pre-docstring base).
- **v1.4** (2026-08-04) — Added a working preference: run
  `copernicus-web/governance/check_citations.py` after any cleanout and before
  committing governance edits, after a cleanout left two dead citations in
  `RESOURCE_MANIFEST.md`.
- **v1.3** (2026-08-03) — Added CI/GitHub Actions ownership section: Claude Code owns
  workflows for repos it already does self-contained work in (not Jetson/cron/pipeline
  CI, which stays Cursor's); read-only vs. side-effecting CI is the approval-relevant
  distinction, not authorship. Anchored to the first instance, `glmp`'s
  `glmp/.github/workflows/published-drift-check.yml`.
- **v1.2** (2026-07-23) — Added a standing credential-handling rule (never print
  secret-shaped files in full; targeted greps for presence/suffix only; flag immediately if
  a credential reaches output) after a live OpenAI key was found in a plaintext `.env` file
  during a Cloud Run audit.
- **v1.1** (2026-07-03) — Added authoritative GitHub repo↔Space map, five discipline
  databases, naming and license conventions, legacy/support repo audit table, Copernicus
  consolidation rule, open items.
- **v1.0** (2026-07-03) — Initial version. Four-agent model, three hardware nodes,
  six-Space science suite with Shadow of Lillya carved out, Claude Code documented as
  intent-with-evaluation.
