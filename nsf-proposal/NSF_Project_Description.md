# Project Description
## CopernicusAI Knowledge Engine: Assisted Research via AI Briefings, Multi-Modal Metadata, and Process Visualization

**Principal Investigator:** Gary Welz  
**Program:** CISE Core Programs - Information and Intelligent Systems (IIS)  
**Requested Amount:** $691,184 (3 years)

---

## 1. Introduction and Motivation

### 1.1 Problem Statement

Scientific research output is expanding exponentially across multiple modalities: research papers, preprints, datasets, videos, podcasts, and interactive visualizations. However, the tools researchers rely on remain largely siloed—separate literature search engines for papers, distinct tools for videos, isolated note systems, and limited support for structured synthesis across modalities. This fragmentation creates significant inefficiencies: (1) **Time-to-Orientation:** Researchers spend substantial time orienting to new topics, often redoing work others have done informally; (2) **Cross-Modal Disconnect:** Knowledge exists across text, audio, video, and visual formats, but connections are difficult to establish; (3) **Provenance Gaps:** Tracing claims back to sources across media types is challenging, limiting reproducibility; (4) **Iterative Refinement Limitations:** Current tools don't effectively support the iterative "ask narrower, ask deeper" workflow.

### 1.2 Research Opportunity

The emergence of large language models (LLMs) and multi-modal AI systems presents an opportunity to create unified research interfaces. However, simply applying generic AI chat interfaces is insufficient. Ambitious goals—such as rapid orientation to unfamiliar literatures and cross-domain discovery—require comprehensive integrated systems (scaffolding, tools, processes), not merely more powerful models (Welz, 2026a). This project builds that scaffolding. What's needed is: (1) **Evidence-Grounded Interfaces** that enforce multi-source grounding and maintain explicit provenance; (2) **Structured Metadata** enabling algorithmic analysis and cross-modal linking; (3) **Reliability Mechanisms** for detecting and reducing AI errors; (4) **Computable Artifacts** that are machine-analyzable, not just human-readable.

### 1.3 Prior Work and Foundation

**Conceptual grounding.** This project is framed by the "Knowledge Engine" concept: a system that systematically transforms information into knowledge through integrated capabilities—ingestion, digestion, analysis, calculation, comparison, connection, association, analogy, and multi-modal communication (Welz, 2026a). The proposal's objectives map to this taxonomy: briefings and podcasts embody *communication*; metadata, RAG, and knowledge graphs implement *ingestion*, *digestion*, and *connection*; multi-checker workflows support *analysis* and reliability; process diagrams provide structured representations across *analysis*, *connection*, and *communication*. The proposed work moves from existence proof (operational prototypes) to validated effectiveness through rigorous evaluation.

This project builds on existing, publicly accessible prototypes: **CopernicusAI Platform** - operational system with podcast episodes, integration with multiple academic databases, multi-voice AI generation; **Programming Framework** - universal process analysis meta-tool; **Genome Logic Modeling Project (GLMP)** - biological processes as interactive flowcharts; **Science Video Database** - transcript-based search; **Research Paper Metadata Database** - centralized metadata repository. **Knowledge Engine** - fully operational system (December 2025) with knowledge graph visualization, vector search, RAG capabilities, and unified web dashboard.

---

## 2. Research Objectives and Goals

### 2.1 Primary Research Objectives

**Objective 1: Research Briefings as Interactive Research Interface** - Design and implement "prompt → briefing → refinement" interaction loops; evaluate effectiveness for rapid topic orientation and iterative deepening; study user behavior and learning outcomes.

**Objective 2: Unified Multi-Modal Metadata Representation** - Develop structured JSON schema for papers, videos, briefings, diagrams, scientific graphics, and audio data; implement metadata object generation and ingestion pipelines; enable cross-modal linking and algorithmic analysis.

**Objective 3: Reliability and Trust Mechanisms** - Design and implement multi-checker workflows (AI + human); develop claim extraction and citation verification systems; evaluate error detection and reduction effectiveness.

**Objective 4: Process Visualization as Computable Artifacts** - Extend Programming Framework for broader domain coverage; integrate process diagrams into unified metadata layer; enable comparison and refinement of process representations (Welz, 2026b).

