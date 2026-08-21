# Handoff — 21 August 2026 (lac collection gaps + self-animating podcasts)

**From:** Cursor / Gary
**To:** Claude Code (ingest) and Claude Chat
**Repo:** `copernicus-web` (`origin/main`)
**Regenerate from a fresh fetch before acting.**

Share this file as-is. Continuous with
`papers/cursor_handoff_2026-08-20_podcast_quality_and_ui.md`.
CopernicusAI.fyi / GLMP Knowledge Engine — not the E. coli decoder build,
except where the same lac/CRP papers overlap.

Gary asked Cursor to **hand these papers to Claude Code to ingest and use as
seeds**, and stated the graphics goal below. Cursor is not running ingest.

---

## 1. Ingest / seed (Claude Code)

While picking a paper that already sits on the **Lac Operon** GLMP chart
(`ecoli_lac_operon`) for the first inline-graphics podcast, `/resolve-paper`
showed collection gaps and a **wrong DOI on the chart itself**.

Use existing #43 intake: `huggingface-space/scripts/acquire_papers/researcher_cited_intake.py`
then `ingest_papers_from_metadata_json.py`. Provenance:

- `cited_by`: Gary Welz
- `cited_date`: 2026-08-21
- `cited_project`: `glmp`
- `cited_for_question`: lac operon / CRP–CAP regulation (chart `ecoli_lac_operon`)
- `cited_context`: seed papers for a paper-sourced podcast that can attach the
  lac flowchart; found while checking whether Napoli 2006 was in the KE

### Missing — ingest these

| Paper | Identifier | What `/resolve-paper` said |
|---|---|---|
| Napoli AA, Lawson CL, Ebright RH, Berman HM (2006). *Indirect readout of DNA sequence at the primary-kink site in the CAP–DNA complex: recognition of pyrimidine-purine and purine-purine steps.* *J Mol Biol* 357:173–183. | DOI **`10.1016/j.jmb.2005.12.051`** | `identifier_not_found` (unscoped and `cited_project=glmp`) |
| Swint-Kruse L, Matthews KS (2009). *Mechanism of the allosteric regulation of the lac repressor.* *Adv Appl Microbiol* 67:1–24. | DOI **`10.1016/S0065-2164(08)01001-8`** | `identifier_not_found` |

**Use those DOIs.** Do not ingest under the chart’s stored Napoli DOI (see trap below). After ingest, confirm each record has a **non-empty abstract** — `/generate-podcast-from-paper` 400s without one.

Treat both as **seeds**: once in, they should be usable as GLMP-scoped identifier matches for the lac-operon podcast path, not only as anonymous Crossref hits.

### In the KE already — do not duplicate; do repair

| Paper | KE id | Issue |
|---|---|---|
| Jacob F, Monod J (1961). *Genetic regulatory mechanisms in the synthesis of proteins.* *JMB* 3:318–356. | `pubmed_13718526`, DOI `10.1016/s0022-2836(61)80072-7`, identifier match even with `cited_project=glmp` | **Abstract empty** — cannot generate. Backfill abstract (PubMed/Crossref), do not create a second doc. |
| Dickson, Abelson, Barnes, Reznikoff (1975). *Genetic regulation: the Lac control region.* *Science*. | `pubmed_1088926`, DOI `10.1126/science.1088926` | **Good.** GLMP-tagged, abstract present. Best *currently generatable* lac paper for a podcast. Not an ingest target. |
| Schmitz (1981). *Cyclic AMP receptor protein interacts with lactose operator DNA.* *NAR*. | `pubmed_6259624`, DOI `10.1093/nar/9.2.277` | In KE with abstract; **`identifier_wrong_project` under `cited_project=glmp`**. Tag/re-cite as GLMP if ingest policy allows (item 45 re-citation), do not duplicate. |
| Ullmann / Magasanik-era catabolite-repression reappraisal (1978). | `pubmed_214424`, DOI `10.1128/jb.136.3.947-954.1978` | Same: in KE + abstract, not GLMP-tagged. |

### Trap — do not treat this DOI as Napoli

`ecoli_lac_operon` `sources` / `related_papers` currently list:

- title: *Revisiting the lac operon: Functional analysis of the cAMP receptor protein*
- DOI: **`10.1016/j.str.2005.11.021`**
- PMID: **`16531234`**
- `paper_id`: `crossref_10_1016_j_str_2005_11_021`

Live resolve of that DOI is **Iengar, Joshi & Balaram**, *Conformational and Sequence Signatures in β Helix Proteins* (`crossref_10.1016_j.str.2005.11.021`), empty abstract, not GLMP. PMID `16531234` is a **third** paper (titin Z1Z2–telethonin, DOI `10.1016/j.str.2005.12.005`).

The chart row is garbled. Napoli’s real 2006 paper is the **JMB** article above, not *Structure*. After ingesting the real Napoli DOI, **fix the chart source row** (title, DOI, PMID, `paper_id`) so the process and the KE point at the same paper. Do not ingest Iengar as a lac seed.

Müller-Hill 1996 *The lactose operon* is a book (ISBN only) — skip unless there is a DOI later.

### Verify

`POST https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app/resolve-paper`

```json
{"query": "10.1016/j.jmb.2005.12.051", "cited_project": "glmp"}
```

Want: `match_type=identifier`, one paper, non-empty `abstract_preview`. Same for the Swint-Kruse DOI. Jacob should keep `identifier` and gain an abstract.

---

## 2. Self-animating podcasts (goal — Cursor later, not this ingest)

Gary confirmed:

- First audience: **website player**
- Graphics must be **meaningful** (GLMP/KE chart, not decorative DALL-E)
- **Synchronize images with cues in the podcast text**
- Flowcharts are authored in **Mermaid (`.mmd` / `mermaid` on the process JSON)**
- Animate as an **inline image sequence** from that mermaid source
- **SVG is optional**, not required, unless we choose it as a render target
- Same method for **Python / matplotlib** (math and other graphics)
- Direction of travel: stills → multiple stills → zooms / pans / tracking down the chart as the process is discussed
- Name for the product: **self-animating podcasts**

Source of truth is the **`.mmd` (or a matplotlib script)**, not hand-authored SVG. A frame is a render of a mermaid snapshot (full graph, or a prefix/highlight of nodes that the cue names). `mmdc` / mermaid-cli already emit PNG or SVG; the player can swap PNGs on cue. Matplotlib likewise emits a PNG sequence. SVG stays a possible intermediate, not a prerequisite.

Cue shape (illustrative, not implemented): the script names beats that exist on the chart (`[CHART ecoli_lac_operon node=ANDGATE2]` or equivalent). The web player uses `audio.currentTime` (or word timing) to advance the frame. RSS stays audio-only for now.

Do **not** start the player/encoder in this ingest task. Do **not** generate another Stormo episode for this. First live graphics episode waits until a lac paper with a real abstract is in the KE (Dickson 1975 can already generate; Napoli after ingest is the preferred seed).

Canonical chart id: **`ecoli_lac_operon`**. Viewer:
`https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/glmp-v2/viewer/index.html?process=ecoli_lac_operon`

A smaller mermaid already exists at `nsf-proposal/flowcharts/lac.mmd` if a 62-node first animation is too dense; that is a later Cursor choice, not ingest.

---

## Out of scope for this handoff

- Cloud Build / podcast UI
- Publishing `ever-bio-250045` / `260008`
- `shadow`
- Ungated bibliography ingest of every reference on the lac chart
