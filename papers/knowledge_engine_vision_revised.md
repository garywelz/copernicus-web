# AI-Powered Knowledge Engines as Research Infrastructure for Systematic Knowledge Discovery

**Gary Welz**

Researcher, New Media Lab, CUNY Graduate Center
Email: gwelz@gc.cuny.edu
ORCID: https://orcid.org/0009-0005-7806-0892

---

## Abstract

This paper proposes *knowledge engines* as a framework for understanding how intelligent systems — both human and artificial — systematically discover, integrate, and generate knowledge. We argue that history's greatest scientific minds functioned as knowledge engines, processing information through iterative cycles of ingestion, analysis, synthesis, and communication, guided by curiosity and willingness to challenge established beliefs.

We propose a taxonomy of nine integrated capabilities — ingestion, digestion, analysis, calculation, comparison, connection, association, analogy, and multimodal communication — that any serious knowledge engine must combine systematically. The argument is deliberately integrative: achieving ambitious research goals requires orchestrating all nine capabilities within a durable infrastructure, not merely scaling up foundation models alone.

We present CopernicusAI as a working proof-of-concept of the knowledge engine framework, demonstrating feasibility through a fully deployed system with 59,499 indexed research papers (100% dense-embedded), 594 JSON-canonical process diagrams across six scientific discipline families, 753 indexed science videos, 90 AI-synthesized podcast briefings, an operational knowledge graph, OpenAI-powered vector search, and retrieval-augmented generation (RAG) with cited answer synthesis. To address reviewer requests for empirical content, we report a preliminary retrieval pilot (30 queries, frozen corpus of 59,499 documents) comparing lexical TF-IDF (nDCG@10 = 0.545) with OpenAI dense retrieval (nDCG@10 = 0.828) under a single-assessor protocol. While extensive validation remains necessary, the system demonstrates that the knowledge engine framework can be instantiated in practice.

**Keywords:** knowledge engines; research infrastructure; human-AI collaboration; retrieval-augmented generation; knowledge graphs; Model Context Protocol; evaluation

---

## 1. Introduction

At its most fundamental level, a knowledge engine is any system — biological or artificial — that systematically transforms information into knowledge. The term "engine" is deliberate: it suggests a mechanism that performs real work, converting raw inputs (information) into useful outputs (knowledge, understanding, actionable insights).

History's greatest scientists — Aristotle, Newton, Euler, Copernicus — functioned as knowledge engines. They processed information through iterative cycles of observation, analysis, calculation, and synthesis. What made them effective was not raw intelligence alone, but systematic processes: disciplined ingestion of evidence, careful structuring of findings, connection of ideas across domains, and communication of results in forms others could scrutinize and build upon. They also contributed tools — telescopes, microscopes, conceptual frameworks, mathematical notation — that enabled future knowledge discovery.

Modern AI creates an opportunity to build computational knowledge engines that combine this kind of systematic rigor with capabilities that exceed human limitations in scale, speed, and persistence. However, creating such systems requires more than applying large language models to a problem. It requires understanding and implementing the systematic processes that make knowledge engines effective — what we call the knowledge engine framework.

**Contributions.** This paper makes four concrete contributions:

1. A nine-capability taxonomy that provides a vocabulary for designing knowledge engines and clarifies what engineering obligations each capability entails in practice.
2. A deployed prototype, CopernicusAI, demonstrating that the framework can be instantiated by a single researcher using commodity tools and modest infrastructure.
3. A preliminary retrieval pilot providing the first quantitative benchmark of the system's performance, with honest acknowledgment of its scope and limitations.
4. An evaluation roadmap outlining how future studies can rigorously assess knowledge engine effectiveness.

**What this paper does not claim.** We are not proposing new machine learning algorithms, claiming validated superiority over existing systems, or presenting a production-ready research tool. We offer a framework and an existence proof, with extensive validation still required.

---

## 2. Related Work and Positioning

The knowledge engine framework builds on seven decades of AI research spanning several distinct traditions.

**Expert systems (1970s–1990s).** Early systems such as MYCIN [19] and CYC [20] demonstrated that structured knowledge representation and rule-based reasoning could achieve expert-level performance in narrow domains. Their lasting lessons were not just about what they could do, but about what they could not: knowledge acquisition became a bottleneck, coverage was brittle, and maintenance costs were high. These failure modes motivate our emphasis on scalable ingestion, flexible representation, and ongoing human oversight rather than static knowledge bases.

**Knowledge representation and the Semantic Web.** Formal frameworks for organizing knowledge — semantic networks, frames, ontologies, and linked data [1, 2, 3] — established durable principles around identifiers, constraints, and interoperability. Contemporary knowledge engines inherit these obligations. Open scholarly infrastructures such as Semantic Scholar [4] and OpenAlex [5] demonstrate what this looks like at scale: reproducible joins, provenance tracking, and participatory correction loops that brittle scraping approaches cannot sustain.

