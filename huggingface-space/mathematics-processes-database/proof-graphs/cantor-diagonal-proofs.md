# Cantor Diagonal Proofs

This extension adds three Cantor-style proof graphs to the pilot. They test a family of structures that differs from the Euclidean and arithmetic examples: enumeration, diagonal traversal, anti-diagonal construction, and self-reference-like contradiction.

## Family Design Note

Cantor's diagonal arguments are best represented as hybrid proof graphs:

- the logical proof is a dependency graph;
- the diagonal scan or enumeration is an algorithm capsule;
- the decisive step is usually an anti-diagonal object constructed from an assumed listing.

These graphs are especially useful for the database because they show a recurring proof pattern across different theorems.

```mermaid
flowchart TD
  assumeListing["Assumption: proposed enumeration or function"] --> diagonalProcedure["Algorithm capsule: inspect diagonal or grid"]
  diagonalProcedure --> constructedObject["Construction: diagonal or anti-diagonal object"]
  constructedObject --> differsFromEach["Assertion: constructed object differs from every listed object"]
  assumeListing --> contradiction["Contradiction: listing was supposed to be complete"]
  differsFromEach --> contradiction
  contradiction --> conclusion["Conclusion: original cardinality claim follows"]
```

## Cantor's Theorem: Power Set Has Greater Cardinality

Metadata:

- `id`: `cantor-power-set-theorem`
- `graph_kind`: `hybrid`
- `granularity`: `medium`
- `temporary_assumptions`: contradiction
- `algorithm_capsules`: diagonal subset construction
- `complexity`: 13 nodes, 16 edges, depth 6

Source note: Cantor's theorem: for every set `S`, there is no surjection from `S` onto its power set `P(S)`. Therefore `|P(S)| > |S|`.

```mermaid
flowchart TD
  target["Target: no function from S onto P(S) is surjective"] --> assumeSurjection["Assumption: f maps S onto P(S)"]
  assumeSurjection --> defineD["Construction: D equals set of x in S such that x is not in f(x)"]
  separation["Set comprehension for subset of S"] --> defineD
  defineD --> dSubset["Assertion: D is an element of P(S)"]
  assumeSurjection --> existsA["Assertion: since f is surjective, some a in S has f(a) equals D"]
  dSubset --> existsA
  defineD --> membershipQuestion{"Is a in D?"}
  existsA --> membershipQuestion
  membershipQuestion -->|"yes"| yesContradiction["If a is in D, then by definition a is not in f(a), so a is not in D"]
  membershipQuestion -->|"no"| noContradiction["If a is not in D, then by definition a is in f(a), so a is in D"]
  yesContradiction --> contradiction["Contradiction in both cases"]
  noContradiction --> contradiction
  contradiction --> discharge["Discharge assumption: f is not surjective"]
  discharge --> conclusion["Conclusion: P(S) has strictly greater cardinality than S"]
```

### Algorithm Capsule: Diagonal Subset

```mermaid
flowchart LR
  inputF["Input: function f from S to P(S)"] --> inspectX["For each x in S, inspect whether x is in f(x)"]
  inspectX --> flipMembership["Put x in D exactly when x is not in f(x)"]
  flipMembership --> outputD["Output: anti-diagonal subset D"]
```

## The Rationals Are Countable

Metadata:

- `id`: `rationals-are-countable`
- `graph_kind`: `hybrid`
- `granularity`: `medium`
- `temporary_assumptions`: none
- `algorithm_capsules`: diagonal grid enumeration
- `complexity`: 14 nodes, 16 edges, depth 6

Source note: a standard enumeration proof: list positive rational numbers by traversing the integer grid of numerator-denominator pairs diagonally, skip duplicates, include signs and zero, and obtain a countable enumeration of `Q`.

```mermaid
flowchart TD
  target["Target: Q is countable"] --> encodeRationals["Construction: represent rationals as integer pairs m,n with n nonzero"]
  defRational["Definition: rational equals m divided by n"] --> encodeRationals
  encodeRationals --> positiveGrid["Construction: positive rationals represented in N by N grid"]
  countableProduct["Fact: N by N is countable by diagonal traversal"] --> enumeratePositive["Assertion: positive rationals can be enumerated"]
  positiveGrid --> enumeratePositive
  enumeratePositive --> skipDuplicates["Inference: skip repeated fractions such as 1/2 and 2/4"]
  equalityFractions["Definition: fraction equality by cross multiplication"] --> skipDuplicates
  skipDuplicates --> positiveList["Assertion: positive rationals have a sequence listing"]
  zero["Construction: include 0"] --> combineSigns["Construction: interleave zero, positives, and negatives"]
  positiveList --> combineSigns
  signSymmetry["Fact: each positive rational has a negative counterpart"] --> combineSigns
  combineSigns --> surjectionNQ["Assertion: there is a surjection from N onto Q"]
  countableDef["Definition: countable means finite or enumerable by N"] --> conclusion["Conclusion: Q is countable"]
  surjectionNQ --> conclusion
```

