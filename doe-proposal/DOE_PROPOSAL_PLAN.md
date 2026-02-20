# Plan: DOE SBIR Phase I Proposal (Post-NSF Submission)

**Purpose:** Move the DOE proposal to submission-ready state using the submitted NSF proposal as the source of truth for narrative, citations, and facts. Do not edit any NSF documents.

**Reference:** MEMO_FOR_DOE_PROPOSAL_AGENT.md; NSF Proposal #2616543 (submitted 02/05/2026).

---

## Phase 1 — Align DOE Narrative with NSF (Do First)

### 1.1 Citations and references (DOE_SBIR_PhaseI_Draft.md)

- **Lead with Zenodo preprints:** Replace the current "References and Prior Work Citations" (Section 9) with the NSF-aligned structure:
  - **Welz (2026a)** — *A Vision for AI-Powered Knowledge Engines...* — Zenodo DOI 10.5281/zenodo.18463304  
  - **Welz (2026b)** — *The Programming Framework: A Universal Method for Process Analysis* — Zenodo DOI 10.5281/zenodo.18463442  
  - Then list supporting prototypes (CopernicusAI, Programming Framework, GLMP, Science Video DB, Metadata DB) as (2024–2025) with Hugging Face; per memo, if DOE disallows hyperlinks in narrative, use DOI only for 2026a/2026b and avoid clickable URLs elsewhere or replace with “Zenodo DOI: …” / “Hugging Face Space: [name]” as plain text.
- **In-text citations:** Anywhere the narrative cites prior work, use **Welz (2026a)** and **Welz (2026b)** for the vision and Programming Framework; keep prototype references consistent with NSF (e.g., “Programming Framework,” “GLMP”).

### 1.2 GLMP naming (DOE_SBIR_PhaseI_Draft.md)

- **First use in document:** Spell out **"Genome Logic Modeling Project (GLMP)"**; thereafter use **"GLMP"** only.  
- Scan full draft and fix any first mention that currently says only "GLMP."

### 1.3 Numeric generalizations (DOE_SBIR_PhaseI_Draft.md)

- **Remove or generalize** specific counts that may become outdated or differ from NSF:
  - e.g. “64+ episodes,” “12,000+ papers,” “50+ processes,” “250+ million papers,” “8+ databases,” “2k to 200k+ videos.”
- Replace with generic wording where appropriate (e.g., “multiple disciplines,” “large corpus,” “many processes,” “major academic databases”) so the narrative stays accurate without hard numbers.

### 1.4 Note on publications (DOE_SBIR_PhaseI_Draft.md)

- Add a short **“Note on Publications”** (in Section 9 or adjacent to references), matching NSF:
  - *The PI has posted two preprints (Welz, 2026a, 2026b) framing this work: a Knowledge Engine vision and the Programming Framework. Additional draft manuscripts are in preparation but have not yet been submitted for publication. The existing operational prototypes and these preprints serve as primary evidence of prior work and technical feasibility.*

### 1.5 Hyperlinks / URLs (DOE-specific)

- **Check** the current DOE SBIR FOA for whether hyperlinks/URLs are allowed in the technical narrative.
- **If not allowed:** Remove clickable links; for preprints use “DOI 10.5281/zenodo.18463304” (and 18463442) as plain text; for prototypes use short plain-text labels (e.g., “Hugging Face Space: garywelz/copernicusai”) without URLs, or move URLs to a separate “Prior Work URLs” page if the FOA permits.

---

## Phase 2 — Compliance (You + Agent)

### 2.1 Research Security Training (you)

- **Action:** Complete DOE Research Security Training before submission; obtain and save certificate PDF.  
- **Reference:** DOE_ResearchSecurity_Training_Guide.md; DOE portal and FAL links in DOE_SBIR_SUBMISSION_CHECKLIST.md.  
- **Agent:** No edits to NSF; ensure checklist and status doc say “certificate required at submission.”

### 2.2 SAM.gov and UEI (verify and document)

- **Current state (from checklist):** SAM.gov ACTIVE; UEI **KX9CBZB6NMV7**; DUNS 017240183; CAGE 8BWB1.  
- **Your action:** Confirm SAM.gov is still ACTIVE and UEI is correct; use exactly these in the proposal and submission system.  
- **Agent:** Update DOE_SBIR_SUBMISSION_CHECKLIST.md Section 3 (UEI) to “Obtained: KX9CBZB6NMV7” and ensure DOE_SBIR_PhaseI_Draft.md (and any admin summary) include UEI where the FOA requires.

