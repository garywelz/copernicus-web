# NSF CISE CORE (IIS) Proposal
## CopernicusAI Knowledge Engine: Assisted Research via AI Briefings, Multi-Modal Metadata, and Process Visualization

**Program:** CISE Core Programs - Information and Intelligent Systems (IIS)
**Track Alignment:** Human-Centered AI (HAI), Foundations, Systems
**Principal Investigator:** Gary Welz

---

## Project Summary (1 Page)

### Project Title
CopernicusAI Knowledge Engine: Assisted Research via AI Briefings, Multi-Modal Metadata, and Process Visualization

### Overview

This project develops and studies an AI-enabled "assisted research" platform that helps researchers and advanced students rapidly orient to a topic, iteratively deepen questions, and connect knowledge across scientific domains using traceable sources and structured metadata—a system that systematically transforms information into knowledge (Welz, 2026a). The core research idea is to treat AI-generated briefings—especially interactive audio briefings—as a research interface rather than as static science communication. The platform extends standard retrieval-augmented generation (RAG) with structured analysis, explicit connection discovery, cross-modal integration, and provenance, supporting both human reasoning and machine-assisted analysis. It links text, audio, video, and diagrammatic representations through a unified metadata layer that enables provenance, visualization, and systematic identification of knowledge gaps.

The work builds on existing, public prototypes created by the PI: CopernicusAI (live research briefing platform) and four component Hugging Face Spaces supporting process visualization, biological process mapping, video transcript search, and research paper metadata management:

- **CopernicusAI:** https://huggingface.co/spaces/garywelz/copernicusai and https://www.copernicusai.fyi
- **Programming Framework:** https://huggingface.co/spaces/garywelz/programming_framework
- **Genome Logic Modeling Project (GLMP):** https://huggingface.co/spaces/garywelz/glmp
- **Science Video Database:** https://huggingface.co/spaces/garywelz/sciencevideodb
- **Research Paper Metadata Database:** https://huggingface.co/spaces/garywelz/metadata_database

### Intellectual Merit

The project contributes to CISE/IIS by advancing methods for human-centered AI-assisted research workflows grounded in multi-source evidence and structured representations. Key research contributions include:

1. **Research briefings as an interactive research interface:** Design and evaluation of "prompt → briefing → refinement" loops that support progressive narrowing and deepening of technical questions, enabling personalized orientation and exploration.

2. **Unified metadata objects across modalities:** Creation of structured JSON representations capturing provenance, entities, methods, claims, and cross-references for papers, videos (via transcripts), audio briefings, process diagrams, scientific graphics (photographs, telescope/microscope images, illustrations, computer graphics), and audio data files. This representation supports reproducibility and enables algorithmic analysis such as clustering, cross-domain comparison, and gap detection. The system acknowledges that audio serves dual roles: as a communication medium (podcasts) and as scientific data (recordings, sonifications, experimental audio data).

3. **Reliable AI output via multi-checker workflows and collaborative validation:** Explicit acknowledgment that LLM outputs can contain errors. The project develops a practical reliability strategy using multiple AI and human "fact/logic checkers," plus provenance enforcement, claim extraction, and citation verification mechanisms. Additionally, the project implements collaborative validation where multiple users (graduate and undergraduate students) test, verify, and refine AI-generated content, creating a collective intelligence layer that improves trustworthiness through peer review and collective verification.

4. **Process visualization as computable artifacts:** Leveraging an existing Programming Framework that converts textual process descriptions into Mermaid diagrams stored as JSON, enabling iterative refinement and comparison, and demonstrated in GLMP with biological processes. The Framework employs AI consensus validation (critic model review) and structured validation checklists, with accessibility support through node shape alternatives for colorblind users.

Collectively, these components create a research platform where knowledge is not only summarized but mapped, linked, and validated through computable metadata and reviewable provenance—supporting both human reasoning and machine-assisted analysis and aligning with the broader Knowledge Engine evaluation agenda (retrieval quality, connection validity, user-reported value).

### Broader Impacts

The platform supports broader impacts in education and research infrastructure by providing a scalable system for research orientation and exploration, lowering barriers for students, educators, and interdisciplinary researchers. The existing system was developed with limited resources (single investigator, modest infrastructure), demonstrating that sophisticated Knowledge Engine–style systems are feasible for individuals and small teams; NSF support will enable scaling, rigorous evaluation, and broader access through open tools and student involvement. Users can generate and share research briefings and associated artifacts (metadata, diagrams, linked sources) within their communities, enabling collective learning dynamics while remaining grounded in scientific sources. The system's focus on provenance, validation, and multi-checker review promotes responsible use of AI in scientific contexts. A key innovation is the integration of collaborative validation mechanisms, where student users participate in alpha and beta testing, creating podcasts, verifying AI outputs, and contributing to collective knowledge building. This approach not only improves system usability but also establishes new models for collaborative intelligence in AI-assisted research. Public prototypes and documentation will remain accessible, supporting reproducible methods and future community contributions.

---

## 1. Introduction and Motivation

### 1.1 Problem Statement

Scientific research output is expanding exponentially across multiple modalities: research papers, preprints, datasets, videos, podcasts, and interactive visualizations. However, the tools researchers rely on remain largely siloed—separate literature search engines for papers, distinct tools for videos, isolated note systems, and limited support for structured synthesis across modalities. This fragmentation creates significant inefficiencies:

- **Time-to-Orientation:** Researchers spend substantial time simply orienting to a new topic, often redoing work others have already done informally
- **Cross-Modal Disconnect:** Knowledge exists across text, audio, video, and visual formats, but connections between these modalities are difficult to establish and navigate
- **Provenance Gaps:** Tracing claims back to sources across different media types is challenging, limiting reproducibility and trust
- **Iterative Refinement Limitations:** Current tools don't effectively support the iterative "ask narrower, ask deeper" workflow that characterizes effective research

### 1.2 Research Opportunity

The emergence of large language models (LLMs) and multi-modal AI systems presents an opportunity to create unified research interfaces that bridge these gaps. However, simply applying generic AI chat interfaces to research is insufficient. Ambitious goals—such as rapid orientation to unfamiliar literatures and cross-domain discovery—require comprehensive integrated systems (scaffolding, tools, processes), not merely more powerful models (Welz, 2026a). This project builds that scaffolding. What's needed is:

