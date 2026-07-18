# Representation Methods Catalog

*Shared reference. Canonical source in GitHub; copies in each Project's knowledge
base. This is the concrete population of the engine's multimodal-communication
capability.*

---

## Purpose

This catalog exists to **prevent the hammer trap**. Its job is not to document
Mermaid — it is to force a choice *before* representing anything: which shape
does this information actually have, and which method renders that shape without
distorting it? Every entry states what a method renders well **and what it
distorts**, because the distortion is the part that gets forgotten.

**Rule of use:** match the *shape of the information* to the method, not the
method to habit. Sequential → timeline. Relational/network → graph. Molecular →
chemical notation. Symbolic → math notation. Numeric → data viz. Logical/process
→ flowchart. If nothing fits, mark the limit; do not force a flowchart.

**Status legend:** `populated` = in active use · `candidate` = identified, not
yet explored.

---

## #1 — Programming Framework (Mermaid Markdown)  ·  `populated`

- **Represents well:** logical and process structure — AND/OR/NOT gates,
  branches, feedback loops, dependency chains. The semantic layer is Boolean
  logic; Mermaid is the visualization/publication layer.
- **Distorts / omits:** anything not reducible to nodes-and-edges — quantitative
  magnitude, spatial/molecular geometry, continuous change, uncertainty. A
  flowchart makes everything look like discrete, well-typed logic even when the
  underlying reality isn't.
- **Reach for it when:** the information *is* a process or a logical circuit
  (gene-regulatory logic in GLMP; proof/algorithm dependency structure in the
  math initiative).
- **It is a point of view, not a dogma or theory.** Treat it as method #1, held
  open to challenge — not the frame all evidence must pass through.

---

## Candidate methods (from the Jan 2026 "text → visualization" survey)

### Mermaid's non-flowchart modes  ·  `candidate`
- **Represents well:** timelines and **Gantt charts** (temporal phases),
  state diagrams (state machines), entity-relationship diagrams (data schemas),
  class diagrams.
- **Distorts:** same node/edge discreteness as flowcharts; poor for magnitude
  or continuous data.
- **Reach for it when:** the information is temporal (bench-to-bedside phases)
  or a state/schema — before you reshape it into a process flow.

### GraphViz / DOT  ·  `candidate`
- **Represents well:** large, dense **network graphs** — citation networks,
  protein–protein interactions, concept maps, dependency webs too tangled for
  Mermaid's layout.
- **Distorts:** direction of *process*; a graph shows relation, not sequence.
- **Reach for it when:** the relationships are the point and there are too many
  to lay out by hand.

### Chemical structure notation (SMILES / MOL, via RDKit)  ·  `candidate`
- **Represents well:** molecular structure and reactions.
- **Distorts:** anything above the molecule — pathway logic, kinetics.
- **Reach for it when:** the object is a molecule, not a process.

### Direct SVG  ·  `candidate`
- **Represents well:** custom scientific diagrams with no standard grammar —
  spatial arrangements, bespoke schematics.
- **Distorts:** nothing inherently, but carries no semantics — it's a drawing,
  not a model, so it can't be validated the way a typed circuit can.
- **Reach for it when:** the picture is genuinely one-off and spatial.

### LaTeX / MathML  ·  `candidate`
- **Represents well:** equations and symbolic mathematics extracted from papers.
- **Distorts:** relationships between equations (that's a graph's job).
- **Reach for it when:** the content is symbolic notation, rendered faithfully.

### Quantitative data viz (matplotlib / D3.js)  ·  `candidate`
- **Represents well:** magnitude, distribution, trend — the numeric shapes every
  method above is bad at.
- **Distorts:** logical/causal structure; a chart shows *how much*, not *why*.
- **Reach for it when:** the information is numbers and you need to see their
  shape (e.g. the dense-retrieval nDCG comparisons).

---

*To promote a candidate to `populated`, add: a worked example, the tool/pipeline
used, and — per the honesty guardrail — the failure mode found in practice.*