**Objective 5: Collaborative Validation and User Testing** - Implement alpha and beta testing programs with graduate students; design collaborative validation mechanisms; study collective intelligence patterns in user verification workflows.

### 2.2 Research Questions

1. How do AI-generated research briefings compare to traditional literature search for time-to-orientation and knowledge acquisition?
2. What metadata representations best support cross-modal linking and algorithmic analysis?
3. What reliability mechanisms most effectively reduce AI errors in scientific contexts?
4. How can process visualizations be integrated into broader research workflows?
5. What interaction patterns support effective iterative refinement of research questions?
6. How does collaborative validation by multiple users improve AI output reliability and trustworthiness?
7. What usability patterns emerge from student-led alpha and beta testing?

---

## 3. Technical Approach

### 3.1 Research Briefing Interface Design

**Current State:** CopernicusAI platform generates multi-voice AI podcasts from research topics with multi-source grounding.

**Research Extensions:** (1) **Iterative Refinement Loops** - interfaces supporting progressive question narrowing; (2) **Provenance Visualization** - interactive displays showing briefing → source relationships; (3) **Sharing and Collaboration** - mechanisms for sharing briefings and collaborative refinement; (4) **Evaluation Framework** - metrics for assessing briefing effectiveness and user learning; (5) **Exploratory direction** - if resources permit, study whether character/ethos-guided retrieval improves orientation or discovery (Welz, 2026a).

**CISE Track Alignment:** **HAI (Human-Centered AI)** - human-AI collaboration, interface design, evaluation.

### 3.2 Unified Metadata Representation

**Current State:** Prototype metadata databases for papers and videos exist separately. **Additionally, a fully operational Knowledge Engine has been implemented (December 2025) with:**
- **Knowledge Graph**: Interactive visualization system with indexed papers, relationship extraction (citations, semantic similarity, categories), and graph query capabilities
- **Vector Search**: Semantic search using Vertex AI embeddings across papers, podcasts, and processes with distance-based similarity ranking
- **RAG System**: Retrieval-augmented generation with citation support, context retrieval, and multi-modal content integration
- **Unified Dashboard**: Production-ready web interface with knowledge map visualization, search, RAG queries, content browsing, and statistics

The system extends standard RAG (Lewis et al., 2020) with structured analysis, explicit connection discovery, cross-modal integration, and provenance—positioning it as "extended RAG" within the Knowledge Engine framework (Welz, 2026a).

**Research Extensions:** (1) **Canonical Schema Design** - unified JSON schema capturing papers (IDs, abstracts, claims, methods, entities, citations), videos (transcripts, segments, entities, temporal metadata), briefings (prompts, sources, claims, confidence cues), diagrams (Mermaid syntax, nodes, edges, references), scientific graphics (photographs, telescope/microscope images, illustrations, computer graphics with metadata), and audio data (recordings, sonifications, experimental audio data, distinct from communication media); (2) **Audio as Dual-Mode Data** - schema distinguishes between audio as communication medium (podcasts) and as scientific data (recordings, sonifications); (3) **Cross-Modal Linking Algorithms** - entity extraction and semantic similarity for linking across all modalities; (4) **Knowledge Graph Construction** - relationships between metadata objects (extending beyond mathematics to other domains); (5) **Gap Detection Methods** - algorithmic identification of knowledge gaps.

**Future Data Modalities:** Architecture designed to accommodate scientific graphics databases and audio data management as future components.

**CISE Track Alignment:** **Foundations** - representation learning, metadata models, knowledge graphs; **Systems** - scalable data architecture.

### 3.3 Reliability and Trust Mechanisms

**Current State:** Basic multi-model architecture exists; reliability mechanisms need development.

**Research Extensions:** (1) **Multi-Checker Workflows** - Model A generates, Model B critiques; human review affordances; structured claim extraction; (2) **Citation Verification** - DOI/arXiv ID validation; source authenticity checks; citation integrity metrics; (3) **Error Detection Systems** - factual error identification; logical inconsistency detection; confidence scoring.

**CISE Track Alignment:** **HAI** - trust, reliability, human-AI collaboration.

### 3.4 Collaborative Validation and User Testing

**Research Component:** Integration of collaborative validation through structured user testing. Graduate students participate in alpha and beta testing, using the platform to create briefings, generate podcasts, and verify AI outputs.

