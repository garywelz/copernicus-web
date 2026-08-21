# Handoff — 21 August 2026 (lac collection gaps — complete)

**From:** Claude Code (this session)
**To:** Cursor and Claude Chat
**Repos:** `copernicus-web` @ `origin/main`, `glmp` @ `af15ee1`
**Regenerate from a fresh fetch before acting.**

Share this file as-is. Completes
`papers/claude_code_handoff_2026-08-21_lac_ingest_and_animating_podcasts.md`. This closes the
ingest gate Cursor's handoff named: *"I am not building the player until those papers are in."*
They're in now.

---

## Status: all four ingest items done, verified live

### 1. Napoli 2006 — ingested

Crossref's DOI-only lookup returned an **empty abstract** for `10.1016/j.jmb.2005.12.051`, which
would have made the record generation-ineligible even after ingest. Found the real abstract via
PubMed instead (PMID `16427082`, same DOI) and ingested through that path. Live doc:
`pubmed_16427082`. Verified via `resolve_by_identifier`: non-empty abstract, correct DOI, `glmp`
project tag, `glmp-q1` question.

### 2. Swint-Kruse — corrected, not the citation originally given

**The DOI Cursor's handoff supplied (`10.1016/S0065-2164(08)01001-8`) is dead** — confirmed via
direct `doi.org` resolution, 404, not just missing from an index. Neither Crossref nor PubMed has
any record titled "Mechanism of the allosteric regulation of the lac repressor" in *Adv Appl
Microbiol* 67:1-24 under any identifier. This looked like the same class of error as the Napoli
chart trap Cursor already caught once, so it wasn't force-ingested. Found and confirmed with Gary
before writing: a real, cleanly-indexed 2009 Swint-Kruse & Matthews paper on the same subject —
*"Allostery in the LacI/GalR family: variations on a theme,"* *Curr Opin Microbiol* 12(2):129-137,
DOI `10.1016/j.mib.2009.01.009`, PMID `19269243`. Ingested that instead, with `cited_context`
explicitly recording the correction. Live doc: `pubmed_19269243`. Verified via
`resolve_by_identifier`.

### 3. Chart trap — fixed, both rows were wrong, not just one

`glmp-v2/processes/ecoli/ecoli_lac_operon.json`'s `sources` array had two garbled rows, not one:

- **Napoli's row** pointed at an unrelated paper via *both* a wrong DOI (`10.1016/j.str.2005.11.021`,
  actually Iengar/Joshi/Balaram on β-helix protein structure) and a wrong PMID (`16531234`, a third,
  also-unrelated paper on titin Z1Z2–telethonin).
- **Swint-Kruse's row** — new finding, not in Cursor's original handoff — its PMID (`19245934`) also
  turned out completely unrelated: a hematology paper on immune thrombocytopenic purpura. Combined
  with the dead DOI, this citation was fabricated end-to-end, not a simple typo.

Both rows corrected with real, verified bibliographic data and an inline `note` explaining what was
wrong and when it was fixed. Committed and pushed: `glmp@af15ee1`.

**Not checked:** whether the live viewer (`.../glmp-v2/viewer/index.html?process=ecoli_lac_operon`)
serves this chart from a GCS mirror that also needs syncing, separate from this git file. If so,
that's a deploy-adjacent step, likely Cursor's.

### 4. Jacob & Monod 1961 — abstract backfilled with an editorial synopsis, after a real copyright check

Confirmed genuinely abstract-less everywhere (PubMed shows no abstract section at all for this
1961 paper; Crossref's `abstract` field is `None`) — not a "backfill from PubMed/Crossref" case, since
neither source has one to fetch. Gary asked whether the full text could be ingested instead.

**Checked, not assumed: this paper is not in the public domain.** *Journal of Molecular Biology* was
first published in **London** by Academic Press, not the US, so the commonly-cited "US pre-1964,
non-renewed copyright" shortcut doesn't apply here — that's a US-publication-specific rule. A
UK-origin work like this is governed by life-of-the-author-plus-70-years. François Jacob died in
**2013**, so under that rule copyright doesn't lapse until **2083**. Full-text ingestion was ruled
out on that basis, not attempted.

**What was done instead:** drafted an editorial synopsis (original description of the paper's content
and significance — the operon model, repressor/operator mechanism, 1965 Nobel Prize — not a
reproduction of the paper's own text), which Gary reviewed and approved verbatim before it was
written. Firestore doc `pubmed_13718526` updated:
- `abstract` — the approved synopsis text
- `abstract_source: "editorial_synopsis_not_original_abstract"` — explicit provenance flag so this
  is never mistaken for the paper's own published abstract by a future script or reader
- `abstract_note` — explains why (paper predates structured-abstract indexing; no real abstract
  exists in any indexed source)
- Re-embedded (`text-embedding-3-small`, 1536 dims, using the same `create_text_for_paper` /
  `embed_one` helpers `scripts/backfill_research_paper_embeddings.py` already uses — reused, not
  reimplemented) — the doc's existing embedding predated the abstract and would otherwise have stayed
  stale after this update. That script's own idempotency gate (skip if `embedding_model` already set)
  would **not** have caught this doc for re-embedding on its own, since it only fills gaps, not
  refreshes changed content — worth knowing if this pattern (abstract added after the fact) comes up
  again for other pre-abstract-era papers.

Verified live: `resolve_by_identifier` confirms non-empty abstract, correct provenance field, correct
embedding dimensions. One honest note: even after re-embedding, this doc still doesn't surface in a
broad semantic search within the top 20 for genuinely on-topic queries — same already-documented
corpus-density limitation as Napoli/Galas-Schmitz, not a new problem. Doesn't matter in practice; this
record will always be reached by its known DOI/PMID (the identifier path), which resolves it
instantly and correctly.

## Not done

- Self-animating podcast player — not started, per the original handoff's own scope ("Cursor later,
  not this ingest"). This handoff is the unblock signal, not a start signal.
- Optional Schmitz/Ullmann re-tagging as GLMP (item 45 re-citation path) — lower priority per the
  original handoff, not touched.
- GCS sync check for the chart JSON (see note under item 3).

## Verify (all confirmed already; commands here for anyone re-checking)

```
POST https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app/resolve-paper
{"query": "10.1016/j.jmb.2005.12.051", "cited_project": "glmp"}   -> Napoli, non-empty abstract
{"query": "10.1016/j.mib.2009.01.009", "cited_project": "glmp"}    -> Swint-Kruse (corrected paper)
{"query": "10.1016/s0022-2836(61)80072-7", "cited_project": "glmp"} -> Jacob & Monod, non-empty abstract
```

All three: `match_type=identifier`, one paper, non-empty `abstract_preview`.

---

## Key paths

- `glmp-v2/processes/ecoli/ecoli_lac_operon.json` — chart source-row fix (`glmp@af15ee1`)
- Firestore `research_papers/pubmed_16427082` — Napoli 2006
- Firestore `research_papers/pubmed_19269243` — Swint-Kruse & Matthews 2009 (corrected)
- Firestore `research_papers/pubmed_13718526` — Jacob & Monod 1961, abstract backfilled
- `cloud-run-backend/scripts/backfill_research_paper_embeddings.py` — reused `embed_one`,
  `get_openai_api_key`, `EMBEDDING_MODEL` for the manual re-embed
- `mcp_server/tools/vector_search.py` — reused `create_text_for_paper`
- Canonical chart id: `ecoli_lac_operon`. Viewer:
  `https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/glmp-v2/viewer/index.html?process=ecoli_lac_operon`
