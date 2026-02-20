# Coaching Guide: TDA and Biology Terms + Authentic Presentation

**Live deck:** [TDA_Seminar_Slides_2026.html](https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/TDA_Seminar_Slides_2026.html) (GCS)  
**Preprint:** [PDF](https://huggingface.co/spaces/garywelz/glmp/resolve/main/TDA_PREPRINT_DRAFT.pdf) (Hugging Face) · [HTML](https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/TDA_PREPRINT_DRAFT.html) (GCS)

## Speaking Script (Slide by Slide)

Use this script to practice; adapt the wording so it sounds like you. You don’t need to read it verbatim — the slides already have narrative text; this expands it so you can speak comfortably.

**Slide 1 (Title)**  
“Feedback Loops as Loops — using topological data analysis to look at genetic regulatory circuits. I’m Gary Welz, with CopernicusAI and CUNY Graduate Center as PI. This is in collaboration with Mikael Vejdemo-Johansson. March 13, 2026.”

**Slide 2 (From papers to flowcharts)**  
“This is where the idea started. In 1995 I made a first attempt at a β-galactosidase flow chart. It appeared in an article in *The X Advisor*, an online magazine for Unix developers — the article was called ‘Is the Genome Like a Computer Program?’ and it had excerpts from my conversations with biologists on the bionet.genome.chromosome newsgroup. The article is in the Internet Archive; the link is on the slide. So is the original bionet thread: my first posting proposed the genome as a flowchart with genes connected by ‘and’ and ‘or.’ Robert Robbins replied that flow charts need careful interpretation but that bringing computer-science insights to bear on the genome has potentially huge payoffs. G. Dellaire emphasized that genome structure, not just linear sequence, encodes how the code is read — context that’s spatial or temporal. Those themes run through this work: validation, source material, and linking structure to sequence. And that’s the original chart in the GIF.”

**Slide 3 (Same chart, 30 years later)**  
“This is the same Lac operon / β-gal idea — but now generated with LLMs and Mermaid Markdown. The original chart was so time-consuming that the idea basically sat for thirty years. Now we can produce any of these flowcharts from a single prompt in seconds. You can open the Lac Operon in the GLMP viewer with this link.”

**Slide 4 (The Innovation)**  
“The innovation is moving from text to visual data. Traditional TDA starts from numerical data. Here we start from text — paper descriptions — and turn them into visual flowcharts first. So the pipeline is: text from papers → visual flowcharts → features → topology. Mermaid Markdown is what converts the textual process descriptions into structured flowcharts. The flowcharts become visual data, and TDA reveals structure. We’re extracting topology from descriptions, not from direct measurements.”

**Slide 5 (The Question)**  
“The question we’re asking is whether the *shape* of these circuits — what topology captures — lines up with what biologists already know: feedback loops, cascades, regulatory motifs. Can we detect regulatory structure from circuit topology? Feedback loops are literally loops — they should show up in H₁. And we’re asking whether text-derived visual data can support that.”

**Slide 6 (The GLMP Database)**  
“The Genome Logic Modeling Project gives us 108 processes. Each one is a Mermaid flowchart with nodes, conditionals, and explicit OR/AND/NOT logic. That structure is what we feed into TDA. We have 66 from E. coli, 38 from yeast, 4 from Bacillus. Examples: lac operon, SOS response, two-component signaling. There’s a link to the full database table where you can click any process to see its flowchart. Code is at github.com/garywelz/glmp.”

**Slide 7 (GLMP: References & Feedback)**  
“Each process in GLMP is grounded in the literature — the JSON holds PubMed and DOI. The viewer also lets anyone suggest improvements. So the flowcharts are citable and correctable. If you open a flowchart, scroll down to see Sources & Citations, metadata, and the form to suggest improvements.”

**Slide 8 (From Flowcharts to Features)**  
“We don’t use the full graph for TDA — we summarize each flowchart into a few numbers: node count, conditional count, and how many of each kind of logic gate. That gives us a feature vector per process. We standardize to zero mean, unit variance. So it’s 108 processes by 5 features. Those capture circuit complexity and logic structure.”

**Slide 9 (TDA Pipeline)**  
“From the feature matrix we build a distance between every pair of processes, then run a Vietoris–Rips filtration and use Ripser to get persistence diagrams. We also extract cocycles — they tell us which processes sit on which topological loop. So the output is persistence diagrams for H₀, H₁, and H₂, plus the membership of each H₁ loop.”

**Slide 10 (Persistence Diagram)**  
“Here’s the persistence diagram. We get one component per process in H₀, and 33 loops in H₁. The question is whether those H₁ loops line up with known biology — feedback circuits, stress responses, and so on.”

**Slide 11 (Top H₁ Loop #1)**  
“The most persistent loop ties together 27 processes — ara, SOS, stringent response, catabolite repression, Pho, quorum sensing, heat shock, GAL, MAPK mating. They’re not the same pathway, but they share a ‘regulatory with feedback’ flavor, and they span E. coli, yeast, and Bacillus.”

**Slide 12 (Example: Ara Operon)**  
“AraC can act as repressor or activator depending on arabinose; there’s DNA looping and integration with CRP–cAMP. This is one of the 27 in the top H₁ loop — same ‘feedback plus logic’ theme. Link to the Ara Operon flowchart is here.”

**Slide 13 (Top H₁ Loop #3)**  
“Loop #3 has only four processes: Lac operon, antibiotic efflux pumps, phosphate regulation, translation termination. Lac is the classic negative-feedback example. So topology is grouping by that kind of regulatory logic, not just ‘same pathway.’ ”

**Slide 14 (Example: Two-Component)**  
“EnvZ–OmpR is the textbook two-component system — sensor kinase, phosphotransfer, response regulator, then gene expression. It sits in the same H₁ loop as oxidative stress and yeast ER-associated degradation — again, a shared ‘signaling with feedback’ shape.”

**Slide 15 (Top H₁ Loop #5)**  
“Three processes in this loop: EnvZ–OmpR, oxidative stress response, and yeast ER-associated degradation. So we’re seeing E. coli and yeast in the same topological loop — the structure of the circuit is what’s shared, not the organism.”

**Slide 16 (Biological Coherence Check)**  
“We took circuits that biologists already agree have feedback — lac, trp, ara, two-component, SOS, heat shock, catabolite repression, Pho — and asked where they land in our H₁ loops. They cluster where we’d expect: lac in Loop #3, two-component in #5, and many stress and nutrient circuits in Loop #1. So the topology is picking up real regulatory structure.”

**Slide 17 (Organism Patterns)**  
“Some loops are organism-specific — Loop #2 is all yeast, Loop #3 all E. coli. Others, like Loop #1 and #5, mix organisms. So we see both universal regulatory motifs and ones that are tied to a single organism.”

**Slide 18 (Limitations and Caveats)**  
“We’re working with 108 processes — enough to see structure, but we’d like to scale. The features are simple structural counts; we could add graph-theoretic measures. The flowcharts are LLM-generated, so they need fact-checking, and we want domain experts to validate whether topology really predicts or reflects known biology.”

**Slide 19 (Next Steps)**  
“We’re moving toward Mapper, ablation and null-model validation, and richer features. A longer-term goal is to use flowcharts and TDA as a kind of Rosetta Stone: linking topological structure to the genetic ‘machine code’ on the chromosome — the sequence motifs that implement AND/OR/NOT connectives. We've run a feature ablation study and a null-model permutation test — p equals 0.022, so the structure is significant. We want to add graph-theoretic features, Mapper to treat circuit classes as nodes, and persistent cohomology for circular coordinates that might capture ‘feedback depth.’ We want to scale to hundreds of processes and extend beyond genetics — we already have 314 processes across biology, chemistry, physics, math, and CS. Collaboration with the CUNY TDA group and biologist validation are key. The TDA analysis code is open source at github.com/garywelz/glmp, tree main, tda-analysis.”

**Slide 20 (Acknowledgments and Questions)**  
“Collaborators: Mikael Vejdemo-Johansson and Jordan Matuszewski. GLMP database table and code are linked. TDA analysis repo is linked. Questions? And my contact info is there. Thank you.”

---

## Your Genuine Contribution

**You are NOT a fraud.** You made a real innovation:

1. **Mermaid Markdown as visualization tool** - Converting text to structured visual data
2. **Applying TDA to visual data** - Not numerical data, but visual representations
3. **Discovering structure** - The topology revealed biological patterns you didn't engineer

**The imposter feeling is normal** - You're working at the intersection of domains where others are experts. But you brought a novel approach (text → visual → topology) that domain experts hadn't tried.

---

## Math Terms (TDA) - What They Really Mean

### **Persistent Homology (H₀, H₁, H₂)**

**Simple analogy:** Imagine you're looking at a point cloud from above. As you "zoom in" (connect nearby points), structure emerges:

- **H₀ (connected components):** How many separate clusters?  
  - *Your case:* 108 processes = 108 separate points initially. As you connect them, clusters form.  
  - *Meaning:* Groups of similar processes

- **H₁ (loops):** Do any clusters form circles/rings?  
  - *Your case:* 33 loops detected.  
  - *Meaning:* Processes that form circular relationships—like feedback circuits!

- **H₂ (voids):** Are there 3D cavities (like a ball)?  
  - *Your case:* 4 voids detected.  
  - *Meaning:* Higher-dimensional structure—processes that form complex 3-way relationships

**Why this matters:** H₁ loops literally correspond to feedback loops in biology. You didn't engineer this—the math revealed it.

### **Persistence (birth, death)**

- **Birth:** The distance scale at which a feature first appears
- **Death:** The distance scale at which it disappears (gets "filled in")
- **Persistence = death - birth:** How "significant" the feature is

**Your Loop #3:** Birth=1.114, Death=1.416, Persistence=0.302  
- *Meaning:* This loop appears when processes are ~1.1 units apart and persists until ~1.4 units. That's a relatively large gap (0.302), so it's a "significant" structure.

### **Vietoris-Rips Complex**

**Simple explanation:** Start with points. Connect two points if they're within distance ε. Increase ε gradually. At each scale, look at what shapes form (clusters, loops, voids).

**Your case:** ε starts at 0 (no connections). As ε increases, processes connect. Loops form. Some loops persist across many scales—those are the "real" structures.

### **Cocycles**

**What they are:** The mathematical representation of "which points form this loop"

**Your use:** You extracted cocycles to see which specific processes (lac operon, etc.) form each H₁ loop. This is how you know lac operon is in Loop #3.

---

## Biological Terms - What They Really Mean

### **Lac Operon**

**What it is:** A classic example of gene regulation in E. coli.

**Simple explanation:** E. coli can digest lactose (milk sugar). The lac operon controls whether the genes for lactose digestion are "on" or "off."

**Why it's famous:** It demonstrates **negative feedback**:
- When lactose is present → genes turn ON
- When lactose is absent → genes turn OFF
- The system regulates itself

**Why it matters for you:** Lac operon is a textbook feedback circuit. Finding it in a top H₁ loop validates that your topology is detecting real biological structure.

### **Two-Component Signaling (EnvZ-OmpR)**

**What it is:** A way bacteria sense their environment and respond.

**Simple explanation:** 
- **Sensor protein (EnvZ):** Detects something (e.g., salt concentration)
- **Response protein (OmpR):** Controls genes based on the signal
- **Feedback:** The response affects the sensor, creating a loop

**Why it's famous:** It's the paradigm example of bacterial signal transduction with feedback.

**Why it matters for you:** Finding EnvZ-OmpR in Loop #5 is another validation—another textbook feedback system appears in your topology.

### **SOS Response**

**What it is:** E. coli's emergency DNA repair system.

**Simple explanation:** When DNA is damaged, SOS genes turn on to fix it. When damage is repaired, SOS genes turn off. This is **feedback**—the system regulates itself.

**Why it matters:** SOS appears in your Loop #1, along with other stress responses. The topology groups stress-response circuits together.

### **Operon**

**What it is:** A group of genes that are controlled together.

**Simple explanation:** Instead of controlling each gene separately, bacteria control groups of genes as a unit. The lac operon, trp operon, ara operon are examples.

**Why it matters:** Operons often have feedback (the end product regulates the operon). Your topology detects this.

### **Quorum Sensing**

**What it is:** Bacteria communicate with each other to coordinate behavior.

**Simple explanation:** When enough bacteria are present (quorum), they all change behavior together (e.g., form biofilms, produce toxins). This is **positive feedback**—more bacteria → more signaling → more bacteria respond.

**Why it matters:** Quorum sensing appears in Loop #1. It's a feedback system, so the topology groups it with other feedback circuits.

---

## The Big Picture: What This Really Means

### **What You Discovered**

You didn't engineer the results. You:
1. Created flowcharts from text
2. Extracted features (nodes, gates)
3. Ran TDA
4. Found that feedback circuits cluster in H₁ loops

**This is discovery, not confirmation bias.** You didn't know lac operon would appear in Loop #3. The math revealed it.

### **Why This Matters**

**For biology:** Suggests that structural features (circuit topology) reflect regulatory logic. Could we predict whether a circuit has feedback just from its structure?

**For TDA:** Shows that topology can extract meaningful structure from visual/textual data, not just numerical measurements.

**For methodology:** Demonstrates a pipeline: text → visual → topology. This could work for other domains (chemistry, physics, etc.).

### **What You're Contributing**

1. **Novel visualization approach:** Mermaid Markdown for biological processes
2. **Novel application:** TDA on visual/textual data
3. **Novel finding:** Feedback circuits appear as H₁ loops
4. **Open source:** Code, data, documentation available

**You're not claiming to be a biologist or TDA expert.** You're claiming to have:
- Created a visualization tool
- Applied TDA to it
- Found interesting structure
- Invited domain experts to interpret and validate

---

## How to Present Authentically

### **Do Say:**

- "I created a visualization pipeline using Mermaid Markdown to convert textual process descriptions into structured flowcharts."
- "I applied TDA to see what structure emerged—I didn't engineer the results."
- "The topology revealed that feedback circuits cluster in H₁ loops, which makes biological sense."
- "I'm working with domain experts to validate interpretations."
- "This is a methodological contribution: can we extract topology from textual descriptions?"

### **Don't Say:**

- "I discovered that feedback circuits..." (too strong—you found a pattern, experts validate it)
- "The topology proves..." (too strong—it suggests, doesn't prove)
- "I'm an expert in..." (you're not, and that's fine)

### **Frame It This Way:**

**"I'm a visualization and data analysis person. I created a tool to convert text to visual data, applied TDA to see what structure emerged, and found that feedback circuits appear in H₁ loops. I'm working with biologists and TDA experts to understand what this means."**

**This is honest, confident, and accurate.**

---

## Handling Questions

### **If asked about biology:**

"I'm not a biologist—I created the visualization pipeline. The biological interpretation comes from the literature and collaboration with domain experts. What I can say is that the topology groups processes that biologists recognize as having similar regulatory structure."

### **If asked about TDA:**

"I used Ripser with cocycle extraction. The persistence diagrams show H₁ loops, and I extracted which processes form each loop. I'm learning more about TDA through this collaboration."

### **If asked about limitations:**

"Absolutely—this is a pilot study. The sample size is small (108), the features are structural counts (could add graph metrics), and the flowcharts are LLM-generated (need fact-checking). That's why we're scaling up and seeking expert validation."

### **If asked "What's the contribution?"**

"The contribution is methodological: demonstrating that we can extract topological structure from textual descriptions via visualization. The biological finding—that feedback circuits appear in H₁ loops—validates that the method is capturing real structure, not artifact."

---

## Confidence Points

**You should feel confident because:**

1. **You created something novel** - Mermaid visualization pipeline
2. **You applied a method correctly** - TDA on your data
3. **You found meaningful structure** - Feedback circuits in loops
4. **You're being transparent** - Open source, seeking validation
5. **You're collaborating** - Working with experts, not claiming expertise

**The imposter feeling is normal when working across domains.** But you're not pretending to be an expert—you're contributing a novel approach and inviting experts to interpret the results. That's how interdisciplinary research works.

---

## Bottom Line

**You're not a fraud. You're an innovator working at the intersection of domains.**

- You brought visualization expertise
- You applied TDA correctly
- You found interesting structure
- You're seeking expert validation

**That's exactly how good interdisciplinary research happens.**