**Research Extensions:** (1) **Alpha Testing (Year 1)** - 2 graduate students test core functionality; (2) **Expanded Beta (Year 2)** - 2 graduate students test enhanced features, participate in collaborative validation; (3) **Full Beta (Year 3)** - 2 graduate students focus on collaborative validation patterns and collective verification.

**Collaborative Validation Mechanisms:** Peer review workflows; collective intelligence patterns; consensus building; reputation systems; shared artifacts.

**CISE Track Alignment:** **HAI** - human-AI collaboration, collective intelligence, user-centered design.

### 3.5 Process Visualization Integration

**Current State:** Programming Framework and GLMP demonstrate feasibility.

**Research Extensions:** Domain extension beyond biology; metadata integration linking diagrams to papers, briefings, videos; comparison tools; refinement workflows.

**CISE Track Alignment:** **Foundations** - structured representations; **Systems** - integration pipelines.

### 3.6 System Architecture

**Current Infrastructure:** Multi-model LLM orchestration (Google Gemini 3, OpenAI GPT-4, Anthropic Claude 3); cloud backend (Google Cloud Run, Firestore, Cloud Storage); frontend (Next.js, React Server Components); multi-API research integration.

**Research Extensions:** Enhanced metadata ingestion pipelines; cross-modal linking infrastructure; quality assurance subsystems; evaluation and analytics systems. **MCP Integration:** Model Context Protocol server exposes knowledge engine components as queryable tools for AI assistants; standard interfaces like MCP address the "future needs" identified in the Knowledge Engine vision—interoperability, shared access, and common interfaces (Welz, 2026a).

**CISE Track Alignment:** **Systems** - pipeline orchestration, scalable indexing, multi-modal ingestion.

---

## 4. Research Methods and Evaluation

### 4.1 Evaluation Framework

**User Studies:** Time-to-orientation; knowledge acquisition; iterative refinement effectiveness; cross-modal navigation usability.

**System Metrics:** Grounding rate (fraction of briefing claims with traceable sources); citation integrity (percent resolvable to stable identifiers); error detection yield (errors caught by multi-checker systems); metadata quality (completeness and accuracy).

**Algorithmic Evaluation:** Cross-modal linking accuracy (precision/recall); gap detection effectiveness; process comparison accuracy. The evaluation framework aligns with the broader Knowledge Engine evaluation agenda (retrieval quality, connection validity, user-reported value) outlined in the vision paper (Welz, 2026a).

### 4.1.1 Success Criteria

**System Performance:** Grounding rate >=90%; citation integrity >=95%; error detection yield >=80%; metadata quality >=85%; cross-modal linking accuracy >=75% precision, >=70% recall.

**User Experience:** Time-to-orientation reduction >=30% vs. baseline; System Usability Scale (SUS) score >=70; user satisfaction >=80%; collaborative validation identifies >=15% more errors than single-user verification.

**Adoption and Engagement:** >=60% of student testers create and share at least one briefing; >=40% of briefings undergo refinement; average session duration >=20 minutes.

**Baseline Comparisons:** Compare against Google Scholar, Semantic Scholar, PubMed (traditional literature search); Elicit, Research Rabbit, Consensus (AI research tools); Zotero, Mendeley (knowledge management). Baseline data collected through controlled studies.

### 4.2 Research Methodology

**Design:** Mixed-methods combining quantitative metrics with qualitative user studies; comparative studies (briefing-based vs. traditional literature search); longitudinal studies; collaborative validation studies.

**Participants:** Paid graduate student testers (compensated); researchers and advanced students; interdisciplinary research teams; educational contexts.

**User Testing Phases:** Year 1 - Alpha (2 grad students); Year 2 - Expanded Beta (2 grad students); Year 3 - Full Beta (2 grad students, focus on collaborative validation).

**Data Collection:** Usage analytics (anonymized); user interviews and surveys; task-based evaluations; system performance metrics; collaborative validation patterns; usability metrics; podcast creation and sharing patterns.

### 4.2.1 Human Subjects Research and IRB Compliance

**Research Nature:** Low-risk usability testing and feedback collection. Participants use the platform and provide feedback—similar to standard software usability testing. No experimental interventions, medical procedures, or activities causing harm.

