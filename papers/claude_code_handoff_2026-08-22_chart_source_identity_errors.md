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
| Nurse 1997 *Checkpoint pathways come of age* | PMID `9428508` DOI `10.1016/s0092-8674(00)80476-6` | closed — Claude Code found the real Cell commentary; editorial synopsis approved; now `identifier` + abstract after `citations[]` glmp tag |
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
| Nurse 1997 *Cyclins and cell cycle checkpoints* Science | Closed: real paper is Cell commentary PMID `9428508`. **Do not invent a Science paper.** |
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

Confirmed-only batches on 22 August closed **92 + 32 + 28 + 37 + 44** colliding chart rows across seven waves. **~63 of 264 remain.** Do not mark the goal complete. Skip already-handled leftovers. Do not overwrite a KE doc that belongs to a different paper or a same-paper Crossref twin. Leave the three surplus KE papers alone (Levine 2019 Cell, Mizushima & Komatsu 2011 Cell, Xie & Klionsky 2007 Nat Cell Biol).

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

## Confirmed-only batch (22 August 2026, fourth wave)

Same method. 18 unique retitles + 14 leftover strips. GCS three prefixes and Firestore sources-only merge + per-doc re-embed for 26 process IDs. Crossref twins not overwritten.

### Confirmed retitles (18)

| Chart | Old IDs | Confirmed | Ingest | Live |
|---|---|---|---|---|
| `yeast_mating_type_switching` Nasmyth 1983 | PMID `6687628` (DOI already official) | PMID `6339953` DOI `10.1038/302670a0` | `pubmed_6339953` | PMID identifier + abstract; DOI = older Crossref twin |
| `yeast_tor_signaling` Loewith+Hall 2011 | PMID `21376230` | PMID `22174183` DOI `10.1534/genetics.111.133363` | `pubmed_22174183` | identifier + abstract |
| `yeast_tor_signaling` Magasanik+Kaiser 2002 | PMID `12493358` | PMID `12062797` DOI `10.1016/s0378-1119(02)00558-9` | `pubmed_12062797` | identifier + abstract |
| `yeast_ubiquitin_proteasome` Finley+Ulrich 2012 | PMID `23151663` | PMID `23028185` DOI `10.1534/genetics.112.140467` | `pubmed_23028185` | identifier + abstract |
| `celegans_dauer_decision` Hu 2007 | PMID `17988075` (DOI already official) | PMID `17988074` DOI `10.1895/wormbook.1.144.1` | `pubmed_17988074` | identifier + abstract |
| `ecoli_e._coli_two_component_signaling` Stock 2000 | PMID `10966467` (DOI already official) | PMID `10966457` DOI `10.1146/annurev.biochem.69.1.183` | `pubmed_10966457` | identifier + abstract |
| `human_tlr4_lps_amplification` Covert 2005 | PMID `16166565` (DOI already official) | PMID `16166516` DOI `10.1126/science.1112304` | `pubmed_16166516` | identifier + abstract |
| `yeast_vesicle_trafficking` Bonifacino+Glick 2004 | PMID `15109499` | PMID `14744428` DOI `10.1016/s0092-8674(03)01079-1` | `pubmed_14744428` | identifier + abstract |
| `human_bcl6_gc_fate_switch` Shaffer+Staudt 2000 | PMID `10947831` | PMID `10981963` DOI `10.1016/s1074-7613(00)00020-0` | `pubmed_10981963` | identifier + abstract |
| `human_foxp3_treg_switch` Josefowicz 2012 | PMID `22278057` (DOI already official) | PMID `22318520` DOI `10.1038/nature10772` | `pubmed_22318520` | identifier + abstract |
| `ecoli_e._coli_heat_shock_response` Yura 1993 | PMID `8257110` | PMID `7504905` DOI `10.1146/annurev.mi.47.100193.001541` | `pubmed_7504905` | identifier + abstract |
| `ecoli_e._coli_acid_resistance` Foster 2004 | PMID `15040261` | PMID `15494746` DOI `10.1038/nrmicro1021` | `pubmed_15494746` | PMID identifier + abstract; DOI = older Crossref twin |
| `yeast_mapk_mating` Dohlman+Thorner 2001 | PMID `11395419` (DOI already official) | PMID `11395421` DOI `10.1146/annurev.biochem.70.1.703` | `pubmed_11395421` | identifier + abstract |
| `mouse_sox2_oct4_pluripotency` Masui 2007 | PMID `17908933` | PMID `17515932` DOI `10.1038/ncb1589` | `pubmed_17515932` | identifier + abstract |
| `yeast_mitochondrial_biogenesis` Liao+Butow 1993 | PMID `8218348` | PMID `8422683` DOI `10.1016/0092-8674(93)90050-z` | `pubmed_8422683` | identifier + abstract |
| `ecoli_fatty_acid_degradation` Clark+Cronan | PMID `15659673` | PMID `26443509` DOI `10.1128/ecosalplus.3.4.4` | `pubmed_26443509` | identifier + abstract |
| `ecoli_sulfur_metabolism` Kredich | PMID `26443778` | PMID `26443742` DOI `10.1128/ecosalplus.3.6.1.11` | `pubmed_26443742` | identifier + abstract |
| `yeast_er_stress_response` Mori 2009 | PMID `19762341` (DOI already official) | PMID `19861400` DOI `10.1093/jb/mvp166` | `pubmed_19861400` | identifier + abstract |

