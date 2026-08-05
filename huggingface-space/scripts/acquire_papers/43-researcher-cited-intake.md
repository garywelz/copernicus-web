# #43 — Researcher-cited intake

**Drafted:** 2026-08-05 · **Status:** implemented, dry-run tested, not yet ingested
**Parent:** item #37 Part A · **Dependencies:** none
**Scope:** Engine Core — acquisition, ingestion
**Serves:** GLMP and ATAP equally
**Implementation:** `researcher_cited_intake.py` in this directory

---

## What this is

When a project participant cites a paper — in an email, a Zoom chat, a review
comment — that paper enters the corpus, carrying a record of **who** cited it,
**when**, and **in what context**.

Today this doesn't happen. Prof. Lents wrote, while working the cAMP-CRP
question, that he'd come across a Biophysical Journal paper and sent the link.
That paper is not in the corpus and nothing brings it in.

## Why it earns priority over a better scout

Under the reframe, the audience is four named researchers and the podcast is a
tool they request on demand. In that frame, a citation from one of those four is
the **highest-precision acquisition signal that exists anywhere in the system**.
A scout infers relevance from query terms. A researcher citing a paper has
already made the judgment, with domain expertise no heuristic approximates.

Three practical arguments:

1. **Ungated.** A1 waits on #25. A2 waits on a scout contract. This waits on
   nothing and could run this week.
2. **It is the only acquisition route that serves ATAP today.** ATAP has no
   scout and — per the 2026-08-05 survey — 218 of 237 process files have an
   empty `sources` array, so there is no citation set to backfill from either.
   A researcher-cited path is currently ATAP's only inbound literature.
3. **Volume is low, value per item is high.** Four researchers will not generate
   a flood. Each item is worth more than a hundred scout hits.

## Why it is small

The machinery already exists. `huggingface-space/scripts/acquire_papers/`
already contains resolvers for Crossref, PubMed, arXiv, bioRxiv/medRxiv, and
NASA-ADS, plus `metadata_schema.json`, `validate_metadata.py`, and
`deduplicate_papers.py`. `cloud-run-backend/scripts/ingest_papers_from_metadata_json.py`
already ingests conforming records.

**#43 is a front door, not a pipeline.** It accepts a citation, resolves it
using machinery that already works, emits a record conforming to the existing
schema, and hands it to the existing ingest. No new acquisition code.

## Proposed design

### Input

Whatever a researcher actually sends, in order of resolution confidence:

1. DOI
2. PMID · arXiv ID · bibcode
3. Publisher URL (including Cell Press PII form, e.g.
   `S0006-3495(22)00045-5`) — resolvable via Crossref
4. Free-text citation — resolvable, less reliably

The path should not require researchers to learn a format. They send what they
have; the system does the work.

### Provenance — the part that matters

The existing schema (`required: id, title, source, acquired_date`) has a
`source` field for *where the record's metadata came from* (a closed enum:
`pubmed, arxiv, biorxiv, medrxiv, nasa_ads, crossref`), not *who recommended
it*. **Correction (2026-08-05, caught before implementation):** the original
draft of this section proposed `source: "researcher_citation"`, which fails
that enum — Crossref/PubMed/etc. is genuinely still where the *metadata* came
from even for a researcher-cited paper. The channel belongs in a separate
field instead. Verified live: `metadata_schema.json` has
`additionalProperties: true`, so this addition needs no schema edit.

```
cited_by:            "Lents"                # which participant
cited_date:          "2026-08-04"           # when
cited_context:       "while looking into the cAMP-CRP issue"   # their words
cited_project:       "GLMP"                 # which research project
acquisition_channel: "researcher_citation"  # distinguishes from scout acquisition
# source: left alone — still "crossref"/"pubmed"/etc., whichever resolver ran
```

`cited_context` is worth arguing for. *Lents flagged this while working the CRP
question* is retrievable information, and under the researcher-tool framing it's
exactly what one of the four might later search for. Ingesting the paper and
discarding the reason throws away the most valuable half of the signal.

`acquisition_channel: "researcher_citation"` also makes the set separable —
"show me everything the team has cited" becomes a query rather than an
archaeology exercise.

### Failure behavior

**Resolve loudly or queue for human correction. Never guess.**

This is item #25's lesson arriving early: a confidently wrong canonical record
is worse than a visible gap, because nobody re-checks a record that looks fine.
If a citation resolves ambiguously or not at all, it goes to a review queue with
the original text preserved verbatim — not a best-effort match.

Note that access and resolvability are independent. A researcher may be reading
a paper their institution licenses while the resolver only reaches metadata.
Metadata is the target (per the 2026-08-05 decision that metadata suffices);
the paywall is not a blocker for intake.

### Intake mechanism — open question

