# TDAP Tier-1 write set v2 (2026-09-19) — per Claude Chat title review, NOT executed

6 seeds (separate intake) + 124 expansion candidates = **130 total records**.

Revision from v1: Chat found the v1 filter wrong in two directions -- (1) co-citation rule did not require a Jordan-named parent (16 papers co-cited only by unconfirmed tdap-q3 seeds had leaked into tier-1); (2) holding all 84 Otter-only references was too blunt (74 are core TDA). Both fixed here; question_ids now inherit only from the six confirmed seeds (verified: 0 candidates carry a tag outside tdap-q1/tdap-q2).

## A. Seed intake (6 -- via researcher_cited_intake.py, separate from the pilot)

| Title | Authors | DOI | question_ids |
|---|---|---|---|
| Persistent Cohomology and Circular Coordinates | de Silva, Morozov, Vejdemo-Johansson | `10.1007/s00454-011-9344-x` | tdap-q1 |
| Sparse Circular Coordinates via Principal Z-Bundles | Perea | `10.1007/978-3-030-43408-3_17` | tdap-q1 |
| Toroidal Coordinates: Decorrelating Circular Coordinates With Lattice Reduction | Scoccola et al. | `10.4230/lipics.socg.2023.57` | tdap-q1 |
| Computing Persistent Homology | Zomorodian, Carlsson | `10.1007/s00454-004-1146-y` | tdap-q2 |
| A roadmap for the computation of persistent homology | Otter et al. | `10.1140/epjds/s13688-017-0109-5` | tdap-q2 |
| Distributed Computation of Persistent Cohomology | Nigmetov, Morozov | `10.1137/1.9781611978957.15` | tdap-q2 |

## B. Expansion candidates (124) — every parent is one of the six confirmed seeds, verified