### Leftovers stripped this batch

Haber 2012 mating-type; Pfanner 2019; Neupert 2007; 2016 26S proteasome; Wanner 1996 phosphate; Yanofsky 2001 trp; Calame 2008; Werner 2005 NF-kB; Nerlov/Graf 2007 PU.1; Tenen 2004 C/EBP; Ye 1997 C/EBP; Lacombe 2010 SCL; Rymond+Rosbash 1992; Hinnebusch 2005 GCN2.

---

## Confirmed-only batch (22 August 2026, fifth wave)

Same method. 19 chart-row retitles (18 papers; Kaczanowska patched on both trees) + 9 leftover strips. Previously skipped informal-title rows (RecA, both MMR reviews, Hippo, ribosome Kaczanowska) were unique author+year or same-paper informal vs official, so they were retitled rather than left leftover. Synthetic-circuit charts were included. GCS three prefixes and Firestore sources-only merge + per-doc re-embed for 13 process IDs. Crossref twins not overwritten. Hippo author+year is not unique across the lab’s 2015 papers, but DOI `10.1016/j.cell.2015.10.044` / PMID `26544935` uniquely is the Yu+Zhao+Guan Cell review; kept IDs and retitled.

### Confirmed retitles (19)

| Chart | Old IDs | Confirmed | Ingest | Live |
|---|---|---|---|---|
| `ecoli_homologous_recombination` Chen+Pavletich 2008 | DOI `10.1038/nature07003` (Drosophila); PMID already official | PMID `18497818` DOI `10.1038/nature06971` *Mechanism of homologous recombination from the RecA-ssDNA/dsDNA structures.* | `pubmed_18497818` | identifier + abstract |
| `ecoli_mismatch_repair` Kunkel+Erie 2005 | titles swapped with Modrich; IDs already official | PMID `15952900` DOI `10.1146/annurev.biochem.74.082803.133243` *DNA mismatch repair.* | `pubmed_15952900` | identifier + abstract |
| `ecoli_mismatch_repair` Modrich+Lahue 1996 | titles swapped with Kunkel; IDs already official | PMID `8811176` DOI `10.1146/annurev.bi.65.070196.000533` *Mismatch repair in replication fidelity…* | `pubmed_8811176` | identifier + abstract |
| `ecoli_ribosome_assembly` Kaczanowska 2007 | glmp informal title; CW FEMS `17371510` | PMID `17804668` DOI `10.1128/mmbr.00013-07` *Ribosome biogenesis and the translation process in Escherichia coli.* | `pubmed_17804668` | identifier + abstract |
| `human_hippo_yap` Yu+Guan 2015 | informal title; IDs already official | PMID `26544935` DOI `10.1016/j.cell.2015.10.044` *Hippo Pathway in Organ Size Control…* | `pubmed_26544935` | identifier + abstract |
| `human_hippo_yap` Zhao+Guan 2007 | official title slightly longer; IDs already official | PMID `17974916` DOI `10.1101/gad.1602907` | `pubmed_17974916` | identifier + abstract |
| `synthetic_crispra_layered_logic` Gilbert+Qi 2013 | PMID `23890179` (rhinovirus); DOI already official | PMID `23849981` DOI `10.1016/j.cell.2013.06.044` | `pubmed_23849981` | identifier + abstract |
| `synthetic_crispr_recorder` Farzadfard 2019 | PMID `31302002`; DOI already official | PMID `31442423` DOI `10.1016/j.molcel.2019.07.011` | `pubmed_31442423` | identifier + abstract |
| `synthetic_crispr_recorder` Farzadfard+Lu 2014 | official title; IDs already official | PMID `25395541` DOI `10.1126/science.1256272` | `pubmed_25395541` | identifier + abstract |
| `synthetic_dcas9_logic` Gander+Klavins 2017 | PMID `28526819`; DOI already official | PMID `28541304` DOI `10.1038/ncomms15459` | `pubmed_28541304` | identifier + abstract |
| `synthetic_protease_and_gate` Win+Smolke 2007 | PMID `17715057`; DOI already official | PMID `17709748` DOI `10.1073/pnas.0703961104` | `pubmed_17709748` | identifier + abstract |
| `synthetic_theophylline_riboswitch` Desai+Gallivan 2004 | PMID `15479073`; DOI already official | PMID `15479078` DOI `10.1021/ja048634j` | `pubmed_15479078` | identifier + abstract |
| `ecoli_cell_division` Rowlett+Margolin 2015 | PMID `25741323`; DOI already official | PMID `26029202` DOI `10.3389/fmicb.2015.00478` | `pubmed_26029202` | identifier + abstract |
| `ecoli_cell_division` Meeske+Bernhardt 2016 | PMID `26840489` DOI `10.1038/nature16966` | PMID `27525505` DOI `10.1038/nature19331` | `pubmed_27525505` | identifier + abstract |
| `ecoli_dna_replication_elongation` Johnson+O'Donnell 2005 | informal title; IDs already official | PMID `15952889` DOI `10.1146/annurev.biochem.73.011303.073859` *Cellular DNA replicases…* | `pubmed_15952889` | identifier + abstract |
| `ecoli_oxidative_stress_response` Greenberg+Demple 1990 | PMID `2164424`; DOI already official | PMID `1696718` DOI `10.1073/pnas.87.16.6181` | `pubmed_1696718` | identifier + abstract |
| `ecoli_oxidative_stress_response` Choi+Storz 2001 | PMID `11323133` DOI `…00531-2` | PMID `11301006` DOI `10.1016/s0092-8674(01)00300-2` | `pubmed_11301006` | identifier + abstract |
| `yeast_mating_response` Brizzio 1996 | PMID `8655580`; DOI already official | PMID `8991086` DOI `10.1083/jcb.135.6.1727` | `pubmed_8991086` | identifier + abstract |