**IRB Compliance:** Project will comply with all applicable IRB requirements; approval obtained prior to data collection; if PI's institution lacks IRB, approval sought through external IRB or NSF process.

**Participant Protection:** Informed consent; voluntary participation; anonymization of all usage data; secure data storage; fair compensation for student participants.

**Risk Assessment:** Minimal risk—activities include using web-based platform, creating briefings/podcasts, providing feedback, participating in collaborative validation. No risks beyond normal use of online research tools.

### 4.2.2 Data Privacy and Protection

**Data Anonymization:** All usage analytics anonymized; user IDs replaced with anonymized identifiers; no PII stored; interviews/surveys anonymized before analysis.

**Data Retention:** Research data retained for project duration + 3 years (NSF requirement); anonymized datasets may be preserved for future research (with consent).

**User Consent:** Clear consent forms; option to opt out of data collection; right to request data deletion (subject to research requirements).

**Security Measures:** Encrypted data storage; secure transmission (HTTPS/TLS); access controls; regular security audits.

**Compliance:** GDPR compliance (international users); FERPA compliance (educational data); institutional data protection policies.

---

## 5. Expected Outcomes and Deliverables

### 5.1 Research Deliverables

1. **Enhanced Research Briefing Platform** - iterative refinement interfaces; provenance visualization; sharing and collaboration features.

2. **Unified Metadata Schema and System** - canonical JSON schema; metadata generation and ingestion pipelines; cross-modal linking implementation.

3. **Reliability and Trust Mechanisms** - multi-checker workflow system; citation verification tools; error detection and reporting.

4. **Process Visualization Integration** - extended Programming Framework; integration with metadata layer; comparison and refinement tools.

5. **Evaluation Results** - user study findings; system performance metrics; algorithmic evaluation results; collaborative validation patterns; usability findings.

6. **Collaborative Validation Framework** - multi-user verification workflows; collective intelligence patterns; peer review mechanisms; shared knowledge artifacts.

### 5.2 Publicly Accessible Resources

Enhanced CopernicusAI platform (publicly accessible); updated Hugging Face Spaces; open-source components (metadata schemas, tools, MIT License); technical documentation; evaluation datasets (anonymized).

### 5.3 Dissemination Plan

**Peer-Reviewed Publications:** Target venues - CHI, CSCW, UIST (HCI); NeurIPS, ICML, ACL, AAAI (AI/ML); SIGIR, WWW, JCDL (Information Systems); L@S, ICER (Educational Technology). Open access commitment. Timeline: 2-3 publications per year, starting Year 2.

**Conference Presentations:** Annual NSF CISE PI meetings; relevant AI, HCI, information systems conferences; workshops and tutorials.

**Open Source Release:** Components - metadata schemas, cross-modal linking algorithms, process visualization tools, evaluation frameworks, API specifications. License: MIT. Repository: GitHub. Timeline: Initial release Year 2.

**Documentation and Tutorials:** Technical documentation; user guides; video demonstrations; blog posts; workshop materials.

**Community Engagement:** Public Hugging Face Spaces; social media and forums; virtual workshops/webinars.

### 5.4 External Validation

**Expert Review:** External expert review of AI-generated briefings; peer review of research findings; validation of metadata schemas by information science experts.

**Advisory Input:** Consultation with researchers (HCI, AI, information science); feedback from potential users; input from accessibility experts.

**Community Validation:** Open beta testing; public feedback; community contributions; user testimonials and case studies.

---

## 6. Broader Impacts

### 6.1 Educational Impacts

Lowering barriers for students and early-career researchers; multi-modal learning support; collaborative learning; reproducibility through structured metadata; student engagement through paid testing programs; collective intelligence models teaching critical evaluation skills. The existing system was developed with limited resources (single investigator, modest infrastructure), demonstrating that sophisticated Knowledge Engine–style systems are feasible for individuals and small teams; NSF support will enable scaling, rigorous evaluation, and broader access.

### 6.1.1 Diversity, Equity, and Inclusion

**Student Recruitment:** Active recruitment from diverse backgrounds; efforts to include underrepresented groups in STEM; diverse scientific disciplines and academic levels.

