# Mathematics Process Taxonomy

**Complete subcategory structure for the Mathematics Processes Database**

---

## Core Branches

### 1. **Algebra**
Fundamental algebraic structures and operations

#### Subcategories:
- `abstract_algebra` - Groups, rings, fields, modules
- `linear_algebra` - Vector spaces, matrices, eigenvalues, linear transformations
- `polynomial_algebra` - Polynomial operations, factoring, roots
- `boolean_algebra` - Logical operations, set theory
- `commutative_algebra` - Commutative rings, ideals, modules
- `noncommutative_algebra` - Non-commutative rings, algebras

**Example Processes:**
- Matrix multiplication algorithm
- Gaussian elimination
- Polynomial long division
- Group operation verification
- Vector space basis construction

---

### 2. **Analysis**
Mathematical analysis and calculus

#### Subcategories:
- `calculus` - Differentiation, integration, limits
- `real_analysis` - Real numbers, sequences, series, continuity
- `complex_analysis` - Complex functions, contour integration, residues
- `functional_analysis` - Banach spaces, Hilbert spaces, operators
- `differential_equations` - ODEs, PDEs, systems of equations
- `measure_theory` - Lebesgue measure, integration theory
- `numerical_analysis` - Numerical methods, approximation, error analysis

**Example Processes:**
- Integration by parts
- Finding derivatives using chain rule
- Solving first-order ODEs
- Newton's method for root finding
- Fourier series computation

---

### 3. **Geometry**
Spatial relationships and shapes

#### Subcategories:
- `euclidean_geometry` - Classical plane and solid geometry
- `differential_geometry` - Manifolds, curves, surfaces, tensors
- `algebraic_geometry` - Varieties, schemes, sheaves
- `topology` - Topological spaces, continuity, compactness
- `projective_geometry` - Projective spaces, transformations
- `non_euclidean_geometry` - Hyperbolic, elliptic geometry
- `computational_geometry` - Algorithms for geometric problems

**Example Processes:**
- Triangle area calculation
- Surface area of revolution
- Graph isomorphism testing
- Convex hull algorithm
- Coordinate transformation

---

### 4. **Number Theory**
Properties and relationships of numbers

#### Subcategories:
- `elementary_number_theory` - Divisibility, primes, modular arithmetic
- `algebraic_number_theory` - Number fields, algebraic integers
- `analytic_number_theory` - Prime number theorem, zeta functions
- `combinatorial_number_theory` - Additive combinatorics, Ramsey theory
- `computational_number_theory` - Primality testing, factorization

**Example Processes:**
- Euclidean algorithm (GCD)
- Prime factorization
- Chinese remainder theorem
- Modular exponentiation
- Miller-Rabin primality test

---

### 5. **Probability & Statistics**
Randomness, uncertainty, and data analysis

#### Subcategories:
- `probability_theory` - Probability spaces, random variables, distributions
- `statistics` - Descriptive statistics, hypothesis testing, regression
- `stochastic_processes` - Markov chains, Brownian motion, random walks
- `bayesian_statistics` - Bayesian inference, prior/posterior distributions
- `statistical_inference` - Estimation, confidence intervals, tests

**Example Processes:**
- Bayes' theorem application
- Hypothesis testing procedure
- Monte Carlo simulation
- Linear regression calculation
- Confidence interval construction

---

### 6. **Combinatorics & Discrete Mathematics**
Counting, arrangements, and discrete structures

#### Subcategories:
- `combinatorics` - Permutations, combinations, counting principles
- `graph_theory` - Graphs, trees, paths, connectivity
- `discrete_optimization` - Integer programming, network flows
- `coding_theory` - Error-correcting codes, information theory
- `design_theory` - Block designs, Latin squares

**Example Processes:**
- Permutation generation
- Shortest path algorithm (Dijkstra)
- Minimum spanning tree
- Binomial coefficient calculation
- Graph coloring algorithm

---

### 7. **Logic & Foundations**
Mathematical logic and foundations

#### Subcategories:
- `proof_methods` - Direct proof, induction, contradiction, construction
- `set_theory` - Sets, functions, relations, cardinality
- `model_theory` - Models, satisfiability, completeness
- `computability_theory` - Turing machines, decidability, complexity
- `category_theory` - Categories, functors, natural transformations

**Example Processes:**
- Mathematical induction proof
- Proof by contradiction
- Set union/intersection operations
- Truth table construction
- Recursive function definition

---

### 8. **Applied Mathematics**
Mathematical methods applied to real-world problems

#### Subcategories:
- `optimization` - Linear programming, nonlinear optimization, convex optimization
- `mathematical_modeling` - Model construction, parameter estimation
- `operations_research` - Scheduling, queuing theory, game theory
- `mathematical_physics` - Differential equations in physics, quantum mechanics
- `financial_mathematics` - Option pricing, risk analysis, portfolio theory
- `cryptography` - Encryption algorithms, cryptographic protocols

**Example Processes:**
- Simplex method for linear programming
- Newton's method for optimization
- Black-Scholes option pricing
- RSA encryption/decryption
- Queue system analysis

---

### 9. **Numerical Methods**
Computational algorithms for mathematical problems

#### Subcategories:
- `numerical_linear_algebra` - Matrix factorization, iterative methods
- `numerical_integration` - Quadrature methods, Monte Carlo integration
- `numerical_optimization` - Gradient descent, Newton's method variants
- `finite_difference_methods` - PDE discretization
- `finite_element_methods` - FEM for PDEs

**Example Processes:**
- LU decomposition
- Newton-Raphson root finding
- Trapezoidal rule integration
- Gradient descent algorithm
- Finite difference approximation

---

### 10. **Mathematical Physics**
Mathematics applied to physical systems

#### Subcategories:
- `quantum_mechanics` - Quantum states, operators, measurement
- `classical_mechanics` - Lagrangian, Hamiltonian mechanics
- `electromagnetism` - Maxwell's equations, field calculations
- `statistical_mechanics` - Partition functions, phase transitions
- `relativity` - Special and general relativity mathematics

**Example Processes:**
- Quantum state measurement
- Lagrangian equation derivation
- Electric field calculation
- Partition function computation
- Lorentz transformation

---

## Taxonomy Summary

**Total Major Branches:** 10  
**Total Subcategories:** ~60  
**Current Processes:** 5  
**Target Coverage:** Multiple processes per subcategory

---

## Implementation Notes

1. **Folder Structure:** Each subcategory becomes a folder under `/math-processes/`
2. **Naming Convention:** Use lowercase with underscores (e.g., `linear_algebra`, `proof_methods`)
3. **Process Naming:** `{subcategory}-{process-name}-process.json`
4. **Metadata:** Each process includes subcategory, complexity, node count, sources

---

## Priority for Initial Population

**Phase 1 (High Priority - Core Concepts):**
- `calculus` - Integration, differentiation
- `linear_algebra` - Matrix operations, eigenvalues
- `proof_methods` - Induction, contradiction
- `probability` - Basic probability, Bayes' theorem
- `algorithms` - Euclidean algorithm, sorting

**Phase 2 (Medium Priority - Common Applications):**
- `differential_equations` - ODE solving methods
- `optimization` - Linear programming, gradient descent
- `graph_theory` - Shortest path, spanning trees
- `statistics` - Hypothesis testing, regression
- `numerical_methods` - Root finding, integration

**Phase 3 (Expansion - Specialized Topics):**
- Advanced topics in each branch
- Interdisciplinary applications
- Research-level processes

---

**Last Updated:** December 31, 2025

