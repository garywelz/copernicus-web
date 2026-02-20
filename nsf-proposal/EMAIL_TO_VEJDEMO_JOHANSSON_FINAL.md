# Email to Dr. Mikael Vejdemo-Johansson (Final Version)

**Subject:** Collaboration Opportunity: TDA for Knowledge Graphs & Genetic Circuits (NSF/CUNY)

---

Dear Dr. Vejdemo-Johansson,

I'm reaching out about a potential collaboration that I believe could be exceptionally productive. I should be transparent: I used Claude Sonnet to analyze your research and help me understand the connections to my work. But there's also something more personal — I was moved by your 2019 AMS Notices article "Mental Health in the Mathematics Community." That kind of openness is rare in academia and resonates with me.

**What I've Built**

I recently submitted an NSF CISE proposal through the Graduate Center, Proposal 2616543, https://www.research.gov/proposalprep/#/proposal/295407/360088  (~$691K, 3 years) for "CopernicusAI Knowledge Engine" — an AI-powered research platform that's fully operational:

- **User-Prompted AI Research Briefing Podcasts** with full citation tracking. https://www.copernicusai.fyi 
- **314 scientific processes** as Mermaid Markdwon format flowcharts across biology, chemistry, physics, math, and CS
- **108 E. Coli and Yeast biochemical process flowcharts** (Genome Logic Modeling Project aka GLMP) with systematic color-coding
- **12,000+ papers** in a prototype knowledge graph with vector search and RAG

Everything is public: https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/copernicusai-public-reviewer.html.

**Why Your TDA Work Fits Perfectly**

Reading about your Mapper algorithm, persistent cohomology for circular coordinates, and cross-disciplinary applications (linguistics, politics, biology), Claude and I see compelling connections:

1. **Knowledge graph topology** - Mapper could reveal research communities, gaps, bridging papers
2. **Process space analysis** - 314 processes across 5 disciplines = unique dataset for universal patterns
3. **Genetic circuit classification** - Persistent cohomology for feedback/oscillatory circuits
4. **Multi-modal integration** - Your 2021 PMC work on heterogeneous data mirrors my challenge

**I've Already Started**

To test the approach, I ran TDA on all 108 process flowcharts in my Genome Logic Modeling Project https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/glmp-database-table.html using Ripser with cocycle extraction. The results are interesting:

**33 persistent H₁ loops detected** (persistence 0.23-0.33)—clear topological structure, not noise.

Most compellingly:
- **Loop #3** (persistence 0.302): Contains **lac operon**—the canonical textbook example of negative feedback regulation
- **Loop #5** (persistence 0.231): Contains **EnvZ-OmpR two-component signaling**—the paradigm for bacterial signal transduction with feedback
- **Feedback enrichment**: Known feedback circuits appear in ~15 of the loop processes vs. ~9 expected by chance (suggesting p < 0.05)

The topology is detecting genuine regulatory architecture, not random structural variation. Some loops are organism-specific (Loop #2 = pure yeast, Loop #3 = pure E. coli), while others mix species, suggesting TDA distinguishes organism-specific circuit families from universal regulatory motifs.

**Questions I'd love to discuss:**
- Do these H₁ features map to established regulatory motifs beyond lac/two-component?
- Would Mapper visualization reveal circuit classes invisible to traditional analysis?
- Can we develop topological metrics for the full 314-process cross-disciplinary database?
- Does the organism-separation pattern suggest a general principle about regulatory evolution?

**Collaboration Options**

I'd welcome exploring several levels:

1. **Current NSF Proposal** Add you as co-PI/consultant. 
2. **Pilot studies** - TDA on process database to demonstrate feasibility for future funding
3. **Future NSF proposal** - Formal integration of TDA with knowledge engine
4. **CUNY affiliation** - As retired CUNY faculty, I need institutional designation (Person of Interest or research/adjunct appointment) to participate in grants. I've previously submitted NSF proposals through the New Media Lab (Prof. Brian Schwartz), but current director Marco Battistella wisely suggested I connect with faculty doing related research - and Claude 4.5 led me to you.

**Proposed Next Step**

Would you be open to a 30-45 minute conversation (Graduate Center or Zoom)? I can demo the live infrastructure and we can explore whether there's genuine research chemistry here.

**Attachments:**
1. **ONE_PAGE_SUMMARY.pdf** - TDA results overview
2. **H1_LOOP_ANALYSIS.pdf** - Detailed analysis of top 5 persistent loops with biological interpretation
3. **BIOLOGICAL_COHERENCE_CHECK.pdf** - Statistical analysis showing feedback circuit enrichment
4. **glmp_persistence_diagram.png** - The persistence diagram (H₀, H₁, H₂)
5. **h1_loop_results.json** - Raw data mapping loops to specific processes
6. **NSF Proposal Summary** - One-page summary of the project.

**Links to Preprints of Related Papers:**
- Knowledge Engine vision: https://doi.org/10.5281/zenodo.18463303
- Programming Framework: https://doi.org/10.5281/zenodo.18463442

Thank you for considering this.

Best regards,

Gary Welz  
garywelz@gmail.com | 917-593-2537  
460 W. 24th St. Apt #3A, New York, NY 10011