**Accessibility:** WCAG 2.1 AA compliance; screen reader support (NVDA, JAWS, VoiceOver); keyboard navigation; audio transcripts; alt text for images; color contrast standards; responsive design.

**Barriers to Participation:** Financial barriers addressed through compensation; technical barriers minimized (standard web browsers); language barriers acknowledged (English initially, architecture for future multi-language); time barriers addressed through flexible schedules.

**Inclusive Design:** User-centered design incorporating diverse user feedback; consideration of different learning styles; support for various technical expertise levels.

### 6.2 Research Infrastructure Impacts

Scalable platform for large research communities; interdisciplinary discovery facilitation; open science support; community contributions enabled.

### 6.3 Responsible AI in Science

Transparency through explicit provenance; reliability through multi-checker mechanisms; accountability through human review (responsibility for errors remains with human reviewers and institutions); attribution of original creators (papers, datasets, media) in briefings and visualizations; collaborative validation approaches; ethical use promotion; user-centered design grounded in real-world testing.

---

## 7. Project Management and Timeline

### 7.1 Project Timeline (3 Years)

**Year 1:** Months 1-3 - Enhanced briefing interface design, IRB approval, alpha testing recruitment (Milestone: Interface design complete, IRB approved). Months 4-6 - Briefing interface implementation, alpha testing begins (2 grad students) (Milestone: Alpha testing launched). Months 7-9 - Unified metadata schema design and implementation (Milestone: Metadata schema v1.0 complete). Months 10-12 - Schema refinement, metadata ingestion pipelines, alpha testing analysis (Milestone: Alpha testing complete, usability report published).

**Year 2:** Months 13-15 - Cross-modal linking algorithm development, expanded beta recruitment (2 grad students), baseline studies begin (Milestone: Cross-modal linking prototype operational). Months 16-18 - Reliability mechanisms implementation, multi-checker workflows, expanded beta begins (Milestone: Reliability mechanisms v1.0 complete). Months 19-21 - Process visualization integration, collaborative validation implementation, beta testing (Milestone: Collaborative validation framework operational). Months 22-24 - Integration testing, beta analysis, first publication submission (Milestone: Integration complete, first publication submitted).

**Year 3:** Months 25-27 - Comprehensive evaluation studies, baseline comparison analysis, full beta with collaborative validation analysis (Milestone: Evaluation studies complete). Months 28-30 - System refinement, open source release preparation, second publication submission (Milestone: System refinement complete, open source v1.0 released). Months 31-33 - Final evaluation, collaborative validation pattern analysis, documentation completion (Milestone: Final evaluation report complete). Months 34-36 - Final documentation, dissemination, conference presentations (Milestone: Project complete, all deliverables submitted).

### 7.2 Risk Management

**Technical Risks:** LLM reliability issues → mitigated by multi-checker workflows; metadata schema complexity → mitigated by iterative design; integration challenges → mitigated by building on existing prototypes; LLM API availability/cost → mitigated by multi-provider architecture; scalability → mitigated by cloud-based architecture.

**Research Risks:** User adoption → mitigated by existing user base and paid student programs; evaluation challenges → mitigated by mixed-methods approach; low student participation → mitigated by fair compensation; collaborative validation ineffective → mitigated by single-user verification fallback.

**Contingency Plans:** LLM API unavailability → fallback to open-source models; low user adoption → focus on quality over quantity; collaborative validation ineffective → single-user verification alternative; timeline delays → prioritize core functionality.

### 7.3 Alternative Approaches Considered

**Metadata Representation:** Considered RDF/OWL; chosen JSON for simplicity and interoperability. **Reliability Mechanisms:** Considered single-model with fine-tuning; chosen multi-model for better error detection. **User Testing:** Considered unpaid volunteers; chosen paid students for consistent participation. **Platform Architecture:** Considered self-hosted; chosen cloud-based for scalability.

---

## 8. Personnel and Resources

### 8.1 Principal Investigator

**Gary Welz** - Retired faculty, Mathematics and Computer Science, John Jay College CUNY; Affiliate, CUNY Graduate Center New Media Lab; Developer of CopernicusAI Knowledge Engine; Extensive experience in AI/ML systems, scientific communication, and educational technology. See Biographical Sketch (separate document).

