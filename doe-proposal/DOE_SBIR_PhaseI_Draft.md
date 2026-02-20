# DOE SBIR Phase I Technical Narrative
## CopernicusAI Knowledge Engine: AI-Powered Research Briefings and Structured Metadata for Multi-Modal Scientific Discovery

---

## 1. Technical Problem and Commercial Opportunity

Scientific research output is expanding across papers, preprints, datasets, videos, and podcasts, but the tools researchers rely on are still largely siloed: literature search engines for papers, separate tools for videos, separate note systems, and limited support for structured synthesis. As a result, researchers and advanced students spend large amounts of time on orientation, filtering, cross-referencing, and iterative deepening—often redoing work others have already done informally.

The market opportunity is a subscription-grade assisted research interface that:
- Rapidly orients users to a topic
- Supports iterative refinement ("ask narrower, ask deeper")
- Exposes provenance and sources
- Converts multi-modal knowledge into structured objects that enable visualization, cross-domain comparison, and gap detection

CopernicusAI addresses this need via a working prototype that generates AI-powered research briefings in audio form, coupled to a roadmap for a structured metadata backbone and multi-modal indexing.

### Prior Work Evidence (Live Prototypes)

Foundational preprints framing this work: Welz (2026a) — *A Vision for AI-Powered Knowledge Engines...* (Zenodo DOI 10.5281/zenodo.18463304); Welz (2026b) — *The Programming Framework: A Universal Method for Process Analysis* (Zenodo DOI 10.5281/zenodo.18463442). Supporting prototypes (2024–2025):

**CopernicusAI Main Platform:**
- Hugging Face Space: garywelz/copernicusai; live production at copernicusai.fyi
- **Status:** Operational platform with multiple generated podcast episodes across several scientific disciplines, large corpus of research papers accessible via integrated APIs, multi-voice AI podcast generation with RSS feed distribution

**Programming Framework:**
- Hugging Face Space: garywelz/programming_framework
- **Status:** Universal process analysis meta-tool using LLM-powered extraction and Mermaid visualization, domain-agnostic methodology demonstrated across multiple disciplines (Welz, 2026b)

**Genome Logic Modeling Project (GLMP):**
- Hugging Face Space: garywelz/glmp
- **Status:** First specialized application of Programming Framework to biology, many biological processes mapped as interactive flowcharts, JSON-based structured data in Google Cloud Storage

**Science Video Database:**
- Hugging Face Space: garywelz/sciencevideodb
- **Status:** Curated searchable database of scientific video content with transcript-based search, scalable architecture designed for thousands to hundreds of thousands of videos

**Research Paper Metadata Database:**
- Hugging Face Space: garywelz/metadata_database
- **Status:** Centralized metadata repository prototype with AI-powered preprocessing, citation network analysis, and structured JSON storage

**Knowledge Engine Implementation (December 2025):**
- **Status:** Fully operational Knowledge Engine with a large indexed set of mathematics papers, interactive knowledge graph visualization, vector search using Vertex AI embeddings, RAG system with citation support, and unified web dashboard deployed on Google Cloud Run
- **Capabilities:** Knowledge graph with relationship extraction (citations, semantic similarity, categories), semantic search across papers/podcasts/processes, retrieval-augmented generation, content browsing, and statistics dashboard
- **Architecture:** FastAPI backend, Next.js frontend, Firestore database, Vertex AI for embeddings and LLM capabilities, Model Context Protocol (MCP) server for AI assistant integration

---

## 2. Proposed Innovation

This project advances a unified approach to AI-assisted research by combining:

### (a) Research Briefings as a Research Interface (CopernicusAI)

A collaborative platform where any user can generate, refine, and share multi-voice AI "podcast briefings" (5–10 minutes) grounded in scientific sources and metadata-aware workflows. These are not static content—they are shareable research artifacts, enabling rapid orientation and iterative deepening.

**Key Innovation:** Rather than functioning as a static content platform, CopernicusAI supports collectively generated and shared research artifacts, analogous to community-driven knowledge platforms (e.g., discussion forums), but grounded in scientific sources and metadata-aware workflows.

### (b) A Canonical Structured Metadata Layer (Phase I foundations → Phase II expansion)

A centralized metadata repository (not a file archive) providing structured JSON objects describing research objects and their relationships (papers, claims, methods, entities, media segments, diagrams). This metadata enables:
- Cross-domain mapping
- Visualization (knowledge graphs, process maps)
- Gap detection
- Reproducible tracing from a briefing back to sources

