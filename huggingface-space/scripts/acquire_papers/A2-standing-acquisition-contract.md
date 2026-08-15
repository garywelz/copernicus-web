# A2 — The standing acquisition contract

**Drafted:** 2026-08-05 · **Status:** proposal, nothing implemented, but its
only blocker (field semantics, see sequencing step 1) is resolved as of the
same day. Filed as `GLMP_MASTER_TODO.md` item #46 — see that item for
verification of every claim below (all four checked against a fresh fetch of
both repos; claim 4, the reference count, corrected from 83/33 to 73/41) and
for the placement decision on the companion governance doc,
`governance/RESOURCE_MANIFEST.md`'s "Scope of a Resource collection"
subsection (`copernicus-web@75cb84e56`).
**Parent:** item #37 Part A · **Relates to:** #36 (scout tuning), #35 (video),
A1 (chart-source backfill)
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
or informational-only. No separately maintained query list — a second
artifact is a second thing to drift, and `daily_scout_config.json` has
already drifted from both projects.

**Two acquisition modes, not one — found 2026-08-06 running ATAP's
declaration against live arXiv (`GLMP_MASTER_TODO.md` item 50).**
`since` is the lower date bound for **standing acquisition** — the
ongoing, windowed mode this contract otherwise assumes. It is the wrong
bound for a project's **first pass**: ATAP's `since` dates predate almost
none of the relevant literature (windowed counts ran 10–60× smaller than
unwindowed on nearly every term tested — "diagonalization" 382 all-time
vs. 7 since `2026-07-01`), so a windowed-only first run would look broken
when it's actually just working through a backlog nobody ever ingested.
**A project's first run under this contract should ignore `since`
entirely** — a one-time historical/frontier sweep — and only switch to
`since`-bounded standing acquisition once that backlog is caught up.
Which mode is running should be an explicit, loggable state, not inferred
from whether `since` happens to be old.

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
  **Amendment, 2026-08-08, from GLMP's retroactive-attribution run
  (`GLMP_MASTER_TODO.md` item 52) — `flagged` gains a second role: query
  anchors, not just always-include records.** Scoring the corpus
  against a `terms`-derived question string hit a real limit: short,
  ambiguous strings ("CRP") pull in whatever a large biomedical corpus
  associates with that string's *dominant* meaning, and rewording the
  question text to spell out the intended meaning made it *worse* (see
  below) rather than fixing it. Scoring against a flagged paper's own
  embedding instead — paper-to-paper similarity, not text-to-paper —
  sidestepped the ambiguity entirely and produced a decisively cleaner
  candidate set, because the paper's actual content carries no register
  for the wrong meaning to begin with. **This is a researcher's judgment
  entering retrieval directly, without the lossy step of describing what
  they want in words** — `flagged`'s justification note is *why* it's a
  good anchor; the paper *is* the anchor. Out of scope still: `flagged`
  papers are not additionally acquired by A2 (per the paragraph above,
  unchanged). In scope now: `flagged` papers (and other known-relevant
  seeds — a researcher-cited paper works the same way) can be **used as
  scoring anchors** for `active_questions`/`frontier` attribution, as an
  alternative or supplement to embedding the question's own text.
  **Tested same day, and the fix isn't "combine more seeds":** ran
  mean/union/intersection across all 6 available seeds (5 flagged +
  Lents' citation) predicting mean would be cleanest — instead all
  three combination methods drifted toward a broader "synthetic gene-
  circuit engineering" theme, off the question's specific target,
  because only 1 of the 6 seeds was actually about this question;
  the other 5 are flagged for GLMP's programme generally. **Seed
  selection has to be per-question**, using only seeds relevant to
  that specific question — sometimes just one, which is a property of
  a well-scoped question, not a shortfall. `flagged` papers are
  project-level judgments, not pre-tagged to a specific
  `active_questions`/`frontier` entry, so treating the whole list as
  one combined anchor set dilutes whichever seed was actually on-topic.
  Whether mean/union/intersection differ *given a correctly-scoped seed
  set* is still untested and still #36's business — this only rules out
  "combine everything flagged."
  **Schema gap this exposed, and the fix, decided 2026-08-08:** neither
  `flagged` nor `active_questions`/`frontier` had anywhere to record
  *which question a seed anchors* — `flagged` entries carry only `id`
  and `note`, no question association, which is exactly why all 6 got
  combined indiscriminately above. Two ways to close it: a `questions`
  back-reference on each `flagged` entry, or a `seeds` list on each
  `active_questions`/`frontier` entry. **Chose the second.** The first
  needs something stable to reference, and `active_questions` entries
  have no ID — only free-text `q` — so a back-reference would have to
  match question text verbatim and silently break on any rewording
  (which happened to this very question, this same session). A `seeds`
  list living inside the question object needs no cross-reference at
  all, and it reads the way the file is actually consumed — one object
  per question carries its own text, terms, *and* anchors, and the
  scoring pass reads one object. Added to `research_focus.json`:
  `active_questions[0].seeds` and `frontier[0].seeds`, populated only
  with the two evidence-justified papers from this session's own
  testing (`pubmed_35648826`, explicitly noted as a direct CRP seed;
  Lents' citation, item 43's original test case, historically tied to
  "the cAMP-CRP question Lents was working"). Not bulk-populated from
  the rest of `flagged` — that's the mistake this whole test surfaced.
  A paper can be both a project-level `flagged` entry and a
  question-level `seeds` entry (or a `seeds` entry without being
  `flagged` at all, as Lents' citation is) — the two fields serve
  different roles and neither implies the other.
  **Consequence, not a blocker:** active-question-1 now has exactly 2
  seeds, still short of a meaningful test of mean-vs-union-vs-
  intersection (that needs a seed set large enough for the methods to
  actually diverge). **The growth path is already built, not
  hypothetical:** every paper a researcher cites through #43 while
  working a specific question is a candidate seed for that question,
  with the justification already captured in `cited_context`. Closing
  that loop — #43 recording *which question* a citation was made
  for, so it can feed straight into that question's `seeds` — is real
  future work, not built here, and not guessed at either.
- **`mute`** — a negative filter. Topics that might keyword-match but
  aren't wanted (GLMP: "CRISPR clinical trials"; ATAP: "cryptocurrency",
  "quantum supremacy claims"). Exclude these from acquisition outright.
  This one *is* A2's scope — a scout ranking/filtering decision, not a
  researcher-citation.
  **Limit, found 2026-08-08:** `mute` excludes a known-irrelevant
  *topic*; it does not correct a query that's matching on the wrong
  *dimension*. Tested directly: muting the specific contaminating
  cluster a mis-scoped question pulled in (C-reactive protein, for a
  question meaning cAMP receptor protein) removed that cluster and
  immediately exposed a different one underneath (generic protein-
  benchmark/biomarker papers) — same underlying cause, different
  symptom. If a dimension is producing off-target hits because the
  scoring text itself is ambiguous or too generic, the fix is a better
  anchor (see `flagged` above) or better question wording, not a longer
  `mute` list chasing each new cluster mute reveals.
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

**Thresholds are per-question or they are not thresholds — found
2026-08-06, ATAP's first-pass run (`GLMP_MASTER_TODO.md` item 51).**
Relevance scores from the same scoring mechanism are not comparable
across questions: one frontier question's entire score range sat below
another active question's 10th percentile, because the active question
dominated the sweep (54% of all candidates) and had denser, more
central literature. A single global cutoff tuned to look reasonable
against the dominant question would have silently deleted the thin
question's candidates while looking like ordinary filtering — not a
visible failure, a quiet one. This is worse precisely where it matters
most: `frontier` questions are higher-stakes and longer-horizon than
`active_questions` per requirement 1 above, not lower-priority, so a
mechanism that disproportionately erases them inverts the contract's
own priority. **Any pruning against a relevance score must be scored
and thresholded within each question's own distribution, never pooled
across questions.** This binds #36's scorer design, not just this
run's one-off choice not to set a threshold at all.

**Every write to `acquisition_matches` (or `cited_for_question`) must also
merge the same question id into `question_scope_ids` — found 2026-08-09,
`GLMP_MASTER_TODO.md` item 53's over-fetch fix.** `acquisition_matches` is
an array of maps; Firestore cannot `array_contains`-query into it, so
scoped retrieval (`search_semantic()`, `knowledge_map_service`'s
`_seed_papers_by_vector`) depends on a flat, indexable mirror of exactly
what's already attributed. This was backfilled once for every doc that
had it missing (8,475 docs, 2026-08-09) — but a backfill is a snapshot,
not a guarantee. Any future one-off scoring/write script (the pattern
every question sweep so far has used) that adds an `acquisition_matches`
entry without also `ArrayUnion`-merging into `question_scope_ids` quietly
re-opens the exact bottleneck the backfill just closed for that one
paper — a *silent* regression, since the paper still shows up correctly
under `_question_matches()`'s Python-side check, just not under the
Firestore-side one the fast retrieval path now depends on.

### 3. Route by domain, not by habit

GLMP's sources (PubMed, bioRxiv/medRxiv) will not serve ATAP. Mathematics needs
arXiv `math.LO`, `math.CT`, `cs.LO`, and likely zbMATH or similar. The source
set is a property of the project, read from its declaration or a per-project
routing table — not a global weight vector.

### 4. Accumulate evidence; never certify a chart

Per the 2026-08-05 reframe, restated 2026-08-15: a GLMP or ATAP chart is
the **best current approximation** of a process, not a verified result.
A biologist review (Lents, Me-Me) can make that approximation better. It
does not certify the chart the way a Lean proof certifies a theorem.
There is no canonical version to elect.

Acquisition therefore **adds candidate evidence** and never overwrites a
chart's existing sources or promotes a paper to a formal "canonical
source." Recording that a chart currently *names* a paper is a fact
about the file, not a verification of the chart.

This is the direct lesson of `pick_canonical_source()`, which took
`sources[0]` with a DOI and no relevance check, and produced the #25
mess. A scout that promotes its own finds to a certified source repeats
that error at scale.

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

### 8. Citation expansion is gated, one-hop, never a scout

Decided with Gary 2026-08-15. Motive: bring in papers the authors of
already-admitted work were likely treating as load-bearing, toward ~75%
coverage of GLMP targets, without a million tangential papers and without
an infinite citation regression.

**A paper's bibliography is not an ingest queue.** If `cited_dois` or
`references` are stored on a record, they are Knowledge Map metadata.
They do not admit the cited works. The ingest allowlist must not treat
those fields as an acquisition trigger.

Citation expansion is a **separate intake path**, same family as #43
(researcher-cited), not a change to the daily PubMed / bioRxiv / arXiv
cron. Channel: `acquisition_channel: "cited_by_collection"`. Each new
record carries the parent paper id (and a question id when one is
known). Production scout cron is not touched for this.

**Seeds, only these classes, in this order:**

1. Papers a GLMP or ATAP chart already names as sources (A1).
2. `research_focus.json` `flagged` papers and #43 researcher-cited papers.
3. Later, a small slice of scout papers already attributed to a declared
   question — never the whole corpus.

**Admission rules:**

- One hop from those seeds. Never expand from a paper this hop just
  admitted.
- Keep a candidate if two or more seeds cite it, or if Semantic Scholar
  marks it `isInfluential` / it is among the most-cited references of
  that seed.
- Cap per seed and per batch (pilot: ~50 seeds; a few hundred new
  papers at most).
- Deduplicate against the whole corpus. A hit still records the new
  attribution (requirement 5).
- Crossref is enough when the seed has a deposited `reference` list.
  OpenAlex or Semantic Scholar is the fallback when that list is empty
  (common for PubMed and preprints). Do not call those APIs on every
  Map or Ask request.

**First coded step after the video backfill:** a ~50-seed pilot
(flagged + researcher-cited + a few chart sources), reporting
already-in-corpus / new / rejected by the two-seed or influential
rule. A1.0 (chart-source papers as candidate evidence) may run in
parallel; it is not a blocker and does not rewrite chart `sources`.

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
5. **Citation-expansion 50-seed pilot** after the video backfill —
   requirement 8. Does not touch scout cron. Does not wait on A1.
6. **A1.0 in parallel** — ingest papers that current charts name, as
   candidate evidence. Calendar wait lifted 2026-08-15. #25 can still
   improve the approximation; it does not certify charts and does not
   block recording that a chart currently names a paper. See
   `A1-glmp-source-backfill-plan.md`.

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
