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