### (c) A Universal Process Visualization Framework (Programming Framework + GLMP)

A domain-agnostic method using LLMs to extract process logic from text, encode it as Mermaid diagrams stored as JSON, and iteratively refine (Welz, 2026b). GLMP demonstrates this in biology with many processes mapped, establishing feasibility for domain-specific extensions.

---

## 3. Phase I Technical Objectives

**Phase I Goal:** Deliver a validated end-to-end research briefing workflow that is measurably more useful than "generic AI chat," while establishing the metadata primitives needed for Phase II scale.

**Note on Current Implementation Status (December 2025):** A fully operational Knowledge Engine has been implemented with knowledge graph visualization, vector search, and RAG capabilities (see Prior Work section). Phase I objectives build upon this foundation, focusing on validation, refinement, and expansion of capabilities rather than initial implementation.

### Objective 1 — Evidence-Grounded Research Briefing Pipeline (CopernicusAI)

Enhance the existing CopernicusAI pipeline to better support "assisted research," not mere communication:
- Enforce minimum-source policies (e.g., multi-source grounding)
- Store structured provenance links (briefing ↔ sources)
- Improve user-driven iterative refinement (topic → subtopic → targeted question)
- Add internal quality checks (see Objective 4)

### Objective 2 — Metadata Object Generation (minimal viable schema + ingestion)

Generate structured JSON objects for:
- A paper/preprint object (IDs, abstract, claims, methods, entities, citations)
- A video object (channel, episode, transcript segments, entities)
- An audio briefing object (prompt, sources used, claims made, confidence cues)
- A diagram/process object (Mermaid + normalized nodes/edges + references)

This builds directly on the Research Paper Metadata Database and Science Video Database prototypes.

### Objective 3 — Cross-Modal Linking (papers ↔ videos ↔ briefings ↔ diagrams)

Implement minimal cross-linking so a user can navigate:
- Briefing → papers used
- Briefing → related videos (by transcript/entity overlap)
- Paper → diagrams/process maps (GLMP/Framework outputs)

### Objective 4 — Reliability: Human + AI Fact/Logic Checking Loop

Acknowledge that LLMs can hallucinate or misstate scientific claims. Phase I will implement a "trust but verify" workflow using:
- Multi-model cross-checking (e.g., one model generates, another critiques)
- Citation validation steps (DOI/arXiv verification when available)
- Structured claim extraction from briefings
- Human review affordances (flagging, annotation, corrections)

The aim is not perfect truth in Phase I; the aim is systematic detection and reduction of errors via redundancy and provenance.

---

## 4. Technical Approach and Methods

### Architecture (Phase I)

Existing production components already include:
- Multi-model LLM orchestration (Google Gemini 3, OpenAI GPT-4, Anthropic Claude 3)
- Text-to-speech synthesis (ElevenLabs TTS)
- Cloud backend infrastructure (Google Cloud Run, Firestore, Cloud Storage)
- Multi-API research integration (multiple academic databases, large paper corpus)

**Phase I Extensions:**
- Extend ingestion and metadata object creation to a consistent JSON schema
- Index metadata for search and retrieval across modalities
- Integrate diagram outputs from the Programming Framework / GLMP as structured, citeable research artifacts
- Implement cross-modal linking algorithms based on entity extraction and semantic similarity

### Data Sources

CopernicusAI already integrates multiple research databases and discovery APIs, including PubMed/NCBI (biomedical), arXiv (preprints), NASA ADS (astronomy/astrophysics), Zenodo (open science datasets), bioRxiv/medRxiv (preprints), CORE (open access), Google Scholar, and YouTube Data API (academic videos).

Phase I will focus on reliable identifiers and provenance capture rather than maximal expansion.

### Technology Stack

- **AI/ML:** Google Gemini 3, OpenAI GPT-4, Anthropic Claude 3, Vertex AI
- **Backend:** FastAPI (Python), Google Cloud Run, Firestore, Cloud Storage
- **Frontend:** Next.js 15.5.7, React Server Components
- **Media Processing:** ElevenLabs TTS, FFmpeg
- **Visualization:** Mermaid.js, JSON-based structured data

### Model Context Protocol (MCP) Server (Phase I Enhancement)

As a Phase I enhancement, we are developing a Model Context Protocol (MCP) server that exposes all knowledge engine components as queryable tools for AI assistants. This server will:

