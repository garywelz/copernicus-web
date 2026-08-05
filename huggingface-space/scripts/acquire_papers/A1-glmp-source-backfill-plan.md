# A1 — Backfill the GLMP source papers into the corpus

**Drafted:** 2026-08-05 · **Status:** proposal, nothing executed.
**Parent:** item #37 Part A · **Blocked, deliberately, until ~2026-09-01** —
not on a resolver run someone could pick up, but on Prof. Lents' and Me-Me's
biology review of item #25 (see "The gate" below, corrected 2026-08-05 —
#25 was reworked hours after this plan was drafted and this section
originally described the pre-rework version).
**Scope:** Engine Core — corpus, ingestion, retrieval

*Filed 2026-08-05 alongside A2 (`A2-standing-acquisition-contract.md`, same
directory) so Part A of item #37 reads coherently: A1 blocked until
September pending Lents/Me-Me, A2 pending `research_focus.json`'s
`mute`/`flagged`/`frontier`/`horizons` field semantics, and item #43 done and
live. This plan was drafted the same day as those two but never handed over
in that batch — filed separately once found. See `GLMP_MASTER_TODO.md` for
the numbered item.*

---

## The finding this plan exists to fix

The engine holds roughly 62,900 papers. **216 of the 217 papers GLMP's own
flowcharts cite as canonical sources are not among them.**

From `collaborations/krampis-virtual-cell/copernicus-corpus-gap-report.tsv`
(217 rows):

| | count |
|---|---|
| `missing_ingest` | **216** |
| `in_corpus` | 1 |
| Found in local acquisition JSON | 1 |
| Found in Zenodo frozen export | 0 |

This is the single largest coverage defect in the suite, and it is not a
discovery problem — the papers are already enumerated, titled, and resolved to
identifiers. It is an ingestion problem.

## Why it matters more under the reframe

The audience is four named researchers, and the podcast is a research
instrument they request on demand: *explain this paper, explain this flowchart*.

That makes the failure concrete rather than statistical. If Prof. Lents asks for
an explanation of the ABA guard-cell homeostat, the engine currently cannot
ground the answer in the paper that flowchart was built from, because that paper
isn't in the corpus. It will retrieve something adjacent and sound fine —
**the same failure mode as item #34**, where Node Explanation returned confident
output that wasn't tied to the thing the user clicked. That was worth fixing at
the retrieval layer; this is the same defect at the corpus layer.

Under a general-audience frame, 62,900 papers looks like abundance. Under the
researcher-tool frame, the 216 papers that are missing matter more than the
62,900 that are present.

## What is actually in the gap list

Identifier readiness (217 rows):

| | count |
|---|---|
| `manifest_status: ok` | 208 |
| `manifest_status: needs_doi` (= the 9 flagged `needs_krampis_review`) | 9 |
| Has a DOI **or** a PMID | 208 |
| Missing DOI | 15 |
| Missing PMID / title | 9 |

Cross-checking against `flowchart-source-papers.tsv` (481 citations across 208
distinct charts) resolves the apparent discrepancy: **217 − 208 = 9**, exactly
the `needs_doi` rows. Those 9 charts carry no source citations at all. They are
a different problem from the other 208 — missing provenance rather than
un-ingested provenance — and should not be counted as ingestible.

Spread, for sequencing:

- **Organism:** E. coli 68 · *Homo sapiens* 52 · *S. cerevisiae* 41 · synthetic
  circuits 39 · *B. subtilis* 6 · Arabidopsis 3 · mouse 3 · *C. elegans* 2
- **Circuit class:** II 73 · I 69 · III 52 · IV 16 · V 7

## The gate: item #25, and why it cannot be automated away

**Corrected 2026-08-05 — #25 was reworked hours after this plan was
originally drafted; this section described the pre-rework version
("roughly 220 of the 481 citation rows need re-resolving") and is replaced
below rather than left stale.**

#25 is no longer a TSV re-harvest — `raw_citation` turned out to be
generated from each row's own `pmid`/`doi`/`title`, so re-resolving it was
circular, not fixable as a resolver run. It's now a re-sourcing problem,
split by what it actually needs:

- **121 multi-source charts** — a selection problem, not a sourcing one; the
  right paper may already be sitting unused in the same row. 54 flagged as
  candidates by embedding similarity, but manual spot-check of the
  highest-confidence tier found a **~40% false-positive rate even there** —
  the metric picks up lexical overlap with the query, not necessarily
  citation correctness (a foundational paper can score lower than a generic
  review whose title happens to contain the search terms). No mechanical
  reselection without per-row review, at any confidence tier.
