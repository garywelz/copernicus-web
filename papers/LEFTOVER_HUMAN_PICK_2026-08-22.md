## OPEN PICKS FOR CLAUDE CODE
Use `papers/claude_code_handoff_2026-08-23_leftover_picks.md` as the current brief.

1. 4a Qi 16105880 — **APPLIED** both trees `yeast_cell_cycle_control`; live resolve identifier + editorial synopsis
2. Zeng → DiRusso 1569108 — **KEEP** (CW-only `ecoli_fatty_acid_degradation`; not reverted)
3. Cox RecA leftover — **B4b APPLIED** `10506835` both trees `ecoli_sos_response`; ingested + `citations[]` patched; live resolve identifier
4. Section C — **leave**
5. Collection leftover-stripped remainder — **accepted**

Do not re-attach Zeng. Do not attach Knowles 5b or Umbarger 6b. Do not attach Section C leftovers.
Do not touch 260009 or regenerate 260010.
---

# GLMP leftover human-pick packet — 22 August 2026

Selected leftover **picks** were attached as official papers (not leftover-blob retitles). 4a and Cox B4b attached 23 August 2026. Invented papers were not used.

## Applied / left / awaiting (23 August 2026 close-out)

- **APPLIED** — 1a Sourjik TIM `15539117`; 2a Xie 2007 `17909521`; 3a Levine 2019 `30633901`; Henestrosa leftover → Little & Mount 1982 `7049397` (on `ecoli_dna_damage_checkpoint` and `ecoli_sos_response`; Little 1980 `6447873` still on damage-checkpoint); Vogt leftover → Raivio 1999 `10464196`
- **4a APPLIED** — Qi & Elion 2005 JCS `16105880` both trees on `yeast_cell_cycle_control`; official title *MAP kinase pathways.*; KE editorial synopsis (no publisher abstract); live resolve identifier
- **B4b APPLIED** — Cox 1999 `10506835` both trees on `ecoli_sos_response`; official title *Recombinational DNA repair in bacteria and the RecA protein.*; ingested + `citations[]` glmp patched; live resolve identifier
- **Zeng KEEP** — DiRusso 1992 `1569108` on CW `ecoli_fatty_acid_degradation` only (not reverted; glmp twin still Clark & Cronan only)
- **still leftover / named** — 5b Knowles BamA 2009; 6b Umbarger 1969 Feedback control; group **C** (leave)
- **remainder accepted** — leftover-stripped collection remainder accepted after Cox/4a; unique leftover repairs exist: **no**

## Counts

- leftover-note rows: copernicus-web **107**; glmp **66** (current process JSONs; `_previous_versions` excluded)
- unique leftover blobs (stem+authors+year+title): **122**
- grouped: A=3 B=6 C=45 D=14 E=54
- author+year+journal unique-enough to auto-repair this pass: **0**
- unique leftover repairs this pass: **no**

Group E is CW-only leftovers that are not on the glmp twin (named leftovers stay in A even if CW-only).
Glmp-only leftovers stay in B/C/D.

Applied picks removed 6 leftover-note rows per tree earlier, then 4a + Cox B4b removed one more leftover-note row per tree each. Remaining C/D rows are still leftover.

## Live check (not a leftover attach)

- GAL episode `ever-bio-260010` still live: **yes** — `request.paper_doi` / `metadata_extended.source_papers` still `10.1093/emboj/17.14.4086` (Platt & Reece 1998); `animation_player_url` still present. `ever-bio-260009` was not touched; 260010 was not regenerated.

## A. Named leftovers — pick by ID

Each option is one confirmed paper. Applied picks replaced the leftover blob with the official paper (not a leftover-blob retitle). Unapplied leftover blobs remain unattached.

### 1. Sourjik 2004 Chemotaxis leftover — `ecoli_chemotaxis` (cw+glmp)

- **leftover blob:** Sourjik V / 2004 / Chemotaxis / Current biology : CB
- **why leftover:** multi-hit. Sourjik 2004 Curr Biol primer titled *Chemotaxis*: **unconfirmed — do not attach**.

- **1a APPLIED** Receptor clustering and signal processing in E. coli chemotaxis. | `15539117` | `10.1016/j.tim.2004.10.003` | 2004 | Trends Microbiol (Sourjik V) — official title + IDs on `ecoli_chemotaxis` in both trees; leftover Curr Biol blob replaced, not retitled
- **1b** Functional interactions between receptors in bacterial chemotaxis. | `15042093` | `10.1038/nature02406` | 2004 | Nature (Sourjik V, Berg HC)
- also confirmed, not the leftover title: Effect of chemoreceptor modification on assembly and activity of the receptor-kinase complex in Escherichia coli. | `15375146` | `10.1128/jb.186.19.6643-6646.2004` | 2004 | J Bacteriol (Liberman L, Berg HC, Sourjik V)

### 2. Xie 2008 JCS unanswered-questions leftover — `yeast_autophagy` (cw+glmp)

- **leftover blob:** Xie Z / 2008 / The molecular machinery of autophagy: unanswered questions / Journal of cell science
- **why leftover:** title-is-someone-else. Xie 2008 JCS paper with that title: **unconfirmed — do not attach**. Do not reassign authorship to Xie.

- title owner (not Xie): The molecular machinery of autophagy: unanswered questions. | `15615779` | `10.1242/jcs.01620` | 2005 | J Cell Sci (Klionsky DJ)
- **2a APPLIED** Autophagosome formation: core machinery and adaptations. | `17909521` | `10.1038/ncb1007-1102` | 2007 | Nat Cell Biol (Xie Z, Klionsky DJ) — official title + IDs on `yeast_autophagy` in both trees; leftover unanswered-questions blob replaced, not retitled
- also confirmed Xie 2008, different title: Atg8 controls phagophore expansion during autophagosome formation. | `18508918` | `10.1091/mbc.e07-12-1292` | 2008 | Mol Biol Cell (Xie Z, Nair U, Klionsky DJ)
- also confirmed Xie 2008, different title: Dissecting autophagosome formation: the missing pieces. | `18719358` | `10.4161/auto.6692` | 2008 | Autophagy (Xie Z, Nair U, Klionsky DJ)

### 3. Levine Autophagy genes leftover — `yeast_autophagy` (cw+glmp)

- **leftover blob:** Levine B / 2021 / Autophagy genes in biology and disease / Annual review of pathology
- **why leftover:** title-is-someone-else. Levine 2021 Annu Rev Pathol paper with that title: **unconfirmed — do not attach**. Do not reassign authorship to Levine.

- **3a APPLIED** Biological Functions of Autophagy Genes: A Disease Perspective. | `30633901` | `10.1016/j.cell.2018.09.048` | 2019 | Cell (Levine B, Kroemer G) — official title + IDs on `yeast_autophagy` in both trees; leftover 2021 blob replaced, not retitled
- **3b** Autophagy genes in biology and disease. | `36635405` | `10.1038/s41576-022-00562-w` | 2023 | Nat Rev Genet (Yamamoto H, Zhang S, Mizushima N) — exact leftover title; do not reassign to Levine

### 4. Qi & Elion 2005 leftover — `yeast_cell_cycle_control` (cw+glmp)

- **leftover blob:** Qi M, Elion EA / 2005 / Control of the eukaryotic cell cycle by MAP kinase signaling pathways / Trends in Cell Biology
- **why leftover:** title-is-someone-else. Qi+Elion 2005 TCB paper with that title: **unconfirmed — do not attach**.

- title owner (not Qi/Elion): Control of the eukaryotic cell cycle by MAP kinase signaling pathways. | `11053235` | `10.1096/fj.00-0102rev` | 2000 | FASEB J (Wilkinson MG, Millar JB)
- **4a APPLIED** MAP kinase pathways. | `16105880` | `10.1242/jcs.02470` | 2005 | J Cell Sci (Qi M, Elion EA) — official title + IDs on `yeast_cell_cycle_control` in both trees; leftover TCB blob replaced, not retitled. KE already live with Gary-approved editorial synopsis (no publisher abstract). Live `/resolve-paper` PMID and DOI → `identifier`, `paper_id=pubmed_16105880`, non-empty `abstract_preview`.
- **4b** Formin-induced actin cables are required for polarized recruitment of the Ste5 scaffold and high level activation of MAPK Fus3. | `15961405` | `10.1242/jcs.02418` | 2005 | J Cell Sci (Qi M, Elion EA)
- **4c** Signal transduction. Signaling specificity in yeast. | `15692041` | `10.1126/science.1109500` | 2005 | Science (Elion EA, Qi M, Chen W)

### 5. Knowles 2009 BamA leftover — `ecoli_outer_membrane_assembly` (cw)

- **leftover blob:** Knowles TJ et al. / 2009 / Structure of BamA, a key component of the outer membrane protein assembly complex. / Science
- **why leftover:** no-hit. Knowles 2009 Science BamA-structure paper: **unconfirmed — do not attach**. Knowles BamA papers exist in 2011/2013/2015; none is a 2009 Science structure.

- **5a** Membrane protein architects: the role of the BAM complex in outer membrane protein assembly. | `19182809` | `10.1038/nrmicro2069` | 2009 | Nat Rev Microbiol (Knowles TJ, Scott-Tucker A, Overduin M, Henderson IR)
- **5b still leftover** Secondary structure and (1)H, (13)C and (15)N backbone resonance assignments of BamC, a component of the outer membrane protein assembly machinery in Escherichia coli. | `19888691` | `10.1007/s12104-009-9175-3` | 2009 | Biomol NMR Assign (Knowles TJ, McClelland DM, Rajesh S, Henderson IR, Overduin M) — not attached

### 6. Umbarger 1969 Feedback control leftover — `ecoli_amino_acid_biosynthesis` (cw)

- **leftover blob:** Umbarger HE. / 1969 / Feedback control of amino acid biosynthesis / Science.
- **why leftover:** multi-hit. Umbarger 1969 Science paper with that title: **unconfirmed — do not attach**. Distinct 1969 Umbarger amino-acid papers (EuropePMC AUTH:Umbarger AND PUB_YEAR:1969):

