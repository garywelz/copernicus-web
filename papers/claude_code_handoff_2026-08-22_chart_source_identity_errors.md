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

## Whole-collection scan (22 August 2026, live `/resolve-paper`)

The original nine charts are repaired except leftover garbled titles
(do not invent). A scan of **all** process `sources[]` IDs is **not
clean**. Do not treat the rest of GLMP as identity-safe.

| Count | What |
|---|---|
| 108 | `copernicus-web` huggingface-space process JSONs |
| 208 | `glmp` `glmp-v2/processes` JSONs (excluding `_previous_versions`) |
| 968 | unique DOI/PMID pairs resolved (`cited_project=glmp`) |
| 293 | identifier match, title compatible with the chart row |
| 264 | identifier match but live title is a **different paper** |
| 146 | `identifier_not_found` |
| 15 | identifier + empty abstract (includes Englesberg; others need published-abstract check, do not invent) |

264 colliding IDs span **73** `glmp` processes (plus overlapping copernicus-web copies). Same pattern as the nine-chart work: the stored PMID/DOI often names an unrelated article. Examples: biofilm DOI `10.1038/nature04187` resolves to a yeast phosphoproteome paper; ArcA PMID `3054468` resolves to a plasmid-classification paper; arginine-repressor PMID `7854251` resolves to a dehalogenase review.

Two confirmed-only batches on 22 August closed **60** colliding chart rows (20+20 unique retitles and 6+14 leftover strips). **~204 of 264 remain.** Do not mark the goal complete. Skip the original-nine leftovers (Kimata, Sourjik 2004, Xie, Levine, Nurse, Qi/Elion, Englesberg) and leftover strips already recorded below. Do not overwrite a KE doc that belongs to a different paper.

---

## Confirmed-only batch (22 August 2026, second wave)

Author + year + topic uniqueness only. Old PMID/DOI ignored as identity. Official ingest `--include-glob "**/chart_repair*.json" --no-skip-existing`. Chart `sources` updated in both repos when the colliding row existed in both (CW often has a different source list — those unpatched CW files were left alone). GCS: three prefixes. Firestore `glmp_processes`: sources-only `update()` + per-doc re-embed for the 22 process IDs below. Old colliding KE docs were not overwritten.

### Confirmed retitles (20)