- **87 single-source charts** — genuine re-sourcing if the one source is
  wrong, with no alternative already present to fall back on.
- **9 charts with no sources at all** — already `needs_krampis_review`,
  unchanged by the rework.

The illustrative case from the original draft still holds exactly:
`ecoli_e._coli_flagellar_assembly` resolves to *"TnpB homologues exapted
from transposons are RNA-guided transcription factors"* — a real paper,
correctly formatted, and not about flagellar assembly. **Ingesting from the
uncorrected list would write wrong papers into the corpus and label them
canonical sources for charts they do not support** — worse than the present
gap, since an absent paper produces a visible miss while a confidently wrong
canonical source produces a plausible answer nobody double-checks.

**All of it needs the same biologist review already queued for the
loop-audit pre-registration and the CRP PWM question — Prof. Lents and
Me-Me, not expected before end of August.** A1 is therefore gated on a
calendar, not on a task someone could pick up and unblock sooner: there is
no resolver run, no engineering fix, that shortens this.

### Attempt made, and its failure recorded

Two automated triage attempts were made to size the safe subset without waiting
for #25, and both failed:

1. **Internal consistency.** All 481 rows agree with themselves — `raw_citation`
   is a full formatted citation containing the resolved title. Self-consistency
   cannot detect a citation that was wrong from the start.
2. **Chart-subject vs paper-title overlap.** Reported 57 of 208 charts as having
   no topically-matching source. **The result is not trustworthy.** The
   tokenizer discarded tokens of three characters or fewer, so
   `SOS DNA-Damage Response (LexA/RecA)` scored 0.0 against *"The SOS regulatory
   system of Escherichia coli"* — a correct match, thrown away. The same defect
   affects ABA, AKT, ppGpp, lin-4, and any short gene or protein symbol.

This is the same error mode as the item #33 trp-operon false positive:
**normalization discarding exactly the token that carries the discriminating
meaning.** Third instance in the suite. Any lexical proxy over biological
naming should be assumed to have it until shown otherwise.

**Conclusion:** the safe-to-ingest subset cannot be sized cheaply. It comes from
#25 doing the re-sourcing properly, or from per-row human confirmation. A1 is
gated, not merely sequenced.

## Proposed execution

Designed in increments, because attention is the binding constraint in practice
regardless of what is nominally binding — a single campaign will stall, and a
stalled campaign leaves the corpus in a half-known state.

**A1.0 — Ingest the ready subset (no #25 dependency).**
Whatever count #25 confirms as correctly resolved, ingest those first. Even a
partial pass converts the most-cited charts from ungroundable to groundable.
Prioritise by number of distinct citations per chart, so the charts researchers
are most likely to ask about land first.

**A1.1 — Ingest the #25-corrected remainder** as corrections land, in batches,
rather than waiting for the full set.

**A1.2 — Resolve the 9 provenance-less charts.** These need a source
identified, not a source ingested. Bundle them into the existing biologist
review rather than opening a third queue — the loop-audit pre-registration and
the CRP PWM question are already waiting on the same people.

**A1.3 — Close the loop.** Re-run the gap report and confirm
`missing_ingest` has fallen. The report is the instrument; it should be
re-run rather than assumed.

## Success criteria

Not "216 papers ingested." Under the reframe, the test is behavioural:

> For a flowchart a researcher names, the engine can retrieve that chart's
> canonical source papers and ground an explanation in them — with the source
> appearing as citation [1], the same bar item #34 was fixed to.

Verification should be a live-endpoint check on a named chart, not a count in
Firestore. Today established that the corpus, the deployed service, and the
document that describes them can each be right while the others are wrong.

## Open questions

1. ~~**Does ingestion route through the stub-gate?**~~ **Answered
   2026-08-05, same day as drafted — the gate is conjunctive
   (`_reject_stub_reason`): it rejects only when there is *no usable title
   AND no identifier*, and runs in `observe` mode by default. Every one of
   the 216 has at least a title and a DOI or PMID (per the identifier
   readiness table above) — all 216 pass. No exception needed, none to
   record.**
2. **Full text or metadata?** Grounding an explanation in a paper's argument
   needs more than a title and abstract. Whether these ingest as full text,
   and what happens for paywalled DOIs, changes both the effort and the result.
3. **Does the corpus record the chart↔paper link?** Ingesting 216 papers into a
   62,900-paper corpus without the association makes them findable but not
   *connected* — presence without findability, in the suite's own terms.
4. **ATAP's equivalent.** No comparable gap report exists for the mathematics
   corpus. Whether one should be generated before A2 designs standing
   acquisition is worth deciding now rather than later.