- **6a** Biosynthesis of branched-chain amino acids in yeast: regulation of synthesis of the enzymes of isoleucine and valine biosynthesis. | `5784215` | `10.1128/jb.98.2.623-628.1969` | 1969 | J Bacteriol (Bussey H, Umbarger HE)
- **6b still leftover** The metabolism of valine and isoleucine in Escherichia coli. XVII. The role of induction in the derepression of acetohydroxy acid isomeroreductase. | `4902782` | `10.1016/0006-291x(69)90216-2` | 1969 | Biochem Biophys Res Commun (Arfin SM, Ratzkin B, Umbarger HE) — not attached
- **6c** Regulation of amino acid metabolism. | `4896242` | `10.1146/annurev.bi.38.070169.001543` | 1969 | Annu Rev Biochem (Umbarger HE)
- **6d** Alpha-isopropylmalate synthase from Salmonella typhimurium. Purification and properties. | `4976555` | `10.1016/s0021-9258(18)97789-6` | 1969 | J Biol Chem (Kohlhaw G, Leary TR, Umbarger HE)
- **6e** Purification and properties of the acetohydroxy acid isomeroreductase of Salmonella typhimurium. | `4388025` | `10.1016/s0021-9258(18)91816-8` | 1969 | J Biol Chem (Arfin SM, Umbarger HE)
- **6f** Operator constitutive mutations in the leucine operon of Salmonella typhimurium. | `4903803` | `10.1093/genetics/61.4.777` | 1969 | Genetics (Calvo JM, Morgolin P, Umbarger HE)
- **6g** Regulation of branched-chain amino acid biosynthesis in Salmonella typhimurium: isolation of regulatory mutants. | `4887507` | `10.1128/jb.97.3.1272-1282.1969` | 1969 | J Bacteriol (Calvo JM, Freundlich M, Umbarger HE)
- wrong year, not a pick: Feedback control by endproduct inhibition. | `13923752` | `10.1101/sqb.1961.026.01.036` | 1961 | Cold Spring Harb Symp Quant Biol (UMBARGER HE)

## B. Title-is-someone-else — title-owner IDs only (do not attach)

Do not silently reassign authorship or year. Title-owner IDs are listed so Gary can see the real paper; they are **not** attach recommendations for the leftover blob.

### `ecoli_dna_damage_checkpoint` (cw+glmp) — Henestrosa 2000 leftover

- **leftover blob:** Fernández De Henestrosa AR et al. / 2000 / The SOS regulatory system of Escherichia coli / Nat Rev Microbiol
- **B1 APPLIED as Little 1982** The SOS regulatory system of Escherichia coli. | `7049397` | `10.1016/0092-8674(82)90085-x` | 1982 | Cell (Little JW, Mount DW) — official title + IDs on `ecoli_dna_damage_checkpoint` and `ecoli_sos_response`; leftover Henestrosa 2000 blob replaced. Little 1980 `6447873` still present on damage-checkpoint

### `ecoli_fatty_acid_degradation` (cw) — Zeng 2023 leftover (CW-only; also listed under E)

- **leftover blob:** Zeng et al. / 2023 / FadR, a global transcriptional regulator of fatty acid metabolism in Escherichia coli / Front Microbiol
- Zeng 2023 FadR paper with that title: **unconfirmed — do not attach**.
- **B2 KEEP** Characterization of FadR, a global transcriptional regulator of fatty acid metabolism in Escherichia coli. Interaction with the fadB promoter is prevented by long chain fatty acyl coenzyme A. | `1569108` | `10.1016/s0021-9258(18)42497-0` | 1992 | J Biol Chem (DiRusso CC, Heimert TL, Metzger AK) — leftover Zeng 2023 blob replaced on CW only; not reverted; glmp twin not given this row

### `ecoli_periplasmic_stress` (cw+glmp) — Vogt 2012 leftover

- **leftover blob:** Vogt SL, Raivio TL / 2012 / The Cpx envelope stress response is controlled by amplification and feedback inhibition / J Bacteriol
- **B3 APPLIED as Raivio 1999** The Cpx envelope stress response is controlled by amplification and feedback inhibition. | `10464196` | `10.1128/jb.181.17.5263-5272.1999` | 1999 | J Bacteriol (Raivio TL, Popkin DL, Silhavy TJ) — official title + IDs on `ecoli_periplasmic_stress` in both trees; leftover Vogt 2012 blob replaced

### `ecoli_sos_response` (cw+glmp) — Cox 1999 leftover

- **leftover blob:** Cox MM / 1999 / RecA protein: structure, function, and role in recombinational DNA repair / Progress in nucleic acid research and molecular biology
- leftover stored title was the 1997 chapter; 1999 is a different chapter. **B4b attached** (stored year + sole author).
- **B4a LEFT** RecA protein: structure, function, and role in recombinational DNA repair. | `9187054` | `10.1016/s0079-6603(08)61005-3` | 1997 | Prog Nucleic Acid Res Mol Biol (Roca AI, Cox MM) — title owner; 1997 not 1999; not attached
- **B4b APPLIED** Recombinational DNA repair in bacteria and the RecA protein. | `10506835` | `10.1016/s0079-6603(08)60726-6` | 1999 | Prog Nucleic Acid Res Mol Biol (Cox MM) — official title + IDs on `ecoli_sos_response` in both trees; leftover RecA-structure blob replaced, not retitled. Ingested `leftover_pick_pubmed_10506835.json`; `citations[]` patched via Firestore `.update()`. Live `/resolve-paper` PMID and DOI → `identifier`.

### `ecoli_tca_cycle` (cw+glmp)

- **leftover:** Hägerhäll C, Hederstedt L / 1996 / Succinate dehydrogenase of Escherichia coli: cellular and molecular biology / Biochim Biophys Acta
- **why leftover:** title-is-someone-else — Second-pass: Hagerhall 1996 unique hit is a structural-model paper, not the SDH review title. Identifiers remain stripped.
- **candidates:**
  - A structural model for the membrane-integral domain of succinate: quinone oxidoreductases. | `8682198` | `10.1016/0014-5793(96)00529-7` | 1996 — leftover blob is not this official title; do not attach

### `human_scl_tal1_hematopoietic_switch` (glmp)

- **leftover:** Lacombe MJ, Del Blanco B, Anguita E, et al. / 2010 / SCL/TAL1 is a major nuclear effector of the Notch/RBPJ pathway in thymocyte development / PLoS ONE
- **why leftover:** title-is-someone-else — Second-pass: Lacombe 2010 SCL unique hit is a different HSC paper. Identifiers remain stripped.
- **candidates:** no credible candidate

### `human_tlr4_lps_amplification` (glmp)

- **leftover:** Werner SL, Barken D, Hoffmann A / 2005 / NF-κB survival pathways and the inflammatory response / Science Signaling
- **why leftover:** title-is-someone-else — Second-pass: Werner+Hoffmann 2005 unique hit is a different IKK paper. Identifiers remain stripped.
- **candidates:** no credible candidate

### `yeast_mating_response` (cw+glmp)

- **leftover:** Dohlman HG / 2001 / Pheromone signaling mechanisms in yeast: a prototypical sex machine / Science
- **why leftover:** title-is-someone-else — Second-pass: Dohlman 2001 unique hit is a different pheromone-regulator paper. Identifiers remain stripped.
- **candidates:**
  - Identification of novel pheromone-response regulators through systematic overexpression of 120 protein kinases in yeast. | `11337509` | `10.1074/jbc.m103436200` | 2001 — Dohlman-lab 2001 pheromone paper; leftover Science primer title was not found; do not attach

### `yeast_tor_signaling` (cw+glmp)

- **leftover:** Binda M, Péli-Gulli MP, Bonfils G, Panchaud N, Urban J, Sturgill TW, Loewith R, De Virgilio C / 2009 / The EGO complex orchestrates the response to amino acid availability / Eukaryot Cell
- **why leftover:** title-is-someone-else — Second-pass: Binda 2009 unique hit is Vam6/EGO, not the amino-acid-availability title. Identifiers remain stripped.
- **candidates:**
  - The Vam6 GEF controls TORC1 by activating the EGO complex. | `19748353` | `10.1016/j.molcel.2009.06.033` | 2009 — unique Binda+De Virgilio 2009 paper; leftover amino-acid-availability title is not this paper; do not attach

## C. Multi-hit with 2–3 named candidates — still leftover

### `bacillus_biofilm_formation` (glmp)

- **leftover:** Vlamakis H, Chai Y, Beauregard P, Losick R, Kolter R / 2013 / Biofilm formation in Bacillus subtilis / Nat Rev Microbiol
- **why leftover:** multi-hit — Second-pass: Vlamakis+Kolter 2013 has several biofilm papers; identifiers remain stripped.
- **candidates:**
  - *Isolation, characterization, and aggregation of a structured bacterial matrix precursor.* (2013; PMID `23632024`; DOI `10.1074/jbc.m113.453605`) — same first-author+year and process-relevant title; leftover blob is not this official title
  - *Bacillus subtilis biofilm induction by plant polysaccharides.* (2013; PMID `23569226`; DOI `10.1073/pnas.1218984110`) — same first-author+year and process-relevant title; leftover blob is not this official title

### `ecoli_catabolite_repression` (cw+glmp)

- **leftover:** Ullmann A, Monod J / 1968 / Catabolite repression and the lac operon / Biochemical and Biophysical Research Communications
- **why leftover:** multi-hit — Second-pass: Ullmann 1968 catabolite-repression title is not unique; stored DOI is a blood-coagulation paper. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_cell_division` (cw+glmp)

- **leftover:** den Blaauwen T, de Pedro MA, Nguyen-Distèche M, Ayala JA / 2008 / Divisome assembly in Escherichia coli: a molecular perspective / Microbiol Mol Biol Rev
- **why leftover:** multi-hit — Second-pass: den Blaauwen 2008 Divisome title is not unique; stored DOI is chaperone/usher fimbriae. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_cell_division` (cw+glmp)

- **leftover:** Erickson HP, Anderson DE, Osawa M / 2010 / FtsZ filament structure reveals the structural basis for assembly dynamics and constriction force generation / Nat Struct Mol Biol
- **why leftover:** multi-hit — Second-pass: Erickson 2010 FtsZ filament title is not unique; stored DOI is alphaB-crystallin. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_dna_damage_checkpoint` (cw+glmp)

- **leftover:** Cordell SC, Robinson EJ, Löwe J / 2003 / SulA inhibits assembly of FtsZ by a simple sequestration mechanism / Biochemistry
- **why leftover:** multi-hit — Second-pass: Cordell 2003 sequestration title does not uniquely match the SulA crystal-structure paper. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_dna_replication_elongation` (cw+glmp)

