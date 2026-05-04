# Fundamental Theorem of Arithmetic

This is the pilot's final, more complicated theorem. It tests whether proof graphs can show nested structure without becoming unreadable: existence, uniqueness, induction, Euclid's lemma, and a factorization procedure all appear in one theorem.

## Theorem

Every integer greater than 1 can be expressed as a product of primes, and this expression is unique up to the order of the factors.

Metadata:

- `id`: `fundamental-theorem-arithmetic`
- `graph_kind`: `hybrid`
- `granularity`: `medium`
- `temporary_assumptions`: induction and contradiction
- `algorithm_capsules`: recursive factorization search
- `complexity`: 27 nodes, 34 edges, depth 9

Source note: a standard elementary proof. Existence is proved by strong induction or descent. Uniqueness is proved using Euclid's lemma: if a prime divides a product, it divides one of the factors.

## Main Proof Graph

```mermaid
flowchart TD
  theorem["Target: every integer greater than 1 has a unique prime factorization"] --> split["Branch: prove existence and uniqueness"]

  subgraph existenceBranch [Existence Branch]
    nGreaterOne["Given: n greater than 1"] --> primeCase{"Is n prime?"}
    defPrime["Definition: prime number"] --> primeCase
    primeCase -->|"yes"| nItself["Assertion: n is a one-factor prime product"]
    primeCase -->|"no"| composite["Assertion: n is composite"]
    defComposite["Definition: composite number"] --> composite
    composite --> factorsAB["Construction: n equals a times b with 1 less than a,b less than n"]
    strongInduction["Strong induction hypothesis: smaller integers have prime factorizations"] --> factorA["Assertion: a has a prime factorization"]
    strongInduction --> factorB["Assertion: b has a prime factorization"]
    factorsAB --> factorA
    factorsAB --> factorB
    factorA --> combineFactors["Inference: combine prime factors of a and b"]
    factorB --> combineFactors
    combineFactors --> existenceConclusion["Conclusion: n has a prime factorization"]
    nItself --> existenceConclusion
  end

  subgraph uniquenessBranch [Uniqueness Branch]
    twoFacts["Assume: n has two prime factorizations"] --> equation["Assertion: p1...pk equals q1...qm"]
    equation --> p1DividesProduct["Assertion: p1 divides q1...qm"]
    euclidLemma["Euclid's lemma: prime dividing product divides some factor"] --> p1DividesSomeQ["Assertion: p1 divides qj for some j"]
    p1DividesProduct --> p1DividesSomeQ
    p1Prime["Definition: qj is prime"] --> p1EqualsQj["Assertion: p1 equals qj"]
    p1DividesSomeQ --> p1EqualsQj
    p1EqualsQj --> cancelEqualPrime["Inference: cancel matching prime factor"]
    cancellation["Cancellation law for integers"] --> cancelEqualPrime
    cancelEqualPrime --> reduceEquation["Assertion: remaining products are equal"]
    reduceEquation --> repeatArgument["Inference: repeat by induction on number of factors"]
    repeatArgument --> sameMultiset["Conclusion: the two lists contain the same primes up to order"]
  end

  split --> nGreaterOne
  split --> twoFacts
  existenceConclusion --> theoremConclusion["Conclusion: existence and uniqueness both hold"]
  sameMultiset --> theoremConclusion
```

## Algorithm Capsule: Recursive Factorization Search

This procedure is not the theorem itself, but it is naturally called by the constructive part of the existence proof.

```mermaid
flowchart LR
  inputN["Input: integer n greater than 1"] --> testPrime{"Is n prime?"}
  testPrime -->|"yes"| outputN["Output: list containing n"]
  testPrime -->|"no"| findDivisor["Find divisor d with 1 less than d less than n"]
  findDivisor --> quotient["Set e equal to n divided by d"]
  quotient --> recurseD["Factor d recursively"]
  quotient --> recurseE["Factor e recursively"]
  recurseD --> concatenate["Concatenate the two factor lists"]
  recurseE --> concatenate
  concatenate --> outputFactors["Output: prime factor list for n"]
```

## Dependency Capsule: Euclid's Lemma

The uniqueness branch depends heavily on Euclid's lemma. If the database later supports expandable lemma nodes, this proof should be expandable.

```mermaid
flowchart TD
  primeP["Given: p is prime"] --> dividesAB["Given: p divides a times b"]
  notDividesA["Assume: p does not divide a"] --> coprimePA["Assertion: gcd of p and a equals 1"]
  primeP --> coprimePA
  bezout["Bezout identity or Euclidean lemma precursor"] --> linearCombo["Assertion: xp plus ya equals 1"]
  coprimePA --> linearCombo
  linearCombo --> multiplyByB["Inference: multiply equation by b"]
  dividesAB --> pDividesYAB["Assertion: p divides y times a times b"]
  multiplyByB --> pDividesB["Assertion: p divides b"]
  pDividesYAB --> pDividesB
  pDividesB --> lemmaConclusion["Conclusion: p divides a or p divides b"]
```

## Structural Notes

The theorem should remain a hybrid graph. The proof dependencies are the main object, but the existence branch naturally invokes a procedure that can be displayed as a flowchart. The uniqueness branch should not be flowcharted; it is a logical dependency chain governed by Euclid's lemma and induction on factor lists.

This example also suggests a future database feature: expandable dependency nodes. `Euclid's lemma`, `strong induction`, and `cancellation law` can be leaf nodes in the top-level graph, but each can also open into its own proof graph.