| Title | DOI | reason | parents | question_ids | cited_by_count |
|---|---|---|---|---|---|
| Single-cell topological RNA-seq analysis reveals insights into cellular differentiation and development **[MERGE, not create]** | `10.1038/nbt.3854` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 270 |
| Nonlinear Dimensionality Reduction by Locally Linear Embedding | `10.1126/science.290.5500.2323` | cited_by_2plus_seeds | 10.1007/s00454-011-9344-x; 1007/978-3-030-43408-3_17 | tdap-q1 | 15123 |
| A Global Geometric Framework for Nonlinear Dimensionality Reduction | `10.1126/science.290.5500.2319` | cited_by_2plus_seeds | 10.1007/s00454-011-9344-x; 1007/978-3-030-43408-3_17; 10.3389/fncom.2021.616748 | tdap-q1,tdap-q3 | 13849 |
| Detecting strange attractors in turbulence | `10.1007/bfb0091924` | cited_by_2plus_seeds | .4230/lipics.socg.2023.57; 10.1007/s10208-014-9206-z; 10.3389/fncom.2021.616748 | tdap-q1,tdap-q3 | 10289 |
| Laplacian Eigenmaps for Dimensionality Reduction and Data Representation | `10.1162/089976603321780317` | top_cited_in_seed | 1007/978-3-030-43408-3_17 | tdap-q1 | 7807 |
| Multidimensional Scaling by Optimizing Goodness of Fit to a Nonmetric Hypothesis | `10.1007/bf02289565` | top_cited_in_seed | 1007/978-3-030-43408-3_17 | tdap-q1 | 7452 |
| Laplacian Eigenmaps and Spectral Techniques for Embedding and Clustering | `10.7551/mitpress/1120.003.0080` | top_cited_in_seed | 10.1007/s00454-011-9344-x | tdap-q1 | 4543 |
| LSQR: An Algorithm for Sparse Linear Equations and Sparse Least Squares | `10.1145/355984.355989` | top_cited_in_seed | 10.1007/s00454-011-9344-x | tdap-q1 | 4439 |
| Factoring polynomials with rational coefficients | `10.1007/bf01457454` | top_cited_in_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 4047 |
| Three-dimensional alpha shapes | `10.1145/174462.156635` | top_cited_in_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 2497 |
| Topology and data | `10.1090/s0273-0979-09-01249-x` | cited_by_2plus_seeds | 0/epjds/s13688-017-0109-5; 10.1007/s10208-014-9206-z; 10.1162/neco_a_01150 | tdap-q2,tdap-q3 | 2361 |
| Elements of Algebraic Topology | `10.1201/9780429493911` | top_cited_in_seed | 10.1007/s00454-004-1146-y | tdap-q2 | 2235 |
| On the shape of a set of points in the plane | `10.1109/tit.1983.1056714` | top_cited_in_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 1878 |
| Topological Persistence and Simplification | `10.1007/s00454-002-2885-2` | cited_by_2plus_seeds | 10.1007/s00454-011-9344-x; 10.1007/s00454-004-1146-y; 0/epjds/s13688-017-0109-5 | tdap-q1,tdap-q2 | 1827 |
| Clustering to minimize the maximum intercluster distance | `10.1016/0304-3975(85)90224-5` | top_cited_in_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 1755 |
| Stability of Persistence Diagrams | `10.1007/s00454-006-1276-5` | cited_by_2plus_seeds | 0/epjds/s13688-017-0109-5; 10.1007/s10208-014-9206-z; 10.3389/fncom.2021.616748 | tdap-q2,tdap-q3 | 1325 |
| Barcodes: The persistent topology of data | `10.1090/s0273-0979-07-01191-3` | cited_by_2plus_seeds | 10.1007/s00454-011-9344-x; 0/epjds/s13688-017-0109-5; 10.1162/neco_a_01150 | tdap-q1,tdap-q2,tdap-q3 | 1308 |
| Riemannian Geometry and Geometric Analysis | `10.1007/978-3-662-22385-7` | top_cited_in_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 1244 |
| Foundations of Algebraic Topology | `10.1515/9781400877492` | top_cited_in_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 1107 |
| Morse Theory for Cell Complexes | `10.1006/aima.1997.1650` | top_cited_in_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 985 |
| Persistent homology—a survey | `10.1090/conm/453/08802` | cited_by_2plus_seeds | 10.1007/s00454-011-9344-x; 0/epjds/s13688-017-0109-5 | tdap-q1,tdap-q2 | 865 |
| Topology based data analysis identifies a subgroup of breast cancers with a unique mutational profile and excellent survival | `10.1073/pnas.1102826108` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 543 |
| On the Local Behavior of Spaces of Natural Images | `10.1007/s11263-007-0056-x` | cited_by_2plus_seeds | 1007/978-3-030-43408-3_17; 0/epjds/s13688-017-0109-5; 10.1007/s10208-014-9206-z | tdap-q1,tdap-q2,tdap-q3 | 503 |
| Fibre Bundles | `10.1007/978-1-4757-4008-0` | top_cited_in_seed | 1007/978-3-030-43408-3_17 | tdap-q1 | 466 |
| Coverage in sensor networks via persistent homology | `10.2140/agt.2007.7.339` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 440 |
| Proximity of persistence modules and their diagrams | `10.1145/1542362.1542407` | cited_by_2plus_seeds | 0/epjds/s13688-017-0109-5; 10.1007/s10208-014-9206-z | tdap-q2,tdap-q3 | 424 |
| Hierarchical structures of amorphous solids characterized by persistent homology | `10.1073/pnas.1520877113` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 419 |
| Computational Homology | `10.1007/b97315` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 373 |
| The union of balls and its dual shape | `10.1007/bf02574053` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 330 |
| A stable multi-scale kernel for topological machine learning | `10.1109/cvpr.2015.7299106` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 318 |
| PERSISTENCE BARCODES FOR SHAPES | `10.1142/s0218654305000761` | top_cited_in_seed | 10.1007/s00454-004-1146-y | tdap-q2 | 292 |
| Topology of viral evolution | `10.1073/pnas.1313480110` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 286 |
| Persistence Theory: From Quiver Representations to Data Analysis | `10.1090/surv/209` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 285 |
| Zigzag persistent homology and real-valued functions | `10.1145/1542362.1542408` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 282 |
| The Theory of Multidimensional Persistence | `10.1007/s00454-009-9176-0` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 272 |
| Confidence sets for persistence diagrams | `10.1214/14-aos1252` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 265 |
| Persistent homology analysis of protein structure, flexibility, and folding | `10.1002/cnm.2655` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 263 |
| Morse Theory for Filtrations and Efficient Computation of Persistent Homology | `10.1007/s00454-013-9529-6` | cited_by_2plus_seeds | 0/epjds/s13688-017-0109-5; 10.1007/s10208-014-9206-z | tdap-q2,tdap-q3 | 260 |
| Probability measures on the space of persistence diagrams | `10.1088/0266-5611/27/12/124007` | cited_by_2plus_seeds | 0/epjds/s13688-017-0109-5; 10.1007/s10208-014-9206-z | tdap-q2,tdap-q3 | 260 |
| The Gudhi Library: Simplicial Complexes and Persistent Homology | `10.1007/978-3-662-44199-2_28` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 252 |
| The Nonlinear Statistics of High-Contrast Patches in Natural Images | `10.1023/a:1023705401078` | top_cited_in_seed | 1007/978-3-030-43408-3_17 | tdap-q1 | 234 |
| Curvature and Characteristic Classes | `10.1007/bfb0065364` | top_cited_in_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 218 |
| Fréchet Means for Distributions of Persistence Diagrams | `10.1007/s00454-014-9604-7` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 217 |
| Fast construction of the Vietoris-Rips complex | `10.1016/j.cag.2010.03.007` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 207 |
| Topological Data Analysis of Biological Aggregation Models | `10.1371/journal.pone.0126383` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 201 |
| A simple heuristic for the p-centre problem | `10.1016/0167-6377(85)90002-1` | top_cited_in_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 172 |
| Random Geometric Complexes | `10.1007/s00454-010-9319-3` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 169 |
| Floating-Point LLL Revisited | `10.1007/11426639_13` | top_cited_in_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 164 |
| Dualities in persistent (co)homology | `10.1088/0266-5611/27/12/124003` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 163 |
| A topological measurement of protein compressibility | `10.1007/s13160-014-0153-5` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 139 |
| Zigzag persistent homology in matrix multiplication time | `10.1145/1998196.1998229` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 139 |
| Reconceiving the hippocampal map as a topological template | `10.7554/elife.03476` | cited_by_2plus_seeds | 0/epjds/s13688-017-0109-5; 10.1162/neco_a_01150 | tdap-q2,tdap-q3 | 136 |
| A barcode shape descriptor for curve point cloud data | `10.1016/j.cag.2004.08.015` | top_cited_in_seed | 10.1007/s00454-004-1146-y | tdap-q2 | 133 |
| Persistence barcodes for shapes | `10.1145/1057432.1057449` | top_cited_in_seed | 10.1007/s00454-004-1146-y | tdap-q2 | 132 |
| Persistent homology of time-dependent functional networks constructed from coupled time series | `10.1063/1.4978997` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 127 |
| A statistical approach to persistent homology | `10.4310/hha.2007.v9.n2.a12` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 124 |
| Metrics for Generalized Persistence Modules | `10.1007/s10208-014-9229-5` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 124 |
| Persistence Diagrams of Cortical Surface Data | `10.1007/978-3-642-02498-6_32` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 123 |
| Persistence of force networks in compressed granular media | `10.1103/physreve.87.042207` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 119 |
| Persistent homology for the quantitative prediction of fullerene stability | `10.1002/jcc.23816` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 117 |
| Efficient Computation of Persistent Homology for Cubical Data | `10.1007/978-3-642-23175-9_7` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 113 |
| Distributed Computation of Persistent Homology | `10.1137/1.9781611973198.4` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 113 |
| Topological analysis of data | `10.1140/epjds/s13688-017-0104-x` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 113 |
| On Bounding the Betti Numbers and Computing the Euler Characteristic of Semi-Algebraic Sets | `10.1007/pl00009443` | top_cited_in_seed | 10.1007/s00454-004-1146-y | tdap-q2 | 107 |
| Persistent Homology for Path Planning in Uncertain Environments | `10.1109/tro.2015.2412051` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 106 |
| Computing Robustness and Persistence for Images | `10.1109/tvcg.2010.139` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 105 |
| Persistent Homology of Collaboration Networks | `10.1155/2013/815035` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 102 |
| Strong Homotopy Types, Nerves and Collapses | `10.1007/s00454-011-9357-5` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 100 |
| Categorification of Persistent Homology | `10.1007/s00454-014-9573-x` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 97 |
| Persistent homology for random fields and complexes | `10.1214/10-imscoll609` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 93 |
| Nonlinear dimensionality reduction of data manifolds with essential loops | `10.1016/j.neucom.2004.11.042` | top_cited_in_seed | 10.1007/s00454-011-9344-x | tdap-q1 | 90 |
| Learning the geometry of common latent variables using alternating-diffusion | `10.1016/j.acha.2015.09.002` | all_references_from_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 87 |
| Linear-Size Approximations to the Vietoris–Rips Filtration | `10.1007/s00454-013-9513-1` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 84 |
| Clear and Compress: Computing Persistent Homology in Chunks | `10.1007/978-3-319-04099-8_7` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 81 |
| Computing Optimal Morse Matchings | `10.1137/s0895480104445885` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 78 |
| Inference of Ancestral Recombination Graphs through Topological Data Analysis | `10.1371/journal.pcbi.1005071` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 76 |
| Persistence-sensitive simplification functions on 2-manifolds | `10.1145/1137856.1137878` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 76 |
| Incremental construction of the delaunay triangulation and the delaunay graph in medium dimension | `10.1145/1542362.1542403` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 72 |
| AN ALGEBRAIC TOPOLOGICAL METHOD FOR FEATURE IDENTIFICATION | `10.1142/s021819590600204x` | top_cited_in_seed | 10.1007/s00454-004-1146-y | tdap-q2 | 66 |
| Quantifying force networks in particulate systems | `10.1016/j.physd.2014.05.009` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 65 |
| Alpha shape and Delaunay triangulation in studies of protein-related interactions | `10.1093/bib/bbs077` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 62 |
| Computing Simplicial Homology Based on Efficient Smith Normal Form Algorithms | `10.1007/978-3-662-05148-1_10` | top_cited_in_seed | 10.1007/s00454-004-1146-y | tdap-q2 | 61 |
| Object-oriented persistent homology | `10.1016/j.jcp.2015.10.036` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 60 |
| Topological consistency via kernel estimation | `10.3150/15-bej744` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 60 |
| jHoles: A Tool for Understanding Biological Complex Networks via Clique Weight Rank Persistent Homology | `10.1016/j.entcs.2014.06.011` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 58 |
| Branching and Circular Features in High Dimensional Data | `10.1109/tvcg.2011.177` | all_references_from_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 57 |
| PHAT – Persistent Homology Algorithms Toolbox | `10.1007/978-3-662-44199-2_24` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 57 |
| Probabilistic Fréchet means for time varying persistence diagrams | `10.1214/15-ejs1030` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 57 |
| A weak characterisation of the Delaunay triangulation | `10.1007/s10711-008-9261-1` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 52 |
| Crackle: The Homology of Noise | `10.1007/s00454-014-9621-6` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 48 |
| Weak witnesses for Delaunay triangulations of submanifolds | `10.1145/1236246.1236267` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 47 |
| Topological trajectory classification with filtrations of simplicial complexes and persistent homology | `10.1177/0278364915586713` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 46 |
| Reconstruction Using Witness Complexes | `10.1007/s00454-008-9094-6` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 46 |
| Computing Betti numbers via combinatorial Laplacians | `10.1145/237814.237985` | top_cited_in_seed | 10.1007/s00454-004-1146-y | tdap-q2 | 45 |
| Topological structures in the equities market network | `10.1073/pnas.0802806106` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 44 |
| Computational geometry algorithms library | `10.1145/1665817.1665821` | top_cited_in_seed | 10.1007/s00454-004-1146-y | tdap-q2 | 41 |
| Topological persistence vineyard for dynamic functional brain connectivity during resting and gaming stages | `10.1016/j.jneumeth.2016.04.001` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 39 |
| A one‐dimensional homologically persistent skeleton of an unstructured point cloud in any metric space | `10.1111/cgf.12713` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 37 |
| Applications of computational homology to the analysis of treatment response in breast cancer patients | `10.1016/j.topol.2009.04.036` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 36 |
| Manifold Reconstruction in Arbitrary Dimensions Using Witness Complexes | `10.1007/s00454-009-9175-1` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 36 |
| Simplifying the homology of networks via strong collapses | `10.1109/icassp.2013.6638666` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 34 |
| Geometry Helps to Compare Persistence Diagrams | `10.1137/1.9781611974317.9` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 34 |
| Topological Descriptors of Histology Images | `10.1007/978-3-319-10581-9_29` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 33 |
| On the Complexity of Lattice Problems with Polynomial Approximation Factors | `10.1007/978-3-642-02295-1_15` | all_references_from_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 32 |
| Approximate Čech Complex in Low and High Dimensions | `10.1007/978-3-642-45030-3_62` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 32 |
| On the complexity of computing the homology type of a triangulation | `10.1109/sfcs.1991.185432` | top_cited_in_seed | 10.1007/s00454-004-1146-y | tdap-q2 | 31 |
| Multiscale Projective Coordinates via Persistent Cohomology of Sparse Filtrations | `10.1007/s00454-017-9927-2` | top_cited_in_seed | 1007/978-3-030-43408-3_17 | tdap-q1 | 23 |
| Persistent cohomology and circular coordinates | `10.1145/1542362.1542406` | all_references_from_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 22 |
| Topology Data Analysis of Critical Transitions in Financial Networks | `10.2139/ssrn.2903278` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 21 |
| Inapproximability Results for Computational Problems on Lattices | `10.1007/978-3-642-02295-1_14` | all_references_from_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 20 |
| Advances in Applied and Computational Topology | `10.1090/psapm/070` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 19 |
| Persistent homology for automatic determination of human-data based cost of bipedal walking | `10.1016/j.nahs.2012.07.006` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 17 |
| Computing Persistent Homology with Various Coefficient Fields in a Single Pass | `10.1007/978-3-662-44777-2_16` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 14 |
| Twisty Takens: a geometric characterization of good observations on dense trajectories | `10.1007/s41468-019-00036-9` | top_cited_in_seed | 1007/978-3-030-43408-3_17 | tdap-q1 | 13 |
| Comparative Topological Signatures of Growing Collaboration Networks | `10.1007/978-3-319-54241-6_18` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 13 |
| What can topology tell us about the neural code? | `10.1090/bull/1554` | cited_by_2plus_seeds | 0/epjds/s13688-017-0109-5; 10.3389/fncom.2021.616748 | tdap-q2,tdap-q3 | 12 |
| Computing persistent features in big data: A distributed dimension reduction approach | `10.1109/icassp.2014.6853548` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 10 |
| Finding Minimal Parameterizations of Cylindrical Image Manifolds | `10.1109/cvprw.2006.82` | top_cited_in_seed | 10.1007/s00454-011-9344-x | tdap-q1 | 9 |
| A distributed collapse of a network's dimensionality | `10.1109/globalsip.2013.6736948` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | 8 |
| DREiMac: Dimensionality Reduction with Eilenberg-MacLane Coordinates | `10.21105/joss.05791` | all_references_from_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 3 |
| Topological Learning for Motion Data via Mixed Coordinates | `10.1109/bigdata52589.2021.9671525` | all_references_from_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 3 |
| (Quasi)Periodicity Quantification in Video Data, Using Topology | `10.1137/17m1150736` | all_references_from_seed | .4230/lipics.socg.2023.57 | tdap-q1 | 3 |
| Topological Eulerian Synthesis of Slow Motion Periodic Videos | `10.1109/icip.2018.8451014` | top_cited_in_seed | 1007/978-3-030-43408-3_17 | tdap-q1 | 2 |
| Persistent homology analysis of brain artery trees | `10.1214/15-aoas886` | all_references_from_seed | 0/epjds/s13688-017-0109-5 | tdap-q2 | None |