Hippo/Zhao and Farzadfard 2014 are glmp-only charts (no CW twin). Synthetic charts are glmp-only.

### Leftovers stripped this batch

Erickson 2010 FtsZ filament; den Blaauwen 2008 Divisome; McHenry 2011 Pol III; Robinson+van Oijen 2013 replisome; Sauer 2022 nucleosome/replisome; Storz 1990 OxyR; Hidalgo+Demple 1997 SoxR; Bardwell 2004 pheromone; Dohlman 2001 Science pheromone.

---

## Confirmed-only batch (22 August 2026, sixth wave)

Same method. Prefer remaining DOI/CW-tree collisions that still live-resolve to the wrong paper (stale scan used only as a candidate list). 23 unique retitles + 14 leftover strips. GCS three prefixes. Firestore sources-only merge + per-doc re-embed for changed process IDs that exist in the glmp twin; CW-only rows were not used to overwrite a previously repaired glmp Firestore source list. Crossref twins not overwritten. Nurse/Englesberg chart rows were committed, not reverted.

### Confirmed retitles (23)

| Chart | Old IDs | Confirmed | Ingest | Live |
|---|---|---|---|---|
| `bacillus_biofilm_formation` Kearns 2005 | PMID `16237402` DOI `10.1038/nature04187` (yeast phosphoproteome) | PMID `15661000` DOI `10.1111/j.1365-2958.2004.04440.x` *A master regulator for biofilm formation by Bacillus subtilis.* | `pubmed_15661000` | identifier + abstract |
| `ecoli_nucleotide_biosynthesis` Gerhart 1965 | PMID `14324200` DOI `10.1021/bi00882a019` (RNase) | PMID `5320387` DOI `10.1021/bi00882a012` *Distinct subunits for the regulation and catalytic activity of aspartate transcarbamylase.* | `pubmed_5320387` | identifier; **abstract empty** (none in EuropePMC — do not invent) |
| `ecoli_ribosome_assembly` Shajani 2011 | PMID `21858987` DOI `10.1038/nrm3173` (ubiquitin) | PMID `21529161` DOI `10.1146/annurev-biochem-062608-160432` *Assembly of bacterial ribosomes.* | `pubmed_21529161` | identifier + abstract |
| `ecoli_sigma_factor_competition` Jishage 2002 | PMID `12169625` DOI `10.1093/emboj/cdf389` (Hodgkin) | PMID `12023304` DOI `10.1101/gad.227902` *Regulation of sigma factor competition by the alarmone ppGpp.* | `pubmed_12023304` | identifier + abstract |
| `ecoli_transcription_regulation` Gruber 2003 | PMID `12511870` DOI `10.1038/nrm1012` | PMID `14527287` DOI `10.1146/annurev.micro.57.030502.090913` *Multiple sigma subunits and the partitioning of bacterial transcription space.* | `pubmed_14527287` | identifier + abstract |
| `yeast_dna_replication` Donovan 1997 | PMID `9356470` DOI `10.1073/pnas.94.23.12419` (Grb2) | PMID `9159120` DOI `10.1073/pnas.94.11.5611` *Cdc6p-dependent loading of Mcm proteins onto pre-replicative chromatin in budding yeast.* | `pubmed_9159120` | identifier + abstract |
| `yeast_mitochondrial_biogenesis` Butow 2004 | PMID `15189150` DOI `10.1146/annurev.biochem.73.011303.073940` (opioid) | PMID `15068799` DOI `10.1016/s1097-2765(04)00179-0` *Mitochondrial signaling: the retrograde response.* | `pubmed_15068799` | identifier + abstract |
| `yeast_nucleotide_excision_repair` Marteijn 2014 | PMID `24485458` DOI `10.1016/j.cell.2014.01.002` | PMID `24954209` DOI `10.1038/nrm3822` *Understanding nucleotide excision repair and its roles in cancer and ageing.* | `pubmed_24954209` | identifier + abstract |
| `yeast_snf1_pathway` Hedbacker 2008 | PMID `18195048` DOI `10.2741/2833` | PMID `17981722` DOI `10.2741/2854` *SNF1/AMPK pathways in yeast.* | `pubmed_17981722` | identifier + abstract |
| `yeast_vesicle_trafficking` Aridor 1995 | PMID `7600570` DOI `10.1016/0092-8674(95)90123-X` (Drosophila MAPK) | PMID `7490291` DOI `10.1083/jcb.131.4.875` *Sequential coupling between COPII and COPI vesicle coats…* | `pubmed_7490291` | identifier + abstract |
| `yeast_vesicle_trafficking` Brandizzi 2013 | PMID `23743846` DOI `10.1038/nrm3601` (macrodomain) | PMID `23698585` DOI `10.1038/nrm3588` *Organization of the ER-Golgi interface for membrane traffic control.* | `pubmed_23698585` | identifier + abstract |
| `ecoli_trp_operon` Oxender 1979 | PMID `388431`; DOI already official | PMID `118451` DOI `10.1073/pnas.76.11.5524` *Attenuation in the Escherichia coli tryptophan operon…* | `pubmed_118451` | identifier + abstract |
| `yeast_ubiquitin_proteasome` Hochstrasser 1996 | informal title; IDs already official | PMID `8982460` DOI `10.1146/annurev.genet.30.1.405` *Ubiquitin-dependent protein degradation.* | `pubmed_8982460` | identifier + abstract |
| `ecoli_starvation_response` Majdalani 1998 | PMID `9826730`; DOI already official | PMID `9770508` DOI `10.1073/pnas.95.21.12462` *DsrA RNA regulates translation of RpoS message…* | `pubmed_9770508` | identifier + abstract |
| `ecoli_nitrogen_assimilation` Ninfa 2005 | PMID `15802258`; DOI already official | PMID `15802248` DOI `10.1016/j.mib.2005.02.011` *PII signal transduction proteins…* | `pubmed_15802248` | identifier + abstract |
| `ecoli_dna_replication_termination` Aussel 2002 | PMID `12068798` DOI `10.1046/j.1365-2958.2002.02962.x` | PMID `11832210` DOI `10.1016/s0092-8674(02)00624-4` *FtsK Is a DNA motor protein that activates chromosome dimer resolution…* | `pubmed_11832210` | identifier + abstract |
| `ecoli_homologous_recombination` Dillingham 2008 | PMID `18322035` DOI `10.1128/MMBR.00020-07` (HIV) | PMID `19052323` DOI `10.1128/mmbr.00020-08` *RecBCD enzyme and the repair of double-stranded DNA breaks.* | `pubmed_19052323` | identifier + abstract |
| `ecoli_heavy_metal_resistance` Patzer 1998 | PMID `9422595` DOI `10.1128/jb.180.3.680-689.1998` (archaeal ABC) | PMID `9680209` DOI `10.1046/j.1365-2958.1998.00883.x` *The ZnuABC high-affinity zinc uptake system and its regulator Zur…* | `pubmed_9680209` | identifier + abstract |
| `ecoli_transcription_elongation` Borukhov 1992 | PMID `1339300` DOI `10.1016/0092-8674(92)90590-4` | PMID `1384037` DOI `10.1073/pnas.89.19.8899` *GreA protein: a transcription elongation factor from Escherichia coli.* | `pubmed_1384037` | identifier + abstract |
| `ecoli_tca_cycle` LaPorte 1982 | PMID `6750117` (ibuprofen); DOI already official | PMID `6292732` DOI `10.1038/300458a0` *A protein with kinase and phosphatase activities involved in regulation of tricarboxylic acid cycle.* | `pubmed_6292732` | identifier; **abstract empty** (none in EuropePMC — do not invent) |
| `yeast_dna_replication` Labib 2010 | PMID `19927129` DOI `10.1038/emboj.2009.340` | PMID `20551170` DOI `10.1101/gad.1933010` *How do Cdc7 and cyclin-dependent kinases trigger the initiation of chromosome replication…* | `pubmed_20551170` | identifier + abstract |
| `ecoli_translation_elongation` Ogle 2001 | PMID `11423924`; DOI already official | PMID `11340196` DOI `10.1126/science.1060612` *Recognition of cognate transfer RNA by the 30S ribosomal subunit.* | `pubmed_11340196` | PMID identifier + abstract; DOI = older Crossref twin |
| `ecoli_transcription_elongation` Wang+Kornberg 2006 | PMID `16630813` DOI `10.1016/j.cell.2006.03.034` (Dscam) | PMID `17129781` DOI `10.1016/j.cell.2006.11.023` *Structural basis of transcription: role of the trigger loop…* | `pubmed_17129781` | identifier + abstract |