**Retrieval and generation.** Dense passage retrieval [6] and retrieval-augmented generation (RAG) [7] represent the current state of the art for grounding language model outputs in external knowledge. RAG addresses a fundamental limitation of standard LLMs: their knowledge is frozen at training time and cannot access current or domain-specific information. By retrieving relevant passages before generating an answer, RAG systems can produce cited, verifiable responses. PaperQA [8] extends this approach with explicit skepticism about absent evidence — a useful counterweight to the tendency of LLMs to confabulate when evidence is thin. Our framework extends RAG further by situating retrieval within a broader infrastructure that includes ingestion provenance, structured process representations, knowledge graph navigation, and multimodal communication.

**Cognitive architectures.** Frameworks such as SOAR [13] and ACT-R [14] provide useful vocabulary for decomposing intelligent behavior into distinct subsystems. We borrow this vocabulary for the nine-capability taxonomy while explicitly disclaiming any claim of psychological fidelity. Our labels denote engineering affordances, not cognitive mechanisms.

**Cautionary cases.** IBM Watson's oncology deployments [10, 11] illustrate the gap between engineering-era optimism and clinical reality. Galactica [9], a large language model trained on scientific text, was withdrawn after generating confident but inaccurate outputs. These cases reinforce a core argument of this paper: building bigger models is not sufficient. Reliable knowledge systems require disciplined infrastructure, transparent evaluation, and honest acknowledgment of limitations.

**Positioning.** Semantic Scholar, OpenAlex, and PaperQA each address important parts of the knowledge engine problem. The contribution of this paper is to argue for their systematic integration within a unified framework that adds ingestion provenance, multimodal delivery, interoperable tool access via the Model Context Protocol [15], and governance artefacts. Section 5 shows how CopernicusAI instantiates this vision; Section 6 provides an initial empirical benchmark.

---

## 3. A Taxonomy of Knowledge Engine Capabilities

We propose nine integrated capabilities that any knowledge engine must combine systematically. These capabilities are not novel — they are well-established in cognitive science and AI. Our contribution is proposing their systematic integration through a clear taxonomy, explicit feedback loops, and governance oversight.

The nine capabilities are:

1. **Ingestion:** Multi-source, multi-modal acquisition of information with provenance tracking and quality assessment.
2. **Digestion:** Processing raw information into structured, usable forms — normalization, chunking, entity extraction, identifier alignment.
3. **Analysis:** Deep examination of structured information to identify patterns, anomalies, and relationships.
4. **Calculation:** Mathematical computation, simulation, optimization, and quantitative prediction.
5. **Comparison:** Similarity assessment, difference identification, and cross-domain juxtaposition.
6. **Connection:** Relationship discovery, network analysis, path finding, and clustering across items.
7. **Association:** Co-occurrence detection, correlation analysis, and weak signal identification.
8. **Analogy:** Structural mapping across domains, enabling transfer of insight from one field to another.
9. **Communication:** Multi-modal expression of results through text, visual, audio, and interactive formats.

The power of a knowledge engine lies not in any single capability but in their integration. A system that can ingest but not analyze is merely a database. One that analyzes but does not connect misses relationships. One that connects but cannot communicate cannot share knowledge. Feedback loops tie the capabilities together: outputs from communication feed back into ingestion priorities; analogy suggestions inform what new material to digest; governance oversight monitors ingestion, analysis, and communication to catch errors and biases before they propagate.

### 3.1 How the Capabilities Work Together

The diagram below illustrates the coupling between capabilities and the role of governance oversight. Note that the nine capabilities need not map one-to-one onto software modules — a single subsystem may implement several capabilities, and a single capability may be distributed across subsystems.

```mermaid
flowchart LR
  subgraph KE["Nine Capabilities"]
    I["Ingestion"]
    D["Digestion"]
    A["Analysis"]
    C["Calculation"]
    P["Comparison"]
    N["Connection"]
    S["Association"]
    Y["Analogy"]
    M["Communication"]
  end
  Gov["Governance & oversight"]
  I --> D --> A --> M
  D --> P --> N --> M
  A --> S --> Y --> M
  C --> A
  Y --> D
  M --> I
  Gov -. oversight .-> I
  Gov -. oversight .-> A
  Gov -. oversight .-> M
```

*Figure 1. Nine-capability coupling diagram showing feedback loops and governance oversight. Arrows indicate data flow and influence; governance oversight (dashed) applies to ingestion, analysis, and communication as the three points of greatest risk for error propagation.*

### 3.2 What Each Capability Means in an Engineered System

Reviewers reasonably ask how abstract capability labels acquire concrete meaning in an engineered system rather than remaining as metaphors. Table 1 answers this by specifying what each capability means operationally — what artefacts it produces, and how CopernicusAI implements it.

**Table 1. Operational semantics of the nine capabilities**