- **leftover:** McHenry CS / 2011 / The Escherichia coli DNA polymerase III holoenzyme / Journal of Biological Chemistry
- **why leftover:** multi-hit — Second-pass: McHenry 2011 has several polymerase III papers. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_dna_replication_elongation` (cw+glmp)

- **leftover:** Robinson A, van Oijen AM / 2013 / The bacterial replisome: back on track? / Molecular Cell
- **why leftover:** multi-hit — Second-pass: Robinson+van Oijen 2013 replisome title is not unique; stored DOI is lesion-skipping. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_glycolysis` (cw+glmp)

- **leftover:** Blangy D, Buc H, Monod J / 1968 / Allosteric regulation of phosphofructokinase from Escherichia coli / J Mol Biol
- **why leftover:** multi-hit — Second-pass: Blangy 1968 has two phosphofructokinase papers. Identifiers remain stripped.
- **candidates:**
  - *Phosphofructokinase from E. Coli: Evidence for a tetrameric structure of the enzyme.* (1968; PMID `11946283`; DOI `10.1016/0014-5793(68)80115-2`) — same first-author+year and process-relevant title; leftover blob is not this official title
  - *Kinetics of the allosteric interactions of phosphofructokinase from Escherichia coli.* (1968; PMID `4229913`; DOI `10.1016/0022-2836(68)90051-x`) — same author-year and journal-ish; title differs from leftover blob

### `ecoli_glycolysis` (cw+glmp)

- **leftover:** Clark DP / 1989 / Mixed-acid fermentation in Escherichia coli / FEMS Microbiol Rev
- **why leftover:** multi-hit — Second-pass: Clark 1989 mixed-acid fermentation title is not unique; stored DOI is a ceftazidime clinical paper. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_mal_regulon` (cw+glmp)

- **leftover:** Richet E, Vidal-Ingigliardi D, Raibaud O / 1991 / The MalT-dependent transcriptional activation of the maltose regulon / Molecular Microbiology
- **why leftover:** multi-hit — Second-pass: Richet 1991 has several MalT papers. Identifiers remain stripped.
- **candidates:**
  - *Two MalT binding sites in direct repeat. A structural motif involved in the activation of all the promoters of the maltose regulons in Escherichia coli and Klebsiella pneumoniae.* (1991; PMID `2010912`; DOI `10.1016/0022-2836(91)90715-i`) — same first-author+year and process-relevant title; leftover blob is not this official title

### `ecoli_mal_regulon` (cw+glmp)

- **leftover:** Dippel R, Boos W / 2005 / ATP-dependent regulation of maltose transport in Escherichia coli / Molecular Microbiology
- **why leftover:** multi-hit — Second-pass: Dippel+Boos 2005 has two maltodextrin papers. Identifiers remain stripped.
- **candidates:**
  - *The maltodextrin system of Escherichia coli: glycogen-derived endogenous induction and osmoregulation.* (2005; PMID `16321937`; DOI `10.1128/jb.187.24.8332-8339.2005`) — same first-author+year and process-relevant title; leftover blob is not this official title

### `ecoli_mismatch_repair` (cw+glmp)

- **leftover:** Jiricny J / 2006 / Mismatch repair proteins MutS and MutL: jack of all trades? / Current Opinion in Structural Biology
- **why leftover:** multi-hit — Second-pass: Jiricny 2006 has several mismatch-repair papers. Identifiers remain stripped.
- **candidates:**
  - *Characterization of the interactome of the human MutL homologues MLH1, PMS1, and PMS2.* (2007; PMID `17148452`; DOI `10.1074/jbc.m609989200`) — same first-author+year and process-relevant title; leftover blob is not this official title
  - *A single cycle of treatment with temozolomide, alone or combined with O(6)-benzylguanine, induces strong chemoresistance in melanoma cell clones in vitro: role of O(6)-methylguanine-DNA methyltransferase and the mismatch repair system.* (2006; PMID `16964376`; DOI `10.3892/ijo.29.4.785`) — same first-author+year and process-relevant title; leftover blob is not this official title
  - *MutLalpha: at the cutting edge of mismatch repair.* (2006; PMID `16873053`; DOI `10.1016/j.cell.2006.07.003`) — same first-author+year and process-relevant title; leftover blob is not this official title

### `ecoli_nucleotide_biosynthesis` (glmp)

- **leftover:** Zalkin H, Dixon JE / 1992 / Nucleotide metabolism / Prog Nucleic Acid Res Mol Biol
- **why leftover:** multi-hit — Second-pass: Zalkin+Dixon 1992 is not unique; identifiers remain stripped.
- **candidates:**
  - *Structural characterization and corepressor binding of the Escherichia coli purine repressor.* (1992; PMID `1400170`; DOI `10.1128/jb.174.19.6207-6214.1992`) — same first-author+year and process-relevant title; leftover blob is not this official title
  - *Crystallization and preliminary X-ray studies on the co-repressor binding domain of the Escherichia coli purine repressor.* (1992; PMID `1613795`; DOI `10.1016/0022-2836(92)90111-v`) — same first-author+year and process-relevant title; leftover blob is not this official title

### `ecoli_outer_membrane_assembly` (glmp)

- **leftover:** Ricci DP, Silhavy TJ / 2012 / The BAM complex in outer membrane protein biogenesis / Biochim Biophys Acta
- **why leftover:** multi-hit — Second-pass: Ricci+Silhavy 2012 has three BAM papers; identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_oxidative_stress_response` (cw+glmp)

- **leftover:** Storz G, Tartaglia LA, Ames BN / 1990 / OxyR: a regulator of antioxidant genes / J Nutr
- **why leftover:** multi-hit — Second-pass: Storz 1990 has several OxyR papers. Identifiers remain stripped.
- **candidates:**
  - *Bacterial defenses against oxidative stress.* (1990; PMID `1965068`; DOI `10.1016/0168-9525(90)90278-e`) — same first-author+year and process-relevant title; leftover blob is not this official title
  - *Alkyl hydroperoxide reductase from Salmonella typhimurium. Sequence and homology to thioredoxin reductase and other flavoprotein disulfide oxidoreductases.* (1990; PMID `2191951`; DOI `10.1016/s0021-9258(18)86980-0`) — same first-author+year and process-relevant title; leftover blob is not this official title

### `ecoli_oxidative_stress_response` (cw+glmp)

- **leftover:** Hidalgo E, Ding H, Demple B / 1997 / SoxR, a [2Fe-2S] transcription factor, is active only in its oxidized form / Proc Natl Acad Sci USA
- **why leftover:** multi-hit — Second-pass: Hidalgo+Demple 1997 has several SoxR papers. Identifiers remain stripped.
- **candidates:**
  - *Feed-back inhibition of oxidative stress by oxidized lipid/amino acid reaction products.* (1997; PMID `9398306`; DOI `10.1021/bi971641i`) — same first-author+year and process-relevant title; leftover blob is not this official title

### `ecoli_periplasmic_stress` (cw+glmp)

- **leftover:** Clausen T, Kaiser M, Huber R, Ehrmann M / 2011 / DegP: a protease of protein quality control in the bacterial periplasm / FEBS Lett
- **why leftover:** multi-hit — Second-pass: Clausen+Ehrmann 2011 has three quality-control papers. Identifiers remain stripped.
- **candidates:**
  - *Pigments protect the light harvesting proteins of chloroplast thylakoid membranes against digestion by gastrointestinal proteases* (2011; PMID none; DOI `10.1016/j.foodhyd.2010.12.004`) — same first-author+year and process-relevant title; leftover blob is not this official title

### `ecoli_pho_regulon` (cw+glmp)

- **leftover:** Wanner BL / 1996 / Phosphate assimilation and control of alkaline phosphatase synthesis in Escherichia coli / Journal of Bacteriology
- **why leftover:** multi-hit — Second-pass: Wanner 1996 has multiple phosphate/Pho papers; identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_pho_regulon` (cw+glmp)

- **leftover:** Stephenson K, Hoch JA / 2002 / Two-component signal transduction as a target for microbial anti-infective therapy / Pharmacology & Therapeutics
- **why leftover:** multi-hit — Second-pass: Stephenson+Hoch 2002 has four two-component papers. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_phosphate_transport` (glmp)

- **leftover:** Wanner BL / 1996 / Phosphate assimilation in E. coli / J Bacteriol
- **why leftover:** multi-hit — Second-pass: Wanner 1996 has several phosphate/Pho papers. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_rna_polymerase_recycling` (cw+glmp)

- **leftover:** Harden TT, Wells CD, Friedman LJ, Landick R, Hochschild A, Kondev J, Gelles J / 2016 / Recycling of the RNA polymerase in Escherichia coli / eLife
- **why leftover:** multi-hit — Second-pass: Harden 2016 recycling title does not uniquely match the sigma70-retention paper. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_sigma_factor_competition` (cw+glmp)

- **leftover:** Gruber TM, Gross CA / 2003 / The alternative sigma factor network in Escherichia coli / Molecular Microbiology
- **why leftover:** multi-hit — Second-pass: Gruber 2003 alternative-sigma title is not unique. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_sigma_factor_competition` (cw+glmp)

- **leftover:** Wade JT, Struhl K / 2008 / Regulation of RNA polymerase sigma subunit synthesis and activity / Microbiology and Molecular Biology Reviews
- **why leftover:** multi-hit — Second-pass: Wade 2008 sigma-subunit title is not unique; stored DOI is an Fe-S cluster paper. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_starvation_response` (cw+glmp)

- **leftover:** Hengge-Aronis R / 2002 / The RpoS sigma factor of Escherichia coli: synthesis and degradation / Mol Microbiol
- **why leftover:** multi-hit — Second-pass: Hengge-Aronis 2002 has several RpoS papers. Identifiers remain stripped.
- **candidates:**
  - *Stationary phase gene regulation: what makes an Escherichia coli promoter sigmaS-selective?* (2002; PMID `12457703`; DOI `10.1016/s1369-5274(02)00372-7`) — same first-author+year and process-relevant title; leftover blob is not this official title
  - *Signal transduction and regulatory mechanisms involved in control of the sigma(S) (RpoS) subunit of RNA polymerase.* (2002; PMID `12208995`; DOI `10.1128/mmbr.66.3.373-395.2002`) — same first-author+year and process-relevant title; leftover blob is not this official title
  - *The cellular level of the recognition factor RssB is rate-limiting for sigmaS proteolysis: implications for RssB regulation and signal transduction in sigmaS turnover in Escherichia coli.* (2002; PMID `12354235`; DOI `10.1046/j.1365-2958.2002.03123.x`) — same author-year and journal-ish; title differs from leftover blob

