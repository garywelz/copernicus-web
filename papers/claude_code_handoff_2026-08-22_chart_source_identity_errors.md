# Handoff — 22 August 2026 (GLMP chart ↔ KE identity errors)

**From:** Cursor / Gary
**To:** Claude Code (ingest + chart repair) and Claude Chat
**Repo:** `copernicus-web` (`origin/main`)
**Regenerate from a fresh fetch before acting.**

Gary called these failures **vitally important to correct**. Chart-side
identifier repairs for the rows below are in this repo’s process JSON
(22 August 2026, Cursor). **KE ingest and abstract backfill are still
Claude Code.** Do not re-introduce the old colliding PMIDs/DOIs.

Continuous with
`papers/claude_code_handoff_2026-08-21_lac_ingest_and_animating_podcasts.md`.
The lac handoff already named the Napoli DOI trap. This file is the wider
pattern: **chart `sources` / PMIDs / DOIs often do not name the paper that
`/resolve-paper` returns.**

---

## Why this matters

Paper-sourced podcasts and self-animating chart walks need a paper that:

1. is listed on a GLMP process chart,
2. resolves in the Knowledge Engine as that same paper,
3. has a non-empty abstract (`/generate-podcast-from-paper` 400s otherwise).

Live checks on 22 August 2026 against
`POST https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app/resolve-paper`
showed that several famous charts fail (2) or (3). Some “hits” are **a
different paper wearing the chart’s PMID or DOI**.

Do not treat `a1_resolve_ingest_report.jsonl` “created” rows as confirmed
chart sources. Several Crossref ingest rows attached the wrong article to the
chart (same DOI collision / garbled citation pattern).

---

## Method

For each row below:

1. Resolve the chart’s stored DOI **and** stored PMID separately (unscoped,
   then `cited_project=glmp`).
2. Resolve the **real** paper (title + year + venue) via PubMed / Crossref /
   EuropePMC.
3. If the KE doc is the wrong paper: **do not overwrite it**. Leave the
   existing doc; ingest or re-link the correct paper; fix the chart row.
4. If the KE doc is the right paper with an empty abstract: **backfill
   abstract only**. Do not duplicate.
5. After repair, `/resolve-paper` on the chart DOI must return that paper,
   `match_type=identifier`, non-empty `abstract_preview`, and
   `cited_project=glmp`.

Provenance for new ingest:

- `cited_by`: Gary Welz
- `cited_date`: 2026-08-22
- `cited_project`: `glmp`
- `cited_context`: repair chart-source identity so flowchart podcasts can
  use the paper the chart actually claims

Use existing intake (`researcher_cited_intake.py` then
`ingest_papers_from_metadata_json.py`) unless a later #43 path has replaced it.

---

## Confirmed identity failures

Checked live. “Chart says” is what is stored on the process JSON. “KE returns”
is `/resolve-paper` on that identifier.

### `ecoli_ara_operon` — Schleif 2000 is not in the KE; chart DOI is fictitious

| Chart says | Live result |
|---|---|
| Schleif, “Positive and negative control of the arabinose operon,” *PNAS* 2000, DOI `10.1073/pnas.97.14.7643`, PMID `10899998`, `paper_id` `crossref_10_1073_pnas_97_14_7643` | DOI: `identifier_not_found` (Crossref 404, EuropePMC 0, PubMed DOI search 0). PMID `10899998`: **hair-cycle automaton paper** (`pubmed_10899998`, DOI `10.1073/pnas.97.15.8328`), not Schleif. |

**Real paper to ingest:** Schleif R (2000). *Regulation of the L-arabinose operon of Escherichia coli.* *Trends in Genetics*. PMID **`11102706`**. DOI **`10.1016/s0168-9525(00)02153-3`**. EuropePMC abstract 667 chars. Not in KE (DOI and PMID both `identifier_not_found`).