---

## Phase 3 — FOA, Formatting, and PDFs

### 3.1 Identify current FOA and deadline

- **Action:** Confirm the **current DOE SBIR Phase I FOA** and submission deadline (e.g., FY 2026 Release 2 or next cycle).  
- **Note:** FY 2026 Release 2 full applications were due Feb 25, 2026; if that window has passed, use the next FOA’s dates.  
- **Agent:** Can search for “DOE SBIR Phase I [fiscal year] FOA” and summarize page limits, sections, and file types.

### 3.2 Format to FOA

- Format **DOE_SBIR_PhaseI_Draft.md** (and any other narrative sections) to FOA page limits, section order, and headings.  
- Ensure **DOE_SBIR_Biographical_Sketch_Welz.md** matches FOA (e.g., 2-page limit) and is consistent with NSF narrative (no need to match SciENcv line-by-line).  
- Align **DOE_SBIR_BUDGET_PhaseI.md** with FOA budget forms/instructions ($250K Phase I; confirm amount in FOA).

### 3.3 Generate PDFs

- Export or convert each required document to PDF per FOA (technical narrative, budget, biosketch, data management plan, facilities/equipment, training certificate when ready).

---

## Phase 4 — DOE-Specific Narrative and Commercialization

- **Emphasize** in the technical narrative (and summary, if any):
  - **Phase I innovation** and feasibility (DOE SBIR focus).  
  - **Commercialization path:** subscription product, institutional licenses, APIs, partnerships (already in Section 7; keep and sharpen).  
- **MCP server and commercial value:** Keep the Phase I enhancement language that ties MCP to developer tools and commercial API foundation; ensure it reads as DOE-friendly (innovation + path to market).

---

## Suggested Order of Work

| Step | Task | Owner |
|------|------|--------|
| 1 | Apply Phase 1 edits to **DOE_SBIR_PhaseI_Draft.md** (citations, GLMP, numbers, publications note, URLs) | Agent |
| 2 | Quick consistency pass on **DOE_SBIR_Biographical_Sketch_Welz.md** vs NSF tone/facts | Agent |
| 3 | Update **DOE_SBIR_SUBMISSION_CHECKLIST.md** (UEI obtained; any new FOA details) | Agent |
| 4 | Update **DOE_SBIR_STATUS.md** (align with memo; “citation alignment done,” next = compliance/FOA) | Agent |
| 5 | Confirm current FOA and deadline; summarize page limits and required sections | Agent (search) / You (confirm) |
| 6 | Complete Research Security Training; attach certificate to submission | You |
| 7 | Verify SAM.gov ACTIVE and UEI in proposal and portal | You |
| 8 | Format all documents to FOA; generate PDFs; submit | You + Agent (format/PDF as needed) |

---

## What Not to Change

- **NSF proposal directory and files** — Do not edit; they are submitted.  
- **SciENcv / NSF biosketch** — Do not assume DOE uses SciENcv; follow DOE FOA for biosketch format.

---

## File Summary

| Document | Role in plan |
|----------|------------------|
| **DOE_SBIR_PhaseI_Draft.md** | Main edits: citations (Welz 2026a/2026b), GLMP first-use, numbers, publications note, URLs |
| **DOE_SBIR_Biographical_Sketch_Welz.md** | Consistency with NSF; format to DOE FOA |
| **DOE_SBIR_BUDGET_PhaseI.md** | Confirm $250K and FOA format |
| **DOE_SBIR_DataManagement_Plan.md** | Optional alignment with NSF content; format to FOA |
| **DOE_SBIR_Facilities_Equipment.md** | Optional alignment with NSF; format to FOA |
| **DOE_SBIR_SUBMISSION_CHECKLIST.md** | Update UEI status; add FOA/deadline when known |
| **DOE_SBIR_STATUS.md** | Update after Phase 1 and as tasks complete |
| **NSF_Project_Description.md**, **NSF_References_Cited.md** | Reference only; do not edit |

---

**Next immediate action:** Run Phase 1 (Section 1.1–1.5) on **DOE_SBIR_PhaseI_Draft.md**, then update STATUS and CHECKLIST.