### `ecoli_tca_cycle` (cw+glmp)

- **leftover:** Gruer MJ, Artymiuk PJ, Guest JR / 1997 / Escherichia coli contains two aconitases: aconitase A and aconitase B / Microbiology
- **why leftover:** multi-hit — Second-pass: Gruer+Guest 1997 has several aconitase papers. Identifiers remain stripped.
- **candidates:**
  - *Transcriptional regulation of the aconitase genes (acnA and acnB) of Escherichia coli.* (1997; PMID `9421904`; DOI `10.1099/00221287-143-12-3795`) — same author-year and journal-ish; title differs from leftover blob

### `ecoli_translation_elongation` (cw+glmp)

- **leftover:** Rodnina MV, Savelsbergh A, Katunin VI, Wintermeyer W / 1997 / EF-G-catalyzed translocation of anticodon stem-loop analogs of transfer RNA in the ribosome / PNAS
- **why leftover:** multi-hit — Second-pass: Rodnina 1997 has three EF-G/ribosome papers, none uniquely matching the anticodon-stem-loop title. Identifiers remain stripped.
- **candidates:**
  - *Visualization of elongation factor Tu on the Escherichia coli ribosome.* (1997; PMID `9311785`; DOI `10.1038/38770`) — same first-author+year and process-relevant title; leftover blob is not this official title
  - *Arrangement of tRNAs in pre- and posttranslocational ribosomes revealed by electron cryomicroscopy.* (1997; PMID `9019401`; DOI `10.1016/s0092-8674(00)81854-1`) — same first-author+year and process-relevant title; leftover blob is not this official title
  - *Hydrolysis of GTP by elongation factor G drives tRNA movement on the ribosome.* (1997; PMID `8985244`; DOI `10.1038/385037a0`) — same first-author+year and process-relevant title; leftover blob is not this official title

### `ecoli_translation_initiation` (cw+glmp)

- **leftover:** Chen J, Tsai A, O'Leary SE, Petrov A, Puglisi JD / 2012 / Structural dynamics of ribosome subunit association studied by mixing-spraying time-resolved cryogenic electron microscopy / Structure
- **why leftover:** multi-hit — Second-pass: Chen 2012 subunit-association title does not uniquely match the translocation review. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_trp_operon` (cw+glmp)

- **leftover:** Merino E, Yanofsky C / 2005 / Regulation of the trp operon / Current Opinion in Microbiology
- **why leftover:** multi-hit — Second-pass: Merino 2005 has two trp/attenuation papers. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_tryptophan_biosynthesis` (glmp)

- **leftover:** Yanofsky C / 2001 / Tryptophan biosynthesis / Adv Enzymol Relat Areas Mol Biol
- **why leftover:** multi-hit — Second-pass: Yanofsky 2001 has several tryptophan papers. Identifiers remain stripped.
- **candidates:**
  - *The mechanism of tryptophan induction of tryptophanase operon expression: tryptophan inhibits release factor-mediated cleavage of TnaC-peptidyl-tRNA(Pro).* (2001; PMID `11470925`; DOI `10.1073/pnas.171299298`) — same first-author+year and process-relevant title; leftover blob is not this official title
  - *The structures of anthranilate synthase of Serratia marcescens crystallized in the presence of (i) its substrates, chorismate and glutamine, and a product, glutamate, and (ii) its end-product inhibitor, L-tryptophan.* (2001; PMID `11371633`; DOI `10.1073/pnas.111150298`) — same first-author+year and process-relevant title; leftover blob is not this official title

### `ecoli_two_component_signaling` (cw+glmp)

- **leftover:** Mizuno T / 1997 / Signal transduction by the EnvZ-OmpR phosphorelay system in bacteria / Molecular Microbiology
- **why leftover:** multi-hit — Second-pass: Mizuno 1997 has several EnvZ/OmpR papers. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_two_component_signaling` (cw+glmp)

- **leftover:** Kenney LJ / 2002 / DNA binding and phosphorylation-dependent dimerization of the response regulator OmpR / Molecular Microbiology
- **why leftover:** multi-hit — Second-pass: Kenney 2002 has several OmpR papers. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_type_iii_secretion` (cw+glmp)

- **leftover:** Dean P / 2011 / The LEE-encoded type III secretion system of enteropathogenic Escherichia coli: a model for understanding EPEC pathogenesis / FEMS microbiology reviews
- **why leftover:** multi-hit — Second-pass: Dean 2011 has several EPEC/T3SS papers. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_type_iii_secretion` (cw+glmp)

- **leftover:** Diepold A / 2015 / Structure and assembly of the bacterial type III secretion machine / FEMS microbiology reviews
- **why leftover:** multi-hit — Second-pass: Diepold 2015 has several T3SS papers. Identifiers remain stripped.
- **candidates:**
  - *Type III secretion systems: the bacterial flagellum and the injectisome.* (2015; PMID `26370933`; DOI `10.1098/rstb.2015.0020`) — same first-author+year and process-relevant title; leftover blob is not this official title
  - *Visualization of the Serratia Type VI Secretion System Reveals Unprovoked Attacks and Dynamic Assembly.* (2015; PMID `26387948`; DOI `10.1016/j.celrep.2015.08.053`) — same first-author+year and process-relevant title; leftover blob is not this official title

### `human_bcl2_bax_momp` (glmp)

- **leftover:** Chipuk JE, Green DR / 2008 / How cells die: apoptosis pathways / Journal of Allergy and Clinical Immunology
- **why leftover:** multi-hit — Second-pass: Chipuk+Green 2008 has several apoptosis papers; identifiers remain stripped.
- **candidates:** no credible candidate

### `human_bcl6_gc_fate_switch` (glmp)

- **leftover:** Calame KL / 2008 / Transcription factors that regulate memory in humoral responses / Current Opinion in Immunology
- **why leftover:** multi-hit — Second-pass: Calame 2008 has several humoral-memory papers. Identifiers remain stripped.
- **candidates:**
  - *Blimp-1 attenuates Th1 differentiation by repression of ifng, tbx21, and bcl6 gene expression.* (2008; PMID `18684923`; DOI `10.4049/jimmunol.181.4.2338`) — same first-author+year and process-relevant title; leftover blob is not this official title

### `human_cebpa_myeloid_commitment` (glmp)

- **leftover:** Zhang DE, Hetherington CJ, Chen HM, Tenen DG / 2004 / C/EBPα is required for the development of granulocytes and macrophages / Molecular and Cellular Biology
- **why leftover:** multi-hit — Second-pass: Tenen 2004 has several C/EBP papers. Identifiers remain stripped.
- **candidates:** no credible candidate

### `yeast_gcn4_starvation` (glmp)

- **leftover:** Hinnebusch AG / 2005 / Translational control by the eIF2α kinase GCN2 / J Biol Chem
- **why leftover:** multi-hit — Second-pass: Hinnebusch 2005 has several GCN2/eIF2 papers. Identifiers remain stripped.
- **candidates:**
  - *Activator Gcn4p and Cyc8p/Tup1p are interdependent for promoter occupancy at ARG1 in vivo.* (2005; PMID `16314536`; DOI `10.1128/mcb.25.24.11171-11183.2005`) — same first-author+year and process-relevant title; leftover blob is not this official title

### `yeast_hog_pathway` (cw+glmp)

- **leftover:** Albertyn J, Hohmann S, Thevelein JM, Prior BA / 1994 / Glycerol production in response to hyperosmotic stress involves the HOG pathway / J Bacteriol
- **why leftover:** multi-hit — Second-pass: Albertyn+Hohmann 1994 has several glycerol/osmotic papers. Identifiers remain stripped.
- **candidates:**
  - *GPD1, which encodes glycerol-3-phosphate dehydrogenase, is essential for growth under osmotic stress in Saccharomyces cerevisiae, and its expression is regulated by the high-osmolarity glycerol response pathway.* (1994; PMID `8196651`; DOI `10.1128/mcb.14.6.4135-4144.1994`) — same first-author+year and process-relevant title; leftover blob is not this official title
  - *The FPS1 gene product functions as a glycerol facilitator in the yeast Saccharomyces cerevisiae.* (1994; PMID `8550015`; DOI `10.1007/bf02814092`) — same first-author+year and process-relevant title; leftover blob is not this official title
  - *Characterization of the osmotic-stress response in Saccharomyces cerevisiae: osmotic stress and glucose repression regulate glycerol-3-phosphate dehydrogenase independently.* (1994; PMID `8082159`; DOI `10.1007/bf00712960`) — same first-author+year and process-relevant title; leftover blob is not this official title

### `yeast_hog_pathway` (cw+glmp)

- **leftover:** Maeda T, Wurgler-Murphy SM, Saito H / 1994 / Two redundant transmembrane mechanisms participate in yeast osmotic stress sensing / J Cell Biol
- **why leftover:** multi-hit — Second-pass: Maeda 1994 osmotic-sensing title is not unique; stored DOI is an erythropoietin-receptor paper. Identifiers remain stripped.
- **candidates:** no credible candidate

### `yeast_mating_response` (cw+glmp)

- **leftover:** Bardwell L / 2004 / The yeast pheromone response pathway: a paradigm for eukaryotic signal transduction / Yeast
- **why leftover:** multi-hit — Second-pass: Bardwell 2004 has several pheromone-pathway papers; stored DOI is fission-yeast end4. Identifiers remain stripped.
- **candidates:**
  - *A walk-through of the yeast mating pheromone response pathway.* (2004; PMID `15374648`; DOI `10.1016/j.peptides.2003.10.022`) — same first-author+year and process-relevant title; leftover blob is not this official title

### `yeast_mating_response` (cw+glmp)

- **leftover:** Haber JE / 2012 / Mechanisms and regulation of mating-type switching in Saccharomyces cerevisiae / Microbiology spectrum
- **why leftover:** multi-hit — Second-pass: Haber 2012 has several mating-type papers. Identifiers remain stripped.
- **candidates:** no credible candidate

### `yeast_mitochondrial_import` (cw+glmp)

- **leftover:** Neupert W / 2007 / Mechanisms of mitochondrial protein import / Annual review of biochemistry
- **why leftover:** multi-hit — Second-pass: Neupert 2007 has several mitochondrial-import papers. Identifiers remain stripped.
- **candidates:**
  - *Alternative splicing gives rise to different isoforms of the Neurospora crassa Tob55 protein that vary in their ability to insert beta-barrel proteins into the outer mitochondrial membrane.* (2007; PMID `17660559`; DOI `10.1534/genetics.107.075051`) — same first-author+year and process-relevant title; leftover blob is not this official title
  - *OPA1 processing reconstituted in yeast depends on the subunit composition of the m-AAA protease in mitochondria.* (2007; PMID `17615298`; DOI `10.1091/mbc.e07-02-0164`) — same first-author+year and process-relevant title; leftover blob is not this official title

### `yeast_mitochondrial_import` (cw+glmp)

- **leftover:** Pfanner N / 2019 / The protein import machinery of mitochondria-a regulatory hub in metabolism, stress, and disease / Cell metabolism
- **why leftover:** multi-hit — Second-pass: Pfanner 2019 has several mitochondrial papers. Identifiers remain stripped.
- **candidates:**
  - *Studying protein import into mitochondria.* (2020; PMID `32183973`; DOI `10.1016/bs.mcb.2019.11.006`) — same first-author+year and process-relevant title; leftover blob is not this official title
  - *Coupling of import and assembly pathways in mitochondrial protein biogenesis.* (2019; PMID `31513529`; DOI `10.1515/hsz-2019-0310`) — same first-author+year and process-relevant title; leftover blob is not this official title
  - *Structure of the mitochondrial import gate reveals distinct preprotein paths.* (2019; PMID `31600774`; DOI `10.1038/s41586-019-1680-7`) — same first-author+year and process-relevant title; leftover blob is not this official title

### `yeast_nitrogen_metabolism` (glmp)

- **leftover:** Cooper TG / 2002 / Nitrogen catabolite repression in yeast / FEMS Microbiol Rev
- **why leftover:** multi-hit — Second-pass: Cooper 2002 has several nitrogen papers; identifiers remain stripped.
- **candidates:** no credible candidate

### `yeast_ubiquitin_proteasome` (cw+glmp)

- **leftover:** Luan B, Huang X, Wu J, Mei Z, Wang Y, Xue X, Yan C, Wang J, Finley DJ, Shi Y, Wang F / 2016 / Structure of the yeast 26S proteasome at 3.6 Angstrom resolution / Science
- **why leftover:** multi-hit — Second-pass: 2016 yeast 26S proteasome structures are not unique. Identifiers remain stripped.
- **candidates:** no credible candidate

## D. No-hit / informal / textbook / database — still leftover / non-paper

### `ecoli_dna_damage_checkpoint` (cw+glmp)

- **leftover:** Keyamura K, Arai K, Hishida T / 2009 / RecN protein and transcription factor DksA combine to promote faithful recombinational repair of DNA double-strand breaks / Mol Microbiol
- **why leftover:** no-hit — Second-pass: Keyamura 2009 RecN title not found; only DiaA paper that year. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_dna_replication_elongation` (cw+glmp)

