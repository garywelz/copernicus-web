# Architecture Review Phase 2, Gap 1: Engine Scoping

*Follow-up to `system_map.md` (Phase 1). Status date 2026-10-04. Read-only
investigation plus an in-progress build, tracked here per
`governance/AGENT_ROLES.md` rule 11 (write durable context back to
GitHub).*

## Situation

The GLMP/ATAP/TDAP toggles on `copernicus-frontend` are chrome-only
(`lib/knowledge-engine-projects.ts`'s own header comment says so). Search,
Ask Questions, Browse, the Knowledge Map, and semantic search all draw on
the full `research_papers` corpus regardless of which project is
selected. Papers carry per-question tags in `question_scope_ids` (GLMP
45,748, ATAP 3,462, TDAP 130; 58.7% untagged, confirmed live 2026-10-02).

## Gary's decision (2026-10-02)

An engine toggle scopes retrieval strictly to that engine's tagged
papers. **v1 drops "include general corpus"** (decided 2026-10-04,
revising the original proposal) — there is no option to widen a scoped
query back out; "All projects" (no `engine` param) stays exactly as
today, fully unscoped.

## What's been investigated

Full findings (every retrieval path's endpoint/mechanism/file:line,
vector-index requirements, how `question_scope_ids` gets assigned, and
the engine-registry gap) are in this conversation's record and in
`copernicus-web` PR #32's description and commit messages — not
duplicated here. Headline findings:

- Browse, RAG, and Knowledge Map already had a proven single-tag
  `question_scope_ids ARRAY_CONTAINS` pre-filter pattern in production
  before this work started; Search had none at the route level despite
  its underlying function supporting it.
- No engine registry existed. `config/engine_registry.py` (PR #32) is the
  first one.
- `question_scope_ids` is written only by two manual scripts
  (`citation_expansion_pilot.py`, `researcher_cited_intake.py`) — never
  by daily ingestion. This is gap 1b, below.
- A composite vector index (`question_scope_ids` + `embedding`, 1536-dim)
  was created and tested 2026-10-04: `find_nearest()` accepts an
  `array_contains_any` pre-filter, and scoping to GLMP's ~45,748-doc
  candidate set measured faster than an unscoped search, not slower.

## Build status

- **PR #32** (`gap1-engine-registry-browse`): engine registry + `engine`
  param on `GET /api/content/browse`, papers only. Draft, not merged, not
  deployed, per Gary's explicit instruction throughout.
- **Not started**: RAG, Search, Knowledge Map, and the frontend toggle —
  explicitly deferred to a separate PR after #32 merges.

## Open design item, recorded here, not built: "gap 1b"

**Auto-tag newly ingested papers against each engine's
`research_focus.json` questions at ingest time.**

Today, routine daily ingestion (the Jetson scout cron, the four batch
acquisition scripts) never writes `question_scope_ids` at all —
confirmed by grep across every ingest script in the suite. Tagging only
happens via the two manual scripts named above. This is the direct,
confirmed explanation for why 58.7% of the corpus is untagged: it isn't
that most papers don't matter to any engine, it's that nothing routine
ever tags them.

Building gap 1b would mean: at ingest time (or as a follow-up batch job),
score each newly-acquired paper against every engine's declared
`active_questions` (the same term/seed matching logic the manual
citation-expansion and researcher-cited-intake scripts already use) and
write `question_scope_ids` automatically where it clears whatever
threshold those scripts use today. This would keep corpus coverage from
continuing to drift away from what engines have actually declared, and
would feed `config/engine_registry.py`'s own drift check
(`scripts/check_engine_registry_drift.py`, PR #32) a shrinking gap
instead of a growing one.

**Not built.** Scoping, threshold selection, and whether this runs
synchronously at ingest or as a nightly batch are all open questions for
whoever picks this up — this entry exists so the gap is on the record,
not to pre-decide its design.