| Capability | What it means in an engineered system | CopernicusAI implementation |
|---|---|---|
| Ingestion | Licensed data acquisition with provenance manifests, checksums, and ingestion telemetry | Scheduled Python adapters for arXiv, PubMed, NASA ADS (ingest frozen for evaluation); curator upload workflows; typed Firestore records; JSON-canonical media catalogs |
| Digestion | Normalization, chunking, identifier alignment, and metadata structuring of raw inputs | LLM-assisted entity extraction; Programming Framework prose-to-JSON pipeline with schema validation, publish manifests, and HTML-to-JSON migration |
| Analysis | Summarization, contradiction surfacing, and pattern identification over structured content | OpenAI RAG with retrieval-fused prompting; exploratory ranking boosts (flagged as unvalidated) |
| Calculation | Executable numerics, surrogate solvers, and quantitative estimation | Mostly delegated to external calculators and notebooks; internal kernels are a roadmap item |
| Comparison | Ranking, deduplication, divergence surfacing, and side-by-side juxtaposition | OpenAI dense similarity (1536d) over papers and process charts; lexical fallback; per-family and content-type filters |
| Connection | Explicit relationship induction, graph traversal, and neighbourhood exploration | Knowledge graph edges encoding citations, semantic similarity, and category links; interactive knowledge map with topic search and focus-id biasing |
| Association | Weak-signal co-occurrence mining and exploratory correlation hints | Embedding neighbourhood overlaps across six process families; metadata correlations (flagged exploratory) |
| Analogy | Cross-domain juxtaposition and provisional structural mapping | Guided prompts; distal neighbourhood retrieval; disclaimer-heavy sceptical scaffolding |
| Communication | Interfaces, rendered artefacts, and inspectable output surfaces | Knowledge Engine dashboard (vector search, RAG Q&A, content browse, stats, interactive knowledge map with node-click explanations); MCP tool payloads; AI-synthesized podcasts |

The embedding-based similarity underlying Comparison, Connection, and Association supplies a topical geometry — approximate proximity in semantic space — rather than logical entailment. CopernicusAI uses OpenAI `text-embedding-3-small` exclusively for all vector representations (1536 dimensions) and `gpt-4o-mini` for RAG answer synthesis. Mixing embedding providers with differing dimensionalities — for example, Vertex AI text-embedding-004 at 768 dimensions versus OpenAI at 1536 — would render cosine similarity scores incomparable across index segments; this was explicitly avoided in favour of a single-provider index. The Model Context Protocol (MCP) [15] surfaces frozen, auditable payloads that reviewers and users can inspect without re-running opaque pipelines. Governance oversight routes through the Communication capability via participatory feedback, explicit refusal when evidence is insufficient, and versioned artefacts that preserve the history of the system's outputs.

---

## 4. Why Ambitious Research Goals Require a Framework

Public discussions of AI research assistants often suggest that a sufficiently powerful language model could answer questions like "What is the cure for cancer?" This framing misses a fundamental reality: no model can generate reliable answers to such questions from scratch, regardless of its scale.

Consider what answering that question actually requires. First, comprehensive ingestion of evidence across oncology, genomics, pharmacology, immunology, and related fields — no single model's training data is sufficient. Second, multimodal analytic tools capable of processing not just text but images, structured clinical data, and time series. Third, hypothesis generation that goes beyond retrieval — the ability to propose novel connections and test them against evidence. Fourth, experimental validation interfaces that route users toward reproducible checks rather than conversational assertions. Fifth, reliability auditing that surfaces uncertainty and conflicting evidence rather than generating fluent but misleading summaries. Sixth, collaboration infrastructure that brings human expertise into the loop at the right moments. Seventh, conceptual scaffolding that organizes the problem space so researchers can navigate it without becoming disoriented.

Each of these requirements maps to one or more of the nine capabilities described in Section 3. Table 2 makes this mapping explicit.

**Table 2. Prerequisites for ambitious research goals, mapped to knowledge engine capabilities**

| Prerequisite | Primary capabilities involved | Notes |
|---|---|---|
| Comprehensive multi-disciplinary ingestion | Ingestion, digestion, communication | Volume without provenance produces an unauditable corpus |
| Multimodal analytic tooling | Digestion, analysis, comparison, calculation | Cross-modal contrast reduces modality-tunnel hallucination |
| Hypothesis scaffolding beyond naive Q&A | Analysis, association, analogy, communication | Creative leaps without auditing create ethical risks |
| Experimental validation interfaces | Calculation, analysis, communication | Claims should route users toward reproducible checks |
| Reliability auditing and explicit refusal | Comparison, analysis, communication | Transparency artefacts are scholarly outputs in their own right |
| Collaboration infrastructure | Communication, ingestion, governance | MCP [15] enables audited, routable access — but is not sufficient alone |
| Conceptual scaffolding | Digestion, connection, communication | Discipline-scale maps reduce disorientation as corpora grow |

The implication is not that AI cannot contribute to ambitious research goals, but that contributing meaningfully requires building the right infrastructure rather than simply scaling model size. This is the core argument for the knowledge engine framework.

---

## 5. CopernicusAI: A Proof-of-Concept Implementation

CopernicusAI is an early prototype demonstrating how the knowledge engine framework can be instantiated in practice. It is an existence proof — showing that such systems can be built by a single researcher using commodity tools — not a validated production system. The implementation is described here with explicit acknowledgment of its current limitations.

### Architecture Overview

The system integrates multiple components following the nine-capability taxonomy. Data flows from ingestion through processing to a variety of query interfaces. The architecture diagram below illustrates the complete pipeline.

![CopernicusAI Architecture](copernicusai_architecture.png)

*Figure 2. CopernicusAI architecture using the Programming Framework five-color palette: Red = inputs, Yellow = structured storage, Green = processing, Blue = decision points, Violet = outputs. The palette annotates diagram roles and does not map one-to-one onto the nine capabilities — a single colored node may implement multiple capabilities. Export at full column width, ≥9pt labels, colorblind-safe palette (Okabe–Ito recommended).*

