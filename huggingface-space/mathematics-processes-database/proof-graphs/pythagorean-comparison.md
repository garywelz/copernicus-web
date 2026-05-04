# Pythagorean Theorem Proof Graph Comparison

This pilot includes two proofs of the same theorem to test whether proof graphs reveal structural differences that are hidden by the final theorem statement.

## Shared Theorem

For a right triangle with legs `a` and `b` and hypotenuse `c`, the square on the hypotenuse has area equal to the sum of the areas of the squares on the legs: `a^2 + b^2 = c^2`.

## Proof A: Euclid Book I, Proposition 47

Metadata:

- `id`: `pythagorean-euclid-i-47`
- `graph_kind`: `dependency`
- `granularity`: `coarse-to-medium`
- `temporary_assumptions`: none
- `algorithm_capsules`: none
- `complexity`: 18 nodes, 22 edges, depth 8

Source note: Euclid Book I, Proposition 47, paraphrased at dependency level. The graph emphasizes the theorem dependencies and area-equality transfers rather than every diagram line in Euclid's construction.

```mermaid
flowchart TD
  rightTriangle["Given: right triangle ABC with right angle at A"] --> constructSquares["Construction: squares on AB, AC, and BC"]
  prop46["Euclid I.46: construct a square on a given straight line"] --> constructSquares
  constructSquares --> drawAuxiliary["Construction: draw auxiliary lines through A and to square vertices"]
  post1["Postulate 1: draw straight line between points"] --> drawAuxiliary
  rightTriangle --> angleRelations["Assertion: required angles are equal or supplementary"]
  constructSquares --> angleRelations
  common2["Common notions: add equals to equals"] --> angleRelations
  angleRelations --> triangleCongruenceLeft["Inference: triangle on leg AB congruent to triangle linked to rectangle under hypotenuse"]
  prop4["Euclid I.4: SAS congruence"] --> triangleCongruenceLeft
  constructSquares --> triangleCongruenceLeft
  angleRelations --> triangleCongruenceRight["Inference: triangle on leg AC congruent to triangle linked to other rectangle under hypotenuse"]
  prop4 --> triangleCongruenceRight
  constructSquares --> triangleCongruenceRight
  triangleCongruenceLeft --> areaLeft["Assertion: square on AB equals corresponding rectangle in square on BC"]
  prop41["Euclid I.41: triangle is half parallelogram on same base and parallels"] --> areaLeft
  triangleCongruenceRight --> areaRight["Assertion: square on AC equals corresponding rectangle in square on BC"]
  prop41 --> areaRight
  areaLeft --> sumAreas["Assertion: sum of leg-square areas equals sum of two hypotenuse rectangles"]
  areaRight --> sumAreas
  constructSquares --> hypSquarePartition["Assertion: two rectangles partition square on BC"]
  hypSquarePartition --> sumAreas
  commonWhole["Common notion: whole equals sum of its parts"] --> conclusion["Conclusion: square on BC equals squares on AB and AC"]
  sumAreas --> conclusion
```

Design note: this graph is dependency-heavy. Its value is that it shows the Pythagorean theorem as the endpoint of a chain of earlier Euclidean construction, congruence, parallel, and area propositions.

## Proof B: Rearrangement Area Proof

Metadata:

- `id`: `pythagorean-area-rearrangement`
- `graph_kind`: `hybrid`
- `granularity`: `medium`
- `temporary_assumptions`: none
- `algorithm_capsules`: geometric rearrangement routine
- `complexity`: 15 nodes, 17 edges, depth 6

Source note: a standard dissection proof using four congruent right triangles arranged inside a square of side `a + b`. Two arrangements leave different central regions whose equal total areas imply `a^2 + b^2 = c^2`.

```mermaid
flowchart TD
  rightTriangle["Given: right triangle with legs a and b, hypotenuse c"] --> fourCopies["Construction: four congruent copies of the triangle"]
  congruence["Definition: congruent figures have equal area"] --> fourCopies
  fourCopies --> outerSquare["Construction: arrange copies in square of side a plus b"]
  areaSquare["Area formula: square side s has area s squared"] --> outerArea["Assertion: outer square area is (a plus b)^2"]
  outerSquare --> outerArea
  fourCopies --> arrangementOne["Construction: arrangement leaves central square of side c"]
  arrangementOne --> centralC["Assertion: remaining central area is c squared"]
  areaSquare --> centralC
  fourCopies --> arrangementTwo["Construction: rearrangement leaves two squares of sides a and b"]
  arrangementTwo --> centralAB["Assertion: remaining central area is a squared plus b squared"]
  areaSquare --> centralAB
  samePieces["Principle: rearranging same pieces preserves total area"] --> equalRemainders["Assertion: the two remaining central areas are equal"]
  outerArea --> equalRemainders
  fourCopies --> equalRemainders
  centralC --> equalRemainders
  centralAB --> equalRemainders
  equalRemainders --> conclusion["Conclusion: c squared equals a squared plus b squared"]
```

## Algorithm Capsule: Rearrangement Procedure

```mermaid
flowchart LR
  inputTriangle["Input: right triangle a, b, c"] --> makeCopies["Make four congruent copies"]
  makeCopies --> arrangeC["Arrange with hypotenuses forming central c-square"]
  arrangeC --> recordC["Record leftover area c squared"]
  makeCopies --> arrangeAB["Rearrange with legs forming a-square and b-square"]
  arrangeAB --> recordAB["Record leftover area a squared plus b squared"]
  recordC --> compare["Compare equal outer area minus same four triangles"]
  recordAB --> compare
  compare --> output["Output: a squared plus b squared equals c squared"]
```

## Structural Comparison

- Euclid I.47 is dependency-rich: the graph points backward into the Euclidean proposition network.
- The rearrangement proof is invariant-rich: the graph centers on conservation of area under rearrangement.
- Euclid I.47 has more theorem dependencies; the rearrangement proof has a clearer algorithmic capsule.
- Both prove the same conclusion, but their graph signatures are different enough to justify storing proof graphs separately from theorem nodes.

## Optional Third Graph

A similar-triangles proof should be considered for a later pass. It would use altitude to the hypotenuse, triangle similarity, proportionality, and algebraic combination. It is an excellent third comparison because it is neither a Euclidean square-area proof nor a pure rearrangement proof.
