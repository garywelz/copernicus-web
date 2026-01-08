---
title: Copernicus AI - Research-Driven Podcast Generation Platform
emoji: 🔬
colorFrom: purple
colorTo: blue
sdk: static
pinned: false
license: mit
---

# 🔬 Copernicus AI - Knowledge Engine for Scientific Discovery

A collaborative research platform that transforms cutting-edge scientific research into accessible, multi-format tools for collective knowledge exploration. These are research instruments—like microscopes for observing the collective knowledge of humanity—enabling hypothesis formation, testing, and discovery across scientific disciplines.

## Summary

**CopernicusAI** is an operational research platform that synthesizes scientific literature from 250+ million papers into AI-generated podcasts, integrates with a knowledge graph of 12,000+ indexed papers, and provides collaborative tools for research discovery. The system demonstrates production-ready multi-source research synthesis with full citation tracking and evidence-based content generation requiring minimum 3 research sources per episode.

The platform includes a fully operational Knowledge Engine Dashboard (deployed December 2025) with interactive knowledge graph visualization, vector search, and RAG capabilities, enabling researchers to explore, query, and synthesize scientific knowledge across disciplines.

## Prior Work: CopernicusAI Research Interface

CopernicusAI is an active research prototype exploring AI-generated audio briefings as an interface for assisted scientific research.

The system allows any user to generate, refine, and share AI-generated science podcasts based on structured prompts, enabling rapid orientation to a topic, iterative deepening, and personalized research briefings.

Rather than functioning as a static content platform, CopernicusAI supports collectively generated and shared research artifacts, analogous to community-driven knowledge platforms (e.g., discussion forums), but grounded in scientific sources and metadata-aware workflows.

This work demonstrates technical feasibility for:
- AI-assisted research briefing and orientation
- Iterative question refinement via conversational interfaces
- Integration of text, audio, and metadata in research workflows

### Current Implementation (December 2025)

The Knowledge Engine Dashboard is **fully operational** and deployed to Google Cloud Run, providing unified access to all components with interactive knowledge graph visualization, vector search, RAG queries, and content browsing.

## 🎯 Mission & Vision

Inspired by Nicolaus Copernicus who challenged accepted knowledge with evidence and rigorous analysis, **Copernicus AI** creates collaborative research tools that enable collective participation in scientific discovery. These platforms are instruments for exploring humanity's collective knowledge—tools for hypothesis formation, testing, and collaborative research, not just educational content.

Just as a microscope enables observation of the microscopic world, Copernicus AI tools enable observation and exploration of humanity's collective knowledge. Subscribers collaborate to prompt, generate, and refine research content—sharing discoveries publicly or keeping them private. As large language models (LLMs) and AI systems gain unprecedented knowledge, Copernicus AI provides the infrastructure for human-AI collaborative knowledge exploration, with evidence-based truth-seeking as our guiding principle.

---

## 🌟 Core Platform Capabilities

### 🎙️ AI-Powered Podcast Generation

**Production-Ready System:**
- Collaborative platform where subscribers prompt and generate multi-voice AI podcasts (5-10 minutes) synthesizing research from multiple academic sources
- Subscribers can share their podcasts publicly or keep them private
- Evidence-based content generation requiring minimum 3 research sources per episode
- Comprehensive research integration across 8+ academic databases
- **64 episodes** generated across Biology, Chemistry, Computer Science, Mathematics, and Physics
- Automated audio synthesis with professional multi-speaker dialogue
- AI-generated episode thumbnails with scientific visualizations
- RSS feed distribution compatible with Spotify, Apple Podcasts, Google Podcasts

**Research Integration:**
- Real-time discovery from PubMed, arXiv, NASA ADS, Zenodo, bioRxiv, CORE, Google Scholar, and News APIs
- Parallel search across multiple databases for comprehensive coverage
- Quality scoring and relevance ranking of research sources
- Paradigm shift identification and interdisciplinary connection analysis
- Automatic citation extraction and formatting
- Source validation and authenticity verification

### 🤖 Advanced LLM Integration

**Multi-Model Architecture:**
- **Google Gemini 3** - Latest research analysis and content generation
- **OpenAI GPT-4/GPT-3.5** - Content synthesis and quality validation
- **Anthropic Claude 3** (Sonnet, Haiku via OpenRouter) - Alternative reasoning paths
- **ElevenLabs TTS** - Multi-voice text-to-speech synthesis
- Model selection based on task complexity and expertise level
- Fallback chains for reliability and cost optimization