- **Evidence-Grounded Interfaces:** Research tools that enforce multi-source grounding and maintain explicit provenance
- **Structured Metadata:** Unified representations that enable algorithmic analysis and cross-modal linking
- **Reliability Mechanisms:** Practical strategies for detecting and reducing AI errors in scientific contexts
- **Computable Artifacts:** Research outputs that are not just human-readable but machine-analyzable

### 1.3 Prior Work and Foundation

**Conceptual grounding.** This project is framed by the "Knowledge Engine" concept: a system that systematically transforms information into knowledge through integrated capabilities—ingestion, digestion, analysis, calculation, comparison, connection, association, analogy, and multi-modal communication (Welz, 2026a). The proposal's objectives map to this taxonomy: briefings and podcasts embody *communication*; metadata, RAG, and knowledge graphs implement *ingestion*, *digestion*, and *connection*; multi-checker workflows support *analysis* and reliability; process diagrams provide structured representations across *analysis*, *connection*, and *communication*. The proposed work moves from existence proof (operational prototypes) to validated effectiveness through rigorous evaluation.

This project builds directly on existing, publicly accessible prototypes demonstrating technical feasibility:

**CopernicusAI Platform (Operational):**
- Live system: https://www.copernicusai.fyi
- Generated podcast episodes across multiple scientific disciplines
- Integration with multiple academic databases
- Multi-voice AI podcast generation with RSS distribution
- Evidence-based content requiring minimum 3 research sources

**Programming Framework:**
- Universal process analysis meta-tool using LLM-powered extraction and Mermaid visualization
- Domain-agnostic methodology demonstrated across biology, chemistry, mathematics, physics, and computer science
- Structured JSON metadata with version control and provenance tracking
- Suggested five-category color-coding system (Red/Yellow/Green/Blue/Violet) with accessibility alternatives (node shapes for colorblind users)
- AI consensus validation workflow using critic models to reduce human review burden
- Complete prompt templates and validation methodology documented

**GLMP:**
- Biological processes mapped as interactive flowcharts
- JSON-based structured data in Google Cloud Storage
- Demonstrates feasibility of process visualization as computable artifacts

**Science Video Database:**
- Curated searchable database with transcript-based search
- Scalable architecture for large video catalogs

**Research Paper Metadata Database:**
- Centralized metadata repository prototype
- AI-powered preprocessing and citation network analysis

**Knowledge Engine Implementation (December 2025):**
- **Fully Operational Knowledge Graph**: Interactive visualization system with indexed papers, relationship extraction (citations, semantic similarity, categories), and graph query capabilities. Live system accessible at https://copernicus-frontend-phzp4ie2sq-uc.a.run.app/knowledge-engine
- **Vector Search**: Semantic search using Vertex AI embeddings across papers, podcasts, and processes with distance-based similarity ranking
- **RAG System**: Retrieval-augmented generation with citation support, context retrieval, and multi-modal content integration
- **Unified Web Dashboard**: Production-ready interface deployed on Google Cloud Run with knowledge map visualization, search, RAG queries, content browsing, and statistics
- **MCP Integration**: Model Context Protocol server enables AI assistant integration with programmatic access to all knowledge engine capabilities

---

## 2. Research Objectives and Goals

### 2.1 Primary Research Objectives

**Objective 1: Research Briefings as Interactive Research Interface**
- Design and implement "prompt → briefing → refinement" interaction loops
- Evaluate effectiveness for rapid topic orientation and iterative deepening
- Study user behavior and learning outcomes with briefing-based research workflows

**Objective 2: Unified Multi-Modal Metadata Representation**
- Develop structured JSON schema for papers, videos, briefings, and diagrams
- Implement metadata object generation and ingestion pipelines
- Enable cross-modal linking and algorithmic analysis

**Objective 3: Reliability and Trust Mechanisms**
- Design and implement multi-checker workflows (AI + human)
- Develop claim extraction and citation verification systems
- Evaluate error detection and reduction effectiveness

**Objective 4: Process Visualization as Computable Artifacts**
- Extend Programming Framework for broader domain coverage
- Integrate process diagrams into unified metadata layer
- Enable comparison and refinement of process representations

**Objective 5: Collaborative Validation and User Testing**
- Implement alpha and beta testing programs with graduate and undergraduate students
- Design collaborative validation mechanisms for AI-generated content
- Study collective intelligence patterns in user verification workflows
- Evaluate usability and effectiveness of collaborative refinement processes

### 2.2 Research Questions

1. How do AI-generated research briefings compare to traditional literature search for time-to-orientation and knowledge acquisition?
2. What metadata representations best support cross-modal linking and algorithmic analysis?
3. What reliability mechanisms most effectively reduce AI errors in scientific contexts?
4. How can process visualizations be integrated into broader research workflows?
5. What interaction patterns support effective iterative refinement of research questions?
6. How does collaborative validation by multiple users improve AI output reliability and trustworthiness?
7. What usability patterns emerge from student-led alpha and beta testing of research briefing workflows?

---

## 3. Technical Approach

### 3.1 Research Briefing Interface Design

**Current State:** CopernicusAI platform generates multi-voice AI podcasts from research topics with multi-source grounding.

**Research Extensions:**
- **Iterative Refinement Loops:** Design interfaces supporting progressive question narrowing
- **Provenance Visualization:** Interactive displays showing briefing → source relationships
- **Sharing and Collaboration:** Mechanisms for sharing briefings and collaborative refinement
- **Evaluation Framework:** Metrics for assessing briefing effectiveness and user learning
- **Exploratory direction:** If resources and evaluation capacity permit, study whether character/ethos-guided retrieval (e.g., emphasis on paradigm-challenging or empirical content) improves orientation or discovery (Welz, 2026a).

**CISE Track Alignment:** **HAI (Human-Centered AI)** - Focus on human-AI collaboration, interface design, and evaluation

### 3.2 Unified Metadata Representation

**Current State:** Prototype metadata databases for papers and videos exist separately. **Additionally, a fully operational Knowledge Engine has been implemented (December 2025) with:**
- **Knowledge Graph**: Interactive visualization system with indexed papers, relationship extraction (citations, semantic similarity, categories), and graph query capabilities deployed at https://copernicus-frontend-phzp4ie2sq-uc.a.run.app/knowledge-engine
- **Vector Search**: Semantic search using Vertex AI embeddings across papers, podcasts, and processes
- **RAG System**: Retrieval-augmented generation with citation support and multi-modal content integration
- **Unified Dashboard**: Production-ready web interface with knowledge map visualization, search, RAG queries, content browsing, and statistics