### Leftovers stripped this batch

Borisov 2011 respiration; Portnoy 2008 anaerobiosis; Gong 2011 acid resistance; Narayana 2018 two-component; Clark 1989 mixed-acid; Blangy 1968 (two PFK papers); Hampton 2022 phage defence; Egan 2017 peptidoglycan; Bassler 2019 ribosome biogenesis; Nakano 1989 Sar1p; Wade 2008 sigma subunit; Maeda 1994 HOG; Richet 1991 MalT; Ullmann 1968 catabolite repression.

---

## Confirmed-only batch (22 August 2026, seventh wave)

Same method. Prefer remaining IDs that still live-resolve to the wrong paper. 37 chart-row retitles (36 papers; Weixlbaumer patched on both elongation and termination charts) + 14 leftover strips. 7 of the 37 were informal-title keep-ID retitles. GCS three prefixes. Firestore sources-only merge + per-doc re-embed for the 15 process IDs whose glmp twin was patched; CW-only rows were not used to overwrite a previously repaired glmp Firestore source list. Crossref twins not overwritten. Nurse/Englesberg chart rows were not touched. Surplus KE papers (Levine 2019, Mizushima & Komatsu 2011, Xie & Klionsky 2007) left alone.

### Confirmed retitles (37)

| Chart | Old IDs | Confirmed | Ingest | Live |
|---|---|---|---|---|
| `ecoli_amino_acid_biosynthesis` Gibson 1968 | PMID `4883395` DOI `10.1128/br.32.4.465-492.1968` | PMID `4884716` DOI `10.1128/mmbr.32.4_pt_2.465-492.1968` | `pubmed_4884716` | identifier; **abstract empty** (none in EuropePMC — do not invent) |
| `ecoli_heavy_metal_resistance` Brocklehurst 1999 | PMID `10383764` DOI `10.1046/j.1365-2958.1999.01459.x` | PMID `10048032` DOI `10.1046/j.1365-2958.1999.01229.x` | `pubmed_10048032` | identifier + abstract |
| `ecoli_heavy_metal_resistance` Rensing 2000 | PMID `10716729`; DOI already official | PMID `10639134` DOI `10.1073/pnas.97.2.652` | `pubmed_10639134` | PMID identifier + abstract; DOI = older Crossref twin |
| `ecoli_pho_regulon` Surin 1985 | PMID `2981804` | PMID `3881386` DOI `10.1128/jb.161.1.189-198.1985` | `pubmed_3881386` | identifier + abstract |
| `ecoli_translation_elongation` Nissen 2000 | PMID `10926528`; DOI already official | PMID `10937990` DOI `10.1126/science.289.5481.920` | `pubmed_10937990` | PMID identifier + abstract; DOI = older Crossref twin |
| `yeast_cell_cycle_checkpoints` Weinert 1988 | PMID `3046045` DOI `10.1126/science.3046045` | PMID `3291120` DOI `10.1126/science.3291120` | `pubmed_3291120` | identifier + abstract |
| `yeast_cell_cycle_checkpoints` Li 1991 | PMID `1716335` DOI `10.1016/0092-8674(91)90013-C` | PMID `1651172` DOI `10.1016/0092-8674(81)90015-5` | `pubmed_1651172` | identifier + abstract |
| `yeast_er_stress_response` Mori 1993 | PMID `8358788` DOI `10.1016/0092-8674(93)90299-F` | PMID `8358794` DOI `10.1016/0092-8674(93)90521-q` | `pubmed_8358794` | identifier + abstract |
| `yeast_mapk_mating` Choi 1994 | PMID `7968393` DOI `10.1128/mcb.14.11.7329-7339.1994` | PMID `8062390` DOI `10.1016/0092-8674(94)90427-8` | `pubmed_8062390` | identifier + abstract |
| `yeast_tor_signaling` Loewith 2002 | PMID `12150915`; DOI already official | PMID `12408816` DOI `10.1016/s1097-2765(02)00636-6` | `pubmed_12408816` | PMID identifier + abstract; DOI = older Crossref twin |
| `yeast_ribosome_biogenesis` Woolford 2013 | PMID `24204128` DOI `10.1534/genetics.113.151121` | PMID `24190922` DOI `10.1534/genetics.113.153197` | `pubmed_24190922` | identifier + abstract |
| `yeast_rna_splicing` Staley 1998 | PMID `9529249` DOI `10.1016/s0092-8674(00)81404-9` | PMID `9476892` DOI `10.1016/s0092-8674(00)80925-3` | `pubmed_9476892` | identifier; **abstract empty** (none in EuropePMC — do not invent) |
| `ecoli_transcription_regulation` Browning 2004 | informal title; IDs already official | PMID `15035009` DOI `10.1038/nrmicro787` | `pubmed_15035009` | identifier + abstract |
| `human_hsf1_heat_shock` Anckar 2011 | informal title; IDs already official | PMID `21417720` DOI `10.1146/annurev-biochem-060809-095203` | `pubmed_21417720` | identifier + abstract |
| `ecoli_nucleotide_excision_repair` Sancar 1983 | informal title; IDs already official | PMID `6380755` DOI `10.1016/0092-8674(83)90354-9` | `pubmed_6380755` | identifier + abstract |
| `ecoli_transcription_regulation` Saecker 2011 | informal title; IDs already official | PMID `21371479` DOI `10.1016/j.jmb.2011.01.018` | `pubmed_21371479` | identifier + abstract |
| `ecoli_nucleotide_excision_repair` Truglio 2006 | informal title; IDs already official | PMID `16532007` DOI `10.1038/nsmb1072` | `pubmed_16532007` | identifier + abstract |
| `ecoli_base_excision_repair` Kuo 1992 | informal title; IDs already official | PMID `1411536` DOI `10.1126/science.1411536` | `pubmed_1411536` | identifier + abstract |
| `ecoli_outer_membrane_assembly` Voulhoux 2003 | PMID `12702812` DOI `10.1126/science.1082531` | PMID `12522254` DOI `10.1126/science.1078973` | `pubmed_12522254` | identifier + abstract |
| `ecoli_phosphate_transport` Hsieh 2010 | PMID `20554707` DOI `10.1101/cshperspect.a000492` | PMID `20171928` DOI `10.1016/j.mib.2010.01.014` | `pubmed_20171928` | identifier + abstract |
| `yeast_pka_pathway` Broach 2012 | PMID `23144415` DOI `10.1534/genetics.112.145330` | PMID `22964838` DOI `10.1534/genetics.111.135731` | `pubmed_22964838` | identifier + abstract |
| `yeast_meiosis_regulation` Vershon 2000 | PMID `10801461`; DOI already official | PMID `10801467` DOI `10.1016/s0955-0674(00)00104-6` | `pubmed_10801467` | identifier + abstract |
| `yeast_meiosis_regulation` Kassir 2003 | PMID `12722949`; DOI already official | PMID `12722950` DOI `10.1016/s0074-7696(05)24004-4` | `pubmed_12722950` | identifier + abstract |
| `yeast_rna_splicing` Yan 2015 | PMID `25977550` DOI `10.1126/science.aab3935` | PMID `26292707` DOI `10.1126/science.aac7629` | `pubmed_26292707` | identifier + abstract |
| `yeast_cell_wall_integrity` Levin 2005 | PMID `16153177` DOI `10.1146/annurev.micro.59.030704.101037` | PMID `15944456` DOI `10.1128/mmbr.69.2.262-291.2005` | `pubmed_15944456` | identifier + abstract |
| `ecoli_aerobic_respiration` Unden 1997 | PMID `9343358` DOI `10.1146/annurev.micro.51.1.795` | PMID `9230919` DOI `10.1016/s0005-2728(97)00034-0` | `pubmed_9230919` | identifier + abstract |
| `ecoli_anaerobic_respiration` Leonardo 1996 | PMID `8631678` DOI `10.1128/jb.178.11.3391-3393.1996` | PMID `8830700` DOI `10.1128/jb.178.20.6013-6018.1996` | `pubmed_8830700` | identifier + abstract |
| `ecoli_mismatch_repair` Warren 2007 | informal title; IDs already official | PMID `17531815` DOI `10.1016/j.molcel.2007.04.018` | `pubmed_17531815` | identifier + abstract |
| `yeast_dna_replication` Bell 1992 | PMID `1374780`; DOI already official | PMID `1579162` DOI `10.1038/357128a0` | `pubmed_1579162` | identifier + abstract |
| `yeast_er_stress_response` Cox 1996 | PMID `8898196` DOI `10.1016/S0092-8674(00)80138-1` | PMID `8898193` DOI `10.1016/s0092-8674(00)81360-4` | `pubmed_8898193` | identifier + abstract |
| `yeast_chromatin_silencing` Imai 2000 | PMID `10688204` DOI `10.1038/35003502` | PMID `10693811` DOI `10.1038/35001622` | `pubmed_10693811` | identifier + abstract |
| `ecoli_translation_elongation` Weixlbaumer 2008 | PMID `18408881` DOI `10.1038/nature06700` | PMID `18596689` DOI `10.1038/nature07115` | `pubmed_18596689` | identifier + abstract |
| `ecoli_translation_termination` Weixlbaumer 2008 | same colliding IDs | same `18596689` | `pubmed_18596689` | identifier + abstract |
| `yeast_snf1_pathway` Hardie 1998 | PMID `9774302` DOI `10.1093/emboj/17.20.5779` | PMID `9759505` DOI `10.1146/annurev.biochem.67.1.821` | `pubmed_9759505` | identifier + abstract |
| `yeast_nucleotide_excision_repair` Guzder 1994 | PMID `8119565` DOI `10.1016/S0021-9258(17)37493-2` | PMID `8202161` DOI `10.1038/369578a0` | `pubmed_8202161` | identifier + abstract |
| `ecoli_dna_replication_termination` Duggin 2009 | PMID `19220742` DOI `10.1111/j.1365-2958.2008.06478.x` | PMID `19233209` DOI `10.1016/j.jmb.2009.02.027` | `pubmed_19233209` | identifier + abstract |
| `yeast_pka_pathway` Toda 1987 | PMID `2820067` DOI `10.1128/MCB.7.4.1371` | PMID `3036373` DOI `10.1016/0092-8674(87)90223-6` | `pubmed_3036373` | identifier + abstract |

