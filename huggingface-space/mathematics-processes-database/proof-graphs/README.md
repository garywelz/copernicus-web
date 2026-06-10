# Proof Graph Pilot

This directory contains the pilot package for adding proof-level graphs to the Mathematics Database.

Start with:

- `schema.md` for graph vocabulary and metadata conventions.
- `proof-graph-schema-v2.md` for the revised visual grammar, proof-specific palette, edge styles, joins, and loop policy.
- `design-notes.md` for the conceptual framing of proofs as hybrid derivational graphs.
- `pilot-summary.md` for scope, selected proofs, and database integration recommendations.

Proof graph drafts:

- `euclid-book-i-pilot.md`
- `infinitely-many-primes.md`
- `pythagorean-comparison.md`
- `fundamental-theorem-arithmetic.md`
- `cantor-diagonal-proofs.md`

The pilot's main recommendation is to attach proof graphs as drill-down views on theorem entries and list them as a distinct proof-level category inside the mathematics database. This keeps theorem-level dependency graphs and proof-level internal dependency graphs distinct while allowing multiple proofs of the same theorem.

The Cantor extension adds a second proof family around diagonal structures: Cantor's theorem for power sets, countability of the rationals by diagonal enumeration, and uncountability of the reals by anti-diagonal construction. It also sketches later candidates involving Russell's paradox, the liar paradox, and Godel's completeness and incompleteness theorems.