- **leftover:** Sauer PV, Corbeski I, Lu Y, et al / 2022 / The replisome guides nucleosome assembly during DNA replication / Cell
- **why leftover:** no-hit — Second-pass: Sauer 2022 nucleosome/replisome title not uniquely found; stored DOI is SYK microglia. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_glycolysis` (cw+glmp)

- **leftover:** Berg JM, Tymoczko JL, Stryer L / 2002 / Glycolysis / Biochemistry
- **why leftover:** chapter-or-book — Second-pass: Berg/Tymoczko/Stryer Glycolysis is a textbook chapter, not a journal paper. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_periplasmic_stress` (cw+glmp)

- **leftover:** Raivio TL, Silhavy TJ / 2001 / The periplasmic folding factor CpxP modulates the Cpx response / J Bacteriol
- **why leftover:** no-hit — Second-pass: Raivio 2001 CpxP-folding title was not uniquely found. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_sos_response` (cw+glmp)

- **leftover row gone — replaced when 7049397 was attached:** Fernández De Henestrosa AR / 2000 / Regulation of the Escherichia coli SOS response / FEMS microbiology reviews
- **why leftover:** no-hit — Second-pass: Henestrosa 2000 SOS title not uniquely found. Identifiers remain stripped.
- **candidates:** no credible candidate
- **status:** leftover blob no longer on the chart; Little & Mount 1982 `7049397` is the attached official paper. Other D leftovers on this chart (Little 2003; Friedberg 2005) remain leftover.

### `ecoli_sos_response` (cw+glmp)

- **leftover:** Little JW / 2003 / The LexA transcriptional repressor / Frontiers in bioscience : a journal and virtual library
- **why leftover:** no-hit — Second-pass: Little 2003 LexA repressor title not uniquely found. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_sos_response` (cw+glmp)

- **leftover:** Friedberg EC / 2005 / The SOS response: recent insights into umuDC-dependent mutagenesis and DNA damage tolerance / Annual review of genetics
- **why leftover:** no-hit — Second-pass: Friedberg 2005 SOS/umuDC title not uniquely found. Identifiers remain stripped.
- **candidates:**
  - *Suffering in silence: the tolerance of DNA damage.* (2005; PMID `16341080`; DOI `10.1038/nrm1781`) — same first-author+year and process-relevant title; leftover blob is not this official title
  - *Database of mouse strains carrying targeted mutations in genes affecting biological responses to DNA damage Version 7.* (2006; PMID `16290067`; DOI `10.1016/j.dnarep.2005.09.009`) — same first-author+year and process-relevant title; leftover blob is not this official title

### `ecoli_starvation_response` (cw+glmp)

- **leftover:** Kvint K, Nachin L, Diez A, Nyström T / 2003 / ppGpp-dependent stationary phase induction of genes on Escherichia coli / Mol Microbiol
- **why leftover:** no-hit — Second-pass: Kvint 2003 ppGpp-stationary title is not uniquely found. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_transcription_elongation` (cw+glmp)

- **leftover:** Artsimovitch I, Landick R / 2000 / NusG is a sequence-specific RNA polymerase pause factor that stimulates transcription elongation / Nature
- **why leftover:** no-hit — Second-pass: Artsimovitch 2000 has several RNAP-pause papers; Nature NusG title not uniquely found. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_translation_initiation` (cw+glmp)

- **leftover:** Rodnina MV, Wintermeyer W / 2009 / Mechanism and regulation of protein synthesis in Escherichia coli / Molecular and Cellular Biology
- **why leftover:** no-hit — Second-pass: Rodnina 2009 protein-synthesis title is not uniquely found; stored DOI is a synaptotagmin paper. Identifiers remain stripped.
- **candidates:**
  - *Thermodynamic and kinetic framework of selenocysteyl-tRNASec recognition by elongation factor SelB.* (2010; PMID `19940162`; DOI `10.1074/jbc.m109.081380`) — same first-author+year and process-relevant title; leftover blob is not this official title
  - *The ribosome goes Nobel.* (2010; PMID `19962317`; DOI `10.1016/j.tibs.2009.11.003`) — same first-author+year and process-relevant title; leftover blob is not this official title
  - *Distinct functions of elongation factor G in ribosome recycling and translocation.* (2009; PMID `19324963`; DOI `10.1261/rna.1592509`) — same first-author+year and process-relevant title; leftover blob is not this official title

### `ecoli_two_component_signaling` (cw+glmp)

- **leftover:** Pratt LA, Hsing W, Gibson KE, Silhavy TJ / 1996 / Modulation of porin gene expression by the two-component regulatory system EnvZ-OmpR / Journal of Bacteriology
- **why leftover:** chapter-or-book — Second-pass: Pratt 1996 has two porin/SprE papers plus a book chapter; chart title is not unique. Identifiers remain stripped.
- **candidates:** no credible candidate

### `human_cebpa_myeloid_commitment` (glmp)

- **leftover:** Ye M, Zhang H, Yang H, et al. / 1997 / Granulocyte colony-stimulating factor induces C/EBPα and C/EBPβ expression in myeloid progenitors / Journal of Immunology
- **why leftover:** no-hit — Second-pass: Ye 1997 C/EBP G-CSF title not uniquely found. Identifiers remain stripped.
- **candidates:** no credible candidate

### `mouse_gata1_spi1_switch` (glmp)

- **leftover:** Nerlov C, Graf T / 2007 / PU.1 induces the commitment of multipotent progenitors to the myeloid lineage / Genes & Development
- **why leftover:** no-hit — Second-pass: Nerlov/Graf 2007 PU.1 title not uniquely found. Identifiers remain stripped.
- **candidates:** no credible candidate

### `yeast_mitochondrial_import` (cw+glmp)

- **leftover:** Endo T / 2015 / The mitochondrial protein import machinery / Biomolecules
- **why leftover:** no-hit — Second-pass: Endo 2015 mitochondrial-import title is not uniquely found. Identifiers remain stripped.
- **candidates:** no credible candidate

### `yeast_rna_splicing` (glmp)

- **leftover:** Rymond BC, Rosbash M / 1992 / Pre-mRNA splicing in yeast / Yeast
- **why leftover:** no-hit — Second-pass: Rymond+Rosbash 1992 splicing title not uniquely found. Identifiers remain stripped.
- **candidates:**
  - *PRP38 encodes a yeast protein required for pre-mRNA splicing and maintenance of stable U6 small nuclear RNA levels.* (1992; PMID `1508195`; DOI `10.1128/mcb.12.9.3939-3947.1992`) — same first-author+year and process-relevant title; leftover blob is not this official title

## E. CW-only leftovers not on glmp twin

### `ecoli_fatty_acid_degradation` (cw)

- **leftover:** Zeng, B; Xiong, M; Wang, S; Zheng, S; Wang, X; Cao, X; Song, C; Li, R; Zhang, C; Chen, B; Peng, C; Wang, Z. / 2023 / FadR, a global transcriptional regulator of fatty acid metabolism in Escherichia coli / Front Microbiol
- **why leftover:** title-is-someone-else — title owner confirmed as **B2** DiRusso 1992. Do not attach wrong year. Identifiers remain stripped.
- **candidates:** see **B2** — do not attach

### `yeast_cell_wall_integrity` (cw)

- **leftover:** Madden K., Sheu YJ., Baetz K., Zheng R., Blankenship D., Sykes K., Snyder M. / 1997 / Slt2p, a cell wall integrity-related mitogen-activated protein kinase of Saccharomyces cerevisiae, is activated in response to cell wall stress and interacts with the Slt2p-dependent protein kinase Skn7p / Proc Natl Acad Sci U S A
- **why leftover:** title-is-someone-else — Second-pass: Madden 1997 unique hit is the SBF-target paper, not the Slt2p CWI title. Identifiers remain stripped.
- **candidates:** no credible candidate

### `yeast_chromatin_silencing` (cw)

