# Proposed governance addition — what a Resource collection is

*Drafted 2026-08-05 (Claude Chat) for review. **Placed 2026-08-05** in
`governance/RESOURCE_MANIFEST.md`, under "Shared resource collections"
(`copernicus-web@75cb84e56`) — Gary's choice over the two other options
considered (a new `CONSTITUTION.md` section; not placing it yet). Kept here
as the original proposal for the record. The placed version corrects the
reference count below from 83 to 73 (independently re-counted; the original
83 came from a regex that also picked up unrelated numbered lists elsewhere
in the source documents — see `GLMP_MASTER_TODO.md` item 46) and adds a note
to `RESOURCE_MANIFEST.md`'s header clarifying that its "last verified against
reality: 2026-08-04" claim does not cover this new subsection.*

---

## Scope of a Resource collection

A Resource collection is **one researcher's working literature**, not a
discipline's library.

The collection serving GLMP and ATAP is a single shared corpus, because both are
Gary Welz's projects and these are his sources. The foundational papers
demonstrate why: paper-I, paper-II, and paper-III draw on Voevodsky and homotopy
type theory alongside Shen-Orr's *E. coli* network motifs, Rice's theorem
alongside the Gardner toggle switch — 83 references across the three, mixing
GLMP and ATAP sources in the same argument. Partitioning by discipline would cut
those papers in half.

**A different scientist, with different projects, would have a different
collection.** The collection is indexed to a researcher's programme, not to a
subject heading. This is what distinguishes a Resource from a database.

## Bounded by relevance, not by volume

The boundary is topical, not numeric.

**Within** the fields the projects work in — molecular genetics and gene
regulation for GLMP; logic, foundations, graph theory, and proof theory for ATAP
— the collection aims at depth a working specialist would recognise as
adequate. The classics through to the frontier: Mendel and the Greeks at one
end, this week's preprints at the other, and the best work of the intervening
decades in between. A biologist or a logician should be able to name a work in
their field and find it here.

**Beyond** those fields, the collection does not expand by breadth. It admits
work from adjacent disciplines — philosophy, computer science, physics — when
semantic relationship earns it. That is not a tolerated leak in the boundary; it
is the point. The suite's ethos prizes *bridges over silos*, and the most
consequential material often sits between fields where a single-discipline
specialist would not look. Embedding-based retrieval is what makes this
tractable: relevance is measured by meaning rather than by subject tag, so a
paper's discipline does not determine its admission.

The result is a collection that is large in absolute terms — many thousands of
papers, far more than any researcher could read in several lifetimes — and small
only by comparison with a universal library. **Size is a consequence of this
boundary, not a target set independently of it.**

## What this rules out

**Undirected volume targets.** Acquiring *n* papers per run, where *n* is the
goal, optimises the wrong thing. The current
`huggingface-space/scripts/acquire_papers/daily_scout_config.json` sets a target
of 1,000 papers per run across generic biology queries, unconnected to either
project's declared research questions. High volume is not the defect —
*undirected* volume is. A run that acquires 1,000 papers against declared
questions and field-coverage gaps is doing its job; a run that acquires 1,000
papers because 1,000 is the number is not.

**Size as an achievement metric.** "~62,900 papers" describes the collection; it
does not commend it. On 2026-08-05 the collection held ~62,900 papers and 216 of
the 217 papers GLMP's own flowcharts cite were absent from it. A collection
missing the works its own project depends on is not succeeding at scale,
whatever the count.

**Discipline as a filter.** A relevance judgment that rejects a paper for being
mathematics when the reader is a biologist defeats the collection's purpose.

## The measure

Coverage against what the projects declare they are working on, and against
what a specialist would expect to find in the field. Both are reportable.
Neither is a count of documents.