| Chart | Old IDs | Confirmed | Ingest | Live `/resolve-paper` |
|---|---|---|---|---|
| `ecoli_anaerobic_respiration` Iuchi & Lin 1988 | PMID `3054468` DOI `10.1128/mr.52.4.452-469.1988` | PMID `2964639` DOI `10.1073/pnas.85.6.1888` *arcA (dye), a global regulatory gene…* | `pubmed_2964639` | identifier + abstract (PMID and DOI) |
| `ecoli_arginine_biosynthesis` Maas 1994 | PMID `7854251` (DOI already correct) | PMID `7854250` DOI `10.1128/mr.58.4.631-640.1994` *The arginine repressor of Escherichia coli.* | `pubmed_7854250` | identifier + abstract |
| `ecoli_biofilm_formation` Bokranz 2005 | PMID `15640219` | PMID `16278431` DOI `10.1099/jmm.0.46064-0` *Expression of cellulose and curli fimbriae…* | `pubmed_16278431` | identifier + abstract |
| `ecoli_biofilm_formation` Flemming 2023 | PMID `36864250` (title already official) | PMID `36127518` DOI `10.1038/s41579-022-00791-0` | `pubmed_36127518` | identifier + abstract |
| `ecoli_catabolite_repression` Busby & Ebright 1999 | PMID `10367881` DOI `10.1016/S0092-8674(00)80764-5` | PMID `10550204` DOI `10.1006/jmbi.1999.3161` *Transcription activation by CAP* | `pubmed_10550204` | identifier + abstract |
| `ecoli_catabolite_repression` Görke & Stülke 2008 | PMID `18626614` DOI `10.1007/s00203-008-0429-6` | PMID `18628769` DOI `10.1038/nrmicro1932` *Carbon catabolite repression in bacteria…* | `pubmed_18628769` | identifier + abstract |
| `ecoli_catabolite_repression` Kolb et al. 1993 | PMID `8341589` DOI `10.1093/nar/21.14.3171` | PMID `8394684` DOI `10.1146/annurev.bi.62.070193.003533` *Transcriptional regulation by cAMP and its receptor protein.* | `pubmed_8394684` | identifier; **abstract empty** (none in EuropePMC — do not invent) |
| `ecoli_dna_damage_checkpoint` Little et al. 1980 | PMID `6449016` (DOI already correct) | PMID `6447873` DOI `10.1073/pnas.77.6.3225` *Cleavage of the E. coli lexA protein by the recA protease.* | `pubmed_6447873` | identifier + abstract |
| `ecoli_dna_replication_termination` Neylon 2005 | PMID `15686551` DOI `10.1111/j.1365-2958.2005.04473.x` (Bacillus CcpN) | PMID `16148308` DOI `10.1128/mmbr.69.3.501-526.2005` *Replication termination in Escherichia coli…* | `pubmed_16148308` | identifier + abstract |
| `ecoli_flagellar_assembly` Minamino 2008 | PMID `18950710` (DOI already official paper) | PMID `18848888` DOI `10.1016/j.sbi.2008.09.006` | `pubmed_18848888` | PMID identifier + abstract. DOI hits older `crossref_10.1016_j.sbi.2008.09.006` (`identifier_wrong_project`, empty abstract) — same paper twin, not overwritten |
| `ecoli_heavy_metal_resistance` Franke 2003 | PMID `12682013` DOI `10.1093/emboj/cdg239` (hair morphogenesis) | PMID `12813074` DOI `10.1128/jb.185.13.3804-3812.2003` *Molecular analysis of … CusCFBA* | `pubmed_12813074` | identifier + abstract |
| `ecoli_homologous_recombination` Saito 1995 | PMID `7489502` | PMID `7638215` DOI `10.1073/pnas.92.16.7470` *…catalytic center of the RuvC…* | `pubmed_7638215` | identifier + abstract |
| `ecoli_homologous_recombination` Smith 2012 | PMID `22503770` DOI `10.1016/j.tig.2012.03.002` (CNV review) | PMID `22688812` DOI `10.1128/mmbr.05026-11` *How RecBCD enzyme and Chi promote DNA break repair…* | `pubmed_22688812` | identifier + abstract |
| `ecoli_sos_lexa` Little & Mount 1982 | PMID `7053433` (DOI already official) | PMID `7049397` DOI `10.1016/0092-8674(82)90085-x` | `pubmed_7049397` | identifier; **abstract empty** (none in EuropePMC — do not invent) |
| `ecoli_pentose_phosphate_pathway` Stincone 2015 | PMID `25585159` DOI `10.1038/nrm3934` (APC/mitosis) | PMID `25243985` DOI `10.1111/brv.12140` *The return of metabolism… pentose phosphate pathway.* | `pubmed_25243985` | identifier + abstract |
| `ecoli_phage_defense` Marraffini & Sontheimer 2010 | PMID `20548291` (DOI already official) | PMID `20125085` DOI `10.1038/nrg2749` *CRISPR interference: RNA-directed adaptive immunity…* | `pubmed_20125085` | identifier + abstract |
| `yeast_chromatin_silencing` Rusche, Kirchmaier, Rine 2003 | PMID `12676795` (DOI already official) | PMID `12676793` DOI `10.1146/annurev.biochem.72.121801.161547` | `pubmed_12676793` | identifier + abstract |
| `yeast_cell_wall_integrity` Levin 2005 | PMID `16339739` DOI `10.1128/MMBR.69.4.262-291.2005` | PMID `15944456` DOI `10.1128/mmbr.69.2.262-291.2005` *Cell wall integrity signaling in Saccharomyces cerevisiae.* | `pubmed_15944456` | identifier + abstract |
| `yeast_snf1_pathway` Hedbacker & Carlson 2008 | PMID `18299209` DOI `10.1016/j.bbapap.2008.01.013` (Zic/Gli CD spectra) | PMID `17981722` DOI `10.2741/2854` *SNF1/AMPK pathways in yeast.* | `pubmed_17981722` | identifier + abstract |
| `yeast_pka_pathway` Thevelein & de Winde 1999 | PMID `10510231` (DOI already official paper) | PMID `10476026` DOI `10.1046/j.1365-2958.1999.01538.x` *Novel sensing mechanisms and targets for the cAMP-protein kinase A pathway…* | `pubmed_10476026` | identifier + abstract |