- **Enable AI Assistant Integration:** Allow AI assistants (Cursor, Claude Desktop) to directly query research papers, GLMP processes, and podcast metadata
- **Demonstrate Cross-Modal Linking:** Provide unified query interface that demonstrates cross-modal linking capabilities through concrete, testable tools
- **Developer Tools:** Provide developer-friendly API for building custom research applications and third-party integrations
- **Commercial API Foundation:** Establish foundation for commercial API offerings targeting enterprise customers and developer communities

**Technical Approach:**
The MCP server uses the Model Context Protocol standard to expose knowledge engine components as structured, queryable tools. It integrates with existing Firestore and Google Cloud Storage infrastructure, providing secure access to research papers, GLMP process diagrams, podcast metadata, and cross-component relationships. The server supports querying by entity, topic, metadata fields, and enables real-time cross-component relationship discovery.

**Commercial Value:**
The MCP server strengthens the technical innovation of the platform and provides a clear path to developer-focused commercialization. It enables third-party integrations, enterprise API access, and positions the platform as infrastructure for AI-assisted research tools. This enhancement demonstrates scalable, modular architecture that can be extended to additional data sources and commercial offerings.

**Status:** Phase 1 (Foundation) in progress. Basic server infrastructure operational. Component-specific tools being implemented incrementally over Phase I timeline.

---

## 5. Expected Phase I Deliverables

1. **Operational "assisted research briefing" workflow** with shareable briefings and structured provenance
2. **Minimal canonical metadata schema + object generator** for papers/videos/briefings/diagrams
3. **Cross-modal linking prototype** demonstrating navigation between artifacts
4. **Quality & reliability subsystem** implementing multi-checker logic and human review loops
5. **Evaluation report** documenting Phase I metrics and outcomes

---

## 6. Phase I Evaluation Plan

We will evaluate on:

1. **Grounding rate:** Fraction of briefing claims that have traceable supporting sources
2. **Citation integrity:** Percent of cited items resolvable to stable identifiers (DOI, arXiv ID, etc.)
3. **User time-to-orientation:** Time for a user to reach a working understanding of a topic (self-report + task-based)
4. **Error detection yield:** Number of factual/logic errors caught by AI checkers + users over a set of briefings
5. **Reuse & sharing:** Rate at which users share and iteratively refine briefings

**Success Criteria:**
- Grounding rate > 90% for all briefing claims
- Citation integrity > 95% for resolvable identifiers
- Measurable reduction in time-to-orientation compared to baseline (literature search + reading)
- Error detection system identifies and flags > 80% of test-set errors
- User engagement metrics demonstrating active sharing and refinement

---

## 7. Commercialization Path (Phase I → Phase II)

**Phase I** strengthens the product as a subscription "personal research briefer."

**Phase II** scales:
- Research Papers Metadata Database into a larger corpus
- Science Video DB toward a large catalog
- More robust knowledge graph and gap detection
- Institutional tiers (labs, classrooms, research groups)
- Developer APIs for third-party tooling

**Market Strategy:**
- Individual researcher subscriptions (Phase I validation)
- Institutional licenses for universities and research labs (Phase II)
- API access for third-party research tools and platforms
- Integration partnerships with academic publishers and database providers

---

## 8. Intellectual Merit and Broader Impacts

### Intellectual Merit

This project advances the state of the art in:
- AI-assisted scientific research interfaces
- Multi-modal knowledge integration and synthesis
- Structured metadata representation for scientific artifacts
- Cross-domain knowledge mapping and visualization
- Human-AI collaborative research workflows

### Broader Impacts

- **Scientific Research:** Enables more efficient research workflows, reducing time spent on orientation and increasing time for discovery
- **Education:** Provides accessible tools for students and researchers to understand complex scientific topics through multi-modal learning
- **Open Science:** Promotes reproducible research through structured metadata and provenance tracking
- **Interdisciplinary Discovery:** Facilitates cross-domain connections and pattern recognition across scientific disciplines
- **Economic Impact:** Creates a sustainable business model supporting continued innovation in research tools

---

## 9. References and Prior Work Citations

**Preprints (Zenodo, 2026):**

Welz, G. (2026a). *A Vision for AI-Powered Knowledge Engines: A Framework for Systematic Knowledge Discovery and Integration*. Preprint. Zenodo. DOI 10.5281/zenodo.18463304

Welz, G. (2026b). *The Programming Framework: A Universal Method for Process Analysis*. Preprint. Zenodo. DOI 10.5281/zenodo.18463442

