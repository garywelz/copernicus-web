# Euclid Book I Pilot Proof Graphs

These examples test whether proof graphs can represent early Euclidean reasoning without collapsing construction, assertion, and prior theorem dependency into a single undifferentiated arrow.

## Euclid I.1: Equilateral Triangle on a Given Segment

Metadata:

- `id`: `euclid-i-1-equilateral-triangle`
- `graph_kind`: `hybrid`, mostly dependency with construction steps
- `granularity`: `medium`
- `temporary_assumptions`: none
- `algorithm_capsules`: compass-and-straightedge construction pattern
- `complexity`: 12 nodes, 14 edges, depth 5

Source note: Euclid Book I, Proposition 1, in the usual Heath-style paraphrase: on a given finite straight line, construct an equilateral triangle.

```mermaid
flowchart TD
  givenAB["Given: finite straight line AB"] --> centerA["Construction: circle with center A through B"]
  givenAB --> centerB["Construction: circle with center B through A"]
  post3["Postulate 3: describe circle with any center and distance"] --> centerA
  post3 --> centerB
  centerA --> intersectionC["Construction: intersection point C of the two circles"]
  centerB --> intersectionC
  defCircle["Definition of circle: radii from center are equal"] --> acEqualsAB["Assertion: AC equals AB"]
  defCircle --> bcEqualsAB["Assertion: BC equals AB"]
  centerA --> acEqualsAB
  centerB --> bcEqualsAB
  common1["Common Notion 1: things equal to same thing are equal"] --> acEqualsBC["Assertion: AC equals BC"]
  acEqualsAB --> acEqualsBC
  bcEqualsAB --> acEqualsBC
  acEqualsAB --> allSidesEqual["Assertion: AB, BC, CA are equal"]
  bcEqualsAB --> allSidesEqual
  acEqualsBC --> allSidesEqual
  defEquilateral["Definition: equilateral triangle has three equal sides"] --> conclusion["Conclusion: triangle ABC is equilateral"]
  allSidesEqual --> conclusion
```

Design note: the graph is useful because it distinguishes the construction of point `C` from the equality claims that use the definition of a circle.

## Euclid I.4: Side-Angle-Side Congruence

Metadata:

- `id`: `euclid-i-4-sas-congruence`
- `graph_kind`: `dependency`
- `granularity`: `medium`
- `temporary_assumptions`: none, but contains a methodological caveat
- `algorithm_capsules`: none
- `complexity`: 13 nodes, 15 edges, depth 5

Source note: Euclid Book I, Proposition 4: if two triangles have two sides respectively equal and the included angles equal, their bases, remaining angles, and whole triangles are equal. The classical proof uses superposition; modern treatments often replace or formalize this with a congruence axiom.

```mermaid
flowchart TD
  givenABDE["Given: AB equals DE"] --> superposeA["Inference: place point A on D"]
  givenACEF["Given: AC equals EF"] --> superposeA
  givenAngle["Given: angle BAC equals angle EDF"] --> alignRays["Inference: align rays AB with DE and AC with EF"]
  superposition["Methodological assumption: rigid superposition preserves equality"] --> superposeA
  superposition --> alignRays
  superposeA --> alignRays
  alignRays --> pointBOnE["Assertion: B coincides with E"]
  alignRays --> pointCOnF["Assertion: C coincides with F"]
  givenABDE --> pointBOnE
  givenACEF --> pointCOnF
  pointBOnE --> baseCoincides["Assertion: base BC coincides with EF"]
  pointCOnF --> baseCoincides
  common4["Common Notion 4: things coinciding are equal"] --> baseEqual["Assertion: BC equals EF"]
  baseCoincides --> baseEqual
  common4 --> remainingAngles["Assertion: remaining angles are equal"]
  pointBOnE --> remainingAngles
  pointCOnF --> remainingAngles
  baseEqual --> conclusion["Conclusion: triangles ABC and DEF are congruent in SAS sense"]
  remainingAngles --> conclusion
```

Design note: this is a stress test for historical proof representation. The graph should not pretend the superposition move is an ordinary postulate from Euclid's explicit list. It should be a visible methodological assumption or replaced by a modern congruence axiom in a variant graph.

## Euclid I.5: Base Angles of an Isosceles Triangle

Metadata:

- `id`: `euclid-i-5-base-angles-isosceles`
- `graph_kind`: `dependency`
- `granularity`: `medium`
- `temporary_assumptions`: none
- `algorithm_capsules`: none
- `complexity`: 16 nodes, 19 edges, depth 7

Source note: Euclid Book I, Proposition 5: in isosceles triangles, the angles at the base are equal, and if the equal sides are produced, the angles under the base are equal. This pilot graph focuses on the main base-angle conclusion.

```mermaid
flowchart TD
  givenABAC["Given: AB equals AC"] --> extendSides["Construction: extend AB and AC beyond B and C"]
  post2["Postulate 2: produce finite straight line continuously"] --> extendSides
  extendSides --> chooseD["Construction: choose point D on extension of AB"]
  chooseD --> cutAE["Construction: cut off AE equal to AD on extension of AC"]
  prop3["Euclid I.3: cut off from greater line a line equal to lesser"] --> cutAE
  cutAE --> adEqualsAE["Assertion: AD equals AE"]
  givenABAC --> compareTriangles["Inference: compare triangles ACD and ABE"]
  adEqualsAE --> compareTriangles
  common3["Common Notion 3: subtract equals from equals"] --> bdEqualsCE["Assertion: BD equals CE"]
  givenABAC --> bdEqualsCE
  adEqualsAE --> bdEqualsCE
  givenABAC --> sasOuter["Euclid I.4: triangles ACD and ABE congruent"]
  adEqualsAE --> sasOuter
  angleACommon["Assertion: angle CAD equals angle BAE"]
  compareTriangles --> angleACommon
  angleACommon --> sasOuter
  sasOuter --> angleACDEqualsABE["Assertion: angle ACD equals ABE"]
  sasOuter --> angleADCEqualsAEB["Assertion: angle ADC equals AEB"]
  bdEqualsCE --> sasInner["Euclid I.4: triangles BCD and CBE congruent"]
  angleACDEqualsABE --> sasInner
  angleADCEqualsAEB --> sasInner
  sasInner --> baseAnglesEqual["Assertion: angle ABC equals angle BCA"]
  baseAnglesEqual --> conclusion["Conclusion: base angles of isosceles triangle ABC are equal"]
```

Design note: Proposition I.5 shows theorem reuse. Its graph depends on I.3 for the auxiliary construction and I.4 for congruence, so the proof-level graph also functions as a local theorem dependency graph.
