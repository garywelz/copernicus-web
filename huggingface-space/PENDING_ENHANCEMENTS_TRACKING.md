# Pending Enhancements Tracking

**Date Created:** January 13, 2025  
**Status:** Awaiting preprint publication  
**Implementation Plan:** All three enhancements to be implemented together once preprints are available

---

## Overview

This document tracks three enhancement tasks that will be implemented together once the two submitted papers are published as preprints. These enhancements will add academic citations, related work, and comparative analysis to the Programming Framework space.

---

## Enhancement Bundle 1: Preprint Citations + Related Work + Comparison

### Status: ⏳ **Pending Preprint Publication**

**Trigger:** When both papers are published as preprints (arXiv, bioRxiv, etc.) and we have preprint URLs/DOIs.

---

### 1. Add Preprint Citations

**Location:** 
- CopernicusAI Space (`index.html`) - Citation section
- Programming Framework Space (`programming-framework/index.html`) - Citations/References section

**Papers to Link:**

#### Paper 1: Knowledge Engine Vision
- **Local File:** `knowledge_engine_vision.pdf`
- **Title:** "A Vision for AI-Powered Knowledge Engines: A Framework for Systematic Knowledge Discovery and Integration"
- **Author:** Gary Welz
- **Status:** ⏳ Submitted, awaiting preprint publication
- **Preprint URL/DOI:** _(To be added when available)_
- **Planned Locations:**
  - CopernicusAI citation section
  - References in Related Work sections

#### Paper 2: Programming Framework
- **Local File:** `programming_framework.pdf`
- **Title:** _(To be confirmed from paper)_
- **Author:** Gary Welz
- **Status:** ⏳ Submitted, awaiting preprint publication
- **Preprint URL/DOI:** _(To be added when available)_
- **Planned Locations:**
  - Programming Framework citation section
  - References in Related Work sections

**Implementation Notes:**
- Add BibTeX format citations
- Link to preprint URLs (arXiv, bioRxiv, etc.)
- Include in "How to Cite This Work" sections
- Update reference lists where appropriate

---

### 2. Related Work Academic Citations (Programming Framework)

**Location:** `programming-framework/index.html`  
**Section:** Before "Related Projects" section  
**Priority:** Medium (Nice to Have)

**Content to Add:**

#### Suggested Citation Categories:

1. **Process Mining Literature**
   - Research on extracting process models from event logs
   - Process discovery algorithms
   - Process visualization techniques

2. **Knowledge Representation Frameworks**
   - Semantic networks (Quillian, 1968)
   - Frames and ontologies (Minsky, 1974; Gruber, 1993)
   - Knowledge graphs (Hogan et al., 2021)
   - Semantic Web (Berners-Lee et al., 2001)

3. **Visual Programming Languages**
   - Visual representation of logic and processes
   - Diagram-based programming paradigms
   - Flowchart-based systems

4. **LLM-Based Knowledge Extraction**
   - Information extraction using large language models
   - Structured output generation from LLMs
   - RAG (Retrieval-Augmented Generation) systems (Lewis et al., 2020)

**Implementation Notes:**
- Use citations from vision paper's "Related Work" section as starting point
- Format as academic reference list
- Include DOIs/URLs where available
- Group by category for clarity

**Reference from Vision Paper:**
- The vision paper (Section 2) already includes extensive related work citations that can inform this section
- Key references: MYCIN, DENDRAL, Cyc, Semantic Networks, Knowledge Graphs, Watson, RAG systems, etc.

---

### 3. Comparison with Manual Methods (Programming Framework)

**Location:** `programming-framework/index.html`  
**Section:** New section (suggest after "Validation & Accuracy")  
**Priority:** Medium (Nice to Have)

**Content to Add:**

#### Comparison Dimensions:

1. **Time to Create Flowchart**
   - Manual process: Hours to days for complex processes
   - Framework-assisted: Minutes to hours (with LLM analysis)
   - Quantify time savings where possible

2. **Accuracy Comparison**
   - Manual: Expert-dependent, potential for human error
   - Framework: LLM-powered extraction with validation
   - Note: Framework accuracy depends on source material quality

3. **Scalability Advantages**
   - Manual: Limited by human time and expertise
   - Framework: Can process multiple processes in parallel
   - Current scale: 314+ processes validated
   - Potential for larger-scale automation

