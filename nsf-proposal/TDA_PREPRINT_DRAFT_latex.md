# Topological Data Analysis of Genetic Regulatory Circuits: Feedback Loops as Persistent Homology Features

**Authors:** Gary Welz¹, Mikael Vejdemo-Johansson²  
¹CopernicusAI, New York, NY; Person of Interest, CUNY Graduate Center  
²CUNY Graduate Center, New York, NY

**Abstract**

We apply topological data analysis (TDA) to 108 genetic regulatory circuits from the Genome Logic Modeling Project (GLMP). Each circuit is represented as a Mermaid Markdown flowchart (nodes, conditionals, OR/AND/NOT gates) derived from textual process descriptions; flowcharts are generated with LLM assistance, making it feasible to produce and curate many such diagrams from a single prompt in seconds—a methodological breakthrough relative to earlier, labor-intensive manual charting. We encode each flowchart as a 5-dimensional feature vector and compute persistent homology (Vietoris–Rips, Ripser, maxdim=2). The most persistent H\textsubscript{1} loops align with known feedback circuits: lac operon appears in a top loop (persistence 0.302), two-component EnvZ–OmpR in another (0.231), and a large loop (0.330) aggregates SOS response, stringent response, catabolite repression, Pho regulon, quorum sensing, and related regulatory systems—all with established feedback structure. Topology thus groups processes by regulatory logic (e.g. negative feedback, stress response) rather than by pathway alone, including across organisms (E. coli, S. cerevisiae, Bacillus subtilis). We conclude that TDA on structural features captures genuine regulatory architecture and discuss limitations, biological coherence checks, and next steps: Mapper, persistent cohomology, and scaling to hundreds of processes with domain-expert validation.

**Keywords:** persistent homology, genetic circuits, feedback loops, regulatory networks, topological data analysis, Mermaid visualization, LLM-assisted curation

---

## 1. Introduction

### 1.1 Origin and motivation

The idea of representing genetic regulatory processes as flowcharts has a long history. A first attempt at a β-galactosidase / Lac operon flowchart appeared in 1995 in an article in *The X Advisor*, an online magazine for Unix developers, entitled “Is the Genome Like a Computer Program?”, drawing on conversations with biologists on the bionet.genome.chromosome newsgroup (archived at the Internet Archive and via Google Groups). The β-galactosidase description used for that chart came from Berg & Singer (1992, pp. 71–73). Notably, the 1995 chart was created from text alone—the same process that LLMs use today: words describing a process → diagram. This methodological continuity shows that diagrams are only as detailed and reliable as their source material; using different sources for the same process can yield different charts, which explains why validation and fact-checking are essential. Producing such charts by hand was so time-consuming that the approach lay dormant for decades.

Recent advances in large language models (LLMs) and the adoption of Mermaid Markdown as a standard for structured diagrams have changed the picture: we can now generate and refine flowcharts from textual descriptions (e.g. paper excerpts) in seconds from a single prompt. The same Lac operon / β-galactosidase idea can be realized today as a Mermaid flowchart in the Genome Logic Modeling Project (GLMP) viewer, alongside 107 other genetic regulatory circuits. That methodological breakthrough—text to visual data at scale—motivates the present work.

We ask whether the *shape* of these circuits, as captured by topology, aligns with what biologists already know: feedback loops, cascades, and regulatory motifs. Feedback loops are literally loops; they should appear as persistent H\textsubscript{1} features. Can text-derived visual data support that?

### 1.2 Innovation: text to visual data

**Traditional TDA pipeline:** Numerical measurements → feature vectors → topology.

**This work:** Text (e.g. papers) → Mermaid flowcharts → feature extraction → topology.

The key innovation is treating flowcharts as visual data objects. Mermaid Markdown converts textual process descriptions into structured diagrams with nodes, edges, and explicit OR/AND/NOT logic. We do not use the full graph for TDA; we summarize each flowchart into a small set of numerical features (node count, conditional count, gate counts). Those features are then used to build a distance between processes and to compute persistent homology. Thus we extract topology from *descriptions* (via their visual representation), not from direct numerical measurements. That shift opens the possibility of analyzing processes for which quantitative data are scarce or incomplete.

### 1.3 Research questions

1. Do feedback circuits appear as persistent H\textsubscript{1} loops in the topological space?
2. Does topology group by regulatory logic (e.g. feedback, stress response) rather than by pathway or organism alone?
3. Can structural features (nodes, gates) support biological interpretation when validated by domain experts?

---

## 2. Methods

### 2.1 Data: GLMP database

The Genome Logic Modeling Project (GLMP) provides 108 genetic regulatory circuits:
- *E. coli:* 66 processes  
- *S. cerevisiae:* 38 processes  
- *Bacillus subtilis:* 4 processes  

Each process is represented as a Mermaid Markdown flowchart with nodes (genes, proteins, metabolites, conditions), edges (activation, repression, synthesis, degradation), and logic gates (OR, AND, NOT). That structure is exactly what we feed into the analysis. Examples include lac operon, SOS response, two-component EnvZ–OmpR signaling, ara and trp operons, heat shock, catabolite repression, and Pho regulon.

Each process JSON includes references (PubMed, DOI) so flowcharts are citable; the GLMP viewer accepts community feedback so diagrams are correctable. Code and data: https://github.com/garywelz/glmp. Interactive table and viewer: https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/glmp-database-table.html.

### 2.2 Feature extraction

We do not use the full graph structure for TDA. From each Mermaid flowchart we extract five numerical features:

1. Node count  
2. Conditional count  
3. OR gates  
4. AND gates  
5. NOT gates  

These capture circuit complexity and logic structure. The feature matrix is 108 processes × 5 features, standardized to zero mean and unit variance.

