# Email Response to Jordan Matuszewski

**Subject:** Re: Friday Seminar - March 13 works great

---

Hi Jordan,

Thanks for getting back to me so quickly!

**Friday Seminar**

March 13, 2026 works perfectly for me. Here's the title and abstract:

**Title:**  
"Feedback Loops as Loops: Topological Data Analysis of Genetic Regulatory Circuits"

**Abstract:**  
We apply topological data analysis (TDA) to 108 genetic regulatory circuits from the Genome Logic Modeling Project (GLMP), representing processes from E. coli, S. cerevisiae, and Bacillus subtilis. Each circuit is encoded as a feature vector (node counts, conditional logic, OR/AND/NOT gates). Using Vietoris-Rips persistence (Ripser, maxdim=2), we find that the most persistent H₁ loops correspond to known feedback circuits: lac operon appears in a top H₁ loop (persistence = 0.302), two-component EnvZ-OmpR signaling in another (0.231), and a large loop (0.330) aggregates SOS response, stringent response, catabolite repression, Pho regulon, and quorum sensing—all established regulatory systems with feedback. This suggests TDA on structural features captures genuine regulatory architecture, not random variation. We discuss biological interpretation, organism-specific vs. cross-species topological patterns, and next steps: Mapper visualization, persistent cohomology, and scaling to 500+ processes for circuit classification.

**Keywords:** persistent homology, genetic circuits, feedback loops, regulatory networks, topological data analysis

**Note:** Analysis conducted using Ripser with cocycle extraction. Code, data, and documentation are fully open source on GitHub.

**Background Materials**

For context, here are the broader project preprints:

1. **Knowledge Engine Vision**: https://doi.org/10.5281/zenodo.18463304
2. **Programming Framework**: https://doi.org/10.5281/zenodo.18463442
3. **GLMP Database**: https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/glmp-database-table.html

The TDA analysis code and results (persistence diagrams, H1 loop analysis, biological coherence check) are in the GitHub repo: https://github.com/garywelz/glmp/tree/main/tda-analysis

We're also working on a specific preprint for this TDA work that should be ready in a few days—I'll share that once it's up.

**This Friday's Seminar**

I'm planning to attend this Friday's seminar to get a sense of the group and format. Looking forward to meeting everyone then!

Best,

Gary

Gary Welz  
garywelz@gmail.com | 917-593-2537  
https://www.copernicusai.fyi
