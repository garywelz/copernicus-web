# Handoff — 22 August 2026 (15 empty-abstract synopses applied; one author-label flag)

**From:** Claude Code (this session)
**To:** Cursor and Claude Chat
**Repo:** `copernicus-web` (Firestore-only change; no git commits for this thread)
**Regenerate from a fresh fetch before acting.**

Share this file as-is. Closes the "Ask Claude Code: editorial synopses for remaining empty
abstracts" section of
`papers/claude_code_handoff_2026-08-22_chart_source_identity_errors.md`.

---

## Done: 15 editorial synopses applied and re-embedded

All 15 papers listed in that section — Gerhart & Schachman 1965, LaPorte & Koshland 1982,
Gibson & Pittard 1968, Staley & Guthrie 1998, Kolb et al. 1993, Little & Mount 1982, Cunin et al.
1986, `pubmed_3070323` (see flag below), Ciechanover 1998, Chen & Dubnau 2004, Truglio et al. 2006,
Rock & Jackowski 2002, Buck et al. 2000, Ingledew & Poole 1984, Fothergill-Gilmore & Michels 1993 —
now have a Gary-approved editorial synopsis on the `abstract` field, `abstract_source =
editorial_synopsis_not_original_abstract`, an `abstract_note` explaining none has a published
abstract in PubMed/Crossref/EuropePMC, and a fresh `text-embedding-3-small` embedding built from the
new text (same treatment as Englesberg/Nurse/Jacob & Monod). Confirmed 15/15 wrote and embedded
cleanly, no failures. `LaPorte pubmed_6292732` now carries the correct AceK kinase/phosphatase
synopsis — not the ibuprofen paper's text — per the caution already in the source handoff.

## Flag: `pubmed_3070323` is very likely mislabeled on the `yeast_cell_cycle_control`-adjacent chart

The synopsis-request table listed this row as **"Pringle & Hartwell 1981/1988 — *Life cycle of the
budding yeast Saccharomyces cerevisiae*."** PMID `3070323` / DOI `10.1128/mr.52.4.536-553.1988`
(Microbiol Rev 52(4):536–553, 1988) is, as best I can determine, **Ira Herskowitz's** 1988 review of
that same title — not a Pringle & Hartwell paper. The title match is real (this is very likely why
your title-matching pass didn't flag it as a collision), but the author attribution attached to the
chart row appears to be wrong.

I wrote and applied the synopsis for the paper this ID actually resolves to, crediting Herskowitz —
Gary reviewed and approved proceeding on that basis. **I did not touch any chart JSON** (author
labels are chart-side, and chart repairs are your side of this split per the original task
division). Whichever chart(s) carry the "Pringle & Hartwell 1981/1988" label for this source should
have the author field corrected to Herskowitz — worth a quick grep for `3070323` or `Pringle` across
the process JSONs to see how many rows are affected before fixing.

I have not independently verified this against PubMed/Crossref beyond my own recollection of the
paper — recommend a quick confirm on your end (author field only; PMID/DOI/title all check out and
don't need re-touching) before correcting the chart.

---

## Key paths

- Firestore `research_papers/{pubmed_5320387, pubmed_6292732, pubmed_4884716, pubmed_9476892,
  pubmed_8394684, pubmed_7049397, pubmed_3534538, pubmed_3070323, pubmed_9857172, pubmed_15083159,
  pubmed_16464004, pubmed_11969206, pubmed_10894718, pubmed_6387427, pubmed_8426905}` — all 15
  updated
- Chart JSON carrying the "Pringle & Hartwell 1981/1988" author label for `pubmed_3070323` — not yet
  located/fixed, flagged for Cursor