### 2.3 Topological data analysis

We build pairwise Euclidean distances between processes in the 5-dimensional feature space, then run a Vietoris–Rips filtration and compute persistent homology with Ripser (maxdim=2), with cocycle extraction enabled. Outputs are persistence diagrams for H\textsubscript{0} (connected components), H\textsubscript{1} (loops), and H\textsubscript{2} (voids). Cocycles identify which specific processes form each H\textsubscript{1} loop.

---

## 3. Results

### 3.1 Persistence diagram

We obtain:
- **H\textsubscript{0}:** 108 components (one per process).  
- **H\textsubscript{1}:** 33 loops.  
- **H\textsubscript{2}:** 4 voids.  

The question we then ask is whether these H\textsubscript{1} loops align with known biology—feedback circuits, stress responses, and regulatory motifs.

### 3.2 Top H\textsubscript{1} loops and biological interpretation

We rank H\textsubscript{1} loops by persistence (death − birth). Highlights:

**Loop #1 (persistence 0.330)**  
27 processes, including ara operon, SOS response, stringent response, catabolite repression, Pho regulon, quorum sensing, heat shock, GAL regulation, MAPK mating. They are not the same pathway but share a “regulatory with feedback” character and span E. coli, yeast, and Bacillus. This loop aggregates many established stress and nutrient regulatory systems.

**Loop #2 (persistence 0.308)**  
Four processes, all yeast (e.g. aerobic respiration, cell wall integrity, DNA replication). Organism-specific.

**Loop #3 (persistence 0.302)**  
Four processes, all E. coli: lac operon, antibiotic efflux pumps, phosphate regulation, translation termination. Lac operon is the textbook negative-feedback example. Topology here groups by that kind of regulatory logic, not by metabolic pathway alone.

**Loop #4 (persistence 0.283)**  
17 processes, largely a subset of Loop #1; nested structure.

**Loop #5 (persistence 0.231)**  
Three processes: two-component EnvZ–OmpR (E. coli), oxidative stress response, yeast ER-associated degradation. EnvZ–OmpR is the paradigm two-component signaling system with feedback. E. coli and yeast appear in the same topological loop—the structure of the circuit is what is shared, not the organism.

### 3.3 Biological coherence check

We took a set of circuits that biologists agree have feedback—lac, trp, ara operons; two-component EnvZ–OmpR; SOS, heat shock; catabolite repression, Pho regulon—and asked where they fall in the H\textsubscript{1} loops. Lac appears in Loop #3; two-component in Loop #5; many stress and nutrient circuits in Loop #1. The topology is therefore picking up real regulatory structure, not random variation.

### 3.4 Organism patterns

Some loops are organism-specific (e.g. Loop #2 all yeast, Loop #3 all E. coli). Others (Loop #1, Loop #5) mix organisms. So we see both universal regulatory motifs and ones that are species-specific.

---

## 4. Discussion

### 4.1 Interpretation

The appearance of lac operon and two-component EnvZ–OmpR in top H\textsubscript{1} loops—both textbook feedback systems—supports the view that TDA on structural features reflects regulatory logic. The topology distinguishes “classic” single-circuit feedback (lac, EnvZ–OmpR) from larger clouds of regulatory processes (Loop #1). The same chart that was infeasible to produce at scale in 1995 can now be generated in seconds; applying TDA to many such flowcharts reveals that feedback loops appear as loops in homology.

### 4.2 Limitations

**Sample size:** 108 processes is enough to see structure but small for broad claims; we aim to scale to hundreds.

**Features:** We use structural counts only; adding graph-theoretic measures (e.g. cycle structure, path lengths) could improve interpretability.

**Flowcharts:** Diagrams are LLM-generated and require fact-checking. Biological interpretation should be validated by domain experts.

**Open question:** Does topology predict circuit function or mainly correlate with known biology? We are seeking biologist and TDA expert collaboration to address this.

### 4.3 Future directions

**Mapper:** Treat circuit classes as nodes to visualize distinct regulatory families (operon-type, two-component, stress-response).

**Persistent cohomology:** Explore circular coordinates that might align with “feedback depth” or cascade structure.

**Scaling:** Expand to 200–500+ genetic circuits; GLMP already includes 314 processes across biology, chemistry, physics, mathematics, and computer science—we will test whether regulatory patterns generalize.

**Collaboration:** Ongoing work with the CUNY TDA group (Mikael Vejdemo-Johansson) and Jordan Matuszewski; we seek biologist validation of flowcharts and interpretations.

---

## 5. Conclusion

We applied TDA to 108 genetic regulatory circuits encoded as Mermaid Markdown flowcharts. The flowcharts are produced with LLM assistance from textual descriptions—the same Lac/β-galactosidase idea that was first sketched in 1995 can now be generated at scale in seconds. The most persistent H\textsubscript{1} loops correspond to known feedback circuits (lac operon, two-component signaling, SOS, stringent response, catabolite repression, Pho, quorum sensing, and related systems). Topology groups processes by regulatory logic and by organism in ways that match biological expectation. The work demonstrates a pipeline: text → visual data → features → topology, and suggests that TDA on structural features captures genuine regulatory architecture. Code, data, and documentation are open source.

---

## Acknowledgments

We thank Jordan Matuszewski and the CUNY Graduate Center TDA seminar group for feedback and collaboration.

---

## References

Berg, P., & Singer, M. (1992). *Dealing With Genes: The Language of Heredity*. University Science Books.

[To be added: Ripser, persim, GLMP repository, relevant TDA and biological circuit literature]

---

## Data availability

- Code: https://github.com/garywelz/glmp/tree/main/tda-analysis  
- Data and GLMP: https://github.com/garywelz/glmp  
- GLMP database table and viewer: https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/glmp-database-table.html  