### Current Status (June 2026)

The system is fully deployed and publicly accessible. Table 3 summarizes current staging statistics. Paper ingest automation was disabled on 2026-05-26 to freeze the evaluation corpus (Section 6); subsequent infrastructure work — embedding backfill, JSON-canonical process catalog rollout, and Knowledge Engine UI updates — did not alter the frozen export artefact cited in the retrieval pilot.

**Table 3. CopernicusAI staging statistics (June 2026)**

| Component | Current count |
|---|---|
| Research papers indexed | 59,499 |
| Process diagrams (six discipline families, JSON-canonical) | 594 |
| — GLMP v2 (biology) | 108[^glmp] |
| — Mathematics | 237 |
| — Chemistry | 123 |
| — Biology (discipline charts) | 55 |
| — Computer science | 50 |
| — Physics | 21 |
| Science videos indexed (JSON catalog) | 753 |
| AI-synthesized podcast briefings (JSON catalog) | 90 |
| Papers with vector embeddings | 59,499 (100% of corpus) |
| Process charts with vector embeddings | 594 across six Firestore collections |
| Knowledge Map build time (topic search, 10 papers) | ~10 s (vector-seeded) |

[^glmp]: The `glmp_processes` collection was reconciled to 108 canonical documents on 2026-06-07; legacy prefixed identifiers were pruned and the collection re-synced from GCS.

The live system is accessible at https://copernicus-frontend-phzp4ie2sq-uc.a.run.app/knowledge-engine. A machine-readable status snapshot (`knowledge-engine-status.json`) is published to public cloud storage for dashboard telemetry.

### How a Query Moves Through the System

The following sequence diagram shows what happens when a researcher submits a query. The six stages correspond to the six checkpoints in the system architecture and map onto the capability taxonomy as follows: ingestion and digestion populate the retrieval pool asynchronously; comparison and connection operate at the indexing stage; analysis and analogy guide the grounded synthesis step; communication is the final delivery.

```mermaid
sequenceDiagram
  participant Researcher
  participant Gateway as MCP / FastAPI Gateway
  participant Pool as Retrieval Pool
  participant LM as OpenAI Chat (RAG synthesis)

  Researcher->>Gateway: query with optional filters, content types, and focus_id
  Gateway->>Pool: OpenAI embedding + vector search over papers and process charts
  Pool-->>Gateway: fused contexts with source offsets, similarity scores, and diagnostics
  Gateway->>LM: grounded prompt with numbered citations and refusal scaffolding
  LM-->>Gateway: drafted answer with provenance (or retrieval-only excerpts if no LLM)
  Gateway-->>Researcher: response via Knowledge Engine dashboard, MCP JSON, or audio
```

*Figure 3. Query lifecycle showing OpenAI embedding retrieval, grounded synthesis via OpenAI chat, and multimodal delivery. If retrieved evidence is insufficient, or no chat model is configured, the system declines to fabricate an answer and returns cited excerpts instead.*

### Technology Stack

The system is built from the following components:

- **Harvesting and ingestion.** Python adapters for arXiv, PubMed, and NASA ADS, with quota management and provenance manifests. Scheduled paper ingest was disabled during the evaluation freeze; media catalogs (videos, podcasts) are maintained as JSON-canonical exports.
- **Structuring.** LLM-assisted parsing and chunking; the Programming Framework [17] pipeline for converting prose process descriptions into JSON-canonical Mermaid flowcharts with schema validation, per-family `metadata.json` / `process-index.json` manifests, GCS publish, and Firestore sync.
- **Storage and embeddings.** Firestore for document records and vector-indexed process collections (`glmp_processes`, `math_processes`, `chemistry_processes`, `physics_processes`, `computer_science_processes`, `biology_processes`); OpenAI `text-embedding-3-small` (1536d) via a provider factory with Secret Manager key retrieval; approximate nearest-neighbour search for semantic similarity; Postgres for relational workloads.
- **Retrieval and generation.** Unified OpenAI provider path: vector search retrieves from papers and all six process families, then `gpt-4o-mini` synthesizes cited RAG answers. Vertex AI generation is disabled on the hosted deployment (`DISABLE_VERTEX_AI=1`); retrieval-only excerpts are returned when no chat model is available.
- **Interfaces.** Next.js Knowledge Engine dashboard (stats, vector search, RAG, content browser with per-family process tabs, interactive knowledge map with semantic topic search and per-node RAG explanations); FastAPI backend on Cloud Run; MCP server [15] for AI assistant integration; optional AI-synthesized podcast briefings.
- **Governance hooks.** Participant-configurable trait overlays that adjust exploratory ranking signals, pending blind replication studies; evaluation corpus freeze documented in operational runbooks.

### Known Limitations

The following limitations are acknowledged explicitly:

- **Trait-conditioned ranking is unvalidated.** The character-inspired ranking boosts (e.g., upweighting papers that challenge established views) are illustrative and have not been tested against a control condition.
- **Contradiction auditing is shallow.** The system can surface conflicting papers but cannot reliably adjudicate between them; human expert review remains essential.
- **Knowledge graph coverage is uneven.** The graph is denser in some disciplines than others; the staging statistics in Table 3 reflect this honestly.
- **Retrieval evaluation remains preliminary.** Section 6 now reports both lexical and dense OpenAI results on the frozen 30-query set, but judgments come from a single assessor with an expanded candidate pool; hybrid reranking, multi-assessor agreement, and external baselines are not yet included.
- **Media catalogs are not fully integrated into vector search.** Videos (753) and podcasts (90) are indexed as JSON-canonical catalogs and exposed in the dashboard; embedding and vector retrieval for media content remain partial.
- **Knowledge map coverage is paper-centric.** The interactive graph supports semantic topic search and node-click RAG over papers; process, video, and podcast nodes in the map UI are not yet fully wired on the backend.
- **Process coverage varies by discipline.** Mathematics (237 charts) and chemistry (123) are well represented; physics (21) and computer science (50) are thinner; GLMP biology (108) and discipline-specific biology charts (55) coexist as separate families.
- **The system was built and is maintained by a single researcher.** This is a strength in terms of demonstrating accessibility, but a limitation in terms of scale, review, and institutional robustness.

### JSON-Canonical Process Catalogs

Between May and June 2026, the process-diagram subsystem was migrated from legacy HTML artefacts to a JSON-canonical catalog strategy. Each discipline family (GLMP v2, mathematics, chemistry, physics, computer science, biology) now maintains:

1. **Schema-validated JSON** per process chart, with Mermaid source, metadata, topology signatures, and provenance fields.
2. **Publish manifests** (`metadata.json`, `process-index.json`) generated by a shared tooling pipeline (`process_catalog/`: schema, publish, HTML-to-JSON conversion, orphan pruning, GCS upload).
3. **Firestore sync** into typed vector-search collections, followed by OpenAI embedding backfill per family.
4. **Archive of superseded files** so reviewers can audit what changed without losing history.

This migration increased the canonical process count from 582 to 594, eliminated duplicate flat-path artefacts in cloud storage, and aligned the live Knowledge Engine browse and search interfaces with six explicit process-family tabs. The approach generalizes the Programming Framework [17] from a visualization method into durable research infrastructure: versioned, searchable, embeddable process knowledge rather than static HTML pages.

### Knowledge Graph Navigation

The Knowledge Engine dashboard includes an interactive **Knowledge Map** that lets researchers explore topical neighbourhoods visually. A user enters a natural-language topic; the backend seeds retrieval with OpenAI dense vector search over the full paper corpus, applies optional discipline and date filters, and lays out the top *N* papers as nodes with concept hubs and similarity edges (typically ~10 seconds for ten papers on the hosted deployment). Clicking a paper node triggers a focused RAG explanation: the system re-retrieves with a `focus_id` bias toward that document and synthesizes a cited summary via OpenAI chat. This implements the Connection and Communication capabilities in a single interface — graph traversal plus grounded explanation — without requiring users to formulate structured queries. The map is currently paper-centric; process, video, and podcast nodes remain on the roadmap (see Known Limitations).

### The Programming Framework as Knowledge Engine Infrastructure

The process diagram component of CopernicusAI has been formalized as a standalone companion methodology — the Programming Framework [17] — described in a companion paper. The Programming Framework provides the pipeline by which textual process descriptions are transformed into structured Mermaid flowcharts, stored as JSON with metadata, and organized into searchable discipline databases. The June 2026 JSON-canonical migration extends this pipeline with schema enforcement, multi-family publish workflows, and vector-indexed Firestore collections. Within the knowledge engine taxonomy, it operationalizes the Digestion capability (transforming unstructured text into structured representations), the Connection capability (linking process diagrams to source papers and cross-family neighbours), and the Communication capability (rendering processes as interactive visual artefacts in the Knowledge Engine dashboard).

---

## 6. Evaluation: Preliminary Pilot and Roadmap

Reviewer 2 requested empirical content beyond the system description. We respond with a preliminary retrieval pilot that provides an initial benchmark while being transparent about its scope. We report only what was actually measured; we do not extrapolate to comparisons with other systems that were not run.

### Preliminary Retrieval Pilot

The pilot evaluates retrieval quality over a frozen corpus export using two comparators on the same 30-query set: a lexical TF-IDF baseline (May 2026) and an OpenAI dense-vector comparator (June 2026, evaluation roadmap track A). Hybrid lexical+dense reranking was not run. Subsequent to the corpus freeze, the live system completed OpenAI embedding backfill over the full 59,499-paper corpus and six process-chart collections, enabling operational dense-vector search and RAG in production; the dense comparator reported here is an offline benchmark over the frozen export, not live Firestore retrieval.

**Corpus.** Firestore database `copernicusai`, collection `research_papers`, exported as a gzipped JSONL file (`research_papers_20260526.jsonl.gz`) on 2026-05-26 with host ingest disabled to freeze the corpus. The export contains 59,499 documents. SHA256: `3dd5e019fca5f8e823bd71020a80c534b2e1a9e7199272b27c0b13da40ee8065`. The corpus and evaluation bundle are archived at https://doi.org/10.5281/zenodo.18463303. Infrastructure improvements after the freeze (embedding backfill, process catalog rollout) did not modify this export artefact.