The system extends standard RAG (Lewis et al., 2020) with structured analysis, explicit connection discovery, cross-modal integration, and provenance—positioning it as "extended RAG" within the Knowledge Engine framework (Welz, 2026a).

**Research Extensions:**
- **Canonical Schema Design:** Develop unified JSON schema capturing:
  - Papers: IDs, abstracts, claims, methods, entities, citations
  - Videos: Transcripts, segments, entities, temporal metadata
  - Briefings: Prompts, sources, claims, confidence cues
  - Diagrams: Mermaid syntax, nodes, edges, references
    - Required metadata fields: id, title, description, mermaid, version, prompt_version, llm_version (for reproducibility)
    - Optional but recommended: domain, category, source, entities, color_distribution, annotations, created_by, reviewed_by
  - Scientific Graphics: Photographs, telescope/microscope images, illustrations, computer graphics with metadata (source, instrument, parameters, annotations)
  - Audio Data: Recordings, sonifications, experimental audio data (distinct from audio briefings/podcasts which are communication media)
- **Audio as Dual-Mode Data:** Acknowledge that audio serves both as communication medium (podcasts, briefings) and as scientific data (experimental recordings, sonifications, acoustic measurements). The metadata schema will distinguish between these modes while enabling cross-linking.
- **Cross-Modal Linking Algorithms:** Entity extraction and semantic similarity for linking across all modalities including graphics and audio data
- **Knowledge Graph Construction:** Build relationships between metadata objects including graphics-to-paper, audio-to-video, and other cross-modal connections
- **Gap Detection Methods:** Algorithmic identification of knowledge gaps across all data types

**CISE Track Alignment:** **Foundations** - Representation learning, metadata models, knowledge graphs

**Future Data Modalities:**
While the current proposal focuses on papers, videos, briefings, and diagrams, the architecture is designed to accommodate additional data types:
- **Scientific Graphics Database:** Future component will include databases of scientific graphics including photographs, telescope images, microscope images, illustrations, and computer-generated graphics. These will be integrated into the unified metadata layer with appropriate metadata (instrument parameters, experimental conditions, annotations).
- **Audio Data Management:** Beyond audio briefings (communication), the system will support audio as scientific data (experimental recordings, sonifications, acoustic measurements). This dual-mode approach recognizes audio's role both as a research communication tool and as primary scientific data.

**CISE Track Alignment:** **Foundations** - Multi-modal representation, **Systems** - Scalable data architecture

### 3.3 Reliability and Trust Mechanisms

**Current State:** Basic multi-model architecture exists; reliability mechanisms need development.

**Research Extensions:**
- **Multi-Checker Workflows:**
  - Model A generates, Model B critiques
  - Human review affordances
  - Structured claim extraction
- **Citation Verification:**
  - DOI/arXiv ID validation
  - Source authenticity checks
  - Citation integrity metrics
- **Error Detection Systems:**
  - Factual error identification
  - Logical inconsistency detection
  - Confidence scoring

**CISE Track Alignment:** **HAI** - Trust, reliability, human-AI collaboration

### 3.4 Collaborative Validation and User Testing

**Research Component:**
A critical innovation of this project is the integration of collaborative validation mechanisms through structured user testing programs. Graduate and undergraduate students will participate in alpha and beta testing phases, using the platform to create research briefings, generate podcasts, and verify AI outputs.

**Research Extensions:**
- **Alpha Testing (Year 1):** Small cohort of students (2 graduate, 3 undergraduate) test core functionality, create initial briefings, provide usability feedback
- **Expanded Beta Testing (Year 2):** Larger cohort (3 graduate, 5 undergraduate) tests enhanced features, participates in collaborative validation workflows, creates shared knowledge artifacts
- **Full Beta and Validation (Year 3):** Full cohort continues testing while focusing on collaborative validation patterns, collective verification of AI outputs, and refinement workflows

**Collaborative Validation Mechanisms:**
- **Peer Review Workflows:** Multiple users verify and refine the same AI-generated briefing
- **Collective Intelligence Patterns:** Study how groups of users identify and correct errors
- **Consensus Building:** Mechanisms for resolving conflicts in user verification
- **Reputation Systems:** Track user contributions to validation and refinement
- **Shared Artifacts:** Users create and share briefings, creating a collective knowledge base

**Research Questions:**
- How does collaborative validation improve AI output reliability compared to single-user verification?
- What patterns emerge in collective error detection and correction?
- How do usability issues identified by students differ from those identified by researchers?
- What collaborative workflows are most effective for knowledge building?

**CISE Track Alignment:** **HAI** - Human-AI collaboration, collective intelligence, user-centered design

### 3.5 Process Visualization Integration

**Current State:** Programming Framework and GLMP demonstrate feasibility with biological processes mapped as structured, computable flowcharts.

**Methodology:**
The Programming Framework employs a systematic five-stage pipeline: (1) Process scoping and selection with granularity guidelines (high-level 5-10 nodes for educational overviews vs. detailed 20+ nodes for technical protocols), (2) LLM-based structure extraction using domain-agnostic but process-aware prompts, (3) Mermaid diagram generation with suggested five-category color-coding system, (4) JSON storage with required metadata fields (id, title, description, mermaid, version, prompt_version, llm_version) and optional fields for domain classification and provenance, (5) Iterative refinement with AI consensus step (critic model review) followed by human validation.

**Validation Approach:**
The Framework employs multi-stage validation: (1) AI consensus step where a second LLM (critic model) reviews the first LLM's output, flagging errors before human review, (2) Structured validation checklist (completeness, accuracy, consistency, clarity), (3) Domain expert review for high-stakes content, (4) Version control and provenance tracking. This approach reduces human labor cost while maintaining quality through multi-model validation.

**Accessibility:**
Beyond color-coding, the Framework supports node shape alternatives for colorblind accessibility: ovals for triggers/inputs, rectangles for structures, hexagons for operations, cylinders for intermediates, trapezoids for outputs. This shape-based encoding provides secondary identifiers independent of color, addressing accessibility concerns while maintaining visual distinction.

**Research Extensions:**
- **Domain Extension:** Apply framework beyond biology (already demonstrated in chemistry, mathematics, physics, computer science)
- **Metadata Integration:** Link process diagrams to papers, briefings, videos
- **Comparison Tools:** Enable side-by-side process comparison
- **Refinement Workflows:** Support iterative improvement of process representations

**CISE Track Alignment:** **Foundations** - Structured representations, **Systems** - Integration pipelines

