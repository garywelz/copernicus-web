# Handoff — 23 August 2026 (leftover garbled-title picks + three questions)

**From:** Cursor
**To:** Claude Code
**Repos:** `copernicus-web`, sibling `glmp`
**Regenerate from a fresh fetch before acting.**

Share this file as-is. Continues
`papers/claude_code_handoff_2026-08-22_chart_source_identity_errors.md` and
`papers/LEFTOVER_HUMAN_PICK_2026-08-22.md`.

Do **not** regenerate `ever-bio-260009` or `ever-bio-260010`. Do **not** invent
papers or publisher abstracts. Do **not** use
`--include-glob "**/chart_repair*.json"` (that merge blanks editorial synopses).
Do **not** overwrite a KE doc that is a different paper.

---

## Reply block (paste this back)

Answer only these. Cursor will apply.

```
4a Qi 16105880 (glance/review, no publisher abstract):
  [ ] stay leftover
  [ ] attach anyway (override no-abstract)
  [ ] write Gary-approved editorial synopsis then attach

Cox RecA leftover on ecoli_sos_response (CW + glmp sources[2]):
  [ ] B4a 9187054 Roca & Cox 1997 — stored TITLE; no publisher abstract
  [ ] B4b 10506835 Cox 1999 — stored YEAR + sole author Cox MM; has abstract
  [ ] leave

Zeng → DiRusso 1569108 already attached on CW ecoli_fatty_acid_degradation:
  [ ] keep
  [ ] revert leftover

Section C (~90 leftover-note rows):
  [ ] leave all
  [ ] I will name specific charts

Collection leftover-stripped remainder:
  [ ] accepted remainder — identity+GAL goal may close after Cox/4a
  [ ] not accepted — keep hunting
```

---

## Already closed (do not redo)

**Herskowitz / `pubmed_3070323`:** confirmed. Live KE authors are Herskowitz, I.
Synopsis credits Herskowitz 1988. Chart `yeast_mating_type_switching` already
says Herskowitz I. The “Pringle & Hartwell 1981/1988” label was only in
Cursor’s old synopsis-request table. No chart or KE author fix needed.

**Original nine charts + GAL:** live-proved 23 August. Every identity-bearing
pmid/doi on both trees is `match_type=identifier` and the intended paper.
`ever-bio-260010` is still Platt DOI `10.1093/emboj/17.14.4086` with
`animation_player_url`. Expected leftovers on those nine: Qi/Elion 2005
(empty IDs), RegulonDB, Müller-Hill book.

**Empty abstracts on current chart identifier matches:** none. Englesberg twins
still have the Claude Code editorial synopsis (852 chars). Ingest
`--no-skip-existing` over empty `chart_repair*.json` will blank those again.

**Your 22 August pick `1a, 2a, 3a, 4a, 5b, 6b` plus B title-owners — applied
except 4a/5b/6b:**

| Pick | Now |
|---|---|
| 1a Sourjik TIM | APPLIED `pubmed_15539117` both trees; resolve identifier |
| 2a Xie & Klionsky 2007 | APPLIED `pubmed_17909521` both trees |
| 3a Levine 2019 Cell | APPLIED `pubmed_30633901` both trees |
| 4a Qi JCS `16105880` | LEFT. Cell Science at a Glance, 4 pp., PubMed Review. **No publisher abstract** (PubMed / EuropePMC / Crossref / JCS page). Per your “drop to 4d if not review-style from the abstract.” |
| 5b Knowles 2009 | LEFT (you were not confident) |
| 6b Umbarger 1969 | LEFT (you were not confident) |
| Henestrosa 2000 → Little & Mount 1982 | APPLIED `pubmed_7049397` on `ecoli_dna_damage_checkpoint` **and** `ecoli_sos_response`. Little 1980 `6447873` still on the damage chart. |
| Vogt 2012 → Raivio 1999 | APPLIED `pubmed_10464196` both trees |

**Zeng 2023 FadR (you asked for the 1992 PMID, then Cursor attached):**
CW-only leftover title uniquely is DiRusso et al. 1992
*Characterization of FadR…*, PMID `1569108`, DOI
`10.1016/s0021-9258(18)42497-0`. Live KE is that paper, now
`match_type=identifier` (glmp `citations[]` tagged; empty DOI filled).
CW `ecoli_fatty_acid_degradation` `sources[1]` retitled to official DiRusso
1992. **glmp twin was not given this row** (Clark & Cronan only). GCS wrote
only `glmp-processes-database/processes/ecoli_fatty_acid_degradation.json`.
Confirm keep vs revert in the reply block.

---

## Still leftover — Cox RecA (need one pick)

Stored blob (CW + glmp `ecoli_sos_response` `sources[2]`):

- authors `Cox MM`
- year `1999`
- title `RecA protein: structure, function, and role in recombinational DNA repair`
- journal *Progress in nucleic acid research and molecular biology*
- pmid/doi empty

| Opt | Paper | PMID | DOI | Matches stored | Abstract | KE |
|---|---|---|---|---|---|---|
| **B4a** | Roca & Cox 1997, same title as stored | `9187054` | `10.1016/s0079-6603(08)61005-3` | title | **none** | `identifier_not_found` |
| **B4b** | Cox 1999 *Recombinational DNA repair in bacteria and the RecA protein* | `10506835` | `10.1016/s0079-6603(08)60726-6` | year + sole author | yes | `identifier_not_found` |

Staged (not applied): `papers/_staged_leftover_picks/cox_b4a_1997.json`,
`cox_b4b_1999.json`. B4a has the same no-abstract gate as 4a.

---

## 4a detail (if you override)

- Official: Qi & Elion 2005 *MAP kinase pathways*, JCS, PMID `16105880`,
  DOI `10.1242/jcs.02470`
- Not ingested (`identifier_not_found`)
- Not the formin/Ste5 paper `15961405` or the Science signaling piece `15692041`
- Stored leftover title is Wilkinson 2000 (`11053235`), not this JCS glance
- Attaching 4a needs ingest. Podcast generate will 400 without an abstract
  unless a Gary-approved editorial synopsis is stored first

---

## Locked method (unchanged)

1. Ignore colliding stored IDs. Search author + year + title.
2. Confirm DOI and PMID separately.
3. Wrong KE doc: do not overwrite; ingest/re-link.
4. Published abstracts only, unless `abstract_source=editorial_synopsis_not_original_abstract`.
5. After attach, `/resolve-paper` `cited_project=glmp` → `match_type=identifier`.
6. Single-file ingest glob only. Never `chart_repair*.json` batch.
7. Match CW↔glmp twins by **filename stem**. Do not overwrite a repaired glmp
   Firestore source list with a CW-only subset.
8. Leave surplus KE papers alone except the ones you already chose to attach
   (Xie 2007, Levine 2019). Do not attach Mizushima 2023 as Levine.

---

## Out of scope unless you name charts

Section C leftover-note rows (Knowles, Umbarger 1969, Cronan 2004, Nunn 1983,
and the rest). Counts after Zeng attach: CW leftover-note rows ~104, glmp ~59.
Unique author+year leftover repairs remaining: **no**.

---

## Key paths

- `papers/LEFTOVER_HUMAN_PICK_2026-08-22.md` — full pick packet (Zeng line in
  OPEN PICKS is stale; attach already done)
- `papers/_staged_leftover_picks/` — Cox objects only still pending
- Live resolve: `POST https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app/resolve-paper`