Also missing / empty on this chart: Schleif 1992 *DNA looping* is in KE as `pubmed_1497310` with **empty abstract**. Englesberg 1974 DOI resolves as `identifier_wrong_project` to a different “REGULATION: POSITIVE CONTROL” record.

### `ecoli_lac_operon` — Napoli row still garbled (repeat from 21 Aug)

Chart still lists DOI `10.1016/j.str.2005.11.021` / PMID `16531234` as Napoli.
That DOI is Iengar/Balaram β-helix proteins. PMID `16531234` is titin
Z1Z2–telethonin. Real Napoli 2006 is *JMB*
DOI **`10.1016/j.jmb.2005.12.051`**, KE id **`pubmed_16427082`** (abstract
present). Fix the chart row. Do not ingest Iengar as a lac source.

### `yeast_cell_cycle_control` — Nurse 1997 not in KE; PMID collision

| Chart says | Live result |
|---|---|
| Nurse P (1997) “Cyclins and cell cycle checkpoints,” *Science*, DOI `10.1126/science.276.5315.1886`, PMID `9220155` | DOI: `identifier_not_found`. PMID `9220155`: **Enterocytozoon bieneusi probe paper** (`pubmed_9220155`), not Nurse. |
| DOI `10.1038/nrm1973` as a cell-cycle review | Resolves to “Microprocessor measures up,” not a CDK/cell-cycle paper. |

Ingest the real Nurse 1997 *Science* paper after confirming its current DOI/PMID
on Crossref/PubMed. Do not attach it to `pubmed_9220155`.

### `yeast_autophagy` — Levine / Mizushima PMIDs are other papers

| Chart says | Live result |
|---|---|
| Levine (2021) “Autophagy genes in biology and disease,” PMID `33197221` | Immune-checkpoint inhibitors review (`pubmed_33197221`). |
| Mizushima (2011) “Molecular mechanism and physiological functions of autophagy,” PMID `21157483` | mTOR / growth-signal review (`pubmed_21157483`, DOI `10.1038/nrm3025`). |

Find the real Levine / Mizushima records, ingest or re-link, fix PMIDs on the
chart. Autophagy is a high-interest chart; do not leave it pointing at oncology
reviews.

### `ecoli_dna_replication_initiation` — Leonard 2015 DOI missing; PMID collision

| Chart says | Live result |
|---|---|
| Leonard & Grimwade (2015) *JBC*, DOI `10.1074/jbc.R115.662783`, PMID `26350459` | DOI: `identifier_not_found`. PMID `26350459`: *Pseudomonas putida* glucose-metabolism paper, not DnaA/oriC. |

Katayama 2010 (`pubmed_20157337`, DOI `10.1038/nrmicro2314`) **is** in KE with
an abstract and is a usable source on this chart. Prefer repairing Leonard
without disturbing Katayama.

### `ecoli_chemotaxis` — Berg / Sourjik PMIDs are other papers

| Chart says | Live result |
|---|---|
| Berg (1972) chemotaxis tracking, PMID `4628819` | H₂O₂ / bacterial-spore radiation paper. |
| Sourjik (2002) receptor sensitivity, PMID `12379844` | SeqA–hemimethylated-DNA structure paper (`pubmed_12379844`). |

Chart `related_papers` is empty; `sources` have no DOIs. Add real DOIs after
PubMed/Crossref confirmation (Berg & Brown 1972 *Nature* is the usual Berg
tracking paper — confirm before ingest).

### `ecoli_heat_shock_response` — Horwich DOI collision

| Chart says | Live result |
|---|---|
| Horwich & Fenton GroEL review, DOI `10.1038/nrm2636` | Resolves to an unrelated clinical paper (ovarian-cancer lymph-node note). |

Mayer & Bukau 2005 (`pubmed_15770419`) **is** in KE with an abstract and is a
usable source on this chart.

### `yeast_unfolded_protein_response` — Ire1 PMID collision