### Leftovers stripped this batch (author+year not unique)

| Chart | Old IDs | Leftover |
|---|---|---|
| `ecoli_pho_regulon` Wanner 1996 | PMID `8752318` DOI `10.1128/jb.178.17.5024-5032.1996` | stripped — several 1996 Wanner phosphate/Pho papers |
| `ecoli_outer_membrane_assembly` Ricci & Silhavy 2012 | PMID `22889723` DOI `10.1016/j.bbamcr.2012.04.007` (neuron mitochondria) | stripped — three 2012 BAM papers |
| `ecoli_nucleotide_biosynthesis` Zalkin & Dixon 1992 | PMID `1410045` DOI `10.1016/s0079-6603(08)60364-4` | stripped — not unique |
| `bacillus_biofilm_formation` Vlamakis et al. 2013 | PMID `23979428` DOI `10.1038/nrmicro3103` | stripped — several 2013 biofilm papers |
| `yeast_nitrogen_metabolism` Cooper 2002 | PMID `12493770` DOI `10.1111/j.1574-6976.2002.tb00614.x` (viral killer) | stripped — several 2002 Cooper nitrogen papers |
| `human_bcl2_bax_momp` Chipuk & Green 2008 | PMID `18505631` DOI `10.1016/j.jaci.2007.10.026` (allergy immunotherapy) | stripped — several 2008 Chipuk/Green apoptosis papers |

Skipped as likely same-paper / informal-title false positives (not in this batch): Hippo `26544935`; mismatch-repair `15952900` / `8811176`; RecA `18497818`; ribosome `17804668`. Glycolysis PTS was repaired in the third wave.

---

## Confirmed-only batch (22 August 2026, third wave)

Same method. 20 unique retitles + 14 leftover strips. GCS three prefixes and Firestore sources-only merge + per-doc re-embed for 21 process IDs. Old colliding KE docs were not overwritten. Several DOI queries hit older same-paper Crossref twins (`identifier_wrong_project`); PMID path is clean.

### Confirmed retitles (20)

