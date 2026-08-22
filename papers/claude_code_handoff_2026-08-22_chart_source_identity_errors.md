# Handoff — 22 August 2026 (GLMP chart ↔ KE identity errors)

**From:** Cursor / Gary
**To:** Claude Code (ingest + chart repair) and Claude Chat
**Repo:** `copernicus-web` (`origin/main`)
**Regenerate from a fresh fetch before acting.**

Gary called these failures **vitally important to correct**. Chart-row
repairs and KE ingest for the unique rows are done. **The goal is not
complete.** Leftover garbled titles and the Englesberg empty abstract
remain. Do not invent papers or abstracts. Do not retitle Qi/Elion or
other non-unique leftovers. Do not re-introduce old colliding PMIDs/DOIs.

Continuous with
`papers/claude_code_handoff_2026-08-21_lac_ingest_and_animating_podcasts.md`.

---

## Why this matters

Paper-sourced podcasts and self-animating chart walks need a paper that:

1. is listed on a GLMP process chart,
2. resolves in the Knowledge Engine as that same paper,
3. has a non-empty abstract (`/generate-podcast-from-paper` 400s otherwise).

Chart `sources` / PMIDs / DOIs often did not name the paper that
`/resolve-paper` returned. Some “hits” were a **different paper wearing
the chart’s PMID or DOI**.

Do not treat `a1_resolve_ingest_report.jsonl` “created” rows as confirmed
chart sources.

---

## Method (locked)

1. Ignore a colliding stored PMID/DOI as identity. Search PubMed /
   Crossref / EuropePMC by **author + year + title**.
2. Confirm DOI and PMID separately.
3. If the KE doc is the wrong paper: **do not overwrite it**. Ingest or
   re-link the correct paper; fix the chart row.
4. If the KE doc is the right paper with an empty abstract: backfill a
   **published** abstract only. Never invent one.
5. After repair, `/resolve-paper` on the chart DOI/PMID must return that
   paper, `match_type=identifier`, and (unless no publisher abstract
   exists) a non-empty `abstract_preview`, scoped `cited_project=glmp`.

**Garbled-citation retitle rule** (same as Walter / Falke / Yura /
Takeshige / Schleif AraC): if AUTHOR + YEAR + TOPIC uniquely identifies
one real paper by that lab, retitle the chart source to that paper’s
official PubMed/Crossref title and attach its confirmed DOI/PMID. Apply
**only** when uniqueness is clear. If the author-year has multiple
plausible papers, leave stripped.

Provenance for new ingest:

- `cited_by`: Gary Welz
- `cited_date`: 2026-08-22
- `cited_project`: `glmp`
- `citations[]` event required or resolve returns `identifier_wrong_project`

Official ingest:
`cloud-run-backend/scripts/ingest_papers_from_metadata_json.py`
`--root C:\Users\garyw\copernicus-web\huggingface-space\metadata-database\papers`
`--include-glob "**/chart_repair*.json"`
`--no-skip-existing --no-reject-gcs --stub-gate-mode off`

---

## Live completion audit (22 August 2026)

Checked live against
`POST https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app/resolve-paper`
with `{"query": "<doi or pmid>", "cited_project": "glmp"}`.

**Result:** every remaining DOI/PMID on the nine charts returns
`match_type=identifier` and the intended paper. No leftover ID still
resolves to the wrong paper. Leftover garbled-title rows have empty
DOI/PMID (`NO_ID`). Englesberg is the intended paper with **empty
abstract**.

### `ecoli_lac_operon`

| Chart title | IDs | Live |
|---|---|---|
| RegulonDB | none | not a journal paper |
| Jacob & Monod 1961 *Genetic regulatory mechanisms in the synthesis of proteins* | DOI `10.1016/S0022-2836(61)80072-7` PMID `13718526` → `pubmed_13718526` | identifier + abstract |
| Müller-Hill 1996 *The lactose operon* | none | book, not a journal paper |
| Napoli 2006 *Indirect readout… CAP-DNA* | DOI `10.1016/j.jmb.2005.12.051` PMID `16427082` → `pubmed_16427082` | identifier + abstract |
| Swint-Kruse & Matthews 2009 *Allostery in the LacI/GalR family: variations on a theme* | DOI `10.1016/j.mib.2009.01.009` PMID `19269243` → `pubmed_19269243` | identifier + abstract |

