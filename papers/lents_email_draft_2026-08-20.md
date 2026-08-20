# Draft email to Prof. Nathan Lents — 2026-08-20

**Status:** draft, not sent. Covers item #26 (CRP PWM sign-off), item #33 (duplicate-node loop-audit
candidates), and item #59 (RegulonDB validation sanity check), bundled per Gary's request.
Section 2 was rebuilt against the authoritative source
(`glmp/docs/open-questions/loop-audit-candidates-2026-08-04.md`) after the version pasted into chat
came through corrupted (missing words, broken sentences, wrong candidate count). Reviewed by Claude
Chat and Claude Code before this version.

---

Subject: CRP PWM sign-off + two smaller things (duplicate-node audit, a computational sanity check)

Nathan,

Thank you again for the ten papers — they're all in the corpus now (DNase footprinting, EMSA, the first PWM/matrix method, the consensus-site model, the ChIP-chip occupancy work, all of it). They filled a real gap: we had the evidentiary CRP-lac papers already, but not the methodology papers behind them.

Three things below. The first is the real ask. The other two are smaller — one needs your judgment on its own schedule, the third is just FYI, no action needed.

**1. CRP/CAP PWM — the actual sign-off, not just the literature**

I should be straightforward about where this stands. We already have a working CRP/CAP position-weight-matrix, built from 54 RegulonDB training sites, wired into the decoder. The review packet for it has said from the start "do not integrate until signed off" — and honestly, we didn't wait: we went ahead with a preliminary integration and labeled the lac operon's Class II call PROVISIONAL specifically because your sign-off hadn't happened yet. I want you to have the real picture, not a cleaned-up version of it.

The packet has three specific questions:

1. Training site quality — are the 54 RegulonDB CRP sites we trained on appropriate for a K-12 CRP/CAP PWM?
2. A specific confound — one RegulonDB row (RDBECOLIRIC06347) annotates a CRP site at lacZp1 whose core overlaps the lac operator itself (AATTGTGAGCGGATAACAATTT). We held it out of training rather than use it, but should it be kept as a holdout, or is it curation noise that should be dropped or re-annotated?
3. Holdout coverage — our held-out validation sites only cover lac, ara, and flhDC (we couldn't find CRP sites for the trp/SOS/lambda/DNA-damage windows). Is that enough to support a claim that the validation isn't circular, or too thin?

I can send you the full review document if that's more useful than this summary — just say the word.

**2. A smaller, separate thing — duplicate node IDs hiding real feedback loops**

Unrelated to CRP: we found a mechanical blind spot in how we detect feedback loops in the flowcharts. If the same biological entity gets modeled as two different node IDs in a diagram, a real cycle can render as a straight line instead of a loop — the loop-detector then correctly counts what's on the page, but what's on the page is wrong. This happened with lac's own LacY permease (drawn as "Lactose Permease LacY" and "Lactose Permease," two nodes for one protein).

We scanned all 217 processes for the same signature and found 11 candidates with an exact duplicate label on two different node IDs. Two resolved themselves on inspection as false positives, both from the same cause — our matching script strips non-ASCII characters, which collapsed genuinely distinct labels together (Tryptophan Synthase's α and β subunits in the trp operon; two different named proteins that happen to share a role description, "PMP Receptor," in yeast peroxisome biogenesis). So it's 9 real candidates worth a look, not 11:

*Probably not defects (same step legitimately recurring):* Yeast Glycolysis (two phosphorylations, two isomerizations, two substrate-level phosphorylations, two ATP-producing steps — glycolysis genuinely has these); Bacillus Sporulation Initiation ("Dephosphorylates Spo0F~P" — multiple Rap phosphatases act here); E. coli Heat Shock Response ("Protein Refolding" — DnaK and GroEL are separate systems); E. coli Flagellar Assembly ("FlgK, FlgL" — reads like protein-vs-export-event, not a real duplicate).

*Plausible missed cycle (worth a closer look):* E. coli Pentose Phosphate Pathway (two "Glucose-6-Phosphate" nodes — the non-oxidative branch regenerates G6P, which is exactly what a missing feedback edge looks like); Yeast PKA Pathway ("PKA Inactive" appearing twice, reading like negative feedback drawn as a second terminal node instead of a returning edge); E. coli Acid Resistance ("Continuous Cycle" appearing twice — close to self-reporting); Yeast GCN4 Starvation Response (four duplicated labels clustering on the uORF1 reinitiation step — "40S Scans from Cap" showing up twice looks to me like it could be two real ribosome-scanning events in a reinitiation cycle, not a duplication artifact, but that's exactly the kind of call I can't make myself).

*Mixed evidence:* E. coli Two-Component Signaling (EnvZ/OmpR) — the ompF/ompC decision recurring under both osmolarity branches reads like real biology, but one "High Osmolarity" node flowing directly into a second one looks like the artifact pattern. Genuinely unclear.

For each: is the duplicated label one entity modeled twice (a real defect, hiding a loop), or the same step legitimately recurring (not a defect)?

**3. FYI, no action needed — a computational sanity check on lac/ara**

Separately, I ran a computational cross-check of the decoder's CRP/LacI predictions against RegulonDB's experimentally validated binding sites for lac, ara, and trp (this was originally assigned to a student reviewer through the validation program; when that didn't move, I ran it directly). Result: every prediction the decoder makes above its own confidence threshold for lac and ara matches a real RegulonDB site exactly, by sequence — zero false positives. Trp didn't clear the threshold at all, so there's nothing to report there yet. Along the way we found a coordinate-labeling bug — the lac decode file's *reported position numbers* don't line up with RegulonDB's, even though the underlying DNA sequence is exactly right — but that's an engineering fix on our end, not something that needs your time. Mentioning it only so the numbers don't look alarming if you ever open the raw file yourself.

No rush on any of this. Let me know if a call would be easier, especially on #2 — happy to walk through it live.

Gary
