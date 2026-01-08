---
title: GLMP - Genome Logic Modeling Project
emoji: 🧬
colorFrom: green
colorTo: blue
sdk: static
pinned: true
license: mit
---

# 🧬 GLMP - Genome Logic Modeling Project

A microscope for biological processes. GLMP applies the Programming Framework to visualize complex biochemical processes as interactive flowcharts, revealing the logic of life at the molecular level.

## 📚 Prior Work & Research Contributions

### Overview
The Genome Logic Modeling Project (GLMP) represents **prior work** that demonstrates the first successful application of the Programming Framework to biological process visualization. This research establishes a novel methodology for transforming complex biochemical processes into structured, interactive visual flowcharts using LLM-powered analysis and Mermaid visualization technology.

### 🔬 Research Contributions
- **Biological Process Visualization:** 50+ processes mapped across 6 major categories
- **LLM-Powered Analysis:** Automated extraction using Google Gemini 2.0 Flash
- **Interactive Visualization:** Mermaid.js-based dynamic flowchart system
- **Knowledge Engine Integration:** Links to Copernicus AI and Programming Framework

### ⚙️ Technical Achievements
- **Structured Database:** JSON format in Google Cloud Storage
- **Process Coverage:** Central Dogma, Metabolism, Signaling, Proteins, Photosynthesis, DNA Repair
- **Scalable Architecture:** GCS-based storage with web viewer integration
- **Metadata-Rich Format:** Categories, versions, references, source papers

### 🎯 Position Within CopernicusAI Knowledge Engine
GLMP serves as a **specialized application component** of the CopernicusAI Knowledge Engine, demonstrating how the Programming Framework can be applied to domain-specific scientific visualization. It integrates with:

- Programming Framework (meta-tool)
- Copernicus AI (main knowledge engine)
- **Knowledge Engine Dashboard** (✅ Implemented December 2025) - Fully operational web interface with knowledge graph visualization, vector search, RAG queries, and content browsing. Live at: https://copernicus-frontend-phzp4ie2sq-uc.a.run.app/knowledge-engine
- Research Papers Metadata Database
- Science Video Database
- Multi-modal learning integration

This work establishes a proof-of-concept for domain-specific applications of the Programming Framework, demonstrating its utility in biological sciences and potential for extension to other scientific disciplines. The Knowledge Engine now provides a unified interface for exploring biological processes alongside research papers, podcasts, and other content types.

## 🎯 What is GLMP?

The Genome Logic Modeling Project is the first specialized application of the [Programming Framework](https://huggingface.co/spaces/garywelz/programming_framework) to the domain of biology. It transforms complex biochemical processes into clear, visual flowcharts that reveal the step-by-step logic underlying life's molecular machinery.

### Key Features

- **50+ Biological Processes** mapped as interactive flowcharts
- **JSON-based storage** in Google Cloud Storage
- **LLM-powered analysis** using Google Gemini 2.0
- **Mermaid visualization** for clear, interactive diagrams
- **Integration with Copernicus AI** for enhanced learning

## 📚 Process Categories

### 🧬 Central Dogma
- DNA Replication
- Transcription
- Translation
- RNA Processing
- Post-translational Modifications

### ⚡ Metabolic Pathways
- Glycolysis
- Krebs Cycle (TCA)
- Oxidative Phosphorylation
- Gluconeogenesis
- Pentose Phosphate Pathway

### 📡 Cell Signaling
- MAPK Pathway
- PI3K/AKT Pathway
- Wnt Signaling
- Notch Pathway
- JAK-STAT Pathway

### 🔄 Protein Processes
- Protein Folding
- Ubiquitination
- Autophagy
- Proteasome Degradation
- Chaperone Systems

### 🌱 Photosynthesis
- Light Reactions
- Calvin Cycle
- C4 Pathway
- CAM Photosynthesis
- Photorespiration

### 🔧 DNA Repair
- Base Excision Repair
- Nucleotide Excision Repair
- Mismatch Repair
- Double-strand Break Repair
- Direct Repair

## 🗄️ Database

All GLMP flowcharts are stored as JSON files in Google Cloud Storage:

```
gs://regal-scholar-453620-r7-podcast-storage/glmp-v2/
```

Each file contains:
- Process name and description
- Mermaid flowchart syntax
- Metadata (category, version, references)
- Links to source papers

## 🚀 How to Use

1. **Browse the interactive viewer** on the main page
2. **Select a biological process** from the dropdown
3. **Explore the flowchart** showing each step and decision point
4. **Link to source papers** for deeper understanding
5. **Integrate with Copernicus AI podcasts** for audio learning

## 🔗 Related Projects

- [Programming Framework](https://huggingface.co/spaces/garywelz/programming_framework) - The meta-tool powering GLMP
- [Copernicus AI](https://huggingface.co/spaces/garywelz/copernicusai) - Knowledge engine integrating GLMP with AI podcasts

### How to Cite This Work

Welz, G. (2024–2025). *Genome Logic Modeling Project (GLMP)*.
Hugging Face Spaces. https://huggingface.co/spaces/garywelz/glmp

This project serves as a testbed for integrating AI systems into scientific reasoning pipelines, enabling both human and AI agents to analyze, compare, and extend biological knowledge structures.

GLMP is designed as infrastructure for AI-assisted science, not as a static visualization collection.

## 💻 Technology Stack

- **LLM**: Google Gemini 2.0 Flash
- **Visualization**: Mermaid.js
- **Storage**: Google Cloud Storage
- **Format**: JSON
- **Frontend**: Static HTML + Tailwind CSS

---

**Part of the Copernicus AI Knowledge Engine**

© 2025 Gary Welz. All rights reserved.

