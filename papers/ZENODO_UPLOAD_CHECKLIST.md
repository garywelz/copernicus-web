# Zenodo Upload Checklist: Knowledge Engine Vision Paper

Use this when uploading the vision paper to Zenodo so NSF and NMI can cite the preprint.

---

## 1. Before you start

- **PDF:** Use `knowledge_engine_vision.pdf` in this folder (or the merged manuscript PDF from your NMI submission).
- **Login:** Go to [https://zenodo.org](https://zenodo.org) and sign in (or create an account). Linking with **ORCID** is recommended for a clean author profile.

---

## 2. Create new upload

- Click **Upload** (top right) → **New upload**.
- **File:** Add the PDF (required). You can also add `knowledge_engine_vision.md` and figure files as “Additional files” if you want.

---

## 3. Metadata (fill in)

- **Publication type:** Preprint (or “Report” if Preprint is not listed).
- **Title:** A Vision for AI-Powered Knowledge Engines: A Framework for Systematic Knowledge Discovery and Integration
- **Authors:** Gary Welz (add your affiliation: e.g. CUNY Graduate Center / John Jay College)
- **Description/Abstract:** Paste the abstract from the paper (the two paragraphs under **Abstract** in `knowledge_engine_vision.md`).
- **License:** e.g. **Creative Commons Attribution 4.0 (CC-BY-4.0)** so others can share and adapt with attribution.
- **Keywords:** knowledge engine, AI systems, knowledge discovery, scientific research, knowledge integration
- **Related identifiers (optional):** If you have a NMI manuscript number, you can add it as “Submitted to: Nature Machine Intelligence” in notes or a custom field if Zenodo offers it.
- **Notes (optional):** “Submitted to *Nature Machine Intelligence* (Perspective); under review.”

---

## 4. Publish and get the DOI

- Click **Publish** (or **Reserve DOI** first if you want to review later; once published, the DOI is permanent).
- After publishing, Zenodo will show:
  - **DOI:** `10.5281/zenodo.XXXXXXX` (numeric ID)
  - **URL:** `https://zenodo.org/record/XXXXXXX`

---

## 5. Update the NSF proposal

- In `nsf-proposal/NSF_CISE_CORE_Proposal_Draft.md`, find the vision paper reference (Section 10) and replace `[ADD_RECORD_ID]` with your Zenodo record ID.
  - Example: if your DOI is `10.5281/zenodo.1234567`, the line should read:
  - `Preprint: https://doi.org/10.5281/zenodo.1234567`
- Remove the instruction text: *“(replace [ADD_RECORD_ID] with your Zenodo record ID after upload)”*.

---

## 6. Notify Nature Machine Intelligence

- In the NMI submission system, use **Send Manuscript Correspondence** (or equivalent) to inform the journal that you have posted a preprint.
- Include: “The manuscript has been posted as a preprint on Zenodo: https://doi.org/10.5281/zenodo.XXXXXXX” (your actual DOI).

---

## Suggested citation (after upload)

```
Welz, G. (2025). A Vision for AI-Powered Knowledge Engines: A Framework for Systematic Knowledge Discovery and Integration. Nature Machine Intelligence (under review; Perspective). Preprint at https://doi.org/10.5281/zenodo.XXXXXXX
```

Replace `XXXXXXX` with your Zenodo record number.
