# Point-by-Point Response to Reviewer Comments

**Manuscript:** AI-Powered Knowledge Engines as Research Infrastructure for Systematic Knowledge Discovery
**Submission ID:** b315049e-4ca5-4707-a6eb-fad93920bc9d
**Journal:** Discover Artificial Intelligence (Springer Nature)
**Author:** Gary Welz, Researcher, New Media Lab, CUNY Graduate Center

We thank the editor and both reviewers for their careful reading of the manuscript and their constructive feedback. The comments have led to substantial improvements in clarity, structure, and empirical content. Below we address each comment in turn, indicating where changes were made in the revised manuscript.

---

## Editorial Comments (Internal Feedback)

### Comment E1: Revise title
*"The title should have a clear, precise scientific meaning. Where possible, the title should be read as one concise sentence, without the use of punctuation (full stops, colons, hyphens, question marks etc.)."*

**Response:** The title has been revised to:

> *AI-Powered Knowledge Engines as Research Infrastructure for Systematic Knowledge Discovery*

The colon has been removed and the title now reads as a single grammatical phrase with clear scientific meaning.

---

### Comment E2: Declarations section
*"Authors are requested to include a separate section in the manuscript titled 'Declarations,' with subheadings for Ethical approval, Consent to participate, and Consent to publish."*

**Response:** A Declarations section has been added at the end of the manuscript with three clearly labelled subheadings. This is a computational research paper involving no human participants and no sensitive personal data; each subheading is addressed accordingly. Prospective user studies referenced in the evaluation roadmap (Section 6) will require institutional review board approval prior to enrolment, and this is noted explicitly.

---

## Reviewer 1

### Comment R1.1: Explanatory figure for Sections 3 and/or 4
*"The choices should be made a little clearer with an explanatory figure in sections 3 and/or 4."*

**Response:** Two new figures have been added:

- **Figure 1 (Section 3.1):** A nine-capability coupling diagram showing how the capabilities interact, including feedback loops and governance oversight nodes. The diagram makes explicit which capabilities feed into which, and where governance oversight applies.
- **Figure 3 (Section 5):** A query lifecycle sequence diagram showing how a researcher's query moves through the system — from submission through the MCP/FastAPI gateway, retrieval pool, language model grounding, and back to the researcher via multiple output channels.

Both figures use the Mermaid diagramming toolchain [18] and are rendered at ≥300dpi in the submitted document.

---

### Comment R1.2: Inconsistent bullet formatting
*"The puces are poorly formed, using two sorts of puces each time. There should be a clear balance between the sections."*

**Response:** All bullet lists throughout the manuscript have been standardized to a single consistent style. Mixed formatting has been eliminated.

---

### Comment R1.3: Figure 1 unclear
*"Figure 1: unclear (make larger, and use adequate colors)."*

**Response:** The CopernicusAI architecture diagram (now Figure 2) has been reproduced at full column width with enlarged node labels. The five-color Programming Framework palette (Red = inputs, Yellow = structured storage, Green = processing, Blue = decision points, Violet = outputs) is retained as it carries semantic meaning in the diagram. The figure caption now explicitly describes the color coding and notes the Okabe–Ito colorblind-safe palette as recommended for final production.

---

### Comment R1.4: No pagination
*"There is no pagination."*

**Response:** Page numbers have been added throughout the document.

---

### Comment R1.5: Insufficient explanation of module interactions and data flux
*"The proposal requires a more thorough explanation in order to understand relevant details (e.g., the interaction between the nine modules, the relationship between the five categories of components and the nine modules mentioned, the data flux)."*

**Response:** This has been addressed in three ways:

1. **Section 3.1** ("How the Capabilities Work Together") now includes the nine-capability coupling diagram (Figure 1) with an accompanying prose explanation of the feedback loops and governance oversight structure.
2. **Table 1** ("Operational semantics of the nine capabilities") has been added to Section 3.2, specifying for each capability what it means in an engineered system and how CopernicusAI implements it. This directly addresses the question of how abstract capability labels translate into concrete engineering obligations.
3. **Figure 3** (Section 5) shows the data flux for a single query traversing the system, mapping each stage back to the capability taxonomy.

The figure caption for the architecture diagram also clarifies that the five-color Programming Framework palette annotates diagram roles and does not map one-to-one onto the nine capabilities — a point of potential confusion that has been explicitly resolved.

---

### Comment R1.6: Subsection titles followed directly by lists
*"For a few subsections, the title is followed by a direct list of elements. I believe that each time, one or two introductory lines should be included."*

**Response:** Introductory prose has been added before every list that was previously introduced directly by a heading. This applies to the nine-capability list (Section 3), the prerequisites list (Section 4), the technology stack (Section 5), the known limitations (Section 5), the evaluation roadmap (Section 6), and the ethical considerations (Section 7).

---

### Comment R1.7: Implementation requires more clarification and figures
*"The implementation aspect seems promising, but it also requires a little more clarification (more explanation, more details, more figures)."*

**Response:** Section 5 has been substantially expanded:

- **Table 3** summarizes current system statistics (59,499 papers, 582 process diagrams, 753 videos, 90 podcasts, 11,746 papers with vector embeddings).
- **Figure 3** (query lifecycle sequence diagram) illustrates the implementation architecture in operational terms.
- A new subsection ("How a Query Moves Through the System") explains the six-stage pipeline in plain language and maps each stage to the nine-capability taxonomy.
- Known limitations are now listed explicitly with honest acknowledgment of what the system cannot yet do reliably.