4. **Cost/Effort Savings**
   - Manual: Requires domain experts, time-intensive
   - Framework: Automated extraction reduces manual effort
   - Resource requirements: LLM API costs vs. expert time

**Implementation Notes:**
- Use quantitative metrics where available
- Acknowledge limitations (e.g., Framework requires validation)
- Highlight Framework's strengths (scalability, consistency)
- Reference actual deployment metrics (314 processes, multiple disciplines)

---

## Implementation Checklist

Once preprints are available:

- [ ] **Step 1: Collect Preprint Information**
  - [ ] Obtain preprint URL/DOI for Knowledge Engine Vision paper
  - [ ] Obtain preprint URL/DOI for Programming Framework paper
  - [ ] Verify preprint titles and publication details
  - [ ] Generate BibTeX citations for both papers

- [ ] **Step 2: Add Preprint Citations**
  - [ ] Add citations to CopernicusAI space citation section
  - [ ] Add citations to Programming Framework space
  - [ ] Update "How to Cite This Work" sections
  - [ ] Include in BibTeX format

- [ ] **Step 3: Add Related Work Section (Programming Framework)**
  - [ ] Create new "Related Work" section before "Related Projects"
  - [ ] Add citations for process mining literature
  - [ ] Add citations for knowledge representation frameworks
  - [ ] Add citations for visual programming languages
  - [ ] Add citations for LLM-based knowledge extraction
  - [ ] Format as academic reference list with DOIs/URLs

- [ ] **Step 4: Add Comparison with Manual Methods Section (Programming Framework)**
  - [ ] Create new section (suggest after "Validation & Accuracy")
  - [ ] Add time comparison metrics
  - [ ] Add accuracy comparison discussion
  - [ ] Add scalability advantages
  - [ ] Add cost/effort savings analysis
  - [ ] Include quantitative data where available

- [ ] **Step 5: Review and Polish**
  - [ ] Review all citations for accuracy
  - [ ] Verify all links work
  - [ ] Check formatting consistency
  - [ ] Test on both Hugging Face Spaces
  - [ ] Update any cross-references

- [ ] **Step 6: Upload and Deploy**
  - [ ] Upload updated files to Hugging Face Spaces
  - [ ] Verify pages render correctly
  - [ ] Test all links and citations
  - [ ] Document completion

---

## Reference Information

### Vision Paper Related Work Citations (from Section 2)

Key references that can inform the Related Work section:

1. **Expert Systems:** MYCIN (Shortliffe, 1976), DENDRAL (Lindsay et al., 1980), Cyc (Lenat, 1995)
2. **Knowledge Representation:** Semantic networks (Quillian, 1968), Frames (Minsky, 1974), Ontologies (Gruber, 1993), Semantic Web (Berners-Lee et al., 2001)
3. **Modern Systems:** IBM Watson (Ferrucci et al., 2010), Google Knowledge Graph, Semantic Scholar (Kinney et al., 2023)
4. **Cognitive Architectures:** SOAR (Laird, 2012), ACT-R (Anderson, 2007), CLARION (Sun, 2006)
5. **RAG Systems:** Retrieval-Augmented Generation (Lewis et al., 2020)
6. **Knowledge Graphs:** Hogan et al. (2021) - "Knowledge graphs" survey

### Current Framework Metrics (for Comparison Section)

- **Processes Validated:** 314+ across 6 databases
- **Disciplines:** Biology (52), Chemistry (91), Physics (21), Computer Science (21), Mathematics (20), GLMP (109)
- **Validation Rate:** 100% syntax accuracy, >=85% metadata quality
- **Source Coverage:** All processes include 1-3 verified research paper citations

---

## Notes

- **Timing:** All three enhancements should be implemented together to maintain consistency and coherence
- **Dependencies:** Enhancement #1 (preprint citations) is prerequisite for proper academic context
- **Future Updates:** This document should be updated as preprints become available
- **Location:** Keep this document in the workspace root for easy reference

---

## Status Updates

| Date | Update |
|------|--------|
| 2025-01-13 | Document created. Awaiting preprint publication for both papers. |
| | |

---

**Last Updated:** January 13, 2025