**Supporting prototypes (Hugging Face Spaces, 2024–2025):**

Welz, G. (2024–2025). *CopernicusAI: AI-Generated Audio Briefings as a Research Interface*. Hugging Face Space: garywelz/copernicusai

Welz, G. (2024–2025). *The Programming Framework: A Universal Method for Process Analysis*. Hugging Face Space: garywelz/programming_framework

Welz, G. (2024–2025). *Genome Logic Modeling Project (GLMP): A Microscope for Biological Processes*. Hugging Face Space: garywelz/glmp

Welz, G. (2024–2025). *Research Paper Metadata Database*. Hugging Face Space: garywelz/metadata_database

Welz, G. (2024–2025). *Science Video Database*. Hugging Face Space: garywelz/sciencevideodb

**Note on Publications.** The PI has posted two preprints (Welz, 2026a, 2026b) framing this work: a Knowledge Engine vision and the Programming Framework. Additional draft manuscripts are in preparation but have not yet been submitted for publication. The existing operational prototypes and these preprints serve as primary evidence of prior work and technical feasibility.

---

## 10. Administrative Details

### Business Entity Information

**Business/Applicant Name (as used in USGrants):** Welz, Gary

**Unique Entity Identifier (UEI):** KX9CBZB6NMV7

**DUNS Number:** 017240183

**CAGE Code:** 8BWB1

**USGrants Application Label:** WELZ,-GARY-017240183-2025-12-17

**Business Description:** Subscription-based online services including an AI podcast generation system and scientific metadata/visualization databases.

**Business Type:** Small Business (SBIR Entrepreneur Track)

**One-Liner:** Welz, Gary is a small business developing AI-driven tools for scientific research synthesis, structured metadata, and research briefing interfaces.

### Principal Investigator

**Name:** Gary Welz

**Title:** Principal Investigator / Business Owner

**Address:** 460 West 24th Street, #3A, New York, NY 10011, United States

**Phone:** 917-593-2537

**Email:** garywelz@gmail.com

### Academic Affiliations (Background Context)

**John Jay College of Criminal Justice (CUNY)**
- Department: Mathematics and Computer Science
- Status: Retired Faculty

**CUNY Graduate Center**
- Affiliation: New Media Lab (Affiliate)
- Contact: garywelz@gmail.com

**Note:** Academic affiliations are provided for background context. This proposal is submitted under the SBIR entrepreneur track as a small business entity.

### Prior Work / Public Artifacts

All prior work is publicly accessible and documented:

1. **Copernicus AI (Main Platform)** — Hugging Face Space: garywelz/copernicusai; live production at copernicusai.fyi. Status: Operational platform with multiple generated podcast episodes, large research paper corpus accessible.

2. **Programming Framework** — Hugging Face Space: garywelz/programming_framework. Status: Universal process analysis meta-tool demonstrated across multiple disciplines (Welz, 2026b).

3. **Genome Logic Modeling Project (GLMP)** — Hugging Face Space: garywelz/glmp. Status: Many biological processes mapped as interactive flowcharts.

4. **Science Video Database** — Hugging Face Space: garywelz/sciencevideodb. Status: Curated searchable database with transcript-based search.

5. **Research Paper Metadata Database** — Hugging Face Space: garywelz/metadata_database. Status: Centralized metadata repository prototype.

### Additional Information

**Completed Sections (see separate documents):**
- ✅ Principal Investigator Biographical Sketch: `DOE_SBIR_Biographical_Sketch_Welz.md`
- ✅ Budget and Budget Justification ($250,000): `DOE_SBIR_BUDGET_PhaseI.md`
- ✅ Facilities, Equipment, and Other Resources: `DOE_SBIR_Facilities_Equipment.md`
- ✅ Data Management and Sharing Plan: `DOE_SBIR_DataManagement_Plan.md`

**Action Items Required:**
- ✅ Research Security Training (DOE requirement effective May 1, 2025): Completed — SECURE Center CTM 1.2; certificate `CTM 1.2.pdf` to be included in submission.
- ✅ SAM.gov registration ACTIVE; UEI KX9CBZB6NMV7 (included above)
- ⚠️ Key Personnel Biographical Sketches (if applicable)
  - Only needed if you have key personnel beyond PI

---

**Document Status:** Technical narrative complete; Phase 1 citation/narrative alignment done; Research Security Training complete (CTM 1.2). Awaiting FOA formatting and submission.