**Capabilities:**
- Multi-paper analysis and synthesis
- Paradigm shift detection in research domains
- Interdisciplinary connection identification
- Entity extraction (genes, proteins, chemical compounds, mathematical concepts)
- Citation tracking and cross-reference analysis
- Content quality scoring and validation

### 📊 Research Resource Access

**Comprehensive Academic Database Coverage:**

Our research pipeline integrates with **8+ major academic databases**, providing access to:

- **PubMed/NCBI** (~30+ million biomedical papers)
- **arXiv** (~2+ million preprints in physics, mathematics, CS, quantitative biology)
- **NASA ADS** (~15+ million astronomy/astrophysics papers)
- **Zenodo** (100K+ open science datasets and publications)
- **bioRxiv/medRxiv** (preprints in life sciences)
- **CORE** (~200+ million open access papers)
- **Google Scholar** (comprehensive academic search)
- **News API** (current events and trending research topics)
- **YouTube Data API** (academic videos, conference talks, lectures)

**Total Access:** **250+ million research papers and academic resources** across all major scientific disciplines.

### 🎙️ Audio and Video Podcast Production

**Operating Audio Podcast System:**
Full production and distribution platform for subscriber-generated podcasts. Users can prompt, generate, publish, and distribute audio podcasts with RSS feed support for Spotify, Apple Podcasts, and Google Podcasts.

- Multi-voice AI podcast generation
- Research-driven content creation
- RSS feed distribution
- Public and private podcast options
- Professional audio quality

**Video Production (Future - Phase 2+):**

Advanced video features planned for future development:

**Planned Advanced Features (Phase 2-4):**
- **Visual Content Integration:**
  - Automated extraction of figures and diagrams from research papers
  - Screen capture and processing of academic illustrations
  - Web scraping from scientific journal websites and preprint servers
  - JSON database integration for structured visual data

- **Dynamic Visualization Generation:**
  - On-the-fly scientific animations (molecular structures, data flows, algorithms)
  - Real-time chart and graph generation from research data
  - Python-based animations using matplotlib, plotly, mayavi
  - Mathematical formula rendering (LaTeX → video)

- **External Video Quoting:**
  - YouTube video segment extraction and integration
  - Time-stamped video quoting with proper attribution
  - Educational fair use compliance
  - Source video discovery during research phase

- **Advanced Composition:**
  - Multi-layer video composition (background, content, overlays, effects)
  - Automatic subtitle generation from transcripts
  - Text overlay system (key concepts, citations, speaker identification)
  - Professional transitions and effects
  - Audio-visual synchronization

