# TDA Seminar: Slide-by-Slide Script

**Live deck:** [TDA_Seminar_Slides_2026.html](https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/TDA_Seminar_Slides_2026.html) (GCS)  
**Preprint:** [PDF](https://huggingface.co/spaces/garywelz/glmp/resolve/main/TDA_PREPRINT_DRAFT.pdf) (Hugging Face) · [HTML](https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/TDA_PREPRINT_DRAFT.html) (GCS)

---

## Slide 1: Title
**Title:** Feedback Loops as Loops: Topological Data Analysis of Genetic Regulatory Circuits  
**Subtitle:** Gary Welz | CopernicusAI / CUNY Graduate Center (PoI)  
**Subtitle 2:** Collaboration with Dr. Mikael Vejdemo-Johansson  
**Footer:** March 13, 2026

---

## Slide 2: From papers to flowcharts
**Title:** From papers to flowcharts

**Content:**
- First attempt at β-galactosidase flow chart (1995), *The X Advisor* article “Is the Genome Like a Computer Program?”, excerpts from bionet.genome.chromosome newsgroup
- 1995 chart created from text alone (Berg & Singer 1992) — same process LLMs use today
- **Links on slide:** 1995 article (Internet Archive); Source: Berg & Singer (1992); bionet thread: [first posting](http://www.bio.net/bionet/mm/biochrom/1995-April/000537.html) (flowchart with “and”/“or”) · Robbins ([000539](http://www.bio.net/bionet/mm/biochrom/1995-April/000539.html)): “care must be taken in interpreting that flow chart”; “computer-science insights… potentially huge payoffs” · Dellaire ([000540](http://www.bio.net/bionet/mm/biochrom/1995-April/000540.html)): genome structure (not just sequence) encodes how the code is read — context spatial/temporal · Robbins ([000543](http://www.bio.net/bionet/mm/biochrom/1995-April/000543.html))
- Image: b-galchart2.gif (1995 chart)

---

## Slide 3: Same chart, 30 years later
**Title:** Same chart, 30 years later

**Content:**
- Same Lac operon / β-galactosidase idea — generated with LLMs and Mermaid Markdown
- Link: Lac Operon (GLMP viewer)
- Image: First LLM-generated Mermaid flowchart (bgachartMedium.webp)

---

## Slide 4: The Innovation
**Title:** The Innovation: Text → Visual Data

**Bullets:**
- Traditional TDA: Numerical data → Feature vectors → Topology
- This work: Text (papers) → Visual flowcharts → Features → Topology
- Key: Mermaid Markdown converts textual process descriptions into structured flowcharts
- Flowcharts become visual data; TDA reveals structure
- We extract topology from descriptions, not from direct measurements

---

## Slide 5: The Question
**Title:** The Question

**Bullets:**
- Can we detect regulatory structure (feedback, cascades) from circuit topology?
- Feedback loops are literally loops — they should appear in H₁
- Can text-derived visual data support that?

---

## Slide 6: GLMP Overview
**Title:** The GLMP Database

**Bullets:**
- 108 genetic regulatory circuits
- E. coli (66), S. cerevisiae (38), Bacillus subtilis (4)
- Each process: Mermaid flowchart (nodes, conditionals, OR/AND/NOT gates)
- Examples: lac operon, SOS response, two-component signaling
- Data: github.com/garywelz/glmp

---

## Slide 8: From Flowcharts to Features
**Title:** From Flowcharts to Features

**Bullets:**
- Node count, conditional count
- OR gates, AND gates, NOT gates
- Standardized (zero mean, unit variance)
- 108 processes × 5 features
- These capture circuit complexity and logic structure

---

## Slide 9: TDA Pipeline
**Title:** TDA Pipeline

**Bullets:**
- Feature matrix → Euclidean distance
- Vietoris-Rips filtration
- Ripser (maxdim=2), cocycle extraction
- Output: persistence diagrams (H₀, H₁, H₂)
- Cocycles tell us which processes form each H₁ loop

---

## Slide 10: Persistence Diagram
**Title:** Persistence Diagram

**Bullets:**
- H₀: 108 components (one per process)
- H₁: 33 loops
- H₂: 4 voids
- Key question: Do these loops correspond to biological structure?
- [Insert image: glmp_persistence_diagram.png]

---

## Slide 11: Loop 1
**Title:** Top H₁ Loop #1 (Persistence = 0.330)

**Bullets:**
- 27 processes: ara operon, SOS, stringent response, catabolite repression, Pho regulon, quorum sensing, heat shock, GAL, MAPK mating
- Common thread: regulatory circuits with feedback
- Cross-organism: E. coli, yeast, Bacillus

---

## Slide 13: Loop 3
**Title:** Top H₁ Loop #3 (Persistence = 0.302)

**Bullets:**
- 4 processes: Lac operon, antibiotic efflux pumps, phosphate regulation, translation termination
- Lac operon = textbook negative feedback
- Topology groups by regulatory logic, not just metabolic function

---

## Slide 15: Loop 5
**Title:** Top H₁ Loop #5 (Persistence = 0.231)

**Bullets:**
- 3 processes: Two-component EnvZ-OmpR, oxidative stress response, yeast ER-associated degradation
- EnvZ-OmpR = paradigm two-component signaling with feedback
- Cross-organism: regulatory logic transcends species

---

## Slide 16: Biological Coherence
**Title:** Biological Coherence Check

**Bullets:**
- Known feedback circuits: lac, trp, ara operons; two-component; SOS, heat shock; catabolite repression, Pho
- Result: lac (Loop #3), two-component (Loop #5), many stress/nutrient circuits (Loop #1)
- Interpretation: topology captures genuine regulatory architecture

---

## Slide 17: Organism Patterns
**Title:** Organism Patterns

**Bullets:**
- Species-specific: Loop #2 (all yeast), Loop #3 (all E. coli)
- Cross-organism: Loop #1, Loop #5
- Some motifs are universal; others organism-specific

---

## Slide 18: Limitations
**Title:** Limitations and Caveats

**Bullets:**
- Sample size: 108 (small but meaningful)
- Feature choice: structural counts only; could add graph metrics
- Biological validation: domain experts should validate
- LLM-generated flowcharts: fact-checking needed
- Open question: Does topology predict function or correlate with known biology?

---

## Slide 19: Next Steps
**Title:** Next Steps

**Bullets:**
- **Rosetta Stone goal:** Use flowcharts and TDA to link topology to the genetic “machine code” on the chromosome — sequence motifs that implement AND/OR/NOT connectives; falsifiable if circuits in the same H₁ loop share enriched motifs
- Mapper: circuit classes as nodes
- Feature ablation study: rerun TDA dropping one feature at a time to test H₁ loop stability
- Null model permutation test (n=1,000): p = 0.022 — significant at p < 0.05
- Graph-theoretic features: cycle rank, longest path, gate ratios — planned for next pipeline iteration
- Persistent cohomology: circular coordinates for feedback depth
- Scaling: 200–500+ processes; 314 across biology, chemistry, physics, math, CS
- Collaboration: Dr. Vejdemo-Johansson, CUNY TDA group; biologist validation
- Open source: github.com/garywelz/glmp/tree/main/tda-analysis

---

## Slide 20: Acknowledgments
**Title:** Acknowledgments and Questions

**Bullets:**
- Collaborators: Dr. Mikael Vejdemo-Johansson, Jordan Matuszewski
- GLMP: github.com/garywelz/glmp
- TDA analysis: github.com/garywelz/glmp/tree/main/tda-analysis
- Questions?

**Footer:** Gary Welz | garywelz@gmail.com | 917-593-2537