### `ecoli_ara_operon`

| Chart title | IDs | Live |
|---|---|---|
| Schleif 2000 *Regulation of the L-arabinose operon of Escherichia coli* | DOI `10.1016/s0168-9525(00)02153-3` PMID `11102706` → `pubmed_11102706` | identifier + abstract |
| Schleif 1992 *DNA looping* | DOI `10.1146/annurev.bi.61.070192.001215` PMID `1497310` → `pubmed_1497310` | identifier + abstract |
| Schleif 2003 *AraC protein: a love-hate relationship* | DOI `10.1002/bies.10237` PMID `12596232` → `pubmed_12596232` | identifier + abstract |
| Englesberg & Wilcox 1974 *Regulation: positive control* | DOI `10.1146/annurev.ge.08.120174.001251` → `crossref_10.1146_annurev.ge.08.120174.001251`; PMID `4374117` → `pubmed_4374117` | identifier; **abstract empty** (no published abstract — do not invent) |

### `ecoli_chemotaxis`

| Chart title | IDs | Live |
|---|---|---|
| Berg & Brown 1972 *Chemotaxis in Escherichia coli analysed by three-dimensional tracking* | DOI `10.1038/239500a0` PMID `4563019` → `pubmed_4563019` | identifier + abstract |
| Falke et al. 1997 two-component chemotaxis review | DOI `10.1146/annurev.cellbio.13.1.457` PMID `9442881` → `pubmed_9442881` | identifier + abstract |
| Sourjik 2004 *Chemotaxis* | none | leftover — not unique |
| Sourjik & Berg 2002 *Receptor sensitivity in bacterial chemotaxis* | DOI `10.1073/pnas.011589998` PMID `11742065` → `pubmed_11742065` | identifier + abstract |

### `ecoli_heat_shock_response`

| Chart title | IDs | Live |
|---|---|---|
| Yura, Nagai, Mori 1993 *Regulation of the heat-shock response in bacteria* | DOI `10.1146/annurev.mi.47.100193.001541` PMID `7504905` → `pubmed_7504905` | identifier + abstract |
| Mayer & Bukau 2005 *Hsp70 chaperones: cellular functions and molecular mechanism* | DOI `10.1007/s00018-004-4464-6` PMID `15770419` → `pubmed_15770419` | identifier + abstract |
| Hayer-Hartl, Bracher, Hartl 2015 GroEL-GroES | DOI `10.1016/j.tibs.2015.07.009` PMID `26422689` → `pubmed_26422689` | identifier + abstract |
| Guisbert, Yura, Rhodius, Gross 2008 MMBR convergence review | DOI `10.1128/mmbr.00007-08` PMID `18772288` → `pubmed_18772288` | identifier + abstract |

### `ecoli_dna_replication_initiation`

| Chart title | IDs | Live |
|---|---|---|
| Leonard & Grimwade 2015 *The orisome: structure and function* | DOI `10.3389/fmicb.2015.00545` PMID `26082765` → `pubmed_26082765` | identifier + abstract |
| Katayama et al. 2010 DnaA/oriC regulation | DOI `10.1038/nrmicro2314` PMID `20157337` → `pubmed_20157337` | identifier + abstract |
| Sekimizu, Bramhill, Kornberg 1987 DnaA-ATP | DOI `10.1016/0092-8674(87)90221-2` PMID `3036372` → `pubmed_3036372` | identifier + abstract |
| Lu et al. 1994 SeqA | DOI `10.1016/0092-8674(94)90156-2` PMID `8011018` → `pubmed_8011018` | identifier + abstract |
| Wahle, Lasken, Kornberg 1989 dnaB-dnaC | DOI `10.1016/s0021-9258(19)81637-x` PMID `2536713` → `pubmed_2536713` | identifier + abstract |

### `yeast_autophagy`

