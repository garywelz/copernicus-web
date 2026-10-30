# Mathematics manuscript collection

**721 manuscripts covering 373 result families.**

[**Read the overview PDF**](overview.pdf).

## Manuscript map

Each result description is followed by its constituent manuscripts and their abstracts. Paper titles link directly to PDFs.

<table>
<thead><tr><th>Result</th></tr></thead>
<table>
<thead><tr><th>Result</th></tr></thead>
<tbody><tr>
<td>

**003. The quasi-Riemann hypothesis.** Proves that every Dirichlet <i>L</i>-function, including $`\zeta(s)`$, is zero-free in $`\Re s\gt 7/8`$, resolving the quasi-Riemann hypothesis. The same half-plane is zero-free for every finite-order Hecke <i>L</i>-function over $`\mathbb Q(\sqrt{-3})`$. A companion gives a different proof of the zero-free half-plane $`\Re s\gt 11/12`$. ([Lean](lean/docs/003.md))

</td>
</tr></tbody>
<tbody><tr>
<td>

&emsp;[The Quasi-Riemann Hypothesis: A Zero-Free Half-Plane $`\Re s\gt 7/8`$ ](preprints/The-Quasi-Riemann-Hypothesis-September-30-2026/paper.pdf)

We prove that all finite-order Hecke <i>L</i>-functions over $`\mathbb Q(\sqrt{-3})`$ and all Dirichlet <i>L</i>-functions are zero-free in the half-plane $`\Re s\gt 7/8`$, with the principal pole at <i>s</i> = 1 allowed. In particular, the Riemann zeta function is zero-free in this half-plane, proving the quasi-Riemann hypothesis.

</td>
</tr></tbody>
<tbody><tr>
<td>

&emsp;[The Quasi-Riemann Hypothesis (alternate 11/12 proof)](preprints/The-Quasi-Riemann-Hypothesis-October-5-2026/paper2.pdf)

We establish the quasi-Riemann hypothesis by proving that every Dirichlet <i>L</i>-function, including Riemann's zeta function, has no zeros in the half-plane $`\mathop{\mathrm{Re}}\nolimits s\gt 11/12`$. More generally, we prove the same zero-free half-plane for every finite-order Hecke <i>L</i>-function over $`K=\mathbb Q(\sqrt{-3})`$. In particular, this rules out the existence of Landau–Siegel zeros.

</td>
</tr></tbody>
<tbody><tr>
<td>

&emsp;[Uniform exclusion of Landau–Siegel zeros](preprints/Uniform-exclusion-of-Landau-Siegel-zeros-October-1-2026/paper.pdf)

We prove the uniform exclusion of Landau–Siegel zeros. There is an absolute constant <i>c</i> &gt; 0 such that every real zero $`\beta\in(0,1)`$ of every primitive nonprincipal real Dirichlet <i>L</i>-function of conductor <i>q</i> ≥ 3 satisfies $`(1-\beta)\log q\ge c`$.

</td>
</tr></tbody>
<tbody><tr>
<td>

**157. Graph coloring, clique minors, and Colin de Verdière invariants.** Disproves Hadwiger's conjecture even for fractional coloring: arbitrarily large finite simple graphs with independence number at most two satisfy $`\chi_f(G)\gt h(G)`$, where $`h(G)`$ is the largest clique-minor order. Also disproves the fractional Colin de Verdière chromatic bound $`\chi_f(G)\le\mu(G)+1`$. In the positive direction, every finite nonempty graph satisfies $`\chi_{\mathrm{list}}(G)\le C h(G)`$ for a universal constant <i>C</i>. ([Lean](lean/docs/157.md))

</td>
</tr></tbody>
<tbody><tr>
<td>

&emsp;[A counterexample to Hadwiger's conjecture](preprints/A-counterexample-to-Hadwigers-conjecture-September-23-2026/paper.pdf)

We disprove Hadwiger's conjecture by constructing arbitrarily large graphs whose chromatic number exceeds their Hadwiger number. The examples have independence number at most two, and even their ordinary fractional chromatic number exceeds their Hadwiger number. Thus they also disprove the fractional-coloring weakening discussed by Reed and Seymour.

</td>
</tr></tbody>
<tbody><tr>
<td>

&emsp;[A counterexample to the Colin de Verdière chromatic conjecture](preprints/A-counterexample-to-the-Colin-de-Verdiere-chromatic-conjecture-September-23-2026/paper.pdf)

We disprove the Colin de Verdière chromatic conjecture by constructing graphs whose chromatic number exceeds their Colin de Verdière invariant by more than one. The examples have independence number at most two. In fact, their ordinary fractional chromatic number also exceeds their Colin de Verdière invariant by more than one.

</td>
</tr></tbody>
<tbody><tr>
<td>

&emsp;[A linear list-coloring bound in terms of the Hadwiger number](preprints/A-linear-list-coloring-bound-in-terms-of-the-Hadwiger-number-September-23-2026/paper.pdf)

We prove that every finite nonempty graph <i>G</i> satisfies $`\chi_{\mathrm{list}}(G)\le C h(G)`$ for an absolute integer <i>C</i>, where $`h(G)`$ is the largest order of a clique minor. This resolves the Linear List Hadwiger conjecture affirmatively.

</td>
</tr></tbody>
<tbody><tr>
<td>

**378. Disproof of the Exponential Time Hypothesis.** For every fixed $`k\ge2`$, a deterministic algorithm counts the satisfying assignments of a $`k`$-CNF with $`n`$ variables and $`m`$ clauses in time $`(n+m)^{O_k(1)}2^{n/(\log n)^{1/2+o(1)}}`$. This yields superlinear circuit lower bounds for a language in $`\mathsf{E}^{\mathsf{NP}}`$ on infinitely many input lengths. ([Lean](lean/docs/378.md))

</td>
</tr></tbody>
<tbody><tr>
<td>

&emsp;[The Exponential Time Hypothesis is False](preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/paper.pdf)

We give a deterministic algorithm for exactly counting the satisfying assignments of an arbitrary $`k`$-CNF formula. For every fixed $`k\ge2`$, on a formula with $`n`$ variables and $`m`$ clauses, our algorithm uses space polynomial in $`n`$ and $`m`$ and runs in time $`(n+m)^{O_k(1)}2^{n/(\log n)^{1/2+o(1)}}`$. Our algorithm refutes the Exponential Time Hypothesis (ETH), which postulates that deciding 3-SAT on $`n`$ variables requires $`2^{\Omega(n)}`$ time in the worst case.

</td>
</tr></tbody>
</table>