### 3.6 System Architecture

**Current Infrastructure:**
- Multi-model LLM orchestration (Google Gemini 3, OpenAI GPT-4, Anthropic Claude 3)
- Cloud backend (Google Cloud Run, Firestore, Cloud Storage)
- Frontend (Next.js, React Server Components)
- Multi-API research integration

**Research Extensions:**
- Enhanced metadata ingestion pipelines
- Cross-modal linking infrastructure
- Quality assurance subsystems
- Evaluation and analytics systems

**CISE Track Alignment:** **Systems** - Pipeline orchestration, scalable indexing, multi-modal ingestion

### 3.7 Model Context Protocol (MCP) Server Integration

**Enhancement:** As an enhancement to the core platform, we are implementing a Model Context Protocol (MCP) server that exposes all knowledge engine components as queryable tools for AI assistants. This server enables:

- **Direct AI Assistant Access:** AI assistants (Cursor, Claude Desktop) can directly query research paper metadata, GLMP process diagrams, and podcast content
- **Unified Query Interface:** Single interface for querying across all components (papers, podcasts, processes, videos)
- **Real-Time Cross-Component Linking:** Enables relationship discovery and cross-modal queries in real-time
- **Developer-Friendly API:** Provides programmatic access for building custom research tools and integrations

**Technical Implementation:**
The MCP server uses the Model Context Protocol standard to expose knowledge engine components as structured tools. It integrates with existing Firestore and Google Cloud Storage infrastructure, providing secure, authenticated access to all data sources. The server supports querying by entity, topic, metadata fields, and cross-component relationships.

**Research Contributions:**
The MCP server demonstrates practical implementation of "computable artifacts" by making all knowledge engine data programmatically accessible, supporting both human researchers and AI-assisted workflows. This enhancement strengthens the platform's utility as infrastructure for AI-assisted research and enables new forms of collaborative validation where AI assistants can query and verify data across components. Standard interfaces like MCP address the "future needs" identified in the Knowledge Engine vision—interoperability, shared access, and common interfaces for knowledge systems (Welz, 2026a).

**Status:** Phase 1 (Foundation) in progress. Full implementation expected within 3-4 weeks, with component-specific tools being added incrementally.

**CISE Track Alignment:** **Foundations** - Structured representations, **Systems** - Integration infrastructure, **HAI** - Human-AI collaboration tools

---

## 4. Research Methods and Evaluation

### 4.1 Evaluation Framework

**User Studies:**
- **Time-to-Orientation:** Measure time for users to reach working understanding of topics
- **Knowledge Acquisition:** Assess learning outcomes from briefing-based workflows
- **Iterative Refinement:** Study effectiveness of refinement loops
- **Cross-Modal Navigation:** Evaluate usability of cross-modal linking

**System Metrics:**
- **Grounding Rate:** Fraction of briefing claims with traceable sources
- **Citation Integrity:** Percent of citations resolvable to stable identifiers
- **Error Detection Yield:** Errors caught by multi-checker systems
- **Metadata Quality:** Completeness and accuracy of generated metadata objects

**Algorithmic Evaluation:**
- **Cross-Modal Linking Accuracy:** Precision/recall of entity-based links
- **Gap Detection Effectiveness:** Validation of identified knowledge gaps
- **Process Comparison:** Accuracy of process diagram comparisons

The evaluation framework aligns with the broader Knowledge Engine evaluation agenda (retrieval quality, connection validity, user-reported value) outlined in the vision paper (Welz, 2026a).

### 4.1.1 Success Criteria

The project will be considered successful if the following quantitative thresholds are met:

**System Performance:**
- **Grounding Rate:** >= 90% of briefing claims have traceable supporting sources
- **Citation Integrity:** >= 95% of citations are resolvable to stable identifiers (DOI, arXiv ID, etc.)
- **Error Detection Yield:** Multi-checker systems identify and flag >= 80% of test-set errors
- **Metadata Quality:** >= 85% completeness score for generated metadata objects
- **Cross-Modal Linking Accuracy:** >= 75% precision and >= 70% recall for entity-based links

**User Experience:**
- **Time-to-Orientation:** Measurable reduction (>= 30%) compared to baseline traditional literature search methods
- **Usability Score:** System Usability Scale (SUS) score >= 70 (above average)
- **User Satisfaction:** >= 80% of users report satisfaction with briefing quality and usefulness
- **Collaborative Validation Effectiveness:** Collaborative verification identifies >= 15% more errors than single-user verification

**Adoption and Engagement:**
- **User Engagement:** >= 60% of student testers create and share at least one briefing
- **Iterative Refinement:** >= 40% of briefings undergo at least one refinement iteration
- **Platform Usage:** Average session duration >= 20 minutes for research orientation tasks

**Baseline Comparisons:**
The project will compare against established research tools:
- **Traditional Literature Search:** Google Scholar, Semantic Scholar, PubMed (for baseline time-to-orientation)
- **AI Research Tools:** Elicit, Research Rabbit, Consensus (for comparison of AI-assisted workflows)
- **Knowledge Management:** Zotero, Mendeley (for comparison of metadata and organization approaches)

Baseline data will be collected through controlled studies where participants complete identical research orientation tasks using both traditional tools and the CopernicusAI platform.

### 4.2 Research Methodology

**Design:**
- Mixed-methods approach combining quantitative metrics with qualitative user studies
- Comparative studies: briefing-based workflows vs. traditional literature search
- Longitudinal studies: user behavior over time with the platform
- Collaborative validation studies: multi-user verification and refinement patterns

**Participants:**
- **Paid Student Testers:** Graduate and undergraduate students participating in alpha/beta testing programs (compensated for their time)
- Researchers and advanced students across scientific disciplines
- Interdisciplinary research teams
- Educational contexts (classrooms, research groups)

**User Testing Phases:**
- **Year 1 - Alpha Testing:** 2 graduate + 3 undergraduate students test core functionality, create initial briefings, provide structured feedback
- **Year 2 - Expanded Beta:** 3 graduate + 5 undergraduate students test enhanced features, participate in collaborative validation, create shared artifacts
- **Year 3 - Full Beta:** Continued testing with focus on collaborative validation patterns and collective intelligence mechanisms

**Data Collection:**
- Usage analytics (anonymized)
- User interviews and surveys
- Task-based evaluations
- System performance metrics
- Collaborative validation patterns (who verifies what, consensus building, error detection)
- Usability metrics from student testers
- Podcast creation and sharing patterns

