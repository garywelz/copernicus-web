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

A comprehensive AI-powered platform that transforms cutting-edge scientific research into accessible, multi-format educational content while building a centralized metadata database connecting concepts, papers, and insights across scientific disciplines.

## 🎯 Mission & Vision

Inspired by Nicolaus Copernicus who challenged accepted knowledge with evidence and rigorous analysis, **Copernicus AI** aims to democratize scientific knowledge by creating advanced tools that help researchers, educators, and the public explore, understand, and communicate scientific insights at the speed and depth that modern AI systems enable.

> "I want to know a lot, and I want to be confident that I am learning and disseminating the truth."

As large language models (LLMs) and AI systems gain unprecedented knowledge and intelligence, Copernicus AI provides the infrastructure for human-AI collaborative knowledge exploration, with evidence-based truth-seeking as our guiding principle.

---

## 🌟 Core Platform Capabilities

### 🎙️ AI-Powered Podcast Generation

**Production-Ready System:**
- Multi-voice AI podcasts (5-10 minutes) synthesizing research from multiple academic sources
- Evidence-based content generation requiring minimum 3 research sources per episode
- Comprehensive research integration across 8+ academic databases
- **64+ episodes** generated across Biology, Chemistry, Computer Science, Mathematics, and Physics
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
- **Google Gemini 2.0** (Pro, Flash) - Primary research analysis and content generation
- **OpenAI GPT-4/GPT-3.5** - Content synthesis and quality validation
- **Anthropic Claude 3** (Sonnet, Haiku via OpenRouter) - Alternative reasoning paths
- **Vertex AI** - Enterprise-scale model deployment
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

### 🎬 Video Production System (Phase 1 Complete, Advanced Features in Development)

**Current Capabilities:**
- Static video generation (thumbnail + audio → MP4)
- Professional encoding for YouTube/podcast platforms
- Multiple resolution options (1080p, 720p, 480p)
- Google Cloud Storage integration

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
- **Google Gemini 2.0** (Pro, Flash) - Primary LLM for research analysis
- **OpenAI GPT-4/GPT-3.5** - Content synthesis and validation
- **Anthropic Claude 3** - Alternative reasoning via OpenRouter
- **Vertex AI** - Enterprise model deployment
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

## 📈 Current Platform Statistics

### Content Production
- **64+ Podcast Episodes** generated across 5 disciplines
  - **Biology:** 9 episodes (molecular biology, genetics, neuroscience)
  - **Chemistry:** 4 episodes (materials science, biochemistry)
  - **Computer Science:** 6 episodes (AI, algorithms, quantum computing)
  - **Mathematics:** 6 episodes (theoretical mathematics, applied math)
  - **Physics:** 7 episodes (quantum mechanics, particle physics, astrophysics)

### Research Coverage
- **250+ million research papers** accessible through integrated APIs
- **8+ academic databases** integrated with parallel search
- **Minimum 3 sources** required per episode for quality assurance
- **Multi-paper analysis** for comprehensive coverage

### Platform Usage
- **3 active subscribers** with custom podcast generation
- **RSS feed distribution** to major podcast platforms
- **Public catalog** for discovery and browsing

---

## 🔗 Live Platform & Resources

### Production Deployment
- 🏠 **[Homepage - Browse Podcasts](https://www.copernicusai.fyi)** - Public podcast catalog
- 📊 **[Creator Dashboard](https://www.copernicusai.fyi/subscriber-dashboard.html)** - Subscriber interface
- 📡 **[RSS Feed](https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/feeds/copernicus-mvp-rss-feed.xml)** - Podcast distribution feed

### Related Projects
- 🔬 **[GLMP - Genome Logic Modeling Project](https://huggingface.co/spaces/garywelz/glmp)** - Biological pathway visualization
- 🛠️ **[Programming Framework](https://huggingface.co/spaces/garywelz/programming_framework)** - Universal process analysis tool
- 🎬 **[Science Video Database](https://huggingface.co/spaces/garywelz/sciencevideodb)** - Research video content management
- 📁 **[GLMP Data Collection (GCS)](https://console.cloud.google.com/storage/browser/regal-scholar-453620-r7-podcast-storage/glmp-v2)** - Structured pathway data

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

### 🎯 Phase 4: Knowledge Integration (Planned)
- Knowledge graph construction
- Semantic search capabilities
- Cross-disciplinary pattern discovery
- AI-powered content recommendations

---

## 🎓 Research & Educational Impact

**Target Audiences:**
- **Researchers** - Rapid synthesis of cross-disciplinary findings
- **Educators** - Engaging content for teaching complex concepts
- **Students** - Accessible explanations of cutting-edge research
- **General Public** - Science communication and literacy

**Key Innovations:**
- **Multi-Source Validation** - Requires minimum 3 research sources per episode
- **Evidence-Based Generation** - No content generated without research backing
- **Paradigm Shift Detection** - Identifies revolutionary vs. incremental research
- **Interdisciplinary Connections** - Reveals cross-domain insights
- **Accessibility** - Multiple expertise levels (beginner, intermediate, expert)
- **Reproducibility** - Full citation tracking and source attribution

---

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