### Algorithm Capsule: Diagonal Enumeration of Positive Rationals

```mermaid
flowchart LR
  start["Start with numerator plus denominator sum equal to 2"] --> listPairs["List pairs m,n with m+n equal current sum"]
  listPairs --> reduceCheck{"Has fraction m/n appeared before?"}
  reduceCheck -->|"yes"| skip["Skip duplicate"]
  reduceCheck -->|"no"| emit["Emit rational m/n"]
  skip --> nextPair{"More pairs at this sum?"}
  emit --> nextPair
  nextPair -->|"yes"| listPairs
  nextPair -->|"no"| nextSum["Increase sum by 1"]
  nextSum --> listPairs
```

## The Reals Are Uncountable

Metadata:

- `id`: `reals-are-uncountable-diagonal`
- `graph_kind`: `hybrid`
- `granularity`: `medium`
- `temporary_assumptions`: contradiction
- `algorithm_capsules`: anti-diagonal real construction
- `complexity`: 15 nodes, 18 edges, depth 7

Source note: Cantor's diagonal proof for real numbers in `(0,1)`: assume all real numbers in `(0,1)` are listed by decimal expansions, construct a new decimal number differing from the nth listed number in its nth digit, and conclude the list was incomplete. A technical note should avoid ambiguous decimal expansions ending in repeating 9s.

```mermaid
flowchart TD
  target["Target: reals in (0,1) are uncountable"] --> assumeList["Assumption: every real in (0,1) appears in a sequence r1, r2, r3, ..."]
  assumeList --> decimalRows["Construction: write each rn as a decimal row"]
  decimalConvention["Convention: choose decimal expansions not ending in repeating 9s"] --> decimalRows
  decimalRows --> diagonalDigits["Algorithm: read nth digit of rn"]
  diagonalDigits --> constructX["Construction: define x by changing each nth diagonal digit"]
  digitRule["Rule: choose a digit different from the diagonal digit and avoid 9"] --> constructX
  constructX --> xInInterval["Assertion: x is a real number in (0,1)"]
  constructX --> differsFromRn["Assertion: x differs from rn in the nth digit for every n"]
  decimalConvention --> differsFromRn
  differsFromRn --> notInList["Assertion: x is not equal to any listed rn"]
  assumeList --> contradiction["Contradiction: list was assumed complete, but x is missing"]
  notInList --> contradiction
  contradiction --> discharge["Discharge assumption: no sequence lists all reals in (0,1)"]
  discharge --> conclusion["Conclusion: reals are uncountable"]
```

### Algorithm Capsule: Anti-Diagonal Real

```mermaid
flowchart LR
  inputRows["Input: sequence of decimal rows r1, r2, r3, ..."] --> readDigit["Read nth digit of row n"]
  readDigit --> chooseDifferent["Choose output digit different from that digit"]
  chooseDifferent --> appendDigit["Append chosen digit to x"]
  appendDigit --> moreRows{"Continue to next row?"}
  moreRows -->|"yes"| readDigit
  moreRows -->|"indefinitely"| outputX["Output: real x determined by anti-diagonal digits"]
```

## Pattern Comparison

- Power set theorem: diagonalization is membership flipping against a function `S -> P(S)`.
- Rationals countable: diagonal traversal is an enumeration algorithm, not a contradiction.
- Reals uncountable: diagonalization is digit flipping against a proposed list.

The three examples are valuable together because they prevent a common mistake: not every diagonal structure proves uncountability. The rationals proof uses a diagonal path to enumerate; the power set and reals proofs use anti-diagonal construction to refute a proposed complete listing.

## Optional Extensions: Paradox and Metatheorem Family

These are natural later additions, but they should be scoped as a second pilot family because they introduce self-reference, syntax, and semantic truth.

- Russell's paradox: graph the set `R = {x | x notin x}` and the contradiction `R in R iff R notin R`.
- Liar paradox: graph semantic self-reference, truth predicate assumptions, and contradiction.
- Godel completeness theorem: graph syntactic consistency, models, and semantic entailment as a precursor to metatheorem diagrams.
- Godel incompleteness theorem: graph arithmetization, provability predicate, diagonal lemma, and the undecidable sentence.

For the current pilot, Cantor's theorem is the best bridge toward these later examples because it uses a diagonal object without requiring the machinery of formal syntax and provability.