| Chart | Old IDs | Confirmed | Ingest | Live |
|---|---|---|---|---|
| `ecoli_base_excision_repair` Mol/Tainer 1999 | PMID `10410796` (DOI already official) | PMID `10410797` DOI `10.1146/annurev.biophys.28.1.101` *DNA repair mechanisms for the recognition and removal of damaged DNA bases.* | `pubmed_10410797` | PMID identifier + abstract; DOI = older Crossref twin |
| `ecoli_glycolysis` Postma 1993 | PMID `8177168` (DOI already official) | PMID `8246840` DOI `10.1128/mr.57.3.543-594.1993` *Phosphoenolpyruvate:carbohydrate phosphotransferase systems of bacteria.* | `pubmed_8246840` | PMID identifier + abstract; DOI = older Crossref twin |
| `ecoli_nucleotide_excision_repair` Selby & Sancar 1994 | PMID `7968919` | PMID `7968917` DOI `10.1128/mr.58.3.317-329.1994` | `pubmed_7968917` | identifier + abstract |
| `ecoli_periplasmic_stress` Rowley 2006 | PMID `16406775` DOI `10.1016/j.mib.2005.12.008` | PMID `16715050` DOI `10.1038/nrmicro1394` *Pushing the envelope…* | `pubmed_16715050` | identifier + abstract |
| `ecoli_starvation_response` Becker 1999 | PMID `10485858` (DOI already official) | PMID `10339606` DOI `10.1073/pnas.96.11.6439` | `pubmed_10339606` | identifier + abstract |
| `ecoli_stringent_response` Hauryliuk 2015 | DOI `10.1038/nrmicro3449` (HIV paper); PMID already correct | PMID `25853779` DOI `10.1038/nrmicro3448` *Recent functional insights into the role of (p)ppGpp…* | `pubmed_25853779` | identifier + abstract |
| `ecoli_transcription_termination` Skordalakes 2003 | PMID `14608371` DOI `10.1038/nature02129` | PMID `12859904` DOI `10.1016/s0092-8674(03)00512-9` | `pubmed_12859904` | identifier + abstract |
| `ecoli_transcription_termination` Gusarov 1999 | PMID `10617163` DOI `10.1016/s1097-2765(00)80159-4` | PMID `10230402` DOI `10.1016/s1097-2765(00)80477-3` | `pubmed_10230402` | identifier + abstract |
| `ecoli_transcription_termination` Burns 1995 | PMID `7537109` DOI `10.1021/bi00016a025` | PMID `7761393` DOI `10.1073/pnas.92.11.4738` | `pubmed_7761393` | identifier + abstract |
| `ecoli_nitrogen_assimilation` Leigh 2007 | PMID `17506685` (DOI already official) | PMID `17506680` DOI `10.1146/annurev.micro.61.080706.093409` | `pubmed_17506680` | PMID identifier + abstract; DOI = older Crossref twin |
| `ecoli_sigma_factor_competition` Mauri 2014 | PMID `25313164` | PMID `25299042` DOI `10.1371/journal.pcbi.1003845` | `pubmed_25299042` | identifier + abstract |
| `ecoli_rna_polymerase_recycling` Mauri 2014 | PMID `25081213` | same `25299042` (unique 2014 Mauri+Klumpp paper) | `pubmed_25299042` | identifier + abstract |
| `ecoli_rna_polymerase_recycling` Mitra 2017 | PMID `28301741` | PMID `28731845` DOI `10.1146/annurev-micro-030117-020432` | `pubmed_28731845` | identifier + abstract |
| `ecoli_ribosome_assembly` Culver 2003 | PMID `14505815` | PMID `12548626` DOI `10.1002/bip.10221` | `pubmed_12548626` | identifier + abstract |
| `ecoli_tca_cycle` Sauer 2005 | PMID `16003780` | PMID `16102602` DOI `10.1016/j.femsre.2004.11.002` | `pubmed_16102602` | identifier + abstract |
| `ecoli_translation_termination` Decatur 2002 | PMID `12127453` | PMID `12114023` DOI `10.1016/s0968-0004(02)02109-6` | `pubmed_12114023` | identifier + abstract |
| `ecoli_translation_termination` Freistroffer 1997 | PMID `9312005` (DOI already official) | PMID `9233821` DOI `10.1093/emboj/16.13.4126` | `pubmed_9233821` | PMID identifier + abstract; DOI = older Crossref twin |
| `ecoli_two_component_signaling` Kenney 2012 | PMID `22580561` | PMID `22543870` DOI `10.1038/emboj.2012.99` | `pubmed_22543870` | identifier + abstract |
| `yeast_hog_pathway` Brewster 1993 | PMID `8391169` (PMID-as-DOI) | PMID `7681220` DOI `10.1126/science.7681220` | `pubmed_7681220` | identifier + abstract |
| `yeast_hog_pathway` Posas 1997 | PMID `9184233` | PMID `9180081` DOI `10.1126/science.276.5319.1702` | `pubmed_9180081` | identifier + abstract |

### Leftovers stripped this batch

Keyamura RecN 2009; Dippel+Boos 2005; Jiricny 2006; Clausen DegP 2011; Stephenson+Hoch 2002; Friedberg 2005 SOS; Henestrosa 2000 SOS; Little 2003 LexA; Hengge-Aronis 2002 RpoS; Gruer 1997 aconitase; Mizuno 1997 EnvZ; Dean 2011 T3SS; Diepold 2015 T3SS; Albertyn 1994 glycerol/HOG.

---

## Chart JSON / metadata

Nine-chart repairs: copernicus-web `a3c791e71`, glmp `1e879f8`. Second wave: copernicus-web `422dea029` / `1febc208b`, glmp `8a0b8cd` (now on origin). Third-wave chart JSON and this handoff commit next. Live GCS and Firestore sources for the process IDs in waves 2–3 were merged. `chart_repair*.json` stays uncommitted.

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
- Committing metadata JSON, GAL mermaid, or website-only listing unless
  Gary asks. Chart-JSON identity corrections in both repos are authorized.