| Chart title | IDs | Live |
|---|---|---|
| Levine *Autophagy genes in biology and disease* | none | leftover — title owned by Mizushima 2023; do not reassign |
| Mizushima, Yoshimori, Ohsumi 2011 *The role of Atg proteins in autophagosome formation* | DOI `10.1146/annurev-cellbio-092910-154005` PMID `21801009` → `pubmed_21801009` | identifier + abstract |
| Xie 2008 *The molecular machinery of autophagy: unanswered questions* | none | leftover — not unique |
| Takeshige et al. 1992 yeast autophagy induction | DOI `10.1083/jcb.119.2.301` PMID `1400575` → `pubmed_1400575` | identifier + abstract |

### `yeast_cell_cycle_control`

| Chart title | IDs | Live |
|---|---|---|
| Nurse 1997 *Cyclins and cell cycle checkpoints* | none | leftover — fictitious Science paper; do not invent |
| Qi & Elion 2005 *Control of the eukaryotic cell cycle by MAP kinase signaling pathways* | none | leftover — not unique; do not retitle |
| Morgan 1997 *Cyclin-dependent kinases: engines, clocks, and microprocessors* | DOI `10.1146/annurev.cellbio.13.1.261` PMID `9442875` → `pubmed_9442875` | identifier + abstract |
| Peters 2006 APC/C | DOI `10.1038/nrm1988` PMID `16896351` → `pubmed_16896351` | identifier + abstract |
| Musacchio & Salmon 2007 *The spindle-assembly checkpoint in space and time* | DOI `10.1038/nrm2163` PMID `17426725` → `pubmed_17426725` | identifier + abstract |

### `yeast_unfolded_protein_response`

| Chart title | IDs | Live |
|---|---|---|
| Walter & Ron 2011 *The unfolded protein response: from stress pathway to homeostatic regulation* | DOI `10.1126/science.1209038` PMID `22116877` → `pubmed_22116877` | identifier + abstract |
| Kimata 2011 *The unfolded protein response in yeast* | none | leftover — multiple 2011 Kimata papers |
| Lee et al. 2002 IRE1 / ATF6 / XBP1 | DOI `10.1101/gad.964702` PMID `11850408` → `pubmed_11850408` | identifier + abstract |
| Shamu & Walter 1996 Ire1 oligomerization/phosphorylation | DOI `10.1002/j.1460-2075.1996.tb00666.x` PMID `8670804` → `pubmed_8670804` | identifier + abstract |

### `yeast_gal_regulation`

| Chart title | IDs | Live |
|---|---|---|
| Johnston, Flick, Pexton 1994 GAL glucose repression | DOI `10.1128/mcb.14.6.3834` PMID `8196626` | identifier + abstract (DOI → `crossref_10.1128_mcb.14.6.3834`; PMID → `pubmed_8196626`) |
| Lohr, Venkov, Zlatanova 1995 GAL network | DOI `10.1096/fasebj.9.9.7601342` PMID `7601342` → `pubmed_7601342` | identifier + abstract |
| Platt & Reece 1998 Gal4p-Gal80p-Gal3p complex | DOI `10.1093/emboj/17.14.4086` PMID `9670023` → `pubmed_9670023` | identifier + abstract |
| Sellick, Campbell, Reece 2008 Leloir pathway | DOI `10.1016/S1937-6448(08)01003-4` PMID `18779058` → `pubmed_18779058` | identifier + abstract |

---

## Remaining leftovers (leave stripped)

Do **not** attach a nearby paper. Do **not** retitle Qi/Elion.

| Row | Why leftover |
|---|---|
| Kimata 2011 *The unfolded protein response in yeast* (Methods Enzymol) | Multiple 2011 Kimata/Kohno papers; no chapter with that exact title |
| Sourjik 2004 *Chemotaxis* (Curr Biol) | Three 2004 Sourjik papers; no Curr Biol primer with that title |
| Xie 2008 *The molecular machinery of autophagy: unanswered questions* | Multiple Xie/Klionsky 2007–08 papers; JCS title is Klionsky 2005 (Xie not author) |
| Levine *Autophagy genes in biology and disease* | Exact title is Yamamoto/Zhang/Mizushima 2023 PMID `36635405`. Levine 2019 Cell is a different title. **Do not reassign.** |
| Nurse 1997 *Cyclins and cell cycle checkpoints* Science | Author+year+title empty; old DOI `10.1126/science.276.5315.1886` was fictitious. **Do not invent.** |
| Qi & Elion 2005 *Control of the eukaryotic cell cycle by MAP kinase signaling pathways* | Three 2005 Qi+Elion papers; Wilkinson 2000 PMID `11053235` owns the stored longer title. **Do not retitle.** |
| Englesberg & Wilcox 1974 *Regulation: positive control* | Identity confirmed; **no published abstract** — leave empty |
| RegulonDB; Müller-Hill 1996 book | Not journal papers |

