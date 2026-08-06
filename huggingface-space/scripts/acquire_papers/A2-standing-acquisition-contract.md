# A2 — The standing acquisition contract

**Drafted:** 2026-08-05 · **Status:** proposal, nothing implemented, but its
only blocker (field semantics, see sequencing step 1) is resolved as of the
same day. Filed as `GLMP_MASTER_TODO.md` item #46 — see that item for
verification of every claim below (all four checked against a fresh fetch of
both repos; claim 4, the reference count, corrected from 83/33 to 73/41) and
for the placement decision on the companion governance doc,
`governance/RESOURCE_MANIFEST.md`'s "Scope of a Resource collection"
subsection (`copernicus-web@75cb84e56`).
**Parent:** item #37 Part A · **Relates to:** #36 (scout tuning), #35 (video)
**Scope:** Engine Core — this document specifies *what* acquisition must satisfy.
*How* a scout ranks and queries is method development and belongs to
Methods & Tools.

---

## The finding

Both active projects already declare what they are looking for, in the same
schema:

| | GLMP | ATAP |
|---|---|---|
| `docs/research_focus.json` | present (updated 2026-07-26) | present (updated 2026-07-25) |
| `active_questions` | 2 | 4 |
| Per question | `q`, `terms`, `since` | `q`, `terms`, `since` |
| Other fields | `flagged`, `frontier`, `horizons`, `mute` | same, plus `categories` |

**Nothing in the acquisition system reads either file.**

`huggingface-space/scripts/acquire_papers/daily_scout_config.json` is a separate,
hand-maintained artifact: 10 PubMed queries and 4 arXiv queries, every one tagged
`discipline: biology`, with a target of 1,000 papers per run and per-source
weights (PubMed 0.5, bioRxiv/medRxiv 0.35, arXiv 0.15).

Two consequences:

1. **GLMP's scout is not tuned to GLMP's research focus.** It is tuned to
   biology in general. The config's own description says so: *"biology,
   regulatory circuits, computational genomics."* GLMP's actual open questions
   — CRP binding-site sets, PWM-grade activator evidence — appear nowhere.
2. **ATAP has no acquisition at all.** Not an untuned scout: zero queries. Its
   four questions, with search terms already written, reach nothing.

## What changes

The current system optimises **volume**: 1,000 papers per run, weighted across
sources. Under the 2026-08-05 reframe — four named researchers, the podcast as
an on-demand research instrument — volume is the wrong target. A corpus of
62,900 papers that lacks the 216 a project actually cites is worse than a
smaller corpus that has them.

**The contract's success measure is coverage — of the projects' declared
questions, and of the fields themselves — not throughput.** Volume may still be
substantial. It just isn't the target.

## The contract

Any scout, in any domain, must satisfy the following. This is the interface;
the ranking behind it is Methods & Tools' business.

### 1. Consume the declaration

Read `research_focus.json` from the project it serves. Treat
`active_questions[].terms` **and `frontier[].terms`** as acquisition
targets, both driving acquisition the same way — `frontier` questions are
longer-horizon and higher-stakes than `active_questions`, not lower-priority
or informational-only. Use `since` as the lower date bound per
`active_questions` entry. No separately maintained query list — a second
artifact is a second thing to drift, and `daily_scout_config.json` has
already drifted from both projects.

**Field semantics confirmed with Gary, 2026-08-05** (this section's own
open question, resolved the same day A2 was filed — see
`GLMP_MASTER_TODO.md` item 46):

- **`flagged`** — a curated list of priority seed papers (paper ID + a
  human-written justification note, e.g. "Jacob & Monod 1961 — foundational
  lac/operon regulation"). Always relevant, but **out of A2's scope, not
  in it** — corrected 2026-08-05, hours after this section was first
  written, once the consequence of "always-include" actually landed:
  a curated paper a researcher chose and justified is researcher-cited by
  another name. It routes through #43's already-proven path (same
  provenance shape, `citations` merge semantics already shipped and
  verified on 8 real cases), not through the scout. **A2 should not
  additionally acquire `flagged` papers itself** — doing so would put a
  resolved ingest problem back through an unbuilt one. Item 25's earlier
  use of `research_focus.flagged` as a retrieval seed stands on its own;
  it doesn't make `flagged`-consumption the scout's job.
- **`mute`** — a negative filter. Topics that might keyword-match but
  aren't wanted (GLMP: "CRISPR clinical trials"; ATAP: "cryptocurrency",
  "quantum supremacy claims"). Exclude these from acquisition outright.
  This one *is* A2's scope — a scout ranking/filtering decision, not a
  researcher-citation.
- **`frontier`** — drives acquisition, same as `active_questions` (see
  above) — not informational-only, despite reading like framing prose at a
  glance. Its own `terms` field exists for exactly this reason.
