# Infinitely Many Primes

This example tests a short arithmetic proof with a temporary contradiction assumption and a constructed witness number.

## Euclid-Style Proof

Metadata:

- `id`: `infinitely-many-primes-euclid`
- `graph_kind`: `hybrid`
- `granularity`: `medium`
- `temporary_assumptions`: contradiction
- `algorithm_capsules`: product-plus-one construction
- `complexity`: 14 nodes, 17 edges, depth 6

Source note: the standard proof attributed to Euclid: assume finitely many primes `p1, ..., pn`; form `N = p1 p2 ... pn + 1`; then no listed prime divides `N`, so either `N` is prime or has a prime divisor not in the list.

```mermaid
flowchart TD
  theoremTarget["Target: there are infinitely many primes"] --> assumeFinite["Assumption: only finitely many primes p1 through pn"]
  assumeFinite --> listAll["Assertion: every prime is in the list"]
  assumeFinite --> constructN["Construction: N equals product p1 through pn plus 1"]
  constructN --> productDivisible["Assertion: each listed prime divides the product"]
  divisibilityDef["Definition: divisibility"] --> productDivisible
  constructN --> remainderOne["Assertion: N leaves remainder 1 when divided by each listed prime"]
  productDivisible --> remainderOne
  arithmetic["Arithmetic fact: if p divides product, p cannot divide product plus 1"] --> remainderOne
  remainderOne --> noListedPrime["Assertion: no listed prime divides N"]
  primeFactorLemma["Lemma: every integer greater than 1 is prime or has a prime divisor"] --> nPrimeOrDivisor["Assertion: N is prime or has a prime divisor q"]
  constructN --> nGreaterOne["Assertion: N is greater than 1"]
  nGreaterOne --> nPrimeOrDivisor
  nPrimeOrDivisor --> newPrime["Assertion: there exists a prime not in the list"]
  noListedPrime --> newPrime
  listAll --> contradiction["Contradiction: every prime is listed, but q is not listed"]
  newPrime --> contradiction
  contradiction --> discharge["Discharge assumption: finite-prime assumption is false"]
  discharge --> conclusion["Conclusion: infinitely many primes exist"]
```

## Algorithm Capsule: Product-Plus-One Witness

The construction of `N` is simple enough to remain a single node in most views, but it is procedural. This capsule can be shown on demand if the database supports expanding algorithm nodes.

```mermaid
flowchart LR
  inputList["Input: finite list p1 through pn"] --> initProduct["Set product equal to 1"]
  initProduct --> multiplyNext["Multiply product by next listed prime"]
  multiplyNext --> remaining{"More primes in list?"}
  remaining -->|"yes"| multiplyNext
  remaining -->|"no"| addOne["Set N equal to product plus 1"]
  addOne --> outputN["Output: witness N"]
```

## Structural Notes

This proof is best represented as a dependency graph with one optional algorithm capsule. The important logical structure is not the multiplication loop; it is the contradiction:

- finite list assumption;
- construction of a number tied to that list;
- divisibility argument excluding every listed prime;
- use of existence of prime divisors;
- discharge of the finite-list assumption.

The graph also demonstrates that a proof can be constructive inside a nonconstructive contradiction frame.
