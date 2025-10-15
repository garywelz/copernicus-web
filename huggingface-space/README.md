---
title: Copernicus AI
emoji: 🔬
colorFrom: purple
colorTo: blue
sdk: static
pinned: false
license: mit
---

# 🔬 Copernicus AI - Knowledge Engine for Scientific Discovery

A comprehensive knowledge engine that transforms cutting-edge research into accessible AI-powered podcasts while building a knowledge graph connecting concepts, papers, and insights across scientific disciplines.

## 🎯 Mission

Inspired by the historical Copernicus who challenged accepted knowledge with evidence and rigorous analysis, Copernicus AI aims to expand human knowledge by creating tools that help us verify, generate, and transmit scientific insights. As AI systems become more capable, we build instruments that enable humans to explore, understand, and communicate knowledge with the same depth and speed that AI possesses.

## 🚀 Core Components

### 🎙️ AI Podcast Generation
- Multi-voice AI podcasts (5-10 minutes) synthesizing research papers
- Powered by Google Gemini 2.0 + ElevenLabs TTS
- 32+ episodes across Biology, Chemistry, Computer Science, Mathematics, Physics
- Scientific references and hashtags included
- Subscriber-generated content with RSS distribution

### 🔧 Programming Framework
- Meta-tool for process analysis combining LLMs with Mermaid visualization
- Universal method for dissecting complex processes across any discipline
- Domain-agnostic analysis and flowchart generation

### 🧬 GLMP - Genome Logic Modeling Project
- Specialized "microscope" applying the Programming Framework to biochemistry
- Visualizes biological processes as interactive flowcharts
- JSON-based pathway visualization

### 📚 Research Papers Database (Phase 1)
- Centralized repository of scientific literature with AI preprocessing
- DOI/arXiv integration with LLM-powered entity extraction
- Tracks genes, proteins, equations, methods
- Citation tracking and reuse across podcasts

### 🕸️ Knowledge Graph (Phase 2)
- Connects concepts, papers, podcasts, and GLMP visualizations
- Enables cross-disciplinary pattern discovery
- Semantic search capabilities

### 👥 Subscriber Platform
- YouTube-style interface for creators
- Custom podcast generation with source paper integration
- Browse public catalog or create custom content
- RSS feed publishing

## 🗄️ Database Architecture

### Firestore Collections
- **subscribers** - User accounts, preferences, usage analytics
- **podcast_jobs** - Generated podcasts with metadata, engagement metrics
- **research_papers** - Scientific papers with AI preprocessing

### Google Cloud Storage
- **audio/** - MP3 podcast files (multi-voice synthesis)
- **transcripts/** - Full text transcripts
- **descriptions/** - Markdown descriptions with references
- **thumbnails/** - AI-generated episode artwork
- **glmp-v2/** - Genome Logic flowcharts (JSON)

### Enhanced Metadata (Phase 1)
Each podcast includes: source papers (DOIs/URLs), extracted keywords, quality scores, GLMP visualization links, and engagement metrics.

## ⚙️ Technology Stack

**AI & ML:**
- Google Gemini 2.0 Flash
- Vertex AI
- ElevenLabs TTS
- Entity extraction

**Backend:**
- FastAPI (Python)
- Google Cloud Run
- Firestore (NoSQL)
- Cloud Storage

**Frontend:**
- Static HTML/Alpine.js
- Tailwind CSS
- Vercel (hosting)

## 🔗 Links & Resources

### Live Platform
- 🏠 [Homepage - Browse Podcasts](https://www.copernicusai.fyi)
- 📊 [Creator Dashboard](https://www.copernicusai.fyi/subscriber-dashboard.html)
- 📡 [RSS Feed](https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/feeds/copernicus-mvp-rss-feed.xml)

### Related Projects
- 🔬 [GLMP - Genome Logic Modeling](https://huggingface.co/spaces/garywelz/glmp)
- 🛠️ [Programming Framework](https://huggingface.co/spaces/garywelz/programming_framework)
- 📁 [GLMP Data Collection (GCS)](https://console.cloud.google.com/storage/browser/regal-scholar-453620-r7-podcast-storage/glmp-v2)

## 🔌 API Endpoints

Base URL: `https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app`

**Podcast Generation:**
- `POST /generate-podcast-with-subscriber`
- `GET /api/subscribers/podcasts/{id}`
- `POST /api/subscribers/podcasts/submit-to-rss`

**Research Papers (Phase 1):**
- `POST /api/papers/upload`
- `GET /api/papers/{paper_id}`
- `POST /api/papers/query`
- `POST /api/papers/{id}/link-podcast/{id}`

## 📊 Current Stats

- **32 Podcasts** across 5 disciplines
- **Biology:** 9 episodes
- **Chemistry:** 4 episodes  
- **Computer Science:** 6 episodes
- **Mathematics:** 6 episodes
- **Physics:** 7 episodes

## 🌟 The Vision

> "I want to know a lot, and I want to be confident that I am learning and disseminating the truth."

As LLMs and other forms of AI gain more knowledge and intelligence, the Copernicus AI project enables humans to keep up with what the AIs are capable of knowing and revealing. We're building the infrastructure for human-AI collaborative knowledge exploration, with truth-seeking as our North Star.

---

**Built with Google Cloud, Gemini AI, ElevenLabs, and Vercel**

© 2025 Copernicus AI. All rights reserved.