- **leftover:** Rusche, L. N.; Kirchmaier, A. L.; Rine, J. / 2002 / A chromatin-silencing pathway mediating transcriptional repression in Saccharomyces cerevisiae. / Genes Dev
- **why leftover:** title-is-someone-else — Second-pass: Rusche 2002 unique hit is ordered nucleation/spreading, not the chromatin-silencing-pathway title. Identifiers remain stripped.
- **candidates:**
  - *Ordered nucleation and spreading of silenced chromatin in Saccharomyces cerevisiae.* (2002; PMID `12134062`; DOI `10.1091/mbc.e02-03-0175`) — same first-author+year and process-relevant title; leftover blob is not this official title

### `yeast_er_stress_response` (cw)

- **leftover:** Kawahara T, Mori K, Katayama T, Goto Y, Inazawa J, Kashiwagi H. / 1998 / Two basic leucine zipper proteins, Hac1p and Hac2p, are involved in the unfolded protein response in Saccharomyces cerevisiae. / J. Biol. Chem.
- **why leftover:** title-is-someone-else — Second-pass: Kawahara 1998 unique hit is HAC1 splicing, not the Hac1p/Hac2p title. Identifiers remain stripped.
- **candidates:** no credible candidate

### `yeast_mitochondrial_biogenesis` (cw)

- **leftover:** Liao X, Small WC, Srere PA, Butow RA. / 1991 / The Rtg1 and Rtg3 proteins are transcription factors required for the expression of the S. cerevisiae genes encoding the peroxisomal proteins citrate synthase and carnitine acetyltransferase. / J Biol Chem.
- **why leftover:** title-is-someone-else — Second-pass: Liao 1991 unique hit is the CIT2 paper, not the Rtg1/Rtg3 title. Identifiers remain stripped.
- **candidates:** no credible candidate

### `yeast_nitrogen_metabolism` (cw)

- **leftover:** Tate, JJ.; Moye-Rowley, WS. / 2002 / The nitrogen catabolite repression-sensitive transcription factor Gln3 is regulated by TOR kinase and the type 2A phosphatase Sit4 in Saccharomyces cerevisiae / J Biol Chem
- **why leftover:** title-is-someone-else — Second-pass: Tate 2002 unique hit is Gln3 compartmentation, not the chart NCR-factor title. Identifiers remain stripped.
- **candidates:** no credible candidate

### `yeast_ribosome_biogenesis` (cw)

- **leftover:** Tollervey, D.; Kiss, T. / 1997 / Site-specific ribonucleases in eukaryotic rRNA processing / Annu Rev Biochem
- **why leftover:** title-is-someone-else — Second-pass: Tollervey 1997 unique hit is snoRNA synthesis, not site-specific RNases. Identifiers remain stripped.
- **candidates:**
  - *Nucleolar KKE/D repeat proteins Nop56p and Nop58p interact with Nop1p and are required for ribosome biogenesis.* (1997; PMID `9372940`; DOI `10.1128/mcb.17.12.7088`) — same first-author+year and process-relevant title; leftover blob is not this official title
  - *The exosome: a conserved eukaryotic RNA processing complex containing multiple 3'-->5' exoribonucleases.* (1997; PMID `9390555`; DOI `10.1016/s0092-8674(00)80432-8`) — same first-author+year and process-relevant title; leftover blob is not this official title
  - *Functional analysis of Rrp7p, an essential yeast protein involved in pre-rRNA processing and ribosome assembly.* (1997; PMID `9271380`; DOI `10.1128/mcb.17.9.5023`) — same first-author+year and process-relevant title; leftover blob is not this official title

### `bacillus_biofilm_formation` (cw)

- **leftover:** Romero D, Aguilar C, Losick R, Kolter R. / 2011 / Amyloid fibers provide structural integrity to Bacillus subtilis biofilms / Proc Natl Acad Sci U S A
- **why leftover:** multi-hit — Second-pass: Romero 2011 amyloid-biofilm title is not unique (2010 PNAS fibers paper plus 2011 accessory-protein paper). Identifiers remain stripped.
- **candidates:** no credible candidate

### `bacillus_biofilm_formation` (cw)

- **leftover:** Vlamakis H, Aguilar C, Losick R, Kolter R. / 2013 / The genetic architecture of biofilm formation in Bacillus subtilis / Annu Rev Genet
- **why leftover:** multi-hit — Second-pass: Vlamakis 2013 genetic-architecture title is not unique; several 2013 biofilm papers. Identifiers remain stripped.
- **candidates:**
  - *Isolation, characterization, and aggregation of a structured bacterial matrix precursor.* (2013; PMID `23632024`; DOI `10.1074/jbc.m113.453605`) — same first-author+year and process-relevant title; leftover blob is not this official title
  - *Bacillus subtilis biofilm induction by plant polysaccharides.* (2013; PMID `23569226`; DOI `10.1073/pnas.1218984110`) — same first-author+year and process-relevant title; leftover blob is not this official title

### `bacillus_germination` (cw)

- **leftover:** Moir A, Smith DA. / 1990 / The Genetics of Spore Germination in Bacillus subtilis / Annu Rev Microbiol.
- **why leftover:** multi-hit — Second-pass: Moir 1990 has two spore-germination papers. Identifiers remain stripped.
- **candidates:** no credible candidate

### `bacillus_germination` (cw)

- **leftover:** Setlow P. / 2014 / Bacterial Spore Germination: Recent Advances and Comments on the State of the Art / Annu Rev Microbiol.
- **why leftover:** multi-hit — Second-pass: Setlow 2014 spore-germination title is not unique. Identifiers remain stripped.
- **candidates:**
  - *Analysis of metabolism in dormant spores of Bacillus species by 31P nuclear magnetic resonance analysis of low-molecular-weight compounds.* (2015; PMID `25548246`; DOI `10.1128/jb.02520-14`) — same first-author+year and process-relevant title; leftover blob is not this official title
  - *Analysis of the dynamics of a Bacillus subtilis spore germination protein complex during spore germination and outgrowth.* (2015; PMID `25349160`; DOI `10.1128/jb.02274-14`) — same first-author+year and process-relevant title; leftover blob is not this official title
  - *Architecture and assembly of the Bacillus subtilis spore coat.* (2014; PMID `25259857`; DOI `10.1371/journal.pone.0108560`) — same first-author+year and process-relevant title; leftover blob is not this official title

### `ecoli_aerobic_respiration` (cw)

- **leftover:** Portnoy VA.; Beauchene NA.; Imlay JA.; Gunsalus RP. / 2008 / Metabolic adaptation to anaerobiosis by Escherichia coli: a systems perspective / FEMS Microbiol Rev
- **why leftover:** multi-hit — Second-pass: Portnoy 2008 anaerobiosis title is not unique; stored DOI is an Alphaproteobacteria secretion paper. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_aerobic_respiration` (cw)

- **leftover:** Borisov VB.; Sviridov RV.; Gennis RB.; Konstantinov AA. / 2011 / The Escherichia coli respiration conundrum: Multiple terminal oxidases, diverse physiological roles, and complex regulation / FEBS J
- **why leftover:** multi-hit — Second-pass: Borisov 2011 respiration title is not unique; stored DOI is a journal contents page. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_e._coli_acid_resistance` (cw)

- **leftover:** Foster JW. / 2004 / Escherichia coli acid resistance: systems and mechanisms / Adv Microb Physiol
- **why leftover:** multi-hit — Second-pass: Foster 2004 acid-resistance title is not unique. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_e._coli_acid_resistance` (cw)

- **leftover:** Gong S, Ma Z, Foster JW, Ni F, Zhou B. / 2011 / Acid-sensing mechanism of glutamate-dependent acid resistance system in Escherichia coli / Nat Struct Mol Biol
- **why leftover:** multi-hit — Second-pass: Gong 2011 acid-resistance title is not unique; stored DOI is a yeast telomere paper. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_e._coli_heat_shock_response` (cw)

- **leftover:** Grossman AD, Erickson JW, Gross CA. / 1984 / The RpoH protein of E. coli, a sigma-32 homolog, is required for induction of heat shock proteins. / Cell
- **why leftover:** multi-hit — Second-pass: Grossman 1984 has several RpoH/htpR papers. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_e._coli_heat_shock_response` (cw)

- **leftover:** Straus DB, Walter WA, Gross CA. / 1990 / DnaK, DnaJ, and GrpE heat shock proteins interact with RNA polymerase sigma 32 to control the initiation of heat shock gene expression. / Genes Dev
- **why leftover:** multi-hit — Second-pass: Straus 1990 RNAP-interaction title does not uniquely match the 1990 negative-regulation paper. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_e._coli_two_component_signaling` (cw)

- **leftover:** Narayana, N., O'Neal, TJ. / 2018 / Structure and Mechanism of Two-Component Signal Transduction Systems. / Chem Rev.
- **why leftover:** multi-hit — Second-pass: Narayana 2018 two-component title is not unique; stored DOI is a graphdiyne materials paper. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_fatty_acid_degradation` (cw)

- **leftover:** Nunn, WD; Binstock, JF; Clark, D. / 1983 / Genes of the Escherichia coli fatty acid oxidation complex: nucleotide sequence of the fadB gene and its product, a multifunctional enzyme, and genetic organization of the fadAB operon / J Bacteriol
- **why leftover:** multi-hit — Second-pass: Nunn 1983 has two fatty-acid papers, neither uniquely matching the oxidation-complex title. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_fatty_acid_degradation` (cw)

- **leftover:** Cronan, JE Jr. / 2004 / Regulation of fatty acid degradation in Escherichia coli / Curr Opin Microbiol
- **why leftover:** multi-hit — Second-pass: Cronan 2004 has several fatty-acid papers. Identifiers remain stripped.
- **candidates:**
  - *The structure of mammalian fatty acid synthase turned back to front.* (2004; PMID `15610841`; DOI `10.1016/j.chembiol.2004.11.011`) — same first-author+year and process-relevant title; leftover blob is not this official title

### `ecoli_nucleotide_biosynthesis` (cw)

- **leftover:** Switzer, R. L. / 1989 / Genetics and regulation of purine and pyrimidine biosynthesis in bacteria / Annu Rev Microbiol
- **why leftover:** multi-hit — Second-pass: Switzer 1989 has several papers, none matching the purine/pyrimidine-regulation title. Identifiers remain stripped.
- **candidates:**
  - *Characterization of the Escherichia coli prsA1-encoded mutant phosphoribosylpyrophosphate synthetase identifies a divalent cation-nucleotide binding site.* (1989; PMID `2542328`; DOI `10.1016/s0021-9258(18)81798-7`) — same first-author+year and process-relevant title; leftover blob is not this official title

