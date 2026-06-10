# Infinitely Many Primes — Proof Graph v2 Demo

This page is a design demonstration of the revised proof graph grammar. It uses the same mathematical proof as the original infinitely-many-primes page, but applies distinct node shapes and edge styles:

- rounded nodes for assumptions;
- parallelogram nodes for constructions;
- a diamond for a proof branch;
- a compact hexagonal AND join marker for multi-premise support;
- a capsule for the invoked algorithm;
- dashed edges for algorithm invocation and returned objects;
- heavy conclusion/contradiction coloring from the proof-specific palette.

The goal is not to replace the original proof yet. The goal is to make the proposed v2 design concrete enough to judge visually.

## V2 Proof-Level Graph

```mermaid
flowchart TD
  target["Target: prove there are infinitely many primes"]
  assumeFinite("Assumption: only finitely many primes p1 through pn")
  listAll["Assertion: every prime is in the list"]
  algorithm(["Algorithm capsule: product-plus-one witness"])
  constructN[/"Construction: N equals product p1 through pn plus 1"/]
  nGreaterOne["Assertion: N is greater than 1"]
  primeFactorLemma(["Lemma: every integer greater than 1 is prime or has a prime divisor"])
  branchPrime{"Branch: N is prime or has prime divisor q?"}
  newPrime["Assertion: there exists a prime not in the list"]
  productDivisible["Assertion: each listed prime divides the product"]
  divisibilityDef(["Definition: divisibility"])
  arithmetic(["Arithmetic fact: if p divides product, p cannot divide product plus 1"])
  remainderOne["Assertion: N leaves remainder 1 when divided by each listed prime"]
  noListedPrime["Assertion: no listed prime divides N"]
  joinNewPrime{{"AND"}}
  contradiction["Contradiction: every prime is listed, but q is not listed"]
  discharge["Discharge assumption: finite-prime assumption is false"]
  conclusion["Conclusion: infinitely many primes exist"]

  target --> assumeFinite
  assumeFinite --> listAll
  assumeFinite -. "invokes_algorithm" .-> algorithm
  algorithm -. "returns_object" .-> constructN
  constructN --> nGreaterOne
  nGreaterOne --> branchPrime
  primeFactorLemma --> branchPrime
  branchPrime -->|"N is prime"| newPrime
  branchPrime -->|"prime divisor q"| newPrime
  constructN --> productDivisible
  divisibilityDef --> productDivisible
  productDivisible --> remainderOne
  arithmetic --> remainderOne
  constructN --> remainderOne
  remainderOne --> noListedPrime
  noListedPrime --> joinNewPrime
  newPrime --> joinNewPrime
  joinNewPrime --> contradiction
  listAll --> contradiction
  contradiction -. "discharges" .-> discharge
  discharge ==> conclusion
```

## Nested Algorithm Capsule

```mermaid
flowchart LR
  inputList(["Input: finite list p1 through pn"])
  initProduct["Set product equal to 1"]
  multiplyNext["Multiply product by next listed prime"]
  remaining{"More primes in list?"}
  addOne[/"Construction: set N equal to product plus 1"/]
  outputN(["Output: witness N"])

  inputList --> initProduct
  initProduct --> multiplyNext
  multiplyNext --> remaining
  remaining -->|"yes"| multiplyNext
  remaining -->|"no"| addOne
  addOne --> outputN
```

## Notes

The top graph remains a proof dependency graph: it shows how the contradiction is licensed. The compact AND marker indicates that the constructed witness and the no-listed-divisor claim jointly support the contradiction step. The nested capsule is an algorithm graph: it shows how the witness `N` is computed from a finite list. This keeps proof-level justification and procedural execution visually related but not identical.