- **`horizons`** — adjacent-field awareness, included at lower priority.
  **This is the concrete mechanism for the adjacency principle in
  `governance/RESOURCE_MANIFEST.md`'s "Scope of a Resource collection"**
  ("admits work from adjacent disciplines... when semantic relationship
  earns it") — not a separate idea that merely resembles it. The
  governance text states the principle; `horizons` is where a project
  declares which adjacent fields it means. Not core to
  `active_questions`'/`frontier`'s coverage target, but not excluded
  either.

### 2. Attribute every candidate

Each acquired record carries **which question it was acquired for**. Not a
discipline tag — the specific `q`. Without it there is no way to measure
coverage, and no way to tell a researcher why a paper is in the corpus.

This mirrors #43's provenance fields, which are live and proven:
`acquisition_channel`, `cited_by`, `cited_context`. A scout-acquired paper
should be as explicable as a researcher-cited one.

**Calibration note, moved up from "What this leaves to #36" below so it sits
next to the requirement it actually bears on:** if attribution to a specific
`q` is ever made by similarity rather than an exact query match, the
2026-08-05 source-reselection exercise measured a **~40% false-positive
rate in its highest-confidence tier** using embedding similarity — after a
single validating case had suggested the method was reliable. The scoring
mechanism itself is #36's business, not specified here, but this number is
the calibration data point for whatever #36 builds, and it should travel
with the requirement, not sit only in the caution below where it's easy to
miss when actually implementing this one.

### 3. Route by domain, not by habit

GLMP's sources (PubMed, bioRxiv/medRxiv) will not serve ATAP. Mathematics needs
arXiv `math.LO`, `math.CT`, `cs.LO`, and likely zbMATH or similar. The source
set is a property of the project, read from its declaration or a per-project
routing table — not a global weight vector.

### 4. Accumulate evidence; never declare canonical

Per the 2026-08-05 reframe: charts are maps, revisable, and there may never be a
canonical version. Acquisition therefore **adds candidate evidence** and never
overwrites a chart's existing sources or elects a canonical one.

This is the direct lesson of `pick_canonical_source()`, which took `sources[0]`
with a DOI and no relevance check, and produced the #25 mess. A scout that
promotes its own finds to canonical repeats that error at scale.

### 5. Deduplicate against the whole corpus

Against all ~63,200 records, not just the current run. `deduplicate_papers.py`
exists; the contract requires it, and requires that a hit still record the new
attribution — the same gap that #45 covers for researcher citations. Learning
that a paper already present is *also* relevant to a newly declared question is
information, not a no-op.

### 6. Pass the stub gate on merit

The gate rejects only records with no usable title *and* no identifier, and runs
in `observe` mode by default. Scouts should not need an exception. If a
candidate cannot clear it, that is a signal about the candidate.

### 7. Report coverage, not counts

Per run, per project, per question: how many new candidates, how many
duplicates, how many failed to resolve. A question returning nothing for weeks
is a finding — either the terms are wrong or the field is quiet, and both are
worth knowing. A raw total of 1,000 tells you neither.

## What this leaves to #36

Everything about *quality*: query construction from terms, ranking, relevance
thresholds, precision/recall tradeoffs, whether embedding similarity beats
keyword matching for candidate scoring. Methods & Tools' work, against this
interface.

One caution to carry across: the 2026-08-05 source-reselection exercise measured
a ~40% false-positive rate in its highest-confidence tier using embedding
similarity, after a single validating case suggested otherwise. **One clean
validation is not a validation set.** Any relevance scorer needs a held-out
sample before it is trusted to filter acquisition.

## Sequencing

1. ~~**Confirm `mute` / `flagged` / `frontier` / `horizons` semantics**~~ —
   **done, 2026-08-05**, same day as filing. See "1. Consume the
   declaration" above for the confirmed meanings. This was the only
   remaining blocker on implementation — nothing else in this contract was
   waiting on a decision.
2. **ATAP first.** It has zero acquisition and a written declaration — the
   largest gap and the cleanest test, with no legacy behaviour to preserve.
   **ATAP's declaration is untested against reality (flagged 2026-08-05,
   not yet acted on).** Four questions with `terms`, written but never run
   against a live source. The first thing worth learning when this starts
   isn't a query-construction question — it's whether these terms return
   anything usable at all. A question returning nothing is itself a finding
   about the declaration (terms too narrow, too jargon-specific, wrong
   source entirely), not just a null result to route past. Pairs naturally
   with item #48 (218 of 237 ATAP process files have no source citations
   at all) — same underlying gap, seen from the acquisition side and the
   corpus side.
3. **Migrate GLMP** from `daily_scout_config.json` to its declaration, with the
   old config retained until coverage reporting shows the new path is no worse.
4. **Retire `daily_scout_config.json`** only once (3) holds.

## Resolved 2026-08-05

**The two projects share one corpus.** Decided, not inferred: GLMP and ATAP are
both Gary Welz's projects and this is his working literature. The foundational
papers make the case concrete — 73 references across paper-I, paper-II, and
paper-III (independently re-counted; the draft's original 83 was a count of
unrelated numbered lists elsewhere in the documents, not just the reference
sections — see `GLMP_MASTER_TODO.md` item 46), mixing homotopy type theory with
*E. coli* network motifs in the same argument. GLMP retrieval seeing category
theory is the intent, not a side effect. A different scientist with different
projects would have a different collection; the collection is indexed to a
research programme, not a subject heading.

**The volume target is wrong in kind, not in magnitude.** The collection should
be large — many thousands of papers, comprehensive enough within molecular
genetics and within logic/foundations that a specialist could name a work and
find it, from the classics through to current preprints. What the 1,000/run
target gets wrong is that the number is the goal and the queries are generic.
Undirected volume, not volume. A run acquiring 1,000 papers against declared
questions and coverage gaps is working correctly.

See `governance/RESOURCE_MANIFEST.md`'s "Scope of a Resource collection"
subsection for the full governance statement (placed 2026-08-05,
`copernicus-web@75cb84e56`).

## Open questions

1. **Databases as sources.** RegulonDB, JASPAR, and similar are structured
   evidence, not papers. Gary flagged database sources as under consideration;
   whether they enter through this contract or a separate path affects the
   schema.
2. **Who maintains the declarations?** `research_focus.json` becomes
   load-bearing under this design. If it goes stale, acquisition quietly drifts
   — the same failure mode as the governance docs, which is why those now carry
   a "last verified" field.
