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

## 📄 Publications

- Welz, G. (2025). "The Programming Framework: A Universal Method for Process Analysis Using LLMs and Visual Flowcharts"
- Welz, G. (2025). "GLMP: Genome Logic Modeling for Biochemical Process Visualization"
- Welz, G. (2025). "Linking GLMP Visualizations to AI-Generated Podcasts for Enhanced Learning"

## 💻 Technology Stack

- **LLM**: Google Gemini 2.0 Flash
- **Visualization**: Mermaid.js
- **Storage**: Google Cloud Storage
- **Format**: JSON
- **Frontend**: Static HTML + Tailwind CSS

---

**Part of the Copernicus AI Knowledge Engine**

© 2025 Gary Welz. All rights reserved.

