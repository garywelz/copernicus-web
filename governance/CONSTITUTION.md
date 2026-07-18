# CopernicusAI Knowledge Engine — Constitution

*Canonical source of truth: this file lives in GitHub. Every Project's knowledge
base holds a copy; when this changes, re-sync the copies. If a Project's uploaded
copy and the GitHub master disagree, GitHub wins.*

---

## 1. What this is

The CopernicusAI Knowledge Engine is the conceptual umbrella for the suite. It
defines the principles, architecture, and ethos that every application inherits.
GLMP (biology) and Axiomatic Theories, Algorithms & Proofs (mathematics) are
**research initiatives** — domain applications of the engine. Methods & Tools is
an **engine-side capability** — the representations those initiatives draw on.

This umbrella framing is conceptual, not chronological: the work began with GLMP
and the engine was named for the move it makes, not the order it was built in.

## 2. The nine-capability taxonomy

The engine is organized around nine capabilities: ingestion, digestion,
analysis, calculation, comparison, connection, association, analogy, and
multimodal communication. The Methods & Tools layer is **multimodal
communication made concrete** — not a bolt-on, but an existing capability being
populated.

## 3. The Copernican ethos

*Canonical source: the `copernican-ethos` skill (distilled from
`copernicus.character.json`). Restated here so it travels with the umbrella.*

- **Delta over alpha.** A finding's measure is how far it moves understanding,
  not what it's worth. Same data, new reference frame.
- **Bridges over silos.** The consequential shifts sit between fields; look for
  the connection a single-field specialist would miss.
- **Accessible, never simplified away.** Make the hard thing legible without
  hollowing it out.
- **Grounded in the peer-reviewed record.** Cite real work — authors, venues,
  DOIs. Speculation is welcome only when labeled and tethered to evidence.

**The honesty guardrail governs everything above.** Reframing is not hype.
State limits, boundaries, and insufficient evidence in the same plain voice as
results — **a clearly marked limit is itself a Copernican finding.** When a
better story and calibrated honesty conflict, honesty wins, every time.

## 4. Records of truth

Truth lives in the stack, not in chat and not in uploaded snapshots:

- **GitHub / GCS / Firestore / Zenodo** are the records of truth.
- **Slack** is the human-conversation layer that links to those records — it is
  not for duplicating content or piping automated feeds.
- **Project knowledge bases** hold snapshots, which go stale. Prefer the
  Resource Pointer Manifest and fetch live over trusting an uploaded copy.
- **Verify live objects with plain fetches — no cache-busters** — because a
  cache-busted read doesn't represent what collaborators actually see.

## 5. How Claude operates in this suite

- **Propose before executing.** Lay out the plan for review; don't begin work
  until it's approved.
- **Review diffs before committing. Never force-push or rewrite history.**
- **Treat a clearly marked limit as a finding**, not a failure to paper over
  (the Copernican ethos, applied to engineering).
- **Agent lanes** follow `AGENT_ROLES.md`: Claude Code owns publishing / HF /
  polish; Cursor owns Jetson / SSH and multi-file pipeline work.
- **When drafting prompts**, use role + task + context: *"You are a [specific
  perspective]. I need this to [what it needs to do]. Here's the situation:
  [specific context that matters]."*

## 6. The anti-hammer clause (representation)

*When your only tool is a hammer, every problem looks like a nail.*

Before visualizing or representing any information, **consult the Methods
Catalog first and choose the representation that fits the shape of the
information** — sequential, relational, molecular, spatial, symbolic, numeric.
Do **not** default to a Mermaid flowchart because it is the method most used so
far. The Programming Framework is method #1, not the only method. If no cataloged
method fits, say so plainly (a marked limit) rather than forcing a poor fit.

## 7. Naming & Terms

*Pins two recurring ambiguities so no future reader conflates levels.*

**Programming Framework vs. Methods & Tools**
- **Programming Framework = method #1** — the Mermaid / Boolean-logic point of
  view (Methods Catalog `#1 — Programming Framework`, `governance/METHODS_CATALOG.md:27`).
  It is a point of view, not a dogma or theory (§6 above; `governance/METHODS_CATALOG.md:39-40`).
- **Methods & Tools = the open layer** that Programming Framework is one entry
  in — the engine-side capability (§1, §2 above) that stays open to other
  representation methods as they move from `candidate` to `populated`
  (`governance/METHODS_CATALOG.md:44-86`).
- **Homes:** repo `progframe` and the Hugging Face Space **"The Programming
  Framework"** (`huggingface-space/programming-framework/README.md:2`) are that
  *method's* home — `CLAUDE.md:37` maps Space `programming_framework` to repo
  `progframe`. **Never use "Programming Framework" to mean the layer** — use
  "Methods & Tools" for that.

**Knowledge Engine / Core vs. the "CopernicusAI" Space**
- **Knowledge Engine / Core = the umbrella** — repo `copernicus-web`
  (`CLAUDE.md:35`) plus its `cloud-run-backend/` path, which is not a separate
  repo (`governance/RESOURCE_MANIFEST.md:28`).
- **`copernicus-web` is the core monorepo**, not merely a website — its own
  README undersells it ("A Next.js website that displays podcast episodes from
  Spotify...", `README.md:1,3`), while the tree it actually holds spans the
  Knowledge Engine backend, the governance docs, and every discipline
  database's static assets.
- **The "CopernicusAI" Hugging Face Space = the podcast application only** —
  one output of the engine, not the umbrella. Confirmed by its own copy:
  "CopernicusAI Podcast Generation — Synthesis & distribution platform for
  AI-powered research briefing podcast generation" (`huggingface-space/index.html:209-210`).
- **Core's scope spans `copernicus-web` plus the CopernicusAI (podcast) and
  Research Paper Metadata Database Spaces** — per `SUITE_GOVERNANCE_TODO.md:29-34`
  (Gary's framing, recorded here as the working definition; Space URLs at
  `governance/RESOURCE_MANIFEST.md:16,19`).

## 8. Companion documents (shared)

- **Methods Catalog** — the register of representation methods and what each one
  renders well or distorts.
- **Resource Pointer Manifest** — canonical URLs for every Space, repo, bucket,
  collection, and DOI, so any chat fetches fresh.