**See:** [Science Video Database](https://huggingface.co/spaces/garywelz/sciencevideodb) - Companion project for research video content management.

### 📚 Research Papers Metadata Database (Phase 2)

**Planned Implementation:**
A centralized **metadata repository** (not a file archive) that provides:

- **Structured JSON Objects:** Research paper metadata including:
  - DOI, arXiv ID, publication information
  - Abstracts and key findings
  - Extracted entities (genes, proteins, chemical compounds, equations)
  - Citation networks and cross-references
  - Paradigm shift indicators
  - Interdisciplinary connections
  - Quality scores and relevance metrics

- **AI-Powered Preprocessing:**
  - LLM-based entity extraction and annotation
  - Automatic categorization by discipline and subdomain
  - Keyword extraction and semantic tagging
  - Citation tracking and relationship mapping
  - Quality assessment and validation

- **Integration Features:**
  - DOI/arXiv ID resolution and metadata enrichment
  - Cross-reference linking between papers
  - Podcast-to-paper relationship tracking
  - Search and query capabilities
  - API access for programmatic retrieval

**Technical Architecture:**
- Firestore NoSQL database for flexible JSON storage
- Google Cloud Functions for automated metadata processing
- Vertex AI for entity extraction and analysis
- RESTful API for external access

**Benefits:**
- Enables rapid research discovery across podcasts
- Supports knowledge graph construction
- Facilitates cross-disciplinary pattern recognition
- Provides foundation for semantic search capabilities

---

## 🗄️ System Architecture

### Database Structure (Firestore)

**Collections:**
- **`subscribers`** - User accounts, preferences, subscription tiers, usage analytics
- **`podcast_jobs`** - Generated podcasts with full metadata, source papers, engagement metrics
- **`episodes`** - Published episodes with RSS distribution status
- **`research_papers`** (Phase 2) - Paper metadata database with AI-extracted entities

### Storage Structure (Google Cloud Storage)

- **`audio/`** - MP3 podcast files (multi-voice ElevenLabs synthesis)
- **`videos/`** - MP4 video podcasts (current and future)
- **`transcripts/`** - Full text transcripts with speaker markers
- **`descriptions/`** - Markdown descriptions with academic references
- **`thumbnails/`** - AI-generated episode artwork (DALL-E 3)
- **`video-assets/`** - Extracted figures, animations, visual content
- **`glmp-v2/`** - Genome Logic Modeling Project flowcharts (JSON)

### Backend Services (Google Cloud Run)

**Microservices Architecture:**
- **Podcast Generation Service** - Orchestrates research, content generation, and media production
- **Research Pipeline Service** - Multi-API academic search and analysis
- **Video Generation Service** - Video composition and encoding (Phase 1 complete)
- **RSS Service** - Feed generation and distribution
- **Episode Service** - Catalog management and metadata

---

## ⚙️ Technology Stack

### AI & Machine Learning
- **Google Gemini 3** - Latest LLM for research analysis
- **Google Vertex AI** - Enterprise-scale model deployment and orchestration (used throughout platform)
- **OpenAI GPT-4/GPT-3.5** - Content synthesis and validation
- **Anthropic Claude 3** - Alternative reasoning via OpenRouter
- **ElevenLabs TTS** - Multi-voice text-to-speech synthesis
- **DALL-E 3** - AI-generated scientific visualizations
- **Google Cloud Vision API** - Image analysis and quality assessment
- **Video Intelligence API** - Scene detection and content analysis

### Backend Infrastructure
- **FastAPI** (Python) - RESTful API framework
- **Google Cloud Run** - Serverless container deployment
- **Firestore** - NoSQL document database
- **Cloud Storage** - Media file storage and CDN
- **Cloud Functions** - Event-driven processing
- **Cloud Tasks** - Background job queuing
- **Secret Manager** - API key and credential management

### Media Processing
- **FFmpeg** - Video encoding and composition
- **MoviePy** - Python video editing (planned)
- **Matplotlib/Plotly** - Scientific visualization (planned)
- **PyPDF2/pdfplumber** - PDF processing (planned)

### Frontend
- **Next.js 15.5.7** - React framework
- **Alpine.js** - Lightweight reactive UI
- **Tailwind CSS** - Utility-first styling
- **Vercel** - Frontend hosting and deployment

---

## 📈 Platform Capabilities

### Research Coverage
- **250+ million research papers** accessible through integrated APIs
- **8+ academic databases** integrated with parallel search
- **Minimum 3 sources** required per episode for quality assurance
- **Multi-paper analysis** for comprehensive coverage

### Platform Features
- **Subscriber-driven content generation** - Users prompt and create podcasts
- **RSS feed distribution** to major podcast platforms
- **Public and private podcast options** - Share discoveries or keep them private

---

## 🔗 Live Platform & Resources

### Production Deployment
- 🏠 **[Homepage - Browse Podcasts](https://www.copernicusai.fyi)** - Public podcast catalog
- 📊 **[Creator Dashboard](https://www.copernicusai.fyi/subscriber-dashboard.html)** - Subscriber interface
- 📡 **[RSS Feed](https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/feeds/copernicus-mvp-rss-feed.xml)** - Podcast distribution feed

## 🧩 CopernicusAI Knowledge Engine Components

The CopernicusAI Knowledge Engine is an integrated ecosystem of research and collaboration tools. The Knowledge Engine is **fully implemented and operational** (December 2025), with a working system deployed to Google Cloud Run. Currently, the platform includes five core components, with additional tools, databases, and collaboration features planned for future development:

### 🎯 Knowledge Engine Implementation (December 2025)

**Fully Operational System:**
- **Live Dashboard:** https://copernicus-frontend-phzp4ie2sq-uc.a.run.app/knowledge-engine
- **Knowledge Graph:** Interactive visualization with 12,000+ indexed mathematics papers, relationship extraction (citations, semantic similarity, categories), and graph query capabilities
- **Vector Search:** Semantic search using Vertex AI embeddings across papers, podcasts, and processes
- **RAG System:** Retrieval-augmented generation with citation support, context retrieval, and multi-modal content integration
- **Unified Web Dashboard:** Production-ready interface with knowledge map visualization, search, RAG queries, content browsing, and statistics
- **Architecture:** FastAPI backend, Next.js frontend, Firestore database, Vertex AI for embeddings and LLM capabilities, Model Context Protocol (MCP) server for AI assistant integration
- **Deployment:** Fully deployed to Google Cloud Run, accessible 24/7

### Core Components

1. **🔬 Copernicus AI (This Platform)** - Core synthesis and distribution component
   - AI-powered research synthesis and podcast generation
   - Multi-API research integration (250+ million papers)
   - Subscriber-driven content creation and sharing
   - RSS feed distribution and platform management

2. **🛠️ Programming Framework** - Foundational meta-tool
   - Universal method for process analysis across any discipline
   - LLM-powered extraction and Mermaid visualization
   - Domain-agnostic methodology for complex process analysis
   - [Explore Framework →](https://huggingface.co/spaces/garywelz/programming_framework)

3. **🧬 GLMP - Genome Logic Modeling Project** - Specialized biological application
   - First application of Programming Framework to biology
   - 50+ biological processes visualized as interactive flowcharts
   - JSON-based structured data in Google Cloud Storage
   - [Explore GLMP →](https://huggingface.co/spaces/garywelz/glmp)

4. **📚 Research Paper Metadata Database** - Core data infrastructure
   - Centralized metadata repository for scientific research papers
   - AI-powered preprocessing and entity extraction
   - Citation network analysis and relationship mapping
   - Foundation for knowledge graph construction
   - [Explore Metadata Database →](https://huggingface.co/spaces/garywelz/metadata_database)

5. **🎬 Science Video Database** - Multi-modal content component
   - Curated searchable database of scientific video content
   - Transcript-based search across multiple disciplines
   - Integration with YouTube and other video sources
   - [Explore Video Database →](https://huggingface.co/spaces/garywelz/sciencevideodb)
   - [Live Demo →](https://scienceviddb-web-204731194849.us-central1.run.app/)

### Future Components

The Knowledge Engine is designed to grow and evolve. Additional tools, databases, and collaboration components will be added as the project develops, expanding capabilities for AI-assisted scientific research and knowledge discovery.

---

## 🔌 API Documentation

**Base URL:** `https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app`

### Podcast Generation Endpoints
- `POST /generate-podcast-with-subscriber` - Generate new podcast from research topic
- `GET /api/subscribers/podcasts/{id}` - Retrieve podcast details
- `POST /api/subscribers/podcasts/submit-to-rss` - Publish to RSS feed

### Research Endpoints
- `POST /api/papers/upload` - Upload paper metadata (Phase 2)
- `GET /api/papers/{paper_id}` - Retrieve paper metadata
- `POST /api/papers/query` - Query papers by discipline, keywords
- `POST /api/papers/{id}/link-podcast/{id}` - Link paper to podcast

### Admin Endpoints
- `GET /api/admin/subscribers` - List all subscribers and statistics
- `POST /api/admin/podcasts/fix-missing-titles` - Content maintenance
- `GET /api/admin/podcasts/catalog` - Full podcast catalog

---

## 🚀 Development Roadmap

### ✅ Phase 1: Core Platform (Complete)
- Multi-API research integration
- AI podcast generation with multi-voice synthesis
- RSS feed distribution
- Subscriber platform
- Basic video generation (static)

### 🔄 Phase 2: Content Enhancement (In Progress)
- **Research Papers Metadata Database** - JSON-based metadata repository
- **Visual Content Extraction** - Figures from papers, web scraping
- **YouTube Video Quoting** - External video integration with attribution
- **Advanced Video Features** - Multi-layer composition, animations

### 📋 Phase 3: Advanced Visualizations (Planned)
- Scientific animation generation (matplotlib, plotly)
- Real-time data visualization
- Mathematical formula rendering
- Dynamic graph and network visualizations

### ✅ Phase 4: Knowledge Integration (Implemented - December 2025)
- **Knowledge Graph:** Fully operational with interactive visualization, 12,000+ papers indexed
- **Vector Search:** Semantic search implemented using Vertex AI embeddings
- **RAG System:** Retrieval-augmented generation with citations operational
- **Cross-Disciplinary Pattern Discovery:** Relationship extraction across papers, concepts, and categories
- **AI-Powered Content Recommendations:** Integrated into unified web dashboard
- **Live System:** https://copernicus-frontend-phzp4ie2sq-uc.a.run.app/knowledge-engine

---

## 🔬 Collaborative Research Tools

**These platforms enable collective participation and collaboration across diverse user communities:**

- **Researchers** - Tools for hypothesis formation and testing, rapid synthesis of cross-disciplinary findings
- **Collaborators** - Collective knowledge exploration and refinement
- **Subscribers** - Prompt, generate, and share podcasts (public or private)
- **Community** - User suggestions, comments, and collaborative flowchart improvement (GLMP)

**Key Innovations:**
- **Multi-Source Validation** - Requires minimum 3 research sources per episode
- **Evidence-Based Generation** - No content generated without research backing
- **Paradigm Shift Detection** - Identifies revolutionary vs. incremental research
- **Interdisciplinary Connections** - Reveals cross-domain insights
- **Collaborative Participation** - User-driven content generation and sharing
- **Reproducibility** - Full citation tracking and source attribution

> *Like a microscope enables observation of the microscopic world, these tools enable observation and exploration of humanity's collective knowledge.*

---

## 📚 Prior Work & Research Contributions

### Overview
This platform represents **prior work** that demonstrates foundational research and development achievements in AI-powered scientific knowledge synthesis, collaborative research tools, and multi-modal content generation. These contributions establish the technical foundation and proof-of-concept for the broader **CopernicusAI Knowledge Engine** initiative.

### Research Contributions

**1. AI-Powered Research Synthesis System**
- Developed and deployed a production-ready system for multi-source research synthesis using LLMs
- Demonstrated integration of 8+ academic databases (250+ million papers) with parallel search capabilities
- Implemented evidence-based content generation requiring minimum 3 research sources per output
- Achieved operational deployment with 64+ generated podcast episodes across 5 scientific disciplines

**2. Multi-Model LLM Architecture**
- Designed and implemented intelligent model selection framework using Google Gemini 3, OpenAI GPT-4, and Anthropic Claude 3
- Developed fallback chains for reliability and cost optimization
- Demonstrated paradigm shift detection and interdisciplinary connection identification in research domains
- Implemented entity extraction (genes, proteins, chemical compounds, mathematical concepts) from research literature

**3. Collaborative Research Platform Infrastructure**
- Built subscriber-driven content generation system enabling public/private research sharing
- Implemented RSS feed distribution compatible with major podcast platforms
- Developed microservices architecture on Google Cloud Run with Firestore and Cloud Storage
- Created RESTful API framework for programmatic access to research synthesis capabilities

**4. Integration with Knowledge Engine Components**
- Established integration pathways with GLMP (Genome Logic Modeling Project) for biological process visualization
- Designed architecture for Research Papers Metadata Database (Phase 2)
- Planned integration with Science Video Database for multi-modal content
- Created framework for Programming Framework integration across disciplines

### Technical Achievements

**Production Deployment:**
- Live platform: https://www.copernicusai.fyi
- Operational API: https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app
- RSS feed distribution: Active and functional
- Multi-voice audio synthesis: ElevenLabs TTS integration operational

**Research Infrastructure:**
- 250+ million research papers accessible via integrated APIs
- 8+ academic database integrations (PubMed, arXiv, NASA ADS, Zenodo, bioRxiv, CORE, Google Scholar, News API)
- **12,000+ mathematics papers indexed** with full metadata and vector embeddings in Knowledge Engine
- Automated citation extraction and formatting
- Quality scoring and relevance ranking systems
- **Knowledge Graph:** Fully operational with relationship extraction and interactive visualization
- **Vector Search:** Semantic search across papers, podcasts, and processes
- **RAG System:** Operational with citation support and multi-modal content integration

**Scalability & Architecture:**
- Serverless microservices architecture (Google Cloud Run)
- NoSQL database (Firestore) for flexible metadata storage
- Cloud Storage for media files and structured data
- Event-driven processing with Cloud Functions and Cloud Tasks

### Position Within CopernicusAI Knowledge Engine

This platform serves as the **core synthesis and distribution component** of the CopernicusAI Knowledge Engine. The Knowledge Engine is an integrated ecosystem of research and collaboration tools that work together to assist scientists in their workflow, from research discovery through knowledge synthesis to multi-format content generation.

**Current Components:**
1. **Copernicus AI** (This platform) - Core synthesis and distribution component for AI-powered research synthesis and podcast generation
2. **Knowledge Engine Dashboard** (✅ Implemented December 2025) - Fully operational web interface with knowledge graph visualization, vector search, RAG queries, content browsing, and statistics. Live at: https://copernicus-frontend-phzp4ie2sq-uc.a.run.app/knowledge-engine
3. **Programming Framework** - Foundational meta-tool providing universal process analysis methodology
4. **GLMP (Genome Logic Modeling Project)** - Specialized biological application demonstrating domain-specific use of the Programming Framework
5. **Research Paper Metadata Database** - Core data infrastructure providing structured metadata and citation networks
6. **Science Video Database** - Multi-modal content component enabling video-based learning and research discovery

**Future Development:**
The Knowledge Engine is designed to grow and evolve. Additional tools, databases, and collaboration components will be added as the project develops, expanding capabilities for AI-assisted scientific research and knowledge discovery.

### Academic & Research Impact

**Publications & Presentations:**
- Platform architecture and methodology suitable for academic publication
- Open-source components available for research community use
- Publicly accessible research tools demonstrating AI-human collaboration in scientific knowledge synthesis

**Research Applications:**
- Supports hypothesis formation and testing through rapid multi-source synthesis
- Enables cross-disciplinary pattern recognition and connection identification
- Facilitates reproducible research communication with full citation tracking
- Provides infrastructure for collaborative knowledge exploration

**Educational Contributions:**
- 64+ research-driven podcast episodes across Biology, Chemistry, Computer Science, Mathematics, and Physics
- Evidence-based content requiring minimum 3 academic sources
- Public and private sharing options for research dissemination
- Integration with major podcast platforms for broad accessibility

### Citation Information

**For Grant Proposals:**
When citing this work as prior research, please reference:

- **Platform Name:** Copernicus AI - Knowledge Engine for Scientific Discovery
- **URL:** https://huggingface.co/spaces/garywelz/copernicusai
- **Live Platform:** https://www.copernicusai.fyi
- **Primary Developer:** Gary Welz
- **Year:** 2024-2025
- **License:** MIT

**Suggested Citation Format:**
```
Welz, G. (2025). Copernicus AI: Knowledge Engine for Scientific Discovery. 
Hugging Face Space. https://huggingface.co/spaces/garywelz/copernicusai
```

## 🌐 Grant Support & Collaboration

**Grant Applications Supported:**
This platform is designed to support grant applications to:
- **NSF (National Science Foundation)** - Science education and research infrastructure
- **DOE (Department of Energy)** - Scientific computing and data science
- **SAIR Foundation** - AI research and development initiatives

**Research Contributions:**
- Open-source components and methodologies
- Publicly accessible research tools
- Educational content for broader scientific literacy
- Infrastructure for reproducible research communication

**Collaboration Opportunities:**
- Integration with academic institutions
- Partnership with research organizations
- Open data initiatives
- Educational program development

---

## How to Cite This Work

Welz, G. (2024–2025). *CopernicusAI: AI-Generated Audio Briefings as a Research Interface*.
Hugging Face Spaces. https://huggingface.co/spaces/garywelz/copernicusai

---

## 📄 License & Attribution

**License:** MIT

**Attributions:**
- Built with Google Cloud Platform, Gemini AI, OpenAI, Anthropic Claude, and ElevenLabs
- Research data from PubMed, arXiv, NASA ADS, Zenodo, bioRxiv, CORE, and Google Scholar
- Academic paper metadata from respective publishers

---

## 📧 Contact & Support

For questions, collaboration inquiries, or grant application support:
- **Hugging Face Space:** [https://huggingface.co/spaces/garywelz/copernicusai](https://huggingface.co/spaces/garywelz/copernicusai)
- **Platform:** [https://www.copernicusai.fyi](https://www.copernicusai.fyi)

---

**© 2025 Copernicus AI. All rights reserved.**

*Advancing scientific knowledge through AI-powered research communication and discovery.*