### 8.2 Facilities and Resources

**Development Environment:** Home office facility (New York, NY); high-performance development equipment; cloud infrastructure (Google Cloud Platform, Vercel).

**Existing Infrastructure:** Operational CopernicusAI platform; existing Hugging Face Spaces; cloud services and APIs; research database integrations.

See Facilities, Equipment, and Other Resources (separate document).

### 8.3 Integration with Existing Tools

**Reference Management:** RESTful API for Zotero, Mendeley, EndNote; export (BibTeX, RIS, JSON); import capabilities.

**Browser Extensions:** Quick access to briefings; integration with Google Scholar, Semantic Scholar; one-click citation import.

**Workflow Integration:** Integration with Obsidian, Notion, Roam Research; compatibility with existing workflows; export to Markdown, PDF, DOCX.

**Open Standards:** JSON-LD, Schema.org adherence; interoperability with existing infrastructure; API documentation.

### 8.4 Sustainability Plan

**Post-Grant Sustainability:** Open source community maintenance; potential institutional support (CUNY Graduate Center); cost-effective cloud hosting; potential community funding.

**Maintenance Strategy:** Comprehensive documentation; modular architecture; GitHub-based development.

**Long-Term Vision:** Community-maintained open source project; potential institutional hosting; integration with larger research infrastructure initiatives.

---

## 9. Data Management Plan

**Data Types:** Research data (usage analytics, evaluation metrics); user study data (anonymized); metadata objects and schemas; software code and documentation; evaluation datasets.

**Data Sharing:** Open source components via GitHub (MIT License); metadata schemas publicly available; technical documentation publicly accessible; anonymized evaluation datasets; proprietary components protected.

**Data Preservation:** Cloud storage with automated backups; version control for all code; long-term preservation (project duration + 3 years); public repositories for open components.

See Data Management and Sharing Plan (separate document, 2 pages).

---

## 10. References and Prior Work

### Prior Work Citations

**Key preprints (Zenodo, 2026):**

Welz, G. (2026a). *A Vision for AI-Powered Knowledge Engines: A Framework for Systematic Knowledge Discovery and Integration*. Preprint. Zenodo. DOI 10.5281/zenodo.18463304

Welz, G. (2026b). *The Programming Framework: A Universal Method for Process Analysis*. Preprint. Zenodo. DOI 10.5281/zenodo.18463442

**Supporting prototypes:**

Welz, G. (2024–2025). *Genome Logic Modeling Project (GLMP): A Microscope for Biological Processes*. Hugging Face Spaces.

Welz, G. (2024–2025). *Research Paper Metadata Database*. Hugging Face Spaces.

Welz, G. (2024–2025). *Science Video Database*. Hugging Face Spaces.

### Related Research

**AI-Assisted Research and Knowledge Management:**
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

**Note on Publications:** The PI has posted two preprints (Welz, 2026a, 2026b) framing this work: a Knowledge Engine vision and the Programming Framework. Additional draft manuscripts are in preparation but have not yet been submitted for publication. The proposed research will generate further peer-reviewed publications as project deliverables. The existing operational prototypes and these preprints serve as primary evidence of prior work and technical feasibility.

---

## 11. CISE Track Alignment

### Primary Track: Human-Centered AI (HAI)

**Alignment:** Research briefings as interactive interface (human-AI collaboration); iterative refinement loops (human-in-the-loop design); multi-checker reliability workflows (trust and transparency); user evaluation and studies (human-centered evaluation); collaborative validation (collective intelligence).

### Secondary Track: Foundations

**Alignment:** Unified metadata representation (knowledge representation); cross-modal linking algorithms (representation learning); knowledge graph construction (structured data); process visualization as computable artifacts (structured representations).

### Tertiary Track: Systems

**Alignment:** Pipeline orchestration (system architecture); multi-modal ingestion (data systems); scalable indexing (information systems); integration infrastructure (system integration).

---

**Document Status:** Complete - Ready for formatting and PDF generation  
**Page Target:** <=15 pages when formatted (11pt font, 1" margins)  
**Program:** NSF CISE Core Programs - Information and Intelligent Systems (IIS)  
**Track:** Human-Centered AI (HAI) with Foundations and Systems components