### 4.2.1 Human Subjects Research and IRB Compliance

**Research Nature:**
This project involves human subjects research in the form of usability testing and feedback collection. Participants will use the research platform in a naturalistic setting and provide feedback on their experience. This is **low-risk research** that does not involve experimental interventions, medical procedures, or any activities that could cause physical or psychological harm. Participants are simply using technology tools and providing feedback, similar to standard software usability testing.

**IRB Compliance:**
- The project will comply with all applicable Institutional Review Board (IRB) requirements
- IRB approval will be obtained prior to any data collection involving human participants
- If the PI's institution does not have an IRB, approval will be sought through an appropriate external IRB or through the NSF's designated IRB process
- All user studies will be conducted in accordance with ethical guidelines for human subjects research

**Validation Methodology (Adapted from Programming Framework):**
The project employs a structured validation approach for AI-generated content:

1. **AI Consensus Step:** A second LLM (critic model) reviews the first LLM's output, flagging potential errors, missing steps, or inconsistencies before human review. This reduces human labor cost while maintaining quality.

2. **Structured Validation Checklist:**
   - Completeness: Are all key steps/elements from the source represented?
   - Accuracy: Do relationships and flows match source descriptions?
   - Consistency: Are color assignments and metadata consistent?
   - Clarity: Is the content readable and interpretable?

3. **Domain Expert Review:** For high-stakes scientific content, domain experts validate correctness. For educational content, knowledgeable reviewers perform validation.

4. **Provenance Tracking:** All content includes metadata about creation, review, and validation, with source references enabling verification.

5. **Version Control:** All changes are tracked with version history, enabling rollback if errors are discovered later.

**Participant Protection:**
- **Informed Consent:** All participants will provide informed consent, clearly explaining the research purpose, data collection methods, and their rights
- **Voluntary Participation:** Participation is entirely voluntary; participants may withdraw at any time
- **Anonymization:** All usage data will be anonymized; no personally identifiable information will be stored or published
- **Data Protection:** User data will be stored securely and used only for research purposes as described in the consent form
- **Compensation:** Student participants will be compensated for their time at fair market rates (as detailed in the budget)

**Risk Assessment:**
The research poses minimal risk to participants. The primary activities are:
- Using a web-based research platform (similar to using any online tool)
- Creating research briefings and podcasts (creative/educational activities)
- Providing feedback through surveys and interviews (standard usability testing)
- Participating in collaborative validation (peer review activities)

No risks beyond those encountered in normal use of online research tools are anticipated.

### 4.2.2 Data Privacy and Protection

**Data Anonymization:**
- All usage analytics will be collected in anonymized form
- User IDs will be replaced with anonymized identifiers
- No personally identifiable information (PII) will be stored with usage data
- User interviews and surveys will be anonymized before analysis

**Data Retention:**
- Research data will be retained for the duration of the project plus 3 years (as required by NSF)
- After the retention period, data will be securely destroyed
- Anonymized datasets may be preserved for future research (with appropriate consent)

**User Consent:**
- Clear consent forms explaining data collection, use, and retention
- Option to opt out of data collection while still using the platform
- Right to request data deletion (subject to research requirements)

**Security Measures:**
- Encrypted data storage
- Secure transmission (HTTPS/TLS)
- Access controls limiting data access to research team
- Regular security audits

**Compliance:**
- GDPR compliance for international users (if applicable)
- FERPA compliance for educational data (if applicable)
- Institutional data protection policies

---

## 5. Expected Outcomes and Deliverables

### 5.1 Research Deliverables

1. **Enhanced Research Briefing Platform**
   - Iterative refinement interfaces
   - Provenance visualization tools
   - Sharing and collaboration features

2. **Unified Metadata Schema and System**
   - Canonical JSON schema for multi-modal research objects
   - Metadata generation and ingestion pipelines
   - Cross-modal linking implementation

3. **Reliability and Trust Mechanisms**
   - Multi-checker workflow system
   - Citation verification tools
   - Error detection and reporting

4. **Process Visualization Integration**
   - Extended Programming Framework
   - Integration with metadata layer
   - Comparison and refinement tools

5. **Evaluation Results**
   - User study findings
   - System performance metrics
   - Algorithmic evaluation results
   - Collaborative validation patterns and effectiveness
   - Usability findings from alpha/beta testing

6. **Collaborative Validation Framework**
   - Multi-user verification workflows
   - Collective intelligence patterns
   - Peer review mechanisms
   - Shared knowledge artifacts created by student testers

### 5.2 Publicly Accessible Resources

- Enhanced CopernicusAI platform (publicly accessible)
- Updated Hugging Face Spaces with research results
- Open-source components (metadata schemas, tools)
- Technical documentation and publications
- Evaluation datasets (anonymized)

### 5.3 Dissemination Plan

**Peer-Reviewed Publications:**
- **Target Venues:**
  - Human-Computer Interaction: CHI, CSCW, UIST
  - AI/ML: NeurIPS, ICML, ACL, AAAI
  - Information Systems: SIGIR, WWW, JCDL
  - Educational Technology: L@S, ICER
- **Open Access Commitment:** All publications will be made available through open access channels (arXiv preprints, institutional repositories, or open access journals)
- **Timeline:** At least 2-3 peer-reviewed publications per year, with first publication in Year 2

**Conference Presentations:**
- Annual presentations at NSF CISE PI meetings
- Presentations at relevant AI, HCI, and information systems conferences
- Workshop and tutorial proposals to share methodologies and tools

**Open Source Release:**
- **Components to be Open Sourced:**
  - Metadata schemas and JSON specifications
  - Cross-modal linking algorithms
  - Process visualization tools (Programming Framework extensions)
  - Evaluation frameworks and metrics
  - API specifications and integration tools
  - Core platform components (subject to business considerations)
