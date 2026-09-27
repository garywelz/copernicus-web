# Engine Onboarding — adding a Knowledge Engine to the suite

*Canonical home: `copernicus-web/governance/ENGINE_ONBOARDING.md`. Version 0.2
(2026-09-27). Distilled from TDAP, the suite's first engine shared with an outside
researcher; each step records TDAP's status so this file doubles as TDAP's audit.
§3 and §5 were decided by Gary on 2026-09-27 and bind every engine.*

---

## 1. Does it qualify?

An engine is the scope over which one `research_focus.json` makes sense: a real
frontier belonging to a real researcher, with questions the literature can answer and
frontier questions where the engine must hand off (`governance/SUITE_REORG_PLAN.md` §1).
A discipline is not an engine. If one focus file can't be honestly maintained for it,
it isn't one yet — say so plainly.

## 2. Two arrangements

| | **A. Hosted engine** (TDAP) | **B. Federated engine** |
|---|---|---|
| PI | Gary | The other researcher |
| Owns the research questions | The domain collaborator | That PI |
| Repo | `garywelz/<engine>`, public | The PI's own account, public |
| Merge gate on `main` | Gary | That PI |
| Local governance (§3) | Gary, with the collaborator's input | That PI |
| Core governance version | Tracks `main` | Pinned to a tagged release, upgraded deliberately |
| Corpus writes (shared Firestore) | Core, run by Gary's agents | Core, on the PI's request (see §5) |
| Their AI workspaces | Collaborator's own Claude via `<engine>/docs/project_instructions.md`; not suite agents; never touch Core | The PI's own agents, bound by the PI's `AGENTS.md`, not by suite lanes; never touch Core |

In both, the public repo is the only shared surface: collaborators contribute through
issues and pull requests, and private work never enters the suite's records.

## 3. Governance inheritance: a shared core plus a local layer — **adopted 2026-09-27**

Every engine inherits the suite's core governance (`governance/CONSTITUTION.md`, the
session rules in `governance/AGENT_ROLES.md`, `governance/METHODS_CATALOG.md`). Each
engine may add a **local layer** in its own repo at `<engine>/docs/GOVERNANCE_LOCAL.md`, owned by
that engine's PI, for the features a particular researcher wants.

**Invariants — a local layer may tighten these, never loosen them:**
1. The honesty guardrail: limits stated as plainly as results; a marked limit is a finding.
2. Records of truth live in version-controlled or persistent stores, not in chat.
3. No force-pushes or history rewriting.
4. The credential-handling rule.
5. Propose before executing anything that writes, deploys, or publishes.
6. Nothing unpublished — a collaborator's drafts, data, or correspondence — enters a
   public repo without that person's consent.

**Defaults — a local layer may change these:** agent lanes and which tools are used;
report format; cadence of recurring work; license; which Methods Catalog entries apply;
acquisition sources and scout settings; naming conventions; anything added on top.

**Precedence:** invariants, then the local layer, then core defaults. A local rule that
would loosen an invariant is not applied; it is raised with Gary as a marked limit.
Good local rules can be proposed upstream as a pull request to `copernicus-web`.

**Governance release tags — adopted 2026-09-27.** Hosted engines track `main`.
Federated engines fetch core governance at a release tag, so a change to the core never
silently changes another PI's rules:

- **Name:** `governance-vMAJOR.MINOR` on `copernicus-web`, starting at `governance-v1.0`.
  This versions the governance set as a whole, independent of any one file's version.
- **Fetch form:** https://raw.githubusercontent.com/garywelz/copernicus-web/governance-v1.0/governance/CONSTITUTION.md —
  raw fetches at a tag were confirmed to work on 2026-09-27 against an existing tag.
- **MAJOR** when an invariant changes or a federated engine must act; **MINOR** for
  additions and clarifications.
- **Tags are immutable** — never moved or deleted, the same rule as no history
  rewriting. A mistake is fixed by a new tag.
- **Who:** Gary, or an agent he directs, after the tagged commit is on `main`. Each tag
  gets a `governance/BULLETIN.md` entry saying what changed and whether federated
  engines need to act.

## 4. Checklist — Arrangement A (hosted)

Status column is TDAP as of 2026-09-27.

**Phase 1 — Agreement (people before code)**

| Step | TDAP |
|---|---|
| Frontier passes §1; who owns the questions is written down | Done |
| Consent on public naming: name, email, affiliation in public files | README: removal in the pending `tdap` PR; name remains in other `tdap` docs, in `papers/TDAP_BACKFILL_RECON_2026-09-19.md`, and in git history |
| License confirmed with the collaborator | Open — CC0 mirrored as default |
| Visibility agreed: the fetch-live pattern needs a public repo | Done — public since 2026-09-19 |
| Roles of advisors or institutions left to the collaborator to define | Done |

**Phase 2 — Engine repo**