### Leftovers stripped this batch

Romero 2011 amyloid biofilm; Vlamakis 2013 genetic architecture; Moir 1990 germination; Setlow 2014 germination; Umbarger 1969; Umbarger 1978 (PMID `354503` occupied by a different KE/EuropePMC record — do not overwrite); Khoroshilova 1997 Science FNR title not found; Georgellis 2001 ArcB/quinone; Grossman 1984 RpoH; Cronan 2004 fatty acid; Elion 1991 FUS3; Yan 2017 spliceosome; Artsimovitch 2000 NusG; Knowles 2009 BamA.

---

## Chart JSON / metadata

Nine-chart: copernicus-web `a3c791e71`, glmp `1e879f8`. Second wave: CW `422dea029` / `1febc208b`, glmp `8a0b8cd`. Third wave: CW `89af4aa7b`, glmp `41e3bed`. Fourth wave: CW `254b82bbe`, glmp `d173663`. Fifth wave: CW `8cfdea764`, glmp `2c506ce`. Sixth wave: CW `12c407614`, glmp `f996d68`. Seventh-wave chart JSON and this handoff commit next. Live GCS and Firestore sources for waves 2–7 were merged. `chart_repair*.json` stays uncommitted. Remaining collisions after this wave: **~63** of the original 264 (row-based; 107 − 30 ID replacements − 14 leftover strips; scan file is stale).

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