Old colliding PMIDs were **left on their original wrong KE docs**. Do not
reuse: `10899998`, `9220155`, `33197221`, `21157483`, `26350459`,
`4628819`, `12379844`, `8670867`, `21427764`, `11739403`, `9442869`,
`1730745`.

---

## GAL + Platt episode (already generated — do not regenerate)

Live `GET https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app/api/episodes/ever-bio-260010`:

| Field | Value |
|---|---|
| `episode_id` | `ever-bio-260010` |
| `title` | Decoding the Yeast Galactose Switch: A Three-Protein Paradigm Shift |
| paper DOI | `10.1093/emboj/17.14.4086` (Platt & Reece 1998) |
| paper PMID | not stored on the episode request; KE/chart PMID is `9670023` |
| `submitted_to_rss` | `false` |
| `job_id` | `7171f92b-8fc5-4958-b175-81b97fc5c6ab` |
| Cloud Run `animation_player_url` | **absent** on the episode document |

Local wiring (present, **uncommitted** — do not commit unless Gary asks):

- `public/website-only-episodes.json` lists `ever-bio-260010`
- `ANIMATED_PLAYERS` in `api/episodes/index.js` and `api/episodes/[episodeId].js` maps it to `/lac-operon-animation/player.html?episode=ever-bio-260010`

Do not touch `ever-bio-260009`. Do not generate Schleif/ara as a podcast.

---

## Chart JSON / metadata still local

Repaired process JSON under
`huggingface-space/glmp-processes-database/processes/` and
`chart_repair*.json` metadata are **not committed**. Chart JSON,
metadata, GAL mermaid, and the website-only listing stay local until
Gary asks.

---

## Historical collisions (repaired — do not re-open)

These were the original 22 August live failures. They are listed so the
old IDs are never put back on the charts.

| Chart row then | Old ID / live miss | Now |
|---|---|---|
| Schleif 2000 PNAS DOI / PMID `10899998` | DOI 404; PMID was hair-cycle paper | Schleif 2000 *Trends Genet* `11102706` |
| Napoli 2006 chart DOI `10.1016/j.str.2005.11.021` / PMID `16531234` | Iengar β-helix / titin | Napoli *JMB* `16427082` |
| Nurse 1997 Science DOI / PMID `9220155` | DOI fictitious; PMID was *E. bieneusi* | IDs stripped; no real Nurse 1997 Science paper |
| Levine PMID `33197221` | immune-checkpoint review | IDs stripped |
| Mizushima PMID `21157483` | mTOR review | Mizushima 2011 Atg `21801009` |
| Leonard 2015 JBC DOI / PMID `26350459` | DOI 404; PMID was *P. putida* | Leonard/Grimwade 2015 orisome `26082765` |
| Berg PMID `4628819` | spore-radiation paper | Berg & Brown 1972 `4563019` |
| Sourjik 2002 PMID `12379844` | SeqA structure | Sourjik & Berg 2002 `11742065` |
| Horwich GroEL DOI `10.1038/nrm2636` | unrelated clinical paper | Hayer-Hartl 2015 `26422689` |
| Ire1 PMID `8670867` | v-rel / T-cell leukemia | Shamu & Walter 1996 `8670804` |
| Peters DOI `10.1038/nrm1973` | “Microprocessor measures up” | Peters APC `10.1038/nrm1988` / `16896351` |

---

## Out of scope

- Generating or editing `ever-bio-260009` (landmark; leave as-is).
- Regenerating `ever-bio-260010`.
- Generating Schleif/ara as a podcast.
- Retitling Qi/Elion or other non-unique leftovers.
- Inventing a Nurse 1997 *Science* paper.
- Reassigning the Levine title to Mizushima.
- Inventing an Englesberg abstract.
- Re-running the whole A1 harvest.
- Committing chart JSON, metadata JSON, GAL mermaid, or website-only listing
  unless Gary asks.