The design above says nothing about *how* a citation reaches the system, because
that depends on how the four researchers actually work. Options, roughly by
effort:

- **Manual**, Gary runs a script with a DOI and a context string. Zero
  infrastructure; works today; depends on Gary's attention.
- **A file in the repo** the four can append to, processed on a cron.
  Collaborators already have repo access.
- **The "Improve this process" form**, extended with a "suggest a paper" mode.
  Reuses a channel that exists and that researchers have already been pointed
  at.
- **Email parsing.** Highest fidelity to how citations actually arrive today —
  and the highest complexity and failure surface.

Recommendation: **start manual.** The volume is four researchers; a script
handles it, and running it manually for a month reveals what the citations
actually look like before any interface is committed to. Implemented this way:
`researcher_cited_intake.py`, manual invocation, no cron, no interface — matches
this recommendation exactly.

## First record and test case

Prof. Lents' Biophysical Journal citation, sent 2026-08-04 during the CRP work,
serves as the first record and a live end-to-end test. It exercises the awkward
path — a publisher URL in PII form rather than a DOI — which is exactly the case
worth proving before anything is automated.

**Resolved (2026-08-05).** The PII → DOI path works, via a mechanism not
originally documented in this plan: Crossref indexes Elsevier/Cell Press PIIs
verbatim (punctuation stripped) as each work's `alternative-id`, and supports
`filter=alternative-id:<value>` as a direct, exact-match lookup — not a
full-text search, not a scrape of the (Cloudflare-gated) cell.com page. PII
`S0006-3495(22)00045-5` → `alternative-id` `S0006349522000455` → exactly one
Crossref match:

- **DOI:** `10.1016/j.bpj.2022.01.016`
- **Title:** "Inducer exclusion, by itself, cannot account for the
  glucose-mediated lac repression of *Escherichia coli*"
- **Authors:** Aggarwal, Ritesh Kumar; Narang, Atul — *Biophysical Journal*,
  vol. 121, issue 5, pp. 820–829, 2022
- Directly on-topic for the cAMP-CRP question Lents was working — this is the
  right paper, not a plausible-looking wrong one.

Dry-run output (`--input` the cell.com URL, `--cited-by Lents`, `--cited-date
2026-08-04`, `--cited-context "while looking into the cAMP-CRP issue"`,
`--cited-project GLMP`, no `--write`): validates at 91.7% quality (the only
gap is `abstract` — Crossref doesn't carry one for this Elsevier record; not a
blocker, `abstract` isn't required), confirmed absent from `research_papers`
by a live Firestore query, confirmed absent from the local `crossref/` mirror
(12,235 files scanned) by `deduplicate_papers.are_duplicates`. Nothing written
pending Gary's go.

*Superseded note from drafting: the sandbox used to draft this plan had no
network access to Crossref or Cell Press, so the PII → DOI step was untested
at draft time. It is no longer untested — see above.*

## Success criteria

Behavioural, not a count:

> A researcher sends a citation. Within one cycle, that paper is in the corpus,
> retrievable, and its record shows who cited it and why. Asking the engine
> about the topic returns it, and asking "what has the team cited about CRP"
> returns it too.

## Open questions

1. **Does a cited paper's project tag affect retrieval?** If Lents cites
   something for GLMP, should ATAP queries rank it lower — or is the corpus flat
   and the tag purely provenance?
2. **What about papers cited in the other direction** — ones the engine
   surfaced and a researcher then found useful? That's a feedback signal for
   scout tuning, which belongs to Methods & Tools, but the data would originate
   here.
3. **Should intake accept non-papers?** Preprints and datasets resolve; a
   conference talk or a blog post may not. Worth deciding before someone sends
   one rather than after.
4. **Already-in-corpus re-citations.** If a researcher cites a paper that's
   already in `research_papers` (caught by this script's dedup check), the
   paper doesn't need re-ingesting, but the provenance (who/when/why) is still
   a real signal and today it's simply dropped — the script reports the
   duplicate and writes nothing. Merging provenance onto an existing Firestore
   doc is a production write with its own failure modes and wasn't in scope
   for the front-door script; needs a decision before it's built.
5. **`validate_metadata.py`'s `valid_sources` list is stale, found in passing
   (2026-08-05).** It hardcodes `["pubmed", "arxiv", "nasa_ads", "crossref"]`,
   missing `biorxiv`/`medrxiv` — both valid per `metadata_schema.json`'s
   six-value enum. Any bioRxiv/medRxiv-sourced record (including one resolved
   by this script's own `10.1101/` preprint-first path) would currently fail
   that one check. Unrelated to #43's own logic — a pre-existing gap in a
   shared validator — flagged here rather than fixed here, since fixing a
   shared validation script wasn't part of this task's scope.
