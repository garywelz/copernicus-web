# TDAP Tier-1 write set (2026-09-19) — for review, NOT executed

6 seeds (separate intake) + 75 expansion candidates (via citation_expansion_pilot.py --write) = **81 total records this tier would add/merge**.

## A. Seed intake (6 -- via researcher_cited_intake.py, one call per seed, separate from the pilot)

| Title | Authors | DOI | question_ids |
|---|---|---|---|
| Persistent Cohomology and Circular Coordinates | de Silva, Morozov, Vejdemo-Johansson | `10.1007/s00454-011-9344-x` | tdap-q1 |
| Sparse Circular Coordinates via Principal Z-Bundles | Perea | `10.1007/978-3-030-43408-3_17` | tdap-q1 |
| Toroidal Coordinates: Decorrelating Circular Coordinates With Lattice Reduction | Scoccola, Gakhar, Bush, Schonsheck, Rask, Zhou, Perea | `10.4230/lipics.socg.2023.57` | tdap-q1 |
| Computing Persistent Homology | Zomorodian, Carlsson | `10.1007/s00454-004-1146-y` | tdap-q2 |
| A roadmap for the computation of persistent homology | Otter, Porter, Tillmann, Grindrod, Harrington | `10.1140/epjds/s13688-017-0109-5` | tdap-q2 |
| Distributed Computation of Persistent Cohomology | Nigmetov, Morozov | `10.1137/1.9781611978957.15` | tdap-q2 |

## B+C+D. Expansion candidates (75) — cited_by_2plus_seeds (32) + parents include a trusted seed (adds 43 more, some overlapping) + the 1 GLMP would_merge

