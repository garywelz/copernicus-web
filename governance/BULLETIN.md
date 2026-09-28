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