| Chart says | Live result |
|---|---|
| Ire1p kinase / UPR, PMID `8670867` | v-rel oncogene / T-cell leukemia paper (`pubmed_8670867`). Chart candidate DOI `10.1002/j.1460-2075.1996.tb00682.x` was ingested as that wrong title in `a1_resolve_ingest_report.jsonl`. |

### Abstracts empty on otherwise correct KE hits

These resolve as the intended paper but cannot generate until the abstract is
backfilled:

| Paper | KE id | Chart |
|---|---|---|
| Yanofsky (1981) attenuation | `pubmed_7007895` | `ecoli_trp_operon` |
| Schleif (1992) DNA looping | `pubmed_1497310` | `ecoli_ara_operon` |
| Jacob & Monod (1961) | `pubmed_13718526` | `ecoli_lac_operon` (already in 21 Aug handoff) |

`/resolve-paper` only returns `abstract_preview` (280 chars). A 280-char
preview means the Firestore `abstract` field is populated. Empty preview /
missing `abstract` is the generation blocker.

---

## Charts that already resolve cleanly (do not “fix” these first)

Use these as the positive control when testing the repair pipeline:

| Chart | Paper | KE id | DOI |
|---|---|---|---|
| `yeast_gal_regulation` | Platt & Reece 1998, *EMBO J* | `pubmed_9670023` | `10.1093/emboj/17.14.4086` |
| `yeast_gal_regulation` | Sellick, Campbell, Reece 2008 | `pubmed_18779058` | `10.1016/s1937-6448(08)01003-4` |
| `ecoli_translation_initiation` | Wimberly et al. 2000 *Nature* | `pubmed_11014182` | `10.1038/35030006` |
| `ecoli_translation_initiation` | Laursen et al. 2005 *MMBR* | `pubmed_15755955` | `10.1128/mmbr.69.1.101-123.2005` |
| `ecoli_stringent_response` | Potrykus & Cashel 2008 | `pubmed_18454629` | `10.1146/annurev.micro.62.081307.162903` |
| `ecoli_dna_replication_initiation` | Katayama et al. 2010 | `pubmed_20157337` | `10.1038/nrmicro2314` |
| `ecoli_heat_shock_response` | Mayer & Bukau 2005 | `pubmed_15770419` | `10.1007/s00018-004-4464-6` |
| `ecoli_lac_operon` | Napoli 2006 *JMB* (real) | `pubmed_16427082` | `10.1016/j.jmb.2005.12.051` |

Cursor is using **GAL + Platt 1998** for the next animated episode. Leave that
pair untouched.

---

## Suggested order for Claude Code

1. **Chart-row repair** for identity collisions (wrong paper behind a PMID/DOI).
   Highest public-interest charts first: autophagy, cell cycle, chemotaxis,
   ara/Schleif, lac/Napoli row, UPR.
2. **Ingest missing real papers** (Schleif 2000 *Trends Genet*; Nurse 1997
   once DOI/PMID confirmed; real Berg / Mizushima / Levine / Leonard).
3. **Abstract backfill** for correct empty docs (Yanofsky, Schleif 1992,
   Jacob & Monod).
4. **Audit script** that, for every process `sources[]` DOI/PMID, resolves
   both identifiers and flags title mismatch vs the chart’s stored title.
   Do not rely on `a1_resolve_ingest_report.jsonl` as ground truth.

### Verify one repaired row

```json
{"query": "10.1016/s0168-9525(00)02153-3", "cited_project": "glmp"}
```

Want: Schleif 2000 *Trends Genet*, `match_type=identifier`, non-empty
`abstract_preview`. Chart `ecoli_ara_operon` source row must use this DOI/PMID,
not `10.1073/pnas.97.14.7643` / `10899998`.

---

## Out of scope for this handoff

- Generating or editing `ever-bio-260009` (landmark; leave as-is).
- Generating the GAL / Platt episode (Cursor).
- Re-running the whole A1 harvest.
