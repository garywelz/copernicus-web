# Memo for DOE Proposal Chat Agent

**Purpose:** Handoff so you can resume work on the DOE SBIR Phase I proposal in this directory (`doe-proposal/`). The NSF CISE proposal on the same research has been submitted; use it for consistency and reference.

---

## 1. Context

- **NSF proposal (submitted):** "CopernicusAI Knowledge Engine: Assisted Research via AI Briefings, Multi-Modal Metadata, and Process Visualization" — submitted to NSF CISE IIS (Proposal #2616543, 02/05/2026). Same research theme as this DOE SBIR.
- **DOE proposal (this directory):** DOE SBIR Phase I for the same CopernicusAI Knowledge Engine work. Technical content is drafted; alignment with NSF, compliance, and formatting remain.

---

## 2. Agreed Plan for DOE Proposal

1. **Align with NSF submission**
   - Use **Welz (2026a)** and **Welz (2026b)** for the two Zenodo preprints (Vision paper; Programming Framework). References: Zenodo DOI 10.5281/zenodo.18463304 (vision); 10.5281/zenodo.18463442 (Programming Framework).
   - First use of GLMP in any document: **"Genome Logic Modeling Project (GLMP)"**; thereafter **"GLMP"**.
   - Remove or generalize specific numeric counts (e.g., 64+ episodes, 12,000+ papers, 50+ processes) to avoid outdated or inconsistent figures; keep narrative generic where appropriate.
   - Any "Note on Publications" (or equivalent): state that the PI has posted two preprints (Welz 2026a, 2026b); additional draft manuscripts are in preparation. Existing prototypes and preprints are primary evidence of prior work.

2. **Compliance**
   - Research Security Training: complete before submission; certificate required.
   - SAM.gov: registration should be ACTIVE; UEI KX9CBZB6NMV7 (and DUNS/CAGE as in checklist). Confirm and use in proposal as required.

3. **FOA and formatting**
   - Identify the **current DOE SBIR FOA** and submission deadline.
   - Format all documents to that FOA (page limits, sections, file types).
   - Generate PDFs as required for submission.

4. **DOE-specific**
   - Emphasize **commercialization** and **Phase I innovation** (DOE SBIR focus).
   - Check whether DOE allows hyperlinks/URLs in the technical narrative; if not, remove or replace with non-clickable text (e.g., DOI only).

---

## 3. DOE Proposal Directory (where to work)

**Path:** `doe-proposal/` (or `copernicus-web-public/doe-proposal/` from repo root)

| Document | Role |
|----------|------|
| DOE_SBIR_PhaseI_Draft.md | Main technical narrative — align citations, GLMP, numbers, publications note |
| DOE_SBIR_Biographical_Sketch_Welz.md | PI biosketch (2-page); keep consistent with NSF narrative |
| DOE_SBIR_BUDGET_PhaseI.md | Budget ($250K) and justification |
| DOE_SBIR_DataManagement_Plan.md | Data management and sharing |
| DOE_SBIR_Facilities_Equipment.md | Facilities and equipment |
| DOE_ResearchSecurity_Training_Guide.md | Research security training instructions |
| DOE_SBIR_STATUS.md | Status summary — update as tasks complete |
| DOE_SBIR_SUBMISSION_CHECKLIST.md | Submission checklist (SAM.gov, training, FOA, etc.) |

---

## 4. NSF Proposal Documents to Share With This Agent

Share these from **`nsf-proposal/`** so the DOE agent can match wording, citations, and facts:

### Essential (cite/narrative alignment)

- **NSF_Project_Description.md** — Authoritative narrative: prior work, objectives, approach, citations (Welz 2026a/2026b), GLMP naming, publications note, no URLs in body.
- **NSF_References_Cited.md** — Canonical reference list: two Welz 2026 preprints (2026a, 2026b) with Zenodo; supporting prototypes; note on publications.

### Useful for consistency

- **NSF_Project_Summary.md** — One-page summary; good for tone and high-level alignment.
- **NSF_Budget_Justification.md** — Budget narrative style and categories (personnel, fringe, indirect, etc.); DOE budget is different ($250K Phase I) but structure can inform.
- **NSF_BUDGET_3Year.md** — Full NSF budget breakdown; reference only (DOE Phase I is separate).

### Optional (if agent needs more context)

- **NSF_Biographical_Sketch_Welz.md** — PI narrative and products; DOE biosketch can stay consistent (no need to match SciENcv line-by-line).
- **NSF_Facilities_Equipment_Resources.md** — Facilities/equipment wording and structure.
- **NSF_DataManagement_Plan.md** — Data management approach; DOE has its own plan but content can align.

Do **not** rely on NSF PDFs for editing; use the `.md` sources above so the DOE agent can apply edits and regenerate DOE PDFs as needed.

---

## 5. What Not to Change

- **NSF proposal directory and files** — Do not edit NSF documents from the DOE agent; they are already submitted.
- **SciENcv / Biographical Sketch** — NSF required SciENcv-generated PDF; DOE may have different rules. Do not assume DOE uses SciENcv unless the FOA says so.

---

## 6. Resuming Work

When the user returns, start by:

1. Reading this memo and the listed NSF docs (if attached).
2. Updating **DOE_SBIR_PhaseI_Draft.md** for citation alignment (Welz 2026a/2026b), GLMP first-use, numeric generalizations, and publications note.
3. Then proceeding to compliance check, FOA/formatting, and DOE-specific narrative/PDFs as above.

---

**Last updated:** 2026-02-05  
**NSF proposal:** Submitted (Proposal #2616543)  
**DOE proposal:** In progress; resume in `doe-proposal/` per this plan.
