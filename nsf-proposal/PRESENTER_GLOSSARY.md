# Glossary — For Presenter Only

Quick reference for technical terms. Use when preparing or if someone asks.

---

## TDA / topology

**Topological Data Analysis (TDA)**  
Methods that study the “shape” of data (holes, loops, clusters) across scales. We use it to see which processes form loops or clusters without assuming a particular model.

**Persistence / persistent homology**  
A way to see which shapes (components, loops, voids) are “real” vs noise by watching when they appear and disappear as we change scale (e.g. connection distance). Features that persist across a wide range of scales are considered significant.

**H₀ (zeroth homology)**  
Counts of **connected components** (clusters). In our case: we start with 108 separate points (processes); as we connect “close” processes, we see how many clusters form.

**H₁ (first homology)**  
Counts of **loops** (1-dimensional holes, like circles). In our case: 33 loops. Biologically, feedback circuits are literally loops, so we expect them to show up in H₁.

**H₂ (second homology)**  
Counts of **voids** (2-dimensional holes, like the inside of a ball). We get 4. Higher-dimensional structure; less central to the narrative.

**Birth / death (of a feature)**  
**Birth:** the distance scale at which a loop (or other feature) first appears. **Death:** the scale at which it disappears (gets “filled in”). **Persistence** = death − birth; large persistence means a “significant” structure.

**Vietoris–Rips complex / filtration**  
Start with points; connect two points if they’re within distance ε. Increase ε step by step. At each scale you get a simplicial complex; persistence tracks how features appear and disappear as ε grows.

**Ripser**  
Software that computes persistence diagrams (and related output) from a distance matrix. We use it with max dimension 2 (so we get H₀, H₁, H₂).

**Cocycle**  
The mathematical object that encodes *which* points (processes) form a given loop. We use cocycles to list which processes belong to each H₁ loop (e.g. Lac in Loop #3).

**Persistence diagram**  
A plot of (birth, death) for each feature. Points far from the diagonal are “persistent” (significant); points near the diagonal are short-lived (often noise).

**Mapper**  
Another TDA-like tool that builds a summary graph of the data (nodes = clusters, edges = overlap). We mention it as a next step: circuit classes as nodes.

**Persistent cohomology**  
Cohomology version of persistence; can be used to get “circular coordinates” on the data. We mention it as a possible way to capture “feedback depth.”

---

## Pipeline / data

**Feature vector**  
A list of numbers summarizing each process. Ours: node count, conditional count, OR gates, AND gates, NOT gates — so 5 numbers per process, then standardized.

**Euclidean distance**  
Standard straight-line distance between two feature vectors. We use it to define “similarity” between processes for the Vietoris–Rips construction.

**Standardized (zero mean, unit variance)**  
Each feature is rescaled so that across all 108 processes it has mean 0 and standard deviation 1. Puts all features on a comparable scale.

---

## Biology / GLMP

**Operon**  
A set of genes controlled together as one unit. Lac, trp, and ara operons are classic examples; they often have feedback (product represses or activates the operon).

**Lac operon**  
E. coli system that controls genes for digesting lactose. Textbook **negative feedback**: lactose present → genes on; lactose absent → genes off.

**β-galactosidase**  
Enzyme that breaks down lactose; part of the Lac system. The 1995 chart was a β-gal/Lac flowchart.

**Two-component system (e.g. EnvZ–OmpR)**  
Sensor protein (EnvZ) detects a signal (e.g. osmolarity); phosphorylates a response regulator (OmpR); OmpR controls genes. Often has feedback from output back to the sensor.

**SOS response**  
E. coli’s emergency DNA repair system. Damage → SOS on; repair → SOS off. A feedback circuit; appears in our Loop #1.

**Quorum sensing**  
Bacteria sense population density and change behavior when “quorum” is reached (e.g. biofilm, toxins). Involves **positive feedback** (more cells → more signal → more response).

**CRP–cAMP**  
Catabolite repression: when glucose is low, cAMP rises and activates CRP, which turns on many operons (including lac, ara). A global regulatory layer.

**GLMP (Genome Logic Modeling Project)**  
The project that produces the 108 (or more) process flowcharts. Each process has a Mermaid flowchart, JSON with references, and a viewer with feedback.

**Mermaid (Markdown)**  
A text-based format for diagrams (flowcharts, etc.). LLMs can output Mermaid; we parse it to get nodes, conditionals, and OR/AND/NOT gates.

---

## Other

**LLM**  
Large language model. We use them to generate Mermaid flowcharts from text (e.g. paper descriptions) so we can produce many charts quickly.

**PubMed / DOI**  
PubMed: database of biomedical literature. DOI: persistent identifier for a publication. GLMP JSON stores these so each flowchart is citable.
