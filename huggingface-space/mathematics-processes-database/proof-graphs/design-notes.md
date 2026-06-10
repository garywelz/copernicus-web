# Proof Graph Design Notes

These notes record the design distinction that emerged from the Proof Graph Pilot: proofs are not just another instance of an algorithm or an axiomatic theory. They are **derivational hybrids**. A proof lives inside an axiomatic setting, but it often invokes constructions, procedures, case splits, diagonal scans, induction, recursion, or other algorithm-like substructures.

## Three Graph Families

- **Algorithms** are operational graphs. They answer: "What action happens next, and what branch or loop controls execution?"
- **Axiomatic theories** are structural dependency graphs. They answer: "Which primitives, axioms, definitions, and prior theorems support the theory?"
- **Proofs** are derivational graphs. They answer: "How is this conclusion licensed from sources, assumptions, constructions, inference moves, and sometimes procedures?"

This makes proof graphs a third category with a hybrid character, rather than a simple extension of the first two.

## Design Problem

The first pilot graphs intentionally used plain Mermaid `flowchart` syntax with rectangular nodes and colored roles. That made the pages easy to build, but it flattened several important distinctions:

- one-to-one sequential derivation looked similar to multi-premise dependence;
- ordinary assertion nodes looked similar to branch/case nodes;
- algorithm capsules inside proofs looked similar to logical proof steps;
- induction, recursion, and diagonalization were visually close to ordinary dependencies;
- all edges looked alike, even when they meant `depends_on`, `constructs`, `invokes_algorithm`, or `discharges`.

The next design pass should make those distinctions visible without turning proof graphs into unreadable formal proof trees.

## Visual Grammar

Recommended node shapes:

- **Rounded rectangle:** source, given, axiom, definition, lemma, prior theorem.
- **Rectangle:** assertion established inside the proof.
- **Parallelogram or clipped rectangle:** construction or introduced object.
- **Diamond:** case split, branch, membership question, or proof fork.
- **Stadium / capsule:** algorithm or procedure invoked by the proof.
- **Heavy bordered rectangle:** discharged assumption or final conclusion.
- **Red bordered node:** contradiction or impossible branch.
- **Small join node:** explicit multi-premise conjunction where several incoming dependencies jointly license one inference.

Recommended edge styles:

- **Solid arrow:** ordinary dependency or derivation.
- **Labeled solid arrow:** instantiation, construction, branch, or derives.
- **Dashed arrow:** invokes an algorithm or procedural capsule.
- **Dotted arrow:** discharges a temporary assumption.
- **Thicker arrow:** decisive inference into a conclusion or contradiction.

## Multi-Premise Nodes

In algorithm flowcharts, multiple incoming arrows often mean control flow can arrive from more than one previous state. In proof graphs, multiple incoming arrows usually mean something stronger: all incoming premises may be jointly required.

Future proof graphs should distinguish:

- **alternative support:** any one incoming route is sufficient;
- **joint support:** all incoming premises are needed;
- **case exhaustion:** all branches together close a proof;
- **dependency reuse:** a prior theorem supports multiple later claims.

This suggests adding explicit AND-join markers in proof graphs, but not necessarily using the same AND gate visual language as algorithm flowcharts. In proofs, a join means joint justification, not simultaneous computation.

## Loops And Recursion

Ordinary mathematical proofs should usually remain acyclic at the visible dependency level. Apparent loops need interpretation:

- **Induction** is a controlled schema: base case plus step case licenses all cases.
- **Recursion** is an algorithmic procedure invoked by a proof, not usually a logical cycle in the proof itself.
- **Diagonalization** is a construction that reads a presumed total list and produces an object outside it.
- **Self-reference** is a special logical pattern, not an ordinary control-flow loop.
- **Theorem reuse** is not a cycle if the reused theorem was already established.

The pilot should therefore avoid representing proof loops as simple Mermaid feedback arrows unless the loop is explicitly an algorithm capsule. For proof-level loops, use named schema nodes such as `Induction schema`, `Recursive subroutine`, or `Diagonal construction`.

## Algorithm Capsules Inside Proofs

Algorithm capsules should be expandable subgraphs. At the top proof level, a procedural step should appear as a single capsule node, connected by a dashed `invokes_algorithm` edge. The capsule itself may then open into a left-to-right algorithm flowchart with decisions, loops, and outputs.

This preserves the distinction:

- the proof dependency graph shows why the procedure matters;
- the algorithm capsule shows how the procedure operates.

## Distinct Proof Color Palette

Proof graphs should not reuse the GLMP/programming-framework five-color palette. That palette describes process roles such as triggers, structures, operations, intermediates, and outputs. Proof graphs need an argument-role palette.

The proof palette should be muted and document-like, with colors chosen for proof roles:

- **Parchment:** source / given / axiom / definition / lemma.
- **Mauve:** assumption or temporary hypothesis.
- **Sage:** construction or introduced object.
- **Blue-gray:** assertion established in the proof.
- **Peach:** inference, branch, or proof move.
- **Indigo:** algorithm or procedural capsule.
- **Oxblood:** contradiction.
- **Sea-teal:** discharge or final conclusion.

Each rendered proof page should carry its own proof color legend. The mathematics database landing page should not show a global color legend, because algorithms, axiomatic theories, GLMP circuits, and proof graphs have different visual grammars.

## Relationship To The Foundational Typology

This design adds a new theoretical dimension but does not require an immediate edit to the GLMP foundational paper. The likely future claim is:

> Algorithms, axiomatic theories, and proofs are related but distinct graph families: operational, structural, and derivational. Proofs are hybrid derivational objects that instantiate axiomatic dependencies while sometimes invoking algorithmic procedures.

That claim connects naturally to Curry-Howard, reverse mathematics, proof assistants, and the broader question of how primitive relations determine logical and computational character.