**Queries.** 30 queries covering a range of scientific topics represented in the corpus, listed in full in Appendix A. The query list was frozen before evaluation (SHA256: `8fcfe7bcd50a85ba665ad065afe4a9623c38422da0254f78cdadac47d4dfdd1f`).

**Retrieval methods.**

- *Lexical TF-IDF (Column A, May 2026 freeze).* TF-IDF over pooled titles and abstracts (`combined_text`), implemented in `retrieval_pilot_colab_bundle.ipynb` (random seed 42, commit `77ebbe92a908edfd77bfb0c207e04164d43016f5`).
- *OpenAI dense (Column B, June 2026).* `text-embedding-3-small` (1536 dimensions) over the same `combined_text` field; cosine similarity via L2-normalised dot product. Corpus embeddings were computed once and cached (`openai_doc_embeddings.npz`); rankings were generated locally with `run_dense_track_a.py` using the same notebook metric definitions. Vertex AI embeddings were not used, to avoid mixing incompatible vector spaces.

**Judgment protocol.** Relevance labels were assigned by one assessor (the author) from title and abstract only — without access to retrieval scores or rank positions. The lexical baseline was judged on the union of lexical top-10 candidates (~300 query–document pairs; May 2026). For a fair dense comparison, the judgment pool was expanded to the union of lexical and dense top-10 candidates per query (558 pairs; 258 additional dense-only candidates labelled in June 2026, before aggregate metrics were recomputed). Metrics in Table 4 use this expanded pool for both columns; lexical scores are unchanged from the original May 2026 freeze because lexical top-10 hits were already within the original pool. Full-text reading, independent second assessors, and Cohen's kappa are deferred to future cycles.

**Table 4. Preliminary retrieval pilot results (30 queries, frozen corpus of 59,499 documents)**

| Metric | Lexical TF-IDF | OpenAI dense |
|---|---:|---:|
| Mean nDCG@10 | 0.545 | 0.828 |
| Mean Precision@10 | 0.323 | 0.517 |
| Median Reciprocal Rank | 0.500 | 1.000 |
| Queries with no relevant result in top-10 | 8 of 30 | 0 of 30 |

**Interpretation.** These results reflect a deliberately narrow protocol — two in-house retrievers, single-assessor binary judgments, no comparison with Semantic Scholar, PubMed, or other external systems — and should be read as a preliminary existence-proof benchmark, not a claim of validated superiority. On this protocol, OpenAI dense retrieval substantially outperforms the lexical baseline: mean nDCG@10 rises from 0.545 to 0.828, mean Precision@10 from 0.323 to 0.517, and all 30 queries receive at least one relevant hit in the top-10 under dense retrieval (versus 8 zero-hit queries under lexical search: queries 9, 17, 18, 19, 21, 22, 26, and 28 in Appendix A). Inspection of those eight queries suggests that conceptually phrased prompts with sparse keyword overlap with corpus abstracts are cases where dense retrieval recovers relevant documents that TF-IDF misses. We do not attribute the improvement to production deployment alone; it is measured offline on the frozen export. Hybrid reranking, multi-assessor adjudication, and external baselines remain future work.

### Evaluation Roadmap

The following evaluation tracks are planned in sequence:

