---
title: Science Video Database
emoji: 🔬
colorFrom: blue
colorTo: purple
sdk: static
pinned: false
license: mit
---

# 🔬 Science Video Database

A curated search experience for technical science enthusiasts, featuring biology, chemistry, computer science, mathematics, and physics videos from YouTube and other sources, searchable by transcript.

## 📚 Prior Work & Research Contributions

### Overview
The Science Video Database represents **prior work** that demonstrates the creation of a curated, searchable database of scientific video content. This project establishes a foundation for integrating video-based learning and research content into the CopernicusAI Knowledge Engine, enabling multi-modal knowledge exploration through searchable transcripts and filtered scientific video content.

### 🔬 Research Contributions
- **Curated Video Collection:** Filtered scientific videos from YouTube and other sources across multiple disciplines
- **Transcript-Based Search:** Searchable video database using transcript content for discovery
- **Multi-Disciplinary Coverage:** Biology, chemistry, computer science, mathematics, and physics content
- **Integration Framework:** Designed for integration with CopernicusAI Knowledge Engine components

### ⚙️ Technical Achievements
- **Hybrid Search System:** Transcript-based search with filtering capabilities
- **Ingestion Pipeline:** Automated video ingestion and transcript processing
- **Vector Database Integration:** Support for semantic search using embeddings
- **Scalable Architecture:** Designed for scaling from prototype (2k videos) to production (200k+ videos)

### 🎯 Position Within CopernicusAI Knowledge Engine
The Science Video Database serves as a **multi-modal content component** of the CopernicusAI Knowledge Engine, providing:

- **Video Content Integration:** Enables video-based learning and research content discovery
- **Transcript Search:** Searchable transcripts support research discovery and content linking
- **Multi-Modal Learning:** Complements text-based (podcasts) and visual (GLMP) content
- **Knowledge Engine Dashboard Integration** (✅ Implemented December 2025) - Video content accessible through unified dashboard with knowledge graph visualization, vector search, and RAG queries. Live at: https://copernicus-frontend-phzp4ie2sq-uc.a.run.app/knowledge-engine
- **Research Paper Linking:** Integration with Research Paper Metadata Database (12,000+ papers indexed)
- **AI Podcast Enhancement:** Can provide video sources for podcast generation

This work establishes a proof-of-concept for AI-assisted video content management in scientific research, demonstrating how searchable transcripts can enable systematic discovery and integration of video-based knowledge. The Knowledge Engine now provides a unified interface for exploring video content alongside research papers, podcasts, and processes.

## 🎯 Project Overview

A curated search experience for technical science enthusiasts, featuring:
- Biology, chemistry, computer science, mathematics, and physics videos
- YouTube and other video sources
- Transcript-based search capabilities
- Filtered and curated scientific content

## 🚀 Project Milestones

### Prototype (Current Phase)
- 10-15 channels, ~2k videos
- Basic ingestion pipeline
- Transcript storage
- Hybrid search UI with filters

### Alpha (Next Phase)
- 50+ channels, 20k videos
- Personalization MVP
- Email digests
- Improved UX polish

### Scaling (Future)
- 200k videos
- Autoscaling workers
- Admin dashboard
- Automated QA

## 🔧 Technical Architecture

### Frontend
- **Next.js 14** (App Router)
- React Server Components
- Hybrid search UI with filters

### Backend
- **Node.js/TypeScript** serverless functions
- Video ingestion worker
- Transcript processing pipeline

### Database & Storage
- **PostgreSQL** (Supabase/Neon) for metadata
- **Vector DB** (Pinecone/Weaviate/Qdrant) for semantic search
- **Search Engine** (OpenSearch/Elasticsearch or Meilisearch)

### Cloud Platform
- **Google Cloud Platform** (regal-scholar-453620-r7)
  - Secrets Manager (for API keys)
  - Cloud Storage (for assets)
  - Vertex AI (for embeddings)
  - Cloud Run (for deployment)

### Deployment
- **Vercel** (frontend)
- **Google Cloud Run** (ingestion)

## 🔗 Related Projects

- [Copernicus AI](https://huggingface.co/spaces/garywelz/copernicusai) - Main knowledge engine that can integrate video content
- [Research Paper Metadata Database](https://huggingface.co/spaces/garywelz/metadata_database) - Potential integration for linking videos to papers
- [GLMP](https://huggingface.co/spaces/garywelz/glmp) - Biological process visualization that could link to related videos
- [Programming Framework](https://huggingface.co/spaces/garywelz/programming_framework) - Process analysis tool that could utilize video content

## 💻 Technology Stack

- **Frontend:** Next.js 14, React Server Components
- **Backend:** Node.js/TypeScript, serverless functions
- **Database:** PostgreSQL, Vector DB (Pinecone/Weaviate/Qdrant)
- **Search:** OpenSearch/Elasticsearch or Meilisearch
- **Cloud:** Google Cloud Platform (Secrets Manager, GCS, Vertex AI, Cloud Run)
- **Deployment:** Vercel (frontend), Google Cloud Run (ingestion)

## 🔗 Resources

- **GitHub Repository:** [garywelz/sciencevideodb](https://github.com/garywelz/sciencevideodb)
- **Hugging Face Space:** [garywelz/sciencevideodb](https://huggingface.co/spaces/garywelz/sciencevideodb)

### How to Cite This Work

Welz, G. (2024–2025). *Science Video Database*.
Hugging Face Spaces. https://huggingface.co/spaces/garywelz/sciencevideodb

This project serves as infrastructure for AI-assisted video content discovery in scientific research, enabling systematic search and integration of video-based knowledge through transcript-based discovery.

The Science Video Database is designed as infrastructure for AI-assisted science, providing multi-modal content discovery capabilities within the CopernicusAI Knowledge Engine.

---

**Part of the Copernicus AI Knowledge Engine**

© 2025 Gary Welz. All rights reserved.