### `ecoli_peptidoglycan_biosynthesis` (cw)

- **leftover:** Ghuysen JM. / 1991 / Penicillin-binding proteins and their relationship to the mechanism of action of penicillin / Science
- **why leftover:** multi-hit — Second-pass: Ghuysen 1991 has several PBP papers. Identifiers remain stripped.
- **candidates:**
  - *The Enterococcus hirae R40 penicillin-binding protein 5 and the methicillin-resistant Staphylococcus aureus penicillin-binding protein 2' are similar.* (1991; PMID `1747121`; DOI `10.1042/bj2800463`) — same first-author+year and process-relevant title; leftover blob is not this official title
  - *Comparison of the sequences of class A beta-lactamases and of the secondary structure elements of penicillin-recognizing proteins.* (1991; PMID `1804001`; DOI `10.1128/aac.35.11.2294`) — same first-author+year and process-relevant title; leftover blob is not this official title
  - *Amino acid sequence of the penicillin-binding protein/DD-peptidase of Streptomyces K15. Predicted secondary structures of the low Mr penicillin-binding proteins of class A.* (1991; PMID `1930140`; DOI `10.1042/bj2790223`) — same first-author+year and process-relevant title; leftover blob is not this official title

### `ecoli_peptidoglycan_biosynthesis` (cw)

- **leftover:** Egan TD, Breukink E. / 2017 / Cell Wall Peptidoglycan Biogenesis in Escherichia coli: A Complex and Dynamically Regulated Process / Chem Rev
- **why leftover:** multi-hit — Second-pass: Egan 2017 peptidoglycan title is not unique; stored DOI is an X-ray spectroscopy paper. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_phage_defense` (cw)

- **leftover:** Arber W. / 1987 / The role of restriction endonucleases and DNA methylation in cellular defense / Annu Rev Genet.
- **why leftover:** multi-hit — Second-pass: Arber 1987 has several restriction/IS papers, none uniquely matching the review title. Identifiers remain stripped.
- **candidates:**
  - *Two DNA antirestriction systems of bacteriophage P1, darA, and darB: characterization of darA- phages.* (1987; PMID `3029954`; DOI `10.1016/0042-6822(87)90324-2`) — same first-author+year and process-relevant title; leftover blob is not this official title

### `ecoli_phage_defense` (cw)

- **leftover:** Hampton HG, Fineran PC / 2022 / Mechanisms of prokaryotic defence against bacteriophages and other mobile genetic elements / Nat Rev Microbiol.
- **why leftover:** multi-hit — Second-pass: Hampton 2022 phage-defence title is not unique; stored DOI is a nomenclature commentary. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_sulfur_metabolism` (cw)

- **leftover:** Kredich NM. / 1987 / Regulation of cysteine biosynthesis in Escherichia coli and Salmonella typhimurium. / Annu Rev Microbiol.
- **why leftover:** multi-hit — Second-pass: Kredich 1987 has two cysB papers, neither uniquely matching the cysteine-regulation review title. Identifiers remain stripped.
- **candidates:**
  - *DNA sequences of the cysB regions of Salmonella typhimurium and Escherichia coli.* (1987; PMID `3032952`; DOI `10.1016/s0021-9258(18)45528-7`) — same first-author+year and process-relevant title; leftover blob is not this official title
  - *Purification of the cysB protein from Salmonella typhimurium.* (1987; PMID `3032953`; DOI `10.1016/s0021-9258(18)45529-9`) — same first-author+year and process-relevant title; leftover blob is not this official title

### `ecoli_tryptophan_biosynthesis` (cw)

- **leftover:** Yanofsky C, Ito J. / 1966 / The tryptophan operon of Escherichia coli. / J Mol Biol
- **why leftover:** multi-hit — Second-pass: Yanofsky 1966 has several trp-operon papers. Identifiers remain stripped.
- **candidates:**
  - *Nonsense codons and polarity in the tryptophan operon.* (1966; PMID `5339605`; DOI `10.1016/0022-2836(66)90102-1`) — same author-year and journal-ish; title differs from leftover blob
  - *Indole-3-glycerol phosphate synthetase of Escherichia coli, an enzyme of the tryptophan operon.* (1966; PMID `5332729`; DOI `10.1016/s0021-9258(18)99693-6`) — same first-author+year and process-relevant title; leftover blob is not this official title
  - *Comparison of the tryptophan synthetase alpha-subunits of several species of Enterobacteriaceae.* (1966; PMID `5327908`; DOI `10.1128/jb.91.5.1819-1826.1966`) — same first-author+year and process-relevant title; leftover blob is not this official title

### `yeast_aerobic_respiration` (cw)

- **leftover:** Carlson M, Botstein D. / 1983 / Regulation of sucrose utilization in yeast by the SNF1 gene / Cell.
- **why leftover:** multi-hit — Second-pass: Carlson 1983 has two SUC/invertase papers, neither SNF1 regulation. Identifiers remain stripped.
- **candidates:** no credible candidate

### `yeast_cell_wall_integrity` (cw)

- **leftover:** Levin DE., Bartlett EH. / 1993 / A Saccharomyces cerevisiae protein kinase C homolog is required for the maintenance of cell integrity / Proc Natl Acad Sci U S A
- **why leftover:** multi-hit — Second-pass: Levin 1993 has several yeast MAPK/PKC papers, none uniquely matching the PKC-homolog title. Identifiers remain stripped.
- **candidates:** no credible candidate

### `yeast_mapk_mating` (cw)

- **leftover:** Elion EA, Brill JA, Fink GR. / 1991 / FUS3, a kinase required for cell fusion in Saccharomyces cerevisiae / Science.
- **why leftover:** multi-hit — Second-pass: Elion 1991 has two FUS3 papers. Identifiers remain stripped.
- **candidates:**
  - *FUS3 represses CLN1 and CLN2 and in concert with KSS1 promotes signal transduction.* (1991; PMID `1946350`; DOI `10.1073/pnas.88.21.9392`) — same first-author+year and process-relevant title; leftover blob is not this official title

### `yeast_pka_pathway` (cw)

- **leftover:** Toda, T., Sass, P., Wigler, M. / 1988 / The yeast adenylyl cyclase gene: structure, function, and relationship to mammalian adenylyl cyclases. / Mol Cell Biol
- **why leftover:** multi-hit — Second-pass: Toda 1988 hits are SCH9/RAS papers, not the CYR1 adenylyl-cyclase title. Identifiers remain stripped.
- **candidates:** no credible candidate

### `yeast_ribosome_biogenesis` (cw)

- **leftover:** Bassler, J.; Hurt, E. / 2019 / Eukaryotic ribosome biogenesis: from small to large / Cell
- **why leftover:** multi-hit — Second-pass: Bassler 2019 ribosome-biogenesis title is not unique; stored DOI is an APOBEC mutagenesis paper. Identifiers remain stripped.
- **candidates:** no credible candidate

### `yeast_snf1_pathway` (cw)

- **leftover:** Hong SP, Carlson M / 2007 / Snf1-activating kinases Sak1, Elm1 and Tos3 regulate yeast carbon metabolism / EMBO Rep
- **why leftover:** multi-hit — Second-pass: Hong 2007 unique hits are stress/Snf4 papers, not Sak1/Elm1/Tos3 carbon metabolism. Identifiers remain stripped.
- **candidates:** no credible candidate

### `bacillus_germination` (cw)

- **leftover:** Moir A, Cutting SM. / 1993 / The Bacillus subtilis gerB locus encodes a germinant receptor and is a cluster of three cotranscribed genes / J Bacteriol.
- **why leftover:** no-hit — Second-pass: Moir 1993 gerB title was not uniquely found. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_e._coli_two_component_signaling` (cw)

- **leftover:** Maeda, S., Inouye, M. / 1983 / Two genes, ompR and envZ, specify the two regulatory components of the major outer membrane porin proteins of Escherichia coli K-12. / EMBO J.
- **why leftover:** no-hit — Second-pass: Maeda 1983 ompR/envZ title was not uniquely found. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_nucleotide_biosynthesis` (cw)

- **leftover:** Greenberg, G. R. / 1969 / Purine and Pyrimidine Nucleotide Biosynthesis and Its Control / Annu Rev Biochem
- **why leftover:** no-hit — Second-pass: Greenberg 1969 title was not uniquely found. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_outer_membrane_assembly` (cw)

- **leftover:** Schwalm J, Stathopoulos C. / 2022 / Biogenesis and Insertion of β-Barrel Outer Membrane Proteins. / Annu Rev Biochem
- **why leftover:** no-hit — Second-pass: Schwalm 2022 barrel-OMP title was not uniquely found. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_pentose_phosphate_pathway` (cw)

- **leftover:** Fraenkel, D. G., Levisohn, S. R., Horecker, B. L. / 1961 / Glucokinase and glucose-6-phosphate dehydrogenase of Escherichia coli. / J Biol Chem
- **why leftover:** no-hit — Second-pass: Fraenkel 1961 G6PD title was not uniquely found. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_pentose_phosphate_pathway` (cw)

- **leftover:** Sauer, U., Hatzimanikatis, V., Bailey, J. E., Stirnimann, F., Hochuli, M. / 1999 / Metabolic fluxes in Escherichia coli metabolism during growth on glucose and xylose mixtures. / Microbiology
- **why leftover:** no-hit — Second-pass: Sauer 1999 flux title was not uniquely found. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_pentose_phosphate_pathway` (cw)

- **leftover:** Sonnenschein, N., Melchiorsen, J., Jensen, P. R., Schuster, S. / 2011 / The pentose phosphate pathway in Escherichia coli. / Mol Microbiol
- **why leftover:** no-hit — Second-pass: Sonnenschein 2011 PPP title was not uniquely found. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_phosphate_transport` (cw)

- **leftover:** Li Y, Guo C, Cao W, Zhou D, Cao W, Xu C, Lei M, Sun X, Li S, Liu P, Wang M, Han M, Tian C, Chen C, Guo R, Guo J, Shao F / 2017 / Structural basis for Pst system-mediated phosphate sensing and transport in Escherichia coli / EMBO J.
- **why leftover:** no-hit — Second-pass: Li 2017 Pst title was not uniquely found. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_phosphate_transport` (cw)