- **(A) Dense retrieval benchmarking — completed June 2026.** OpenAI dense retrieval (`text-embedding-3-small`, 1536d) was run over the frozen May 2026 export against the same 30-query set; results appear in Table 4 (Column B). Reproducibility bundle: `dense_track_a_bundle_20260608.zip` (rankings, expanded judgments, cached embeddings, `run_dense_track_a.py`, manifest). Deposited at Zenodo as version 2 of the May 2026 evaluation freeze (https://doi.org/10.5281/zenodo.18463303). Hybrid lexical+dense reranking remains a secondary variant.
- **(B) Knowledge graph adjudication.** Domain experts will rate candidate neighbourhood connections against randomised negatives. Earlier informal pilots suggested approximately 60% plausibility; a formal study with institutional recruitment is in preparation.
- **(C) User study.** A participatory study will ask researchers to use CopernicusAI for literature review and hypothesis generation tasks, measuring time-to-completion, output quality, and user satisfaction relative to their existing tools.
- **(D) Trait-conditioned ablations.** The character-inspired ranking boosts will be evaluated in a controlled A/B design, comparing Copernicus-inspired, Aristotle-inspired, and neutral baseline configurations.
- **(E) Longitudinal impact tracking.** With appropriate consent, long-term tracking of whether system-assisted insights contribute to publications, grant applications, or experimental designs.

---

## 7. Limitations, Future Directions, and Ethical Considerations

### Current Limitations

Several limitations of the current implementation are worth restating clearly:

- The character-specification ranking boosts remain illustrative and unvalidated; they may or may not improve retrieval quality compared to a neutral baseline.
- The system has not been evaluated against established retrieval benchmarks or compared directly with Semantic Scholar, PubMed, or similar tools.
- Dense vector retrieval is operational over the full 59,499-paper corpus using OpenAI `text-embedding-3-small` (1536 dimensions). Section 6 reports a preliminary offline comparison on the frozen 30-query set (dense nDCG@10 = 0.828 vs lexical 0.545). This evaluation uses a single assessor and an expanded judgment pool; it does not establish superiority over external retrieval systems.
- RAG answer quality has not been evaluated with human assessors; OpenAI chat synthesis is deployed but unvalidated against expert judgments.
- Analogy-based suggestions carry hallucination risk if not accompanied by adversarial auditing; users should treat them as hypotheses to investigate rather than conclusions.
- The system was built and is maintained by a single researcher on a modest budget (~$200/month in cloud infrastructure costs), which is a demonstration of accessibility but also a constraint on robustness and scale.

### Future Directions

Key open research questions include: How should knowledge engine effectiveness be measured holistically, beyond retrieval metrics? Do character-specification approaches meaningfully improve research outcomes for users? How do integrated systems compare with specialized point solutions for specific tasks? What is the right division of labor between human researchers and automated components?

### Ethical Considerations

Building knowledge infrastructure at scale raises several ethical obligations:

- **Representational bias.** Which research traditions, languages, and institutions are represented in the indexed corpus? What perspectives are missing? The current corpus is heavily weighted toward English-language papers from arXiv, PubMed, and NASA ADS.
- **Accuracy and hallucination.** How do we ensure outputs are correct and do not mislead users? The explicit refusal behavior and citation requirements in the RAG system are partial mitigations, not solutions.
- **Attribution.** How should original researchers be credited when their work is summarized, connected, or synthesized by an automated system?
- **Access.** Who has access to knowledge engine tools, and who benefits? Demonstrating that such systems can be built at low cost is one contribution toward democratizing access.
- **Responsibility.** When a knowledge engine produces an incorrect or misleading output, who is responsible — the system builder, the infrastructure provider, or the user?

---

## 8. Conclusion

This paper proposes knowledge engines as a framework for systematically transforming information into knowledge. By recognizing common patterns across effective knowledge systems — historical and computational — we can design better research infrastructure for the AI era.

The nine-capability taxonomy provides a concrete vocabulary for knowledge engine design. While each capability is well-established individually, the contribution here is proposing their systematic integration through explicit feedback loops and governance oversight. The framework argues that achieving ambitious research goals requires not just powerful models, but comprehensive infrastructure: disciplined ingestion, structured representation, calibrated retrieval, contestable outputs, and collaborative interfaces.

CopernicusAI demonstrates that this infrastructure can be built by a single researcher working with a laptop, standard cloud services, and AI coding assistants, at a total monthly cost under $200. This is not a claim of superiority over well-resourced systems, but a demonstration that sophisticated knowledge engines are now accessible to individual researchers and small teams. Since the evaluation freeze, the system has reached 100% dense-embedding coverage over 59,499 papers, rolled out 594 JSON-canonical process charts across six discipline families, and deployed OpenAI-powered vector search and RAG synthesis on Cloud Run. The preliminary retrieval pilot now reports both lexical (nDCG@10 = 0.545) and dense OpenAI (nDCG@10 = 0.828) results on the same frozen 30-query set; RAG answer quality and multi-assessor validation remain on the roadmap.

The term "knowledge engine" should enter AI discourse as a generic concept describing systems that systematically convert information into auditable, citable, extensible knowledge. We offer this framework to stimulate discussion, provide common vocabulary, and motivate the infrastructure investments that ambitious research goals require.

---

## Acknowledgements

The author thanks the open-source and open-science communities whose infrastructure — including arXiv, PubMed, NASA ADS, Zenodo, and the Mermaid diagramming toolchain — makes independent research of this kind possible.

---

## Competing Interests

The author declares no competing interests.

## Author Contributions

G.W. conceived the framework, designed and implemented CopernicusAI, conducted the retrieval pilot, and wrote the manuscript.

## Funding

The author received no funding for this research.

## Data Availability

The live, interactive CopernicusAI system is publicly accessible at https://huggingface.co/spaces/garywelz/copernicusai, with the Knowledge Engine frontend deployed at https://copernicus-frontend-phzp4ie2sq-uc.a.run.app/knowledge-engine and the FastAPI backend at https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app. A machine-readable staging snapshot (`knowledge-engine-status.json`) is published to public cloud storage. The Programming Framework companion is published on Zenodo (https://doi.org/10.5281/zenodo.18463441), with a live demo at https://huggingface.co/spaces/garywelz/programming_framework. The evaluation corpus, query list, retrieval notebook, judgments, and metrics are archived at https://doi.org/10.5281/zenodo.18463303, the citable permanent record for this paper's empirical results. Operational notes on the evaluation corpus freeze are maintained in the repository (`docs/EVAL_FREEZE.md`).

---

## Declarations

### Ethical Approval

This is a computational research paper describing system architecture, methodology, and a retrieval pilot over publicly available research literature. No human participants were recruited, no sensitive personal data were processed, and no interventions were conducted. Prospective user studies referenced in Section 6 will require appropriate institutional review board approval prior to enrolment.

### Consent to Participate

Not applicable. No human participants are described in this paper. Future participatory studies referenced in Section 6 will obtain appropriate informed consent prior to data collection.

### Consent to Publish

Not applicable. No identifiable personal data or case records appear in this paper.

---

## Appendix A: Pilot Query Prompts

The following 30 queries were used in the preliminary retrieval pilot (Section 6). The list was frozen before evaluation; SHA256 of `appendix_queries.json`: `8fcfe7bcd50a85ba665ad065afe4a9623c38422da0254f78cdadac47d4dfdd1f`.

1. Probabilistic causal claims in single-cell perturbation screens: ML-heavy analyses, summaries, safeguards, and critiques (arXiv, 2024 onward)
2. Contrasts between transformer scaling-law narratives and recurrent memory-augmented architectures with empirical ablations
3. Automated peer-review augmentation: leakage critiques and dataset issues
4. Dissipative adaptation thermodynamics juxtaposed with maximum-entropy framings in statistical physics and neuroscience
5. Geometric deep learning for biomedical graph anomaly detection: open problems and pitfalls
6. Uncertainty in diffusion and generative models: a survey of negative results
7. Neuroscience reproducibility: Jupyter-heavy workflows, container critiques
8. Synthetic chart understanding in vision-language models: benchmark and distribution-shift critiques
9. Self-supervised protein representation learning: pitfalls and limited negative controls
10. Climate-econometrics causal inference: disclaimers, cross-domain challenges, robustness probes
11. Multilingual speech corpora: governance and consent issues
12. Robotics sim-to-real transfer: adversarial robustness surveys
13. Retrieval-augmented radiology assistants: evaluation, hallucination, and responsible deployment
14. Graph neural network oversmoothing: critiques and positional-encoding remedies
15. Federated learning with differential privacy in genomics meta-analysis: trade-offs
16. Computational modeling of political polarization: ethics and exploratory caution
17. Transformer carbon-accounting: methodological disputes
18. Ontology alignment and knowledge-graph embedding benchmarking: contradictions and surveys
19. SOAR, ACT-R, and CLARION versus neural hybrids: history and crosswalk
20. Hallucination taxonomies for conversational scientific assistants: fabrication, omission, confabulation
21. Reading-comprehension benchmark saturation: leaderboard inflation and adversarial filtration
22. Astronomical anomaly detection benchmarking: dataset bias
23. Multilingual toxicity classifiers: fairness and cultural nuance critiques
24. Wearable mental-health sensing: informed-consent and instrumentation critiques
25. Differentiable physics simulators: reproducibility pitfalls
26. Dataset lineage and combating scraped data recycling
27. Few-shot molecular property prediction: metric-learning and scaffold-split pitfalls
28. Conflicting empirical replications in adversarial purification
29. Large reasoning model evaluation: transparency and chain-of-thought cautions
30. Scientific foundation model benchmarking: methodological governance cautions

---

## References

1. Hogan, A., et al. (2021). Knowledge graphs. *ACM Computing Surveys*, 54(4), Article 71. https://doi.org/10.1145/3447772

2. Berners-Lee, T., Hendler, J., & Lassila, O. (2001). The semantic web. *Scientific American*, 284(5), 34–43.

3. Bizer, C., Heath, T., & Berners-Lee, T. (2009). Linked data: The story so far. *International Journal on Semantic Web and Information Systems*, 5(3), 1–22.

4. Kinney, R., et al. (2023). The Semantic Scholar Open Data Platform. *arXiv:2301.10140*.

5. Priem, J., Piwowar, H., & Orr, R. (2022). OpenAlex: A fully-open index of scholarly works. *arXiv:2205.01833*.

6. Karpukhin, V., et al. (2020). Dense passage retrieval for open-domain question answering. In *Proceedings of EMNLP*, 6769–6781.

7. Lewis, P., et al. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. *Advances in Neural Information Processing Systems*, 33, 9459–9474.

8. Lala, J., et al. (2023). PaperQA: Retrieval-augmented generative agent for scientific research. *arXiv:2312.07559*.

9. Taylor, R., et al. (2022). Galactica: A large language model for science. *arXiv:2211.09085*.

10. Ferrucci, D., et al. (2010). Building Watson: An overview of the DeepQA project. *AI Magazine*, 31(3), 59–79.

11. Ross, C., & Swetlitz, I. (2017). IBM pitched Watson as a revolution in cancer care. It's nowhere close. *STAT News*. https://www.statnews.com/2017/09/05/watson-ibm-cancer/

12. Manning, C. D., Raghavan, P., & Schütze, H. (2008). *Introduction to Information Retrieval*. Cambridge University Press.

13. Laird, J. E. (2012). *The SOAR Cognitive Architecture*. MIT Press.

14. Anderson, J. R. (2007). *How Can the Human Mind Occur in the Physical Universe?* Oxford University Press.

15. Model Context Protocol documentation (2024). https://modelcontextprotocol.io

16. Schick, T., et al. (2023). Toolformer: Language Models Can Teach Themselves to Use Tools. *arXiv:2302.04761*.

17. Welz, G. (2026). The Programming Framework: A general method for process analysis using LLMs and Mermaid visualization. Zenodo. https://doi.org/10.5281/zenodo.18463441

18. Sveidqvist, K., et al. Mermaid diagramming toolchain. GitHub repository. https://github.com/mermaid-js/mermaid

19. Shortliffe, E. H. (1976). *Computer-Based Medical Consultations: MYCIN*. Elsevier Science.

20. Lenat, D. B. (1995). CYC: A large-scale investment in knowledge infrastructure. *Communications of the ACM*, 38(11), 33–38.