- **License:** MIT License (permissive, enabling broad adoption)
- **Repository:** GitHub (https://github.com/garywelz/copernicusai-research)
- **Timeline:** Initial open source release in Year 2, with ongoing contributions
- **Community Contributions:** Guidelines for community contributions, code of conduct, contribution process

**Documentation and Tutorials:**
- Comprehensive technical documentation
- User guides and tutorials
- Video demonstrations
- Blog posts and case studies
- Workshop materials and slides

**Community Engagement:**
- Maintain public Hugging Face Spaces with research updates
- Engage with research communities through social media and forums
- Respond to community questions and contributions
- Host virtual workshops or webinars

### 5.4 External Validation

**Expert Review:**
- External expert review of AI-generated briefings for quality assessment
- Peer review of research findings by domain experts
- Validation of metadata schemas by information science experts

**Advisory Input:**
- Consultation with researchers in relevant fields (HCI, AI, information science)
- Feedback from potential users (researchers, students, educators)
- Input from accessibility experts on platform design

**Community Validation:**
- Open beta testing beyond paid student testers
- Public feedback and bug reports
- Community contributions to open source components
- User testimonials and case studies

---

## 6. Broader Impacts

### 6.1 Educational Impacts

- **Lowering Barriers:** Makes research orientation more accessible to students and early-career researchers
- **Multi-Modal Learning:** Supports diverse learning styles through audio, visual, and textual content
- **Collaborative Learning:** Enables sharing and collective knowledge building
- **Reproducibility:** Promotes reproducible research through structured metadata and provenance
- **Student Engagement:** Paid student testing programs provide real-world research experience while improving the platform
- **Collective Intelligence:** Establishes new models for collaborative validation of AI outputs, teaching students critical evaluation skills

### 6.1.1 Diversity, Equity, and Inclusion

**Student Recruitment:**
- Student testing programs will actively recruit participants from diverse backgrounds
- Efforts to include students from underrepresented groups in STEM fields
- Consideration of diverse scientific disciplines and academic levels
- Geographic diversity where possible (though primarily local to PI's area)

**Accessibility:**
- **WCAG 2.1 AA Compliance:** Platform will be designed to meet Web Content Accessibility Guidelines Level AA
- **Screen Reader Support:** Full compatibility with screen readers (NVDA, JAWS, VoiceOver)
- **Keyboard Navigation:** All functionality accessible via keyboard (no mouse-only interactions)
- **Audio Transcripts:** All audio briefings will have text transcripts available
- **Alt Text:** All images, graphics, and diagrams will include descriptive alt text
- **Color Contrast:** Sufficient color contrast for text readability (white text on colored backgrounds for Red, Green, Blue, Violet; black text on Yellow)
- **Colorblind Accessibility:** Process visualizations will support node shape alternatives (ovals, rectangles, hexagons, cylinders, trapezoids) as secondary identifiers independent of color, enabling colorblind users to distinguish process stages
- **Responsive Design:** Platform accessible on multiple devices and screen sizes

**Barriers to Participation:**
- **Financial Barriers:** Student participants are compensated for their time
- **Technical Barriers:** Platform designed for standard web browsers, no special software required
- **Language Barriers:** Initial focus on English-language content, with architecture designed for future multi-language support
- **Time Barriers:** Flexible participation schedules for student testers

**Inclusive Design:**
- User-centered design process incorporating feedback from diverse users
- Consideration of different learning styles and preferences
- Support for various levels of technical expertise

### 6.2 Research Infrastructure Impacts

- **Scalable Platform:** Provides infrastructure that can scale to large research communities
- **Interdisciplinary Discovery:** Facilitates cross-domain connections and pattern recognition
- **Open Science:** Supports open science through accessible tools and documentation
- **Community Contributions:** Enables community-driven improvements and extensions

### 6.3 Responsible AI in Science

- **Transparency:** Explicit provenance and source tracking
- **Reliability:** Multi-checker mechanisms for error reduction
- **Accountability:** Human review and correction capabilities; responsibility for errors remains with human reviewers and institutions
- **Attribution:** Crediting original creators (papers, datasets, media) in briefings and visualizations
- **Collaborative Validation:** Collective intelligence approaches to verifying AI outputs
- **Ethical Use:** Promotes responsible use of AI in scientific contexts
- **User-Centered Design:** Grounded in real-world usability testing and user feedback

---

## 7. Project Management and Timeline

### 7.1 Project Timeline (3 Years)

**Year 1:**
- **Months 1-3:**
  - Enhanced briefing interface design
  - IRB approval process initiated
  - Alpha testing recruitment begins
  - **Milestone:** Interface design complete, IRB approval obtained
- **Months 4-6:**
  - Briefing interface implementation
  - Alpha testing program begins (2 grad + 3 undergrad students)
  - Initial usability testing
  - **Milestone:** Alpha testing launched, initial feedback collected
- **Months 7-9:**
  - Unified metadata schema design
  - Initial schema implementation
  - Alpha testing continues
  - **Milestone:** Metadata schema v1.0 complete
- **Months 10-12:**
  - Metadata schema refinement based on feedback
  - Initial metadata ingestion pipelines
  - Alpha testing analysis and reporting
  - **Milestone:** Alpha testing complete, usability report published

**Year 2:**
- **Months 13-15:**
  - Cross-modal linking algorithm development
  - Expanded beta testing recruitment (3 grad + 5 undergrad students)
  - Baseline comparison studies begin
  - **Milestone:** Cross-modal linking prototype operational
- **Months 16-18:**
  - Reliability mechanisms implementation
  - Multi-checker workflow development
  - Expanded beta testing begins
  - **Milestone:** Reliability mechanisms v1.0 complete
- **Months 19-21:**
  - Process visualization integration
  - Collaborative validation mechanisms implementation
  - Beta testing with focus on collective verification
  - **Milestone:** Collaborative validation framework operational
- **Months 22-24:**
  - Integration testing and refinement
  - Beta testing analysis
  - First peer-reviewed publication submission
  - **Milestone:** Integration complete, first publication submitted

**Year 3:**
- **Months 25-27:**
  - Comprehensive evaluation studies
  - Baseline comparison analysis
  - Full beta testing with collaborative validation analysis
  - **Milestone:** Evaluation studies complete
- **Months 28-30:**
  - System refinement based on evaluation results
  - Open source release preparation
  - Second publication submission
  - **Milestone:** System refinement complete, open source v1.0 released
- **Months 31-33:**
  - Final evaluation and analysis
  - Collaborative validation pattern analysis
  - Documentation completion
  - **Milestone:** Final evaluation report complete
- **Months 34-36:**
  - Final documentation and dissemination
  - Conference presentations
  - Project summary and recommendations
  - **Milestone:** Project complete, all deliverables submitted

### 7.2 Risk Management

**Technical Risks:**
- **LLM reliability issues** → Mitigated by multi-checker workflows and collaborative validation
- **Metadata schema complexity** → Mitigated by iterative design and user feedback
- **Integration challenges** → Mitigated by building on existing prototypes
- **LLM API availability/cost** → Mitigated by multi-provider architecture (Gemini, OpenAI, Claude) and cost monitoring
- **Scalability concerns** → Mitigated by cloud-based architecture with auto-scaling capabilities

**Research Risks:**
- **User adoption** → Mitigated by building on existing user base and paid student testing programs
- **Evaluation challenges** → Mitigated by mixed-methods approach and baseline comparisons
- **Low student participation** → Mitigated by fair compensation and flexible schedules
- **Collaborative validation not effective** → Mitigated by alternative single-user verification workflows as fallback

**Contingency Plans:**
- **If LLM APIs become unavailable:** Fallback to open-source models (Llama, Mistral) with local deployment
- **If user adoption is low:** Focus on quality over quantity, deeper engagement with smaller user base
- **If collaborative validation doesn't work:** Single-user verification workflows remain viable alternative
- **If timeline delays occur:** Prioritize core functionality, defer non-essential features

### 7.3 Alternative Approaches Considered

**Metadata Representation:**
- **Considered:** RDF/OWL semantic web standards
- **Chosen:** JSON schema for simplicity and interoperability
- **Rationale:** JSON is more accessible to developers and easier to integrate with existing systems

**Reliability Mechanisms:**
- **Considered:** Single-model with extensive fine-tuning
- **Chosen:** Multi-model architecture with cross-checking
- **Rationale:** Multi-model approach provides better error detection without requiring extensive training data

**User Testing:**
- **Considered:** Unpaid volunteer testing
- **Chosen:** Paid student testing programs
- **Rationale:** Fair compensation ensures consistent participation and recognizes student contributions

**Platform Architecture:**
- **Considered:** Self-hosted infrastructure
- **Chosen:** Cloud-based (GCP, Vercel)
- **Rationale:** Cloud infrastructure provides scalability and reliability without infrastructure management overhead

---

## 8. Personnel and Resources

### 8.1 Principal Investigator

**Gary Welz**
- Retired faculty, Mathematics and Computer Science, John Jay College CUNY
- Affiliate, CUNY Graduate Center New Media Lab
- Developer of CopernicusAI Knowledge Engine and related prototypes
- Extensive experience in AI/ML systems, scientific communication, and educational technology

**See:** Biographical Sketch (separate document: `NSF_Biographical_Sketch_Welz.md`)

### 8.2 Facilities and Resources

**Development Environment:**
- Home office facility (New York, NY)
- High-performance development equipment
- Cloud infrastructure (Google Cloud Platform, Vercel)

**Existing Infrastructure:**
- Operational CopernicusAI platform
- Existing Hugging Face Spaces
- Cloud services and APIs
- Research database integrations

**See:** Facilities, Equipment, and Other Resources (separate document - can adapt from DOE version)

### 8.3 Integration with Existing Tools

**Reference Management Integration:**
- **API Development:** RESTful API for integration with reference managers (Zotero, Mendeley, EndNote)
- **Export Capabilities:** Support for standard formats (BibTeX, RIS, JSON)
- **Import Capabilities:** Import existing reference libraries into metadata database

**Browser Extensions:**
- Browser extension for quick access to briefings while reading papers
- Integration with academic search engines (Google Scholar, Semantic Scholar)
- One-click citation import from web pages

**Workflow Integration:**
- Integration with note-taking tools (Obsidian, Notion, Roam Research)
- Compatibility with existing research workflows
- Export to common formats (Markdown, PDF, DOCX)

**Open Standards:**
- Adherence to open standards (JSON-LD, Schema.org)
- Interoperability with existing research infrastructure
- API documentation for third-party integrations

### 8.4 Sustainability Plan

**Post-Grant Sustainability:**
- **Open Source Community:** Open source release enables community maintenance and contributions
- **Institutional Support:** Potential ongoing support through CUNY Graduate Center New Media Lab affiliation
- **Cloud Infrastructure:** Cost-effective cloud hosting enables long-term operation
- **Community Funding:** Potential for community donations or institutional support

**Maintenance Strategy:**
- **Documentation:** Comprehensive documentation enables community contributions
- **Modular Architecture:** Modular design allows independent component maintenance
- **Version Control:** GitHub-based development enables community contributions

**Long-Term Vision:**
- Platform continues as community-maintained open source project
- Potential for institutional hosting or community foundation
- Integration with larger research infrastructure initiatives

---

## 9. Data Management Plan

### 9.1 Data Types

- Research data (usage analytics, evaluation metrics)
- User study data (anonymized)
- Metadata objects and schemas
- Software code and documentation
- Evaluation datasets

### 9.2 Data Sharing

- **Open Source Components:** Code and tools via GitHub
- **Metadata Schemas:** Publicly available schema definitions
- **Documentation:** Technical documentation publicly accessible
- **Evaluation Data:** Anonymized datasets for research community
- **Proprietary Components:** Business-sensitive algorithms protected

### 9.3 Data Preservation

- Cloud storage with automated backups
- Version control for all code
- Long-term preservation of research data
- Public repositories for open components

**See:** Data Management and Sharing Plan (separate document - can adapt from DOE version)

---

## 10. References and Prior Work

### Prior Work Citations

Welz, G. (2024–2025). *CopernicusAI: AI-Generated Audio Briefings as a Research Interface*. Hugging Face Spaces. https://huggingface.co/spaces/garywelz/copernicusai

Welz, G. (2024–2025). *The Programming Framework: A Universal Method for Process Analysis*. Hugging Face Spaces. https://huggingface.co/spaces/garywelz/programming_framework. Zenodo: https://doi.org/10.5281/zenodo.18463442

Welz, G. (2024–2025). *Genome Logic Modeling Project (GLMP): A Microscope for Biological Processes*. Hugging Face Spaces. https://huggingface.co/spaces/garywelz/glmp

Welz, G. (2024–2025). *Research Paper Metadata Database*. Hugging Face Spaces. https://huggingface.co/spaces/garywelz/metadata_database

Welz, G. (2024–2025). *Science Video Database*. Hugging Face Spaces. https://huggingface.co/spaces/garywelz/sciencevideodb

Welz, G. (2025). A Vision for AI-Powered Knowledge Engines: A Framework for Systematic Knowledge Discovery and Integration. *Nature Machine Intelligence* (under review; Perspective). Preprint: https://doi.org/10.5281/zenodo.18463304

### Related Research

**AI-Assisted Research and Knowledge Management:**
- Lewis, P., et al. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. *Advances in Neural Information Processing Systems*, 33, 9459-9474.
- Ammar, W., et al. (2018). Construction of the Literature Graph in Semantic Scholar. *NAACL-HLT*.
- Cachola, I., et al. (2020). TLDR: Extreme Summarization of Scientific Documents. *Findings of EMNLP*.
- Färber, M., & Jatowt, A. (2020). Citation Recommendation: Approaches and Datasets. *International Journal on Digital Libraries*, 21(4), 375-405.

**Human-Centered AI and Interactive Systems:**
- Amershi, S., et al. (2019). Guidelines for Human-AI Interaction. *CHI 2019*.
- Bansal, G., et al. (2021). Updates in Human-AI Teams: Understanding and Addressing the Performance/Compatibility Tradeoff. *AAAI 2021*.
- Liao, Q. V., & Varshney, L. R. (2021). Human-Centered Explainable AI (XAI): From Algorithms to User Experiences. *arXiv preprint arXiv:2110.10790*.

**Multi-Modal Knowledge Representation:**
- Hogan, A., et al. (2021). Knowledge Graphs. *ACM Computing Surveys*, 54(4), 1-37.
- Ji, S., et al. (2021). A Survey on Knowledge Graphs: Representation, Acquisition and Applications. *IEEE Transactions on Neural Networks and Learning Systems*, 33(2), 494-514.
- Wang, X., et al. (2021). Cross-Modal Retrieval: A Systematic Review of Methods and Future Directions. *ACM Transactions on Multimedia Computing, Communications, and Applications*, 17(3), 1-34.

**Reliability and Trust in AI Systems:**
- Bubeck, S., et al. (2023). Sparks of Artificial General Intelligence: Early Experiments with GPT-4. *arXiv preprint arXiv:2303.12712*.
- Lin, S., et al. (2022). TruthfulQA: Measuring How Models Mimic Human Falsehoods. *ACL 2022*.
- Zhang, T., et al. (2023). Benchmarking Large Language Models for News Summarization. *arXiv preprint arXiv:2301.13848*.

**Process Visualization and Computable Artifacts:**
- Heer, J., & Bostock, M. (2010). Crowdsourcing Graphical Perception: Using Mechanical Turk to Assess Visualization Design. *CHI 2010*.
- Munzner, T. (2014). *Visualization Analysis and Design*. CRC Press.
- Stasko, J., et al. (2018). Visual Analytics for Data Science. *Foundations and Trends in Human-Computer Interaction*, 11(3-4), 154-307.
- Le Novère, N., et al. (2009). The Systems Biology Graphical Notation. *Nature Biotechnology*, 27(8), 735-741.
- Larkin, J. H., & Simon, H. A. (1987). Why a diagram is (sometimes) worth ten thousand words. *Cognitive Science*, 11(1), 65-100.

**Knowledge Representation and Ontology Engineering:**
- Gruber, T. R. (1993). A translation approach to portable ontology specifications. *Knowledge Acquisition*, 5(2), 199-220.
- Noy, N. F., & McGuinness, D. L. (2001). Ontology development 101: A guide to creating your first ontology. *Stanford Knowledge Systems Laboratory Technical Report KSL-01-05*.
- Berners-Lee, T., Hendler, J., & Lassila, O. (2001). The semantic web. *Scientific American*, 284(5), 34-43.
- Uschold, M., & Gruninger, M. (1996). Ontologies: Principles, methods and applications. *Knowledge Engineering Review*, 11(2), 93-136.

**LLM-Based Knowledge Extraction:**
- Zelenko, D., Aone, C., & Richardella, A. (2003). Kernel methods for relation extraction. *Journal of Machine Learning Research*, 3, 1083-1106.
- Ahn, D. (2006). The stages of event extraction. *Proceedings of the Workshop on Annotating and Reasoning about Time and Events*, 1-8.
- White, J., et al. (2023). A prompt pattern catalog to enhance prompt engineering with ChatGPT. *arXiv preprint arXiv:2302.11382*.

**Note on Publications:** A vision paper framing this work ("A Vision for AI-Powered Knowledge Engines...") is under review at *Nature Machine Intelligence* (Perspective). The proposed research will generate additional peer-reviewed publications as part of the project deliverables. The existing operational prototypes (cited above) and the conceptual framework in the vision paper serve as the primary evidence of prior work and technical feasibility.

---

## 11. CISE Track Alignment

### Primary Track: Human-Centered AI (HAI)

**Alignment:**
- Research briefings as interactive research interface (human-AI collaboration)
- Iterative refinement loops (human-in-the-loop design)
- Multi-checker reliability workflows (trust and transparency)
- User evaluation and studies (human-centered evaluation)

### Secondary Track: Foundations

**Alignment:**
- Unified metadata representation (knowledge representation)
- Cross-modal linking algorithms (representation learning)
- Knowledge graph construction (structured data)
- Process visualization as computable artifacts (structured representations)

### Tertiary Track: Systems

**Alignment:**
- Pipeline orchestration (system architecture)
- Multi-modal ingestion (data systems)
- Scalable indexing (information systems)
- Integration infrastructure (system integration)

---

## 12. Budget Summary

**Total Budget Request:** $441,000 (direct costs) + indirect costs
**Project Period:** 36 months (3 years)

**Major Budget Categories:**
- Senior Personnel (PI): $180,000 (40%)
- Other Personnel: $70,000 (16%)
- Equipment: $10,000 (2%)
- Travel: $16,000 (4%)
- Other Direct Costs (primarily cloud infrastructure): $110,000 (24%)
- Indirect Costs: $78,750 (18% of modified total direct costs)

**Total Request:** $528,750 (including indirect costs)

**See:** Budget and Budget Justification (separate document: `NSF_BUDGET_3Year.md`)

**See:** Current and Pending Support (separate document: `NSF_Current_Pending_Support.md`)

---

## 13. Administrative Information

### Principal Investigator

**Name:** Gary Welz  
**Address:** 460 West 24th St, Suite 3A, New York, NY 10011  
**Phone:** 917-593-2537  
**Email:** gwelz@jjay.cuny.edu

### NSF Information

**NSF ID:** 000423180  
**NSF Email:** gwelz@jjay.cuny.edu

### Academic Affiliations

**John Jay College of Criminal Justice (CUNY)**
- Department: Mathematics and Computer Science
- Status: Retired Faculty

**CUNY Graduate Center**
- Affiliation: New Media Lab (Affiliate)

---

**Program:** NSF CISE Core Programs - Information and Intelligent Systems (IIS)
**Track:** Human-Centered AI (HAI) with Foundations and Systems components