---

## Reviewer 2

### Comment R2.1: Extensive validation remains necessary; extend with new experimental results
*"As the author is also writing, extensive validation remains necessary. I propose to extend the current version with new experimental results."*

**Response:** We agree entirely that extensive validation remains necessary and say so explicitly throughout the manuscript. In direct response to this request, we have added a preliminary retrieval pilot (Section 6) providing the first quantitative benchmark of the system.

The pilot evaluates lexical TF-IDF retrieval over a frozen corpus of 59,499 documents using 30 queries. Results are reported in Table 4:

| Metric | Lexical TF-IDF |
|---|---|
| Mean nDCG@10 | 0.545 |
| Mean Precision@10 | 0.323 |
| Median Reciprocal Rank | 0.500 |
| Queries with no relevant result in top-10 | 8 of 30 |

Full reproducibility artefacts — the frozen corpus export (SHA256: `3dd5e019...40ee8065`), the query list (SHA256: `8fcfe7bc...4dfdd1f`), retrieval rankings, binary relevance judgments, and the Colab notebook (seed 42, commit `77ebbe92`) — are archived at https://doi.org/10.5281/zenodo.18463303.

We are transparent about the protocol's scope: this is a single-assessor lexical pilot with no external baseline comparison. Dense-vector retrieval was deferred due to infrastructure costs. The interpretation section (Section 6) makes these limitations explicit and situates the results as a preliminary benchmark rather than a validated performance claim. Section 6 also provides a five-track evaluation roadmap for future validation work.

---

### Comment R2.2: Discussion of related work should be elaborated
*"The discussion of related work should be elaborated much more."*

**Response:** Section 2 has been substantially expanded. It now covers:

- Expert systems and their failure modes, with explicit lessons for the knowledge engine framework
- Knowledge representation and the Semantic Web, including contemporary open scholarly infrastructures (Semantic Scholar, OpenAlex)
- Dense passage retrieval and RAG, including PaperQA as a relevant recent development
- Cognitive architectures, with an explicit disclaimer about psychological fidelity
- **Cautionary cases** — a new subsection covering IBM Watson's oncology failures and the Galactica withdrawal, reinforcing the paper's core argument that scaling alone is insufficient
- A positioning paragraph explaining how CopernicusAI relates to and differs from Semantic Scholar, OpenAlex, and PaperQA

---

### Comment R2.3: How does the system understand the semantics of each capability?
*"The aforementioned capabilities concern complex concepts. Please provide a discussion of how the system is able to understand their semantics."*

**Response:** This is addressed directly in the new Table 1 (Section 3.2, "Operational Semantics of the Nine Capabilities"). For each capability, the table specifies: (1) what the capability means as an engineering obligation in a concrete system, and (2) how CopernicusAI implements it.

The accompanying prose in Section 3.2 clarifies a key point: the embedding-based similarity underlying Comparison, Connection, and Association provides a *topical geometry* — approximate proximity in semantic space — rather than logical entailment. The system does not "understand" semantics in a philosophical sense; it operationalizes each capability through specific engineering affordances. This distinction is made explicit to avoid overclaiming.

---

### Comment R2.4: Deeper discussion of the proposed architecture
*"Please provide a deeper discussion on the proposed architecture of the system."*

**Response:** The architecture discussion has been expanded across three locations in Section 5:

1. The **Architecture Overview** subsection now cross-references the nine-capability taxonomy explicitly, explaining how the five-color diagram palette maps onto system roles.
2. The **Technology Stack** subsection lists the concrete components (Python adapters, LLM-assisted structuring, Firestore, Vertex AI, Next.js, FastAPI, MCP server) with explanations of what each does.
3. The new **"How a Query Moves Through the System"** subsection and Figure 3 provide an end-to-end operational view of the architecture, showing how retrieval pooling, grounded synthesis, and multimodal delivery work together in practice.

---

## Summary of All Changes

| Issue | Location in revised manuscript |
|---|---|
| Title revised (no colon) | Title |
| Declarations section added | End of manuscript |
| Nine-capability coupling diagram added | Figure 1, Section 3.1 |
| Operational semantics table added | Table 1, Section 3.2 |
| Architecture diagram enlarged and captioned | Figure 2, Section 5 |
| Query lifecycle sequence diagram added | Figure 3, Section 5 |
| Introductory prose added before all bare lists | Sections 3, 4, 5, 6, 7 |
| Bullet formatting standardized | Throughout |
| Page numbers added | Throughout |
| Related work substantially expanded | Section 2 |
| Cautionary cases subsection added | Section 2 |
| System statistics table added | Table 3, Section 5 |
| Known limitations expanded | Section 5 |
| Preliminary retrieval pilot added | Section 6 |
| Table 4 with pilot metrics added | Section 6 |
| Evaluation reproducibility bundle archived | Zenodo: 10.5281/zenodo.18463303 |
| Five-track evaluation roadmap added | Section 6 |
| Statistics updated to May 2026 | Throughout |

We believe the revised manuscript fully addresses the concerns raised by both reviewers and the editorial office. We are grateful for the constructive feedback and look forward to the editors' assessment of the revision.

**Gary Welz**
Researcher, New Media Lab, CUNY Graduate Center
gwelz@gc.cuny.edu
May 2026