| Step | TDAP |
|---|---|
| Repo with README, including a "Using <engine> inside your own Claude" section | Done |
| `<engine>/docs/research_focus.json` using the A2 contract fields (`huggingface-space/scripts/acquire_papers/A2-standing-acquisition-contract.md`) | Done — questions provisional |
| `<engine>/docs/project_instructions.md`: collaborator-owned instructions for their own Claude | Done (v0.3) |
| `<engine>/docs/seed_papers.md` with full titles and verified identifiers, not authors alone | Done |
| `AGENTS.md` + one-line `CLAUDE.md` | In the pending governance PR |
| `<engine>/docs/GOVERNANCE_LOCAL.md`, if the collaborator wants local rules | None yet |

**Phase 3 — Corpus (Core)**

| Step | TDAP |
|---|---|
| Question ids named `<engine>-qN` | Done |
| Seed intake with `huggingface-space/scripts/acquire_papers/researcher_cited_intake.py`, then ingest from an **isolated directory** (the default root is the whole local mirror) | Done |
| Expansion with `huggingface-space/scripts/acquire_papers/citation_expansion_pilot.py` using `--cited-project` and `--seed-doi-file`; dry run first, review, then `--write` | Done — 130 papers |
| Embedding with `cloud-run-backend/scripts/backfill_research_paper_embeddings.py` | Done — 130/130 |
| Video sweep config in `sciencevideodb/packages/ingestion/sweeps/` | **Not done** — no `tdap-*` config |

**Phase 4 — Surfaces**

| Step | TDAP |
|---|---|
| Entry in `lib/knowledge-engine-projects.ts` (`KEProjectId`, `KE_PROJECTS`, `KE_PROJECT_IDS`) | Done |
| Question labels in `BROWSE_QUESTIONS`, `components/knowledge-engine/constants.ts` | **Not done** — no `tdap` entries on `main` |
| Question ids in `INITIATIVE_QUESTION_IDS`, `huggingface-space/scripts/generate_status_page.py` (hand-maintained: undercounts silently if stale); republish the status JSON | Done |
| `PROCESS_FAMILY_COLLECTIONS`, in both `cloud-run-backend/endpoints/content/routes.py` and `cloud-run-backend/services/knowledge_map_service.py` — only if the engine has a chart family | N/A — deferred |
| Frontend deploy via `cloudbuild-frontend.yaml`. There is no CI/CD: pushing to `main` does not deploy | Done |

**Phase 5 — Governance registration**

| Step | TDAP |
|---|---|
| Row in the repo↔Space map, `governance/AGENT_ROLES.md` | In the pending governance PR |
| Repo prefix in `SIBLING_REPOS`, `governance/check_citations.py` | In the pending governance PR |
| Entry in `governance/RESOURCE_MANIFEST.md` | **Not done** |
| Blocks in `governance/PROJECT_HEADERS.md` for any Claude or Cursor Project of Gary's | Cursor Project created 2026-09-27; header in the pending governance PR |
| Entry in `governance/BULLETIN.md` | In the pending governance PR |
| Named in Constitution §1 alongside GLMP and ATAP | In the pending governance PR (decided 2026-09-27) |

**Phase 6 — Limits to tell the collaborator up front**

- Choosing a project in the Knowledge Engine changes framing and chart filtering, but
  does not yet scope paper, podcast, or video search to that project.
- The corpus is metadata-first and seed-anchored: strong on foundations, thin on
  recent work that cites the seeds.
- External sources rate-limit (Semantic Scholar especially); an empty result is an
  instrument question first.

## 5. Arrangement B (federated) — what differs — **decided 2026-09-27**

- **Repo and merge gate belong to the other PI.** Their `AGENTS.md` and local layer are
  theirs; the suite can suggest, not require, beyond the §3 invariants.
- **Governance is fetched at a pinned tag** (§3), so the engine opts into each change.
- **Core access: only Gary's agents touch Core infrastructure.** No other PI's agents,
  and no collaborator's, may touch Firestore, GCS, Cloud Run, the Jetson, or the HF
  Spaces. If the engine uses Core's corpus, Gary's agents run the writes; the PI
  requests them by pull request to their seed file or focus file. Their records are
  tagged by `cited_project`, so they stay separable.
- **Costs:** Core's compute and API costs are borne by Gary Welz.
- **Departure:** when a PI leaves, their engine's records are stored in Gary's archives.
  Not yet decided: whether the departing PI also receives a copy.
- **Credit:** suite outputs — podcasts and others — credit the engine by its project
  title (e.g. "TDAP").
- **Registration** is the same as Phase 5, with the map row marked *federated* and the PI
  named only with their consent.

## 6. Lessons TDAP paid for

- **Relay full titles and identifiers, not author names.** One seed was mis-resolved
  because a hand-off carried "Perea" rather than the paper's title.
- **An intake script that "writes" may only write a local file.** Read a script's own
  output before assuming it reached Firestore.
- **Default-argument parity must be tested, not asserted.** A TDAP-motivated change
  silently enlarged GLMP's default admissions until a before/after DOI-set comparison
  caught it.
- **A toggle is chrome until scoping is built.** A project selector that changes labels
  can make results look scoped when they aren't.
