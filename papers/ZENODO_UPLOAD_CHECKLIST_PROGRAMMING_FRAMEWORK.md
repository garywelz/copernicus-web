# Zenodo Upload Checklist: Programming Framework Article

Use this when uploading the Programming Framework article to Zenodo for citation and reproducibility.

**Published DOI:** https://doi.org/10.5281/zenodo.18463442

---

## 1. Before you start

- **PDF:** Use `programming_framework.pdf` in this folder.
- **Optional files:** `programming_framework.md`, `mermaid_images/` (diagram examples), or other supporting files as “Additional files.”
- **Login:** Go to [https://zenodo.org](https://zenodo.org) and sign in (or create an account). Linking with **ORCID** is recommended.

---

## 2. Create new upload

- Click **Upload** (top right) → **New upload**.
- **File:** Add the PDF (required). Add `programming_framework.md` and/or diagram files if desired.

---

## 3. Metadata (fill in)

- **Publication type:** Preprint (or “Report” or “Technical report”).
- **Title:** The Programming Framework: A General Method for Process Analysis Using LLMs and Mermaid Visualization
- **Authors:** Gary Welz (Contact person). Affiliations: John Jay College CUNY, Borough of Manhattan Community College CUNY, CUNY Graduate Center New Media Lab.
- **Description/Abstract:** Paste the abstract from the paper:

  > Scientific and technical fields rely heavily on textual process descriptions that are difficult to compare, analyze, or reuse computationally. We introduce the Programming Framework, a methodology for transforming textual process descriptions into structured, computable flowcharts using large language models (LLMs) and Mermaid diagram syntax. The framework suggests a five-category color-coding system (Red: triggers/inputs, Yellow: structures/objects, Green: processing/operations, Blue: intermediates/states, Violet: products/outputs) for consistent representation across disciplines, with customization for domain-specific needs. We demonstrate effectiveness through application across biology (100+ processes via the Genome Logic Modeling Project), chemistry (70+ processes), mathematics, physics, and computer science. The methodology enables researchers, educators, and AI systems to visualize, compare, and optimize processes across scientific disciplines. The Programming Framework is designed as reusable infrastructure that others can adopt, extend, and critique, with all methodology, tools, and examples publicly available.

- **License:** e.g. **Creative Commons Attribution 4.0 (CC-BY-4.0)**.
- **Keywords:** process visualization, LLM-powered analysis, Mermaid diagrams, knowledge representation, cross-disciplinary analysis, scientific workflows
- **Notes (optional):** “Methodology paper. Hugging Face implementation: https://huggingface.co/spaces/garywelz/programming_framework”

---

## 4. Dates

- **Date:** Use deposit date (e.g. YYYY-MM-DD).
- **Type:** Submitted.
- **Description:** Optional; can leave blank.

---

## 5. Publish and get the DOI

- Click **Publish** (or **Reserve DOI** first if you want to review later; once published, the DOI is permanent).
- After publishing, Zenodo will show:
  - **DOI:** `10.5281/zenodo.XXXXXXX` (numeric ID)
  - **URL:** `https://zenodo.org/record/XXXXXXX`

---

## 6. Update references (if applicable)

- In the NSF proposal or other documents, cite as:
  - `Welz, G. (2024–2025). The Programming Framework: A General Method for Process Analysis. Hugging Face Spaces. Zenodo: https://doi.org/10.5281/zenodo.18463442`
- Or use the Zenodo-generated citation.

---

## Suggested citation (current version)

```
Welz, G. (2026). The Programming Framework: A General Method for Process Analysis Using LLMs and Mermaid Visualization. Zenodo. https://doi.org/10.5281/zenodo.18463442
```

---

## Related resources

- **Hugging Face Space:** https://huggingface.co/spaces/garywelz/programming_framework
- **GLMP (demonstration):** https://huggingface.co/spaces/garywelz/glmp
