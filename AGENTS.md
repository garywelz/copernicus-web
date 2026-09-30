# AGENTS.md — copernicus-web

Read by every agent that works in this repo: Claude Code (via `CLAUDE.md`), Cursor (local
and Cursor Projects), and Claude Chat. This file holds only pointers and facts specific
to this repo. **Everything shared lives in one place:**
https://raw.githubusercontent.com/garywelz/copernicus-web/main/governance/AGENT_ROLES.md

## Before you do anything

Fetch these live, with plain fetches (no cache-busters). GitHub wins over any uploaded,
remembered, or pasted copy.

- Agent roles, lanes, session rules, repo↔Space map: https://raw.githubusercontent.com/garywelz/copernicus-web/main/governance/AGENT_ROLES.md
- Constitution: https://raw.githubusercontent.com/garywelz/copernicus-web/main/governance/CONSTITUTION.md
- Bulletin (read the newest entries): https://raw.githubusercontent.com/garywelz/copernicus-web/main/governance/BULLETIN.md

Then follow the **Session rules** and your lane in `AGENT_ROLES.md`, and report in its
four-section format. If this repo has `docs/GOVERNANCE_LOCAL.md`, read it too: it may add
to or tighten the shared rules, never loosen their invariants
(`governance/ENGINE_ONBOARDING.md` §3).

## The floor — holds even if the fetch fails

1. Propose before executing; Gary approves significant changes first.
2. Never force-push or rewrite history; no autonomous or triggered run pushes to `main`.
3. Never print credential-shaped files in full; if one reaches output, say so at once.

*(Deliberately duplicated in every repo's `AGENTS.md`; canonical text is in
`AGENT_ROLES.md` → Session rules. Change it there first.)*

## This repo

- **Knowledge Engine Core** — the umbrella's shared plumbing and production
  infrastructure: corpus, embeddings/retrieval, ingestion, cron/status, generators.
  Method development belongs to Methods & Tools, not here.
- **`governance/`** is the canonical home of all suite governance. Run
  `governance/check_citations.py` before committing any governance edit and after any
  cleanout that moves files.
- The `copernicusai` static Space lives in `huggingface-space/`, not the repo root.
  `cloud-run-backend/` is a path in this repo, not a separate repo.
- Deploy-coupled engine content (including ATAP's math processes) stays here per the
  Reorg Plan's Option B, even when an engine owns it conceptually.
- **A merge to `main` is a production deploy.** Vercel builds this repo on every push
  (previews on branches, production from `main`). The Vercel project
  `copernicus-web-public` serves the public podcast site, www.copernicusai.fyi, whose
  episodes feed the podcast's RSS distribution. Treat every merge to `main` — a
  documentation-only one included — as publishing.
- **Deploys of `copernicus-podcast-api` (Cloud Run) follow
  `cloud-run-backend/DEPLOY.md`.** `cloud-run-backend/cloudbuild.yaml` builds and
  pushes the image only — it does not deploy, and a merge to `main` never touches
  this service.
