# TDA Seminar Talk: Title, Abstract, and Outline

## Title

**"Feedback Loops as Loops: Topological Data Analysis of Genetic Regulatory Circuits"**

*Alternative shorter title:*  
**"Persistent Homology Detects Feedback Architecture in Biological Circuits"**

---

## Abstract

We apply topological data analysis (TDA) to 108 genetic regulatory circuits from the Genome Logic Modeling Project (GLMP), representing processes from E. coli, S. cerevisiae, and Bacillus subtilis. Each circuit is encoded as a feature vector (node counts, conditional logic, OR/AND/NOT gates). Using Vietoris-Rips persistence (Ripser, maxdim=2), we find that the most persistent H₁ loops correspond to known feedback circuits: lac operon appears in a top H₁ loop (persistence = 0.302), two-component EnvZ-OmpR signaling in another (0.231), and a large loop (0.330) aggregates SOS response, stringent response, catabolite repression, Pho regulon, and quorum sensing—all established regulatory systems with feedback. This suggests TDA on structural features captures genuine regulatory architecture, not random variation. We discuss biological interpretation, organism-specific vs. cross-species topological patterns, and next steps: Mapper visualization, persistent cohomology, and scaling to 500+ processes for circuit classification.

**Keywords:** persistent homology, genetic circuits, feedback loops, regulatory networks, topological data analysis

**Note:** Analysis conducted using Ripser with cocycle extraction. Code, data, and documentation are fully open source on GitHub.

---

## Outline (30-45 minutes)

### 1. Introduction (5 min)
- **The problem:** Can we detect regulatory structure (feedback, cascades) from circuit topology?
- **Why TDA?** Feedback loops are literally loops—should appear in H₁
- **The data:** 108 GLMP processes (E. coli, yeast, Bacillus), Mermaid flowcharts → feature vectors

### 2. Methods (5-7 min)
- **Feature extraction:** Nodes, conditionals, OR/AND/NOT gates
- **TDA pipeline:** Standardization → Vietoris-Rips → Ripser (maxdim=2)
- **Cocycle analysis:** Mapping H₁ loops to specific processes

### 3. Results (10-12 min)
- **Persistence diagram:** 33 H₁ loops, 4 H₂ voids
- **Top 5 H₁ loops:**
  - Loop #1 (0.330): Large regulatory cloud (SOS, stringent, Pho, quorum sensing)
  - Loop #3 (0.302): **Lac operon** + phosphate regulation
  - Loop #5 (0.231): **Two-component EnvZ-OmpR** + oxidative stress
- **Biological coherence:** Feedback circuits cluster in H₁
- **Organism patterns:** Some loops are species-specific (yeast-only), others cross-organism

### 4. Interpretation and Discussion (8-10 min)
- **What this means:** Structural features (gates, nodes) reflect regulatory logic
- **Limitations:** Small sample (108), feature choice (could add graph metrics)
- **Biological questions:** Do circuit classes map to H₁ clusters? Can we predict feedback from topology?

### 5. Next Steps and Future Work (5-7 min)
- **Mapper visualization:** Circuit classes as Mapper nodes
- **Persistent cohomology:** Circular coordinates for feedback depth
- **Scaling:** 200-500+ processes for robustness
- **Cross-disciplinary extension:** 314 processes across biology, chemistry, physics, math, CS—do regulatory patterns generalize?
- **Collaboration:** Working with Dr. Vejdemo-Johansson and CUNY TDA group

### 6. Q&A (5-10 min)

---

## Slides Structure (Suggested)

1. **Title slide**
2. **The question:** Feedback loops → H₁ loops?
3. **GLMP overview:** What are these circuits?
4. **Methods diagram:** Flowchart → Features → TDA
5. **Persistence diagram** (the main visual)
6. **Loop #1:** Large regulatory cloud
7. **Loop #3:** Lac operon
8. **Loop #5:** Two-component signaling
9. **Biological coherence:** Feedback circuits in loops
10. **Organism patterns:** Species-specific vs. universal
11. **Limitations and caveats**
12. **Next steps:** Mapper, cohomology, scaling
13. **Collaboration and acknowledgments**
14. **Questions**

---

## Key Points to Emphasize

- **Novel finding:** Feedback circuits appear in persistent H₁ loops—this is biologically meaningful, not artifact
- **Concrete examples:** Lac operon and two-component signaling are textbook feedback systems
- **Open questions:** What other circuit types cluster? Can topology classify circuits?
- **Collaboration angle:** This is a pilot; we want TDA expertise to deepen the analysis

---

## Technical Level

- **Assumes:** Familiarity with persistent homology, Vietoris-Rips, persistence diagrams
- **Doesn't assume:** Biology background—explain operons, two-component systems briefly
- **Focus:** Interpretation over computation (they know Ripser; they want to see what topology reveals)