| Title | DOI | reason | parents | question_ids | cited_by_count |
|---|---|---|---|---|---|
| Single-cell topological RNA-seq analysis reveals insights into cellular differentiation and development **[MERGE, not create]** | `10.1038/nbt.3854` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 270 |
| Nonlinear Dimensionality Reduction by Locally Linear Embedding | `10.1126/science.290.5500.2323` | cited_by_2plus_seeds | 10.1007/s00454-011-9344-x; 1007/978-3-030-43408-3_17 | tdap-q1 | 15123 |
| A Global Geometric Framework for Nonlinear Dimensionality Reduction | `10.1126/science.290.5500.2319` | cited_by_2plus_seeds | 10.1007/s00454-011-9344-x; 1007/978-3-030-43408-3_17; 10.3389/fncom.2021.616748 | tdap-q1,tdap-q3 | 13849 |
| Detecting strange attractors in turbulence | `10.1007/bfb0091924` | cited_by_2plus_seeds | .4230/lipics.socg.2023.57; 10.1007/s10208-014-9206-z; 10.3389/fncom.2021.616748 | tdap-q1,tdap-q3 | 10289 |
| UMAP: Uniform Manifold Approximation and Projection | `10.21105/joss.00861` | cited_by_2plus_seeds | 0.1038/s41586-021-04268-7; 10.3389/fncom.2021.616748 | tdap-q3 | 10145 |
| Laplacian Eigenmaps for Dimensionality Reduction and Data Representation | `10.1162/089976603321780317` | top_cited_in_seed | 1007/978-3-030-43408-3_17 | tdap-q1 | 7807 |
| Multidimensional Scaling by Optimizing Goodness of Fit to a Nonmetric Hypothesis | `10.1007/bf02289565` | top_cited_in_seed | 1007/978-3-030-43408-3_17 | tdap-q1 | 7452 |
| Laplacian Eigenmaps and Spectral Techniques for Embedding and Clustering | `10.7551/mitpress/1120.003.0080` | top_cited_in_seed | 10.1007/s00454-011-9344-x | tdap-q1 | 4543 |
| LSQR: An Algorithm for Sparse Linear Equations and Sparse Least Squares | `10.1145/355984.355989` | top_cited_in_seed | 10.1007/s00454-011-9344-x | tdap-q1 | 4439 |
| Microstructure of a spatial map in the entorhinal cortex | `10.1038/nature03721` | cited_by_2plus_seeds | 0.1038/s41586-021-04268-7; 10.3389/fncom.2021.616748 | tdap-q3 | 4285 |
| Factoring polynomials with rational coefficients | `10.1007/bf01457454` | top_cited_in_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 4047 |
| Fully integrated silicon probes for high-density recording of neural activity | `10.1038/nature24636` | cited_by_2plus_seeds | 0.1038/s41586-021-04268-7; 10.3389/fncom.2021.616748 | tdap-q3 | 2447 |
| Topology and data | `10.1090/s0273-0979-09-01249-x` | cited_by_2plus_seeds | 0/epjds/s13688-017-0109-5; 10.1007/s10208-014-9206-z; 10.1162/neco_a_01150 | tdap-q2,tdap-q3 | 2361 |
| Elements of Algebraic Topology | `10.1201/9780429493911` | top_cited_in_seed | 10.1007/s00454-004-1146-y | tdap-q2 | 2235 |
| Place units in the hippocampus of the freely moving rat | `10.1016/0014-4886(76)90055-8` | top_cited_in_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 1920 |
| Head-direction cells recorded from the postsubiculum in freely moving rats. I. Description and quantitative analysis | `10.1523/jneurosci.10-02-00420.1990` | cited_by_2plus_seeds | 0.1038/s41586-021-04268-7; 10.3389/fncom.2021.616748 | tdap-q3 | 1895 |
| Topological Persistence and Simplification | `10.1007/s00454-002-2885-2` | cited_by_2plus_seeds | 10.1007/s00454-011-9344-x; 10.1007/s00454-004-1146-y; 0/epjds/s13688-017-0109-5 | tdap-q1,tdap-q2 | 1827 |
| Clustering to minimize the maximum intercluster distance | `10.1016/0304-3975(85)90224-5` | top_cited_in_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 1755 |
| Conjunctive Representation of Position, Direction, and Velocity in Entorhinal Cortex | `10.1126/science.1125572` | cited_by_2plus_seeds | 0.1038/s41586-021-04268-7; 10.3389/fncom.2021.616748 | tdap-q3 | 1558 |
| Stability of Persistence Diagrams | `10.1007/s00454-006-1276-5` | cited_by_2plus_seeds | 0/epjds/s13688-017-0109-5; 10.1007/s10208-014-9206-z; 10.3389/fncom.2021.616748 | tdap-q2,tdap-q3 | 1325 |
| Barcodes: The persistent topology of data | `10.1090/s0273-0979-07-01191-3` | cited_by_2plus_seeds | 10.1007/s00454-011-9344-x; 0/epjds/s13688-017-0109-5; 10.1162/neco_a_01150 | tdap-q1,tdap-q2,tdap-q3 | 1308 |
| ELEMENTS OF ALGEBRAIC TOPOLOGY | `10.1016/b978-0-08-016160-0.50028-2` | cited_by_2plus_seeds | .4230/lipics.socg.2023.57; 10.1007/s00454-004-1146-y | tdap-q1,tdap-q2 | 1304 |
| Riemannian Geometry and Geometric Analysis | `10.1007/978-3-662-22385-7` | top_cited_in_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 1244 |
| Representation of spatial orientation by the intrinsic dynamics of the head-direction cell ensemble: a theory | `10.1523/jneurosci.16-06-02112.1996` | cited_by_2plus_seeds | 0.1038/s41586-021-04268-7; 10.1162/neco_a_01150 | tdap-q3 | 1069 |
| Persistent Propagation of Concentration Waves in Dissipative Media Far from Thermal Equilibrium | `10.1143/ptp.55.356` | top_cited_in_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 1049 |
| Persistent homology—a survey | `10.1090/conm/453/08802` | cited_by_2plus_seeds | 10.1007/s00454-011-9344-x; 0/epjds/s13688-017-0109-5 | tdap-q1,tdap-q2 | 865 |
| Accurate Path Integration in Continuous Attractor Network Models of Grid Cells | `10.1371/journal.pcbi.1000291` | cited_by_2plus_seeds | 0.1038/s41586-021-04268-7; 10.3389/fncom.2021.616748 | tdap-q3 | 858 |
| The entorhinal grid map is discretized | `10.1038/nature11649` | cited_by_2plus_seeds | 0.1038/s41586-021-04268-7; 10.3389/fncom.2021.616748 | tdap-q3 | 762 |
| On the Local Behavior of Spaces of Natural Images | `10.1007/s11263-007-0056-x` | cited_by_2plus_seeds | 1007/978-3-030-43408-3_17; 0/epjds/s13688-017-0109-5; 10.1007/s10208-014-9206-z | tdap-q1,tdap-q2,tdap-q3 | 503 |
| Fibre Bundles | `10.1007/978-1-4757-4008-0` | top_cited_in_seed | 1007/978-3-030-43408-3_17 | tdap-q1 | 466 |
| The intrinsic attractor manifold and population dynamics of a canonical cognitive circuit across waking and sleep | `10.1038/s41593-019-0460-x` | cited_by_2plus_seeds | 0.1038/s41586-021-04268-7; 10.3389/fncom.2021.616748 | tdap-q3 | 432 |
| Proximity of persistence modules and their diagrams | `10.1145/1542362.1542407` | cited_by_2plus_seeds | 0/epjds/s13688-017-0109-5; 10.1007/s10208-014-9206-z | tdap-q2,tdap-q3 | 424 |
| Clique topology reveals intrinsic geometric structure in neural correlations | `10.1073/pnas.1506407112` | cited_by_2plus_seeds | 0.1038/s41586-021-04268-7; 10.1162/neco_a_01150; 10.3389/fncom.2021.616748 | tdap-q3 | 415 |
| Grid cell symmetry is shaped by environmental geometry | `10.1038/nature14153` | cited_by_2plus_seeds | 0.1038/s41586-021-04268-7; 10.3389/fncom.2021.616748 | tdap-q3 | 412 |
| A Multiplexed, Heterogeneous, and Adaptive Code for Navigation in Medial Entorhinal Cortex | `10.1016/j.neuron.2017.03.025` | cited_by_2plus_seeds | 0.1038/s41586-021-04268-7; 10.1162/neco_a_01150; 10.3389/fncom.2021.616748 | tdap-q3 | 353 |
| The Kuramoto-Sivashinsky equation: A bridge between PDE'S and dynamical systems | `10.1016/0167-2789(86)90166-1` | top_cited_in_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 335 |
| Internally organized mechanisms of the head direction sense | `10.1038/nn.3968` | cited_by_2plus_seeds | 0.1038/s41586-021-04268-7; 10.1162/neco_a_01150 | tdap-q3 | 325 |
| Three-dimensional head-direction coding in the bat brain | `10.1038/nature14031` | cited_by_2plus_seeds | .4230/lipics.socg.2023.57; 0.1038/s41586-021-04268-7 | tdap-q1,tdap-q3 | 317 |
| Nonlinear analysis of hydrodynamic instability in laminar flames—II. Numerical experiments | `10.1016/0094-5765(77)90097-2` | top_cited_in_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 293 |
| PERSISTENCE BARCODES FOR SHAPES | `10.1142/s0218654305000761` | top_cited_in_seed | 10.1007/s00454-004-1146-y | tdap-q2 | 292 |
| On Irregular Wavy Flow of a Liquid Film Down a Vertical Plane | `10.1143/ptp.63.2112` | top_cited_in_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 282 |
| Morse Theory for Filtrations and Efficient Computation of Persistent Homology | `10.1007/s00454-013-9529-6` | cited_by_2plus_seeds | 0/epjds/s13688-017-0109-5; 10.1007/s10208-014-9206-z | tdap-q2,tdap-q3 | 260 |
| Probability measures on the space of persistence diagrams | `10.1088/0266-5611/27/12/124007` | cited_by_2plus_seeds | 0/epjds/s13688-017-0109-5; 10.1007/s10208-014-9206-z | tdap-q2,tdap-q3 | 260 |
| Shearing-induced asymmetry in entorhinal grid cells | `10.1038/nature14151` | cited_by_2plus_seeds | 0.1038/s41586-021-04268-7; 10.3389/fncom.2021.616748 | tdap-q3 | 246 |
| The Nonlinear Statistics of High-Contrast Patches in Natural Images | `10.1023/a:1023705401078` | top_cited_in_seed | 1007/978-3-030-43408-3_17 | tdap-q1 | 234 |
| Topological analysis of population activity in visual cortex | `10.1167/8.8.11` | cited_by_2plus_seeds | 0.1038/s41586-021-04268-7; 10.1162/neco_a_01150 | tdap-q3 | 232 |
| A Topological Paradigm for Hippocampal Spatial Map Formation Using Persistent Homology | `10.1371/journal.pcbi.1002581` | cited_by_2plus_seeds | 0.1038/s41586-021-04268-7; 10.1162/neco_a_01150; 10.3389/fncom.2021.616748 | tdap-q3 | 223 |
| Curvature and Characteristic Classes | `10.1007/bfb0065364` | top_cited_in_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 218 |
| A simple heuristic for the p-centre problem | `10.1016/0167-6377(85)90002-1` | top_cited_in_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 172 |
| Floating-Point LLL Revisited | `10.1007/11426639_13` | top_cited_in_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 164 |
| Reconceiving the hippocampal map as a topological template | `10.7554/elife.03476` | cited_by_2plus_seeds | 0/epjds/s13688-017-0109-5; 10.1162/neco_a_01150 | tdap-q2,tdap-q3 | 136 |
| A barcode shape descriptor for curve point cloud data | `10.1016/j.cag.2004.08.015` | top_cited_in_seed | 10.1007/s00454-004-1146-y | tdap-q2 | 133 |
| Persistence barcodes for shapes | `10.1145/1057432.1057449` | top_cited_in_seed | 10.1007/s00454-004-1146-y | tdap-q2 | 132 |
| On Bounding the Betti Numbers and Computing the Euler Characteristic of Semi-Algebraic Sets | `10.1007/pl00009443` | top_cited_in_seed | 10.1007/s00454-004-1146-y | tdap-q2 | 107 |
| Nonlinear dimensionality reduction of data manifolds with essential loops | `10.1016/j.neucom.2004.11.042` | top_cited_in_seed | 10.1007/s00454-011-9344-x | tdap-q1 | 90 |
| Learning the geometry of common latent variables using alternating-diffusion | `10.1016/j.acha.2015.09.002` | all_references_from_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 87 |
| AN ALGEBRAIC TOPOLOGICAL METHOD FOR FEATURE IDENTIFICATION | `10.1142/s021819590600204x` | top_cited_in_seed | 10.1007/s00454-004-1146-y | tdap-q2 | 66 |
| Computing Simplicial Homology Based on Efficient Smith Normal Form Algorithms | `10.1007/978-3-662-05148-1_10` | top_cited_in_seed | 10.1007/s00454-004-1146-y | tdap-q2 | 61 |
| Branching and Circular Features in High Dimensional Data | `10.1109/tvcg.2011.177` | all_references_from_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 57 |
| Computing Betti numbers via combinatorial Laplacians | `10.1145/237814.237985` | top_cited_in_seed | 10.1007/s00454-004-1146-y | tdap-q2 | 45 |
| Computational geometry algorithms library | `10.1145/1665817.1665821` | top_cited_in_seed | 10.1007/s00454-004-1146-y | tdap-q2 | 41 |
| An Algebraic Family of Complex Lattices for Fading Channels With Application to Space–Time Codes | `10.1109/tit.2005.858923` | all_references_from_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 34 |
| On the Complexity of Lattice Problems with Polynomial Approximation Factors | `10.1007/978-3-642-02295-1_15` | all_references_from_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 32 |
| On the complexity of computing the homology type of a triangulation | `10.1109/sfcs.1991.185432` | top_cited_in_seed | 10.1007/s00454-004-1146-y | tdap-q2 | 31 |
| Multiscale Projective Coordinates via Persistent Cohomology of Sparse Filtrations | `10.1007/s00454-017-9927-2` | top_cited_in_seed | 1007/978-3-030-43408-3_17 | tdap-q1 | 23 |
| Persistent cohomology and circular coordinates | `10.1145/1542362.1542406` | all_references_from_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 22 |
| Inapproximability Results for Computational Problems on Lattices | `10.1007/978-3-642-02295-1_14` | all_references_from_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 20 |
| Twisty Takens: a geometric characterization of good observations on dense trajectories | `10.1007/s41468-019-00036-9` | top_cited_in_seed | 1007/978-3-030-43408-3_17 | tdap-q1 | 13 |
| What can topology tell us about the neural code? | `10.1090/bull/1554` | cited_by_2plus_seeds | 0/epjds/s13688-017-0109-5; 10.3389/fncom.2021.616748 | tdap-q2,tdap-q3 | 12 |
| Finding Minimal Parameterizations of Cylindrical Image Manifolds | `10.1109/cvprw.2006.82` | top_cited_in_seed | 10.1007/s00454-011-9344-x | tdap-q1 | 9 |
| DREiMac: Dimensionality Reduction with
Eilenberg-MacLane Coordinates | `10.21105/joss.05791` | all_references_from_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 3 |
| Topological Learning for Motion Data via Mixed Coordinates | `10.1109/bigdata52589.2021.9671525` | all_references_from_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 3 |
| (Quasi)Periodicity Quantification in Video Data, Using Topology | `10.1137/17m1150736` | all_references_from_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 3 |
| Topological Eulerian Synthesis of Slow Motion Periodic Videos | `10.1109/icip.2018.8451014` | top_cited_in_seed | 1007/978-3-030-43408-3_17 | tdap-q1 | 2 |
| Wolfram | `10.1007/bf01565634` | all_references_from_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 0 |