- **leftover:** Wang T, Nada S, Zhao M, Shi D, Ma M, Tan Y, Fan S, Cui M, Wang X / 2017 / Structure of the PstB subunit of the Pst system reveals a critical role for PhoU in Pst-mediated phosphate sensing / Proc Natl Acad Sci U S A.
- **why leftover:** no-hit — Second-pass: Wang 2017 PstB title was not uniquely found. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_sulfur_metabolism` (cw)

- **leftover:** Tai GC, Kredich NM, Tai PC, Wu JY. / 1996 / The cysK and cysM gene products of Escherichia coli catalyze the in vivo formation of cysteine from thiosulfate and sulfide, respectively. / J Bacteriol.
- **why leftover:** no-hit — Second-pass: Tai 1996 cysK/cysM title was not uniquely found. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_sulfur_metabolism` (cw)

- **leftover:** Koga H, Nakano S, Fujie A, Tomatsu H, Ishihama A, Oshima T. / 2015 / The transcriptional activator CysB and the global regulator IscR control the expression of the sulfate assimilation genes in Escherichia coli. / J Biol Chem.
- **why leftover:** no-hit — Second-pass: Koga 2015 CysB title was not uniquely found. Identifiers remain stripped.
- **candidates:** no credible candidate

### `ecoli_tryptophan_biosynthesis` (cw)

- **leftover:** Morita K, Shimodaira N, Fujii H, Ishikawa K, Yanase M, Yamashita K, Sakuraba H, Kawakami T, Yamagishi A, Ohshima T. / 2013 / Structural and functional analysis of anthranilate synthase from Escherichia coli: Insight into substrate recognition and allosteric regulation. / J Biol Chem
- **why leftover:** no-hit — Second-pass: Morita 2013 anthranilate-synthase title was not uniquely found. Identifiers remain stripped.
- **candidates:** no credible candidate

### `yeast_aerobic_respiration` (cw)

- **leftover:** Verma M, Gancedo C. / 2018 / Glucose availability and the regulation of mitochondrial function in Saccharomyces cerevisiae / Curr Genet.
- **why leftover:** no-hit — Second-pass: Verma 2018 mitochondrial-regulation title was not uniquely found. Identifiers remain stripped.
- **candidates:** no credible candidate

### `yeast_alcoholic_fermentation` (cw)

- **leftover:** Fraenkel, R. G. / 1982 / Regulation of glucose metabolism in Saccharomyces cerevisiae / Annu Rev Biochem
- **why leftover:** no-hit — Second-pass: Fraenkel 1982 yeast-glucose title was not uniquely found. Identifiers remain stripped.
- **candidates:** no credible candidate

### `yeast_alcoholic_fermentation` (cw)

- **leftover:** Jansen, R. K., van Maris, A. J. A., Pronk, J. T. / 1999 / Control of glycolysis in yeast: a revisit to the Pasteur effect / J Biol Chem
- **why leftover:** no-hit — Second-pass: Jansen 1999 Pasteur-effect title was not uniquely found. Identifiers remain stripped.
- **candidates:** no credible candidate

### `yeast_gcn4_starvation` (cw)

- **leftover:** Thireos G, Penn MD, Hinnebusch AG / 1984 / The yeast GCN4 transcriptional activator is translated in response to amino acid starvation by a mechanism involving reinitiation on upstream open reading frames / Cell
- **why leftover:** no-hit — Second-pass: Thireos 1984 GCN4 title was not uniquely found. Identifiers remain stripped.
- **candidates:**
  - *5' untranslated sequences are required for the translational control of a yeast regulatory gene.* (1984; PMID `6433345`; DOI `10.1073/pnas.81.16.5096`) — same first-author+year and process-relevant title; leftover blob is not this official title

### `yeast_gcn4_starvation` (cw)

- **leftover:** Hinnebusch AG, Lincicum MJ / 2019 / Translational Control of GCN4 by Upstream Open Reading Frames: A Paradigm for Translational Control by Phosphorylation of eIF2α / Cold Spring Harb Perspect Biol
- **why leftover:** no-hit — Second-pass: Hinnebusch 2019 GCN4 title is not uniquely found. Identifiers remain stripped.
- **candidates:**
  - *Temperature-dependent regulation of upstream open reading frame translation in S. cerevisiae.* (2019; PMID `31810458`; DOI `10.1186/s12915-019-0718-5`) — same first-author+year and process-relevant title; leftover blob is not this official title
  - *Selective Translation Complex Profiling Reveals Staged Initiation and Co-translational Assembly of Initiation Factor Complexes* (2019; PMID none; DOI `10.1101/806125`) — same first-author+year and process-relevant title; leftover blob is not this official title
  - *Temperature-Dependent Regulation of Upstream Open Reading Frame Translation in  <i>S. Cerevisiae</i>* (2019; PMID none; DOI `10.1101/678409`) — same first-author+year and process-relevant title; leftover blob is not this official title

### `yeast_mapk_mating` (cw)

- **leftover:** Bardwell AJ, Thorner J. / 2018 / Signal Transduction by the Pheromone-Responsive G Protein-Coupled Receptor and Associated MAP Kinase Cascade in Saccharomyces cerevisiae / Cold Spring Harb Perspect Biol.
- **why leftover:** no-hit — Second-pass: Bardwell 2018 pheromone-receptor title was not uniquely found. Identifiers remain stripped.
- **candidates:** no credible candidate

### `yeast_nitrogen_metabolism` (cw)

- **leftover:** Cui, Y.; Moye-Rowley, WS. / 1996 / GLN3-mediated transcriptional regulation of the nitrogen catabolite repression-sensitive gene DAL5 in Saccharomyces cerevisiae requires TOR2 / Mol Cell Biol
- **why leftover:** no-hit — Second-pass: Cui 1996 GLN3 title was not uniquely found. Identifiers remain stripped.
- **candidates:** no credible candidate

### `yeast_nitrogen_metabolism` (cw)

- **leftover:** Ljungdahl, PO.; Daignan-Fornier, B.; Gaxiola, RA. / 2015 / Nitrogen Homeostasis in Yeast: An Integrated View / Annu Rev Biochem
- **why leftover:** no-hit — Second-pass: Ljungdahl 2015 nitrogen-homeostasis title is not uniquely found. Identifiers remain stripped.
- **candidates:**
  - *Diverse nitrogen sources in seminal fluid act in synergy to induce filamentous growth of Candida albicans.* (2015; PMID `25662979`; DOI `10.1128/aem.03595-14`) — same first-author+year and process-relevant title; leftover blob is not this official title

### `yeast_vesicle_trafficking` (cw)

- **leftover:** Nakano A, Schekman R. / 1989 / A budding role for Sar1p: the role of a small GTP-binding protein in ER export / Cell
- **why leftover:** no-hit — Second-pass: Nakano 1989 Sar1p title is not uniquely found; stored DOI is a Drosophila numb paper. Identifiers remain stripped.
- **candidates:** no credible candidate

## Unique-repair scan (this pass)

A leftover is treated as newly unique only if first-author+year returned **exactly one** EuropePMC hit that is process-relevant **and** journal-ish with the leftover blob.

Hits this pass: **0**. Unique leftover repairs exist: **no**.

23 August 2026 close-out: 4a Qi `16105880` and Cox B4b `10506835` attached on both trees and live-resolve `identifier`. Zeng→DiRusso KEEP (CW-only). Section C left. Remainder accepted. Named leftovers still stripped: Knowles 2009 BamA; Umbarger 1969 Feedback control. Applied PMIDs still identifier (`15539117`, `17909521`, `30633901`, `7049397` on damage-checkpoint and SOS, `10464196`, plus `16105880` and `10506835`). GAL `ever-bio-260010` still live: Platt DOI `10.1093/emboj/17.14.4086` + `animation_player_url`. 260009/260010 not touched. Unique leftover repairs exist: **no**.

## Nine-chart + GAL live evidence (23 August 2026 completion audit)

Live `/resolve-paper` (`cited_project=glmp`) on every pmid/doi row of the original nine charts in both trees. No leftovers attached. `ever-bio-260009` not touched; `ever-bio-260010` not regenerated. Do not mark the leftover-identity goal complete.

| chart | identity-bearing rows (cw+glmp) | leftover-stripped (empty IDs expected) |
|---|---|---|
| ecoli_lac_operon | PASS — Jacob `13718526`, Napoli `16427082`, Swint-Kruse `19269243` identifier + intended titles | RegulonDB; Müller-Hill 1996 book |
| ecoli_ara_operon | PASS — Schleif 2000 `11102706`; Englesberg DOI `10.1146/annurev.ge.08.120174.001251` identifier + non-empty `abstract_preview` | none |
| ecoli_chemotaxis | PASS — Berg `4563019`, Sourjik TIM `15539117`, Sourjik 2002 `11742065` identifier + intended titles | none |
| ecoli_heat_shock_response | PASS — Yura `7504905`, Hayer-Hartl `26422689` identifier + intended titles | none |
| ecoli_dna_replication_initiation | PASS — Leonard `26082765` identifier + intended title | none |
| yeast_autophagy | PASS — Mizushima `21801009`, Xie `17909521`, Levine `30633901`, Takeshige `1400575` identifier + intended titles | none |
| yeast_cell_cycle_control | PASS — Nurse `9428508`, Morgan `9442875`, Qi `16105880` identifier + intended titles | none |
| yeast_unfolded_protein_response | PASS — Walter `22116877`, Kimata/Oikawa `21266252`, Shamu `8670804` identifier + intended titles | none |
| yeast_gal_regulation | PASS — Platt `9670023` / `10.1093/emboj/17.14.4086` identifier + intended title | none |

**Nine-chart verdict:** yes — every identity-bearing row is `match_type=identifier` and the live title is the intended paper. Failures: none.

**Leftover-expected on the nine (not attached):** RegulonDB and Müller-Hill book on `ecoli_lac_operon` (cw+glmp). Qi/Elion 2005 leftover replaced by official 4a `16105880`.

**GAL live:** `ever-bio-260010` yes — `request.paper_doi` and `metadata_extended.source_papers` = `10.1093/emboj/17.14.4086` (Platt & Reece 1998); `animation_player_url` present.

**Collection leftover-note rows (cheap, `_previous_versions` excluded):** copernicus-web **107**; glmp **66**. Unique leftover repairs exist: **no**.

**Remaining named leftovers:** Knowles 5b; Umbarger 6b / 1969 Feedback control; Section C (leave). Zeng KEEP. Remainder accepted. Unique leftover repairs exist: **no**.
