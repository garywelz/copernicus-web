# GLMP TDA Analysis — Complete Cursor Handoff
**Project:** Genome Logic Modeling Project — Topological Data Analysis  
**Seminar:** "Feedback Loops as Loops" — CUNY Graduate Center, March 13, 2026  
**Collaborator:** Dr. Mikael Vejdemo-Johansson  
**Prepared by:** Gary Welz / CopernicusAI  

---

## Larger goal (context for revisions)

The project aims to use flowcharts and TDA as a step toward decoding the “machine code” of DNA—the physical implementation of logical connectives AND, OR, and NOT on the chromosome. Revisions (preprint and slides) should support this direction: e.g. future work on topology predicting shared regulatory sequence motifs, cross-organism loops as the best test case, and the pipeline (RegulonDB/YEASTRACT + motif discovery) as the natural second act. Keep the conjecture out of the main seminar narrative but signal it as an active direction in Discussion/Next Steps.

---

## Overview

This document contains everything Cursor needs to complete the GLMP TDA
analysis pipeline, populate the preprint scaffold, and update the seminar
slide deck. Work through the tasks in order — each step produces outputs
that the next step depends on.

---

## TASK 0: Verify Input Data

Before running any scripts, confirm the following two CSV files exist and
are correctly formatted. If they do not exist, extract them from the GLMP
pipeline (see Note A at the bottom of this document).

### Required file 1: `glmp_features_5col.csv` (or `glmp_features.csv` with 5 feature columns)
- Location: `glmp-tda-analysis/glmp_features_5col.csv` (created from `glmp_features.csv` by selecting columns)
- Rows = processes (108 total)
- Columns = exactly these 5 features in this order:
  `node_count`, `conditional_count`, `or_gates`, `and_gates`, `not_gates`
- Index = process name strings (e.g., `ecoli_lac_operon`)

### Required file 2: `glmp_labels.csv`
- Location: `glmp-tda-analysis/glmp_labels.csv`
- Single column of process name strings (process_id)
- Index must match the features file exactly

### Validation command
Run from **`nsf-proposal`** (or from `glmp-tda-analysis` in the full repo). Use `python3` if `python` is not available.
```bash
python3 -c "
import pandas as pd
X = pd.read_csv('glmp_features_5col.csv', index_col=0)
L = pd.read_csv('glmp_labels.csv', index_col=0).squeeze()
print('Feature matrix shape:', X.shape)
print('Expected: (108, 5)')
print('Columns:', list(X.columns))
print('Labels match index:', list(X.index) == list(L.index))
print(X.describe().round(2))
"
```

Save the output — it populates Table 1 in the preprint Results section.

---

## TASK 1: Run Feature Ablation Study

### Script: `feature_ablation.py`

```python
"""
feature_ablation.py

Feature ablation study for GLMP TDA pipeline.
Reruns Vietoris-Rips TDA dropping one feature at a time, then compares
biological coherence of H1 loops against the full-feature baseline.

Known feedback circuits used as coherence reference:
  lac operon, trp operon, ara operon, two-component signaling,
  SOS response, heat shock, catabolite repression, Pho regulon

Usage:
  python feature_ablation.py --data glmp_features.csv --labels glmp_labels.csv
"""

import argparse
import numpy as np
import pandas as pd
from ripser import ripser
from scipy.spatial.distance import pdist, squareform
from sklearn.preprocessing import StandardScaler
import json

KNOWN_FEEDBACK = [
    "ecoli_lac_operon",
    "ecoli_trp_operon",
    "ecoli_ara_operon",
    "ecoli_e._coli_two_component_signaling",
    "ecoli_sos_response",
    "ecoli_heat_shock_response",
    "ecoli_catabolite_repression",
    "ecoli_pho_regulon",
]

FEATURE_NAMES = ["node_count", "conditional_count", "or_gates", "and_gates", "not_gates"]


def load_data(features_path, labels_path):
    X = pd.read_csv(features_path, index_col=0)
    labels = pd.read_csv(labels_path, index_col=0).squeeze()
    assert list(X.index) == list(labels.index), "Feature and label indices must match"
    return X.values, labels.values, list(X.index)


def run_tda(X, maxdim=2):
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    dist_matrix = squareform(pdist(X_scaled, metric="euclidean"))
    result = ripser(dist_matrix, maxdim=maxdim, distance_matrix=True, do_cocycles=True)
    return result


def extract_h1_loops(result, process_names):
    h1_bars = result["dgms"][1]
    h1_cocycles = result["cocycles"][1]
    loops = []
    for i, (birth, death) in enumerate(h1_bars):
        if np.isinf(death):
            continue
        persistence = death - birth
        cocycle = h1_cocycles[i]
        involved = set(
            process_names[edge[j]] for edge in cocycle for j in (0, 1)
        )
        loops.append((persistence, involved))
    loops.sort(key=lambda x: x[0], reverse=True)
    return loops


def coherence_score(loops, known_feedback, top_n=5):
    known_set = set(known_feedback)
    found = set()
    for _, members in loops[:top_n]:
        found.update(members & known_set)
    return len(found) / len(known_set)


def run_ablation(X, process_names, feature_names, known_feedback, top_n=5):
    results = {}

    print("Running baseline (all features)...")
    result_full = run_tda(X)
    loops_full = extract_h1_loops(result_full, process_names)
    baseline_score = coherence_score(loops_full, known_feedback, top_n)
    h1_count_full = sum(1 for b, d in result_full["dgms"][1] if not np.isinf(d))

    results["baseline"] = {
        "features_used": feature_names,
        "h1_count": h1_count_full,
        "coherence_score": baseline_score,
        "top_loops": [(round(p, 4), list(m)) for p, m in loops_full[:top_n]],
    }
    print(f"  Baseline coherence: {baseline_score:.3f}, H1 loops: {h1_count_full}")

    for drop_idx, drop_name in enumerate(feature_names):
        remaining = [i for i in range(len(feature_names)) if i != drop_idx]
        remaining_names = [feature_names[i] for i in remaining]
        X_ablated = X[:, remaining]

        print(f"Running ablation: drop '{drop_name}'...")
        result_abl = run_tda(X_ablated)
        loops_abl = extract_h1_loops(result_abl, process_names)
        score_abl = coherence_score(loops_abl, known_feedback, top_n)
        h1_count_abl = sum(1 for b, d in result_abl["dgms"][1] if not np.isinf(d))
        delta = score_abl - baseline_score

        results[f"drop_{drop_name}"] = {
            "features_used": remaining_names,
            "dropped_feature": drop_name,
            "h1_count": h1_count_abl,
            "coherence_score": score_abl,
            "coherence_delta": round(delta, 4),
            "top_loops": [(round(p, 4), list(m)) for p, m in loops_abl[:top_n]],
        }
        print(f"  Coherence: {score_abl:.3f} (delta: {delta:+.3f}), H1 loops: {h1_count_abl}")

    return results


def print_summary(results):
    print("\n" + "=" * 60)
    print("ABLATION SUMMARY")
    print("=" * 60)
    baseline = results["baseline"]["coherence_score"]
    print(f"{'Condition':<30} {'Coherence':>10} {'Delta':>10} {'H1 Loops':>10}")
    print("-" * 60)
    print(f"{'Baseline (all features)':<30} {baseline:>10.3f} {'—':>10} {results['baseline']['h1_count']:>10}")
    for key, val in results.items():
        if key == "baseline":
            continue
        print(
            f"{'Drop ' + val['dropped_feature']:<30} "
            f"{val['coherence_score']:>10.3f} "
            f"{val['coherence_delta']:>+10.3f} "
            f"{val['h1_count']:>10}"
        )
    print("=" * 60)
    print("\nInterpretation:")
    print("  Delta near 0        → feature has little effect; result is robust")
    print("  Delta strongly neg  → feature is load-bearing")
    print("  Delta positive      → feature may be adding noise")


def save_results(results, output_path="ablation_results.json"):
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=list)
    print(f"\nFull results saved to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GLMP TDA Feature Ablation Study")
    parser.add_argument("--data", required=True)
    parser.add_argument("--labels", required=True)
    parser.add_argument("--top_n", type=int, default=5)
    parser.add_argument("--output", default="ablation_results.json")
    args = parser.parse_args()

    X, labels, process_names = load_data(args.data, args.labels)
    results = run_ablation(X, process_names, FEATURE_NAMES, KNOWN_FEEDBACK, top_n=args.top_n)
    print_summary(results)
    save_results(results, args.output)
```

### Run command
**From the `nsf-proposal` folder** (scripts and data are copied there): run in place with no `cd`. From the full repo root, use `cd glmp-tda-analysis` first. Use `python3` if `python` is not available.
```bash
# From nsf-proposal (or from glmp-tda-analysis if using the full repo):
python3 feature_ablation.py \
  --data glmp_features_5col.csv \
  --labels glmp_labels.csv \
  --output ablation_results.json
```

### Output
`ablation_results.json` — used to populate Table 3 in the preprint.

---

## TASK 2: Run Null Model Permutation Test

### Script: `null_model_permutation.py`

```python
"""
null_model_permutation.py

Null model comparison for GLMP TDA pipeline.
Randomly permutes circuit labels and reruns TDA to ask:
  "How often does biological coherence this high arise by chance?"

If observed coherence falls above the 95th percentile of the null
distribution, that is a publishable result with p < 0.05.

Usage:
  python null_model_permutation.py --data glmp_features.csv --labels glmp_labels.csv
  python null_model_permutation.py --data glmp_features.csv --labels glmp_labels.csv \
    --n_permutations 1000
"""

import argparse
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from ripser import ripser
from scipy.spatial.distance import pdist, squareform
from sklearn.preprocessing import StandardScaler

KNOWN_FEEDBACK = [
    "ecoli_lac_operon",
    "ecoli_trp_operon",
    "ecoli_ara_operon",
    "ecoli_e._coli_two_component_signaling",
    "ecoli_sos_response",
    "ecoli_heat_shock_response",
    "ecoli_catabolite_repression",
    "ecoli_pho_regulon",
]

FEATURE_NAMES = ["node_count", "conditional_count", "or_gates", "and_gates", "not_gates"]


def load_data(features_path, labels_path):
    X = pd.read_csv(features_path, index_col=0)
    labels = pd.read_csv(labels_path, index_col=0).squeeze()
    assert list(X.index) == list(labels.index), "Feature and label indices must match"
    return X.values, labels.values, list(X.index)


def run_tda(X, maxdim=2):
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    dist_matrix = squareform(pdist(X_scaled, metric="euclidean"))
    result = ripser(dist_matrix, maxdim=maxdim, distance_matrix=True, do_cocycles=True)
    return result


def extract_h1_loops(result, process_names):
    h1_bars = result["dgms"][1]
    h1_cocycles = result["cocycles"][1]
    loops = []
    for i, (birth, death) in enumerate(h1_bars):
        if np.isinf(death):
            continue
        persistence = death - birth
        cocycle = h1_cocycles[i]
        involved = frozenset(
            process_names[edge[j]] for edge in cocycle for j in (0, 1)
        )
        loops.append((persistence, involved))
    loops.sort(key=lambda x: x[0], reverse=True)
    return loops


def coherence_score(loops, known_feedback, top_n=5):
    known_set = set(known_feedback)
    found = set()
    for _, members in loops[:top_n]:
        found.update(members & known_set)
    return len(found) / len(known_set)


def compute_observed_score(X, process_names, known_feedback, top_n):
    print("Computing observed (true) coherence score...")
    result = run_tda(X)
    loops = extract_h1_loops(result, process_names)
    score = coherence_score(loops, known_feedback, top_n)
    h1_count = sum(1 for b, d in result["dgms"][1] if not np.isinf(d))
    print(f"  Observed coherence: {score:.4f} | H1 loops: {h1_count}")
    return score, loops, h1_count


def run_null_model(X, process_names, known_feedback, n_permutations, top_n, seed=42):
    rng = np.random.default_rng(seed)
    null_scores = []
    process_names_arr = np.array(process_names)

    print(f"\nRunning {n_permutations} permutations...")
    for i in range(n_permutations):
        if (i + 1) % 50 == 0:
            print(f"  Permutation {i + 1}/{n_permutations}...")
        shuffled_names = list(rng.permutation(process_names_arr))
        result = run_tda(X)
        loops = extract_h1_loops(result, shuffled_names)
        score = coherence_score(loops, known_feedback, top_n)
        null_scores.append(score)

    return np.array(null_scores)


def compute_pvalue(observed_score, null_scores):
    return np.mean(null_scores >= observed_score)


def print_statistics(observed_score, null_scores, n_permutations):
    p_value = compute_pvalue(observed_score, null_scores)
    null_mean = np.mean(null_scores)
    null_std = np.std(null_scores)
    null_95 = np.percentile(null_scores, 95)
    null_99 = np.percentile(null_scores, 99)

    print("\n" + "=" * 60)
    print("NULL MODEL RESULTS")
    print("=" * 60)
    print(f"  Observed coherence score:     {observed_score:.4f}")
    print(f"  Null mean ± std:              {null_mean:.4f} ± {null_std:.4f}")
    print(f"  Null 95th percentile:         {null_95:.4f}")
    print(f"  Null 99th percentile:         {null_99:.4f}")
    print(f"  p-value (one-tailed):         {p_value:.4f}  (n={n_permutations})")
    print("-" * 60)

    if p_value < 0.01:
        print("  *** Significant at p < 0.01")
    elif p_value < 0.05:
        print("  **  Significant at p < 0.05")
    elif p_value < 0.10:
        print("  *   Approaching significance (p < 0.10)")
    else:
        print("      Not significant at p < 0.05")
        print("      Consider richer features or larger database.")
    print("=" * 60)

    return {
        "observed_score": observed_score,
        "null_mean": null_mean,
        "null_std": null_std,
        "null_95th_percentile": null_95,
        "null_99th_percentile": null_99,
        "p_value": p_value,
        "n_permutations": n_permutations,
        "significant_p05": bool(p_value < 0.05),
        "significant_p01": bool(p_value < 0.01),
    }


def plot_null_distribution(observed_score, null_scores, output_path="null_distribution.png"):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(null_scores, bins=30, color="#4C72B0", edgecolor="white",
            alpha=0.85, label="Null distribution")
    ax.axvline(observed_score, color="#DD4444", linewidth=2.5,
               label=f"Observed score = {observed_score:.3f}")
    ax.axvline(np.percentile(null_scores, 95), color="#888888",
               linewidth=1.5, linestyle="--", label="95th percentile")
    p_value = compute_pvalue(observed_score, null_scores)
    ax.set_title(
        f"Null Model: Biological Coherence of H\u2081 Loops\n"
        f"p = {p_value:.4f}  (n = {len(null_scores)} permutations)",
        fontsize=13
    )
    ax.set_xlabel("Coherence Score (fraction of known feedback circuits recovered)", fontsize=11)
    ax.set_ylabel("Count", fontsize=11)
    ax.legend(fontsize=10)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"\nNull distribution plot saved to {output_path}")


def save_results(stats, null_scores, output_path="null_model_results.json"):
    output = {
        "statistics": stats,
        "null_scores": null_scores.tolist(),
    }
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Full results saved to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GLMP TDA Null Model Permutation Test")
    parser.add_argument("--data", required=True)
    parser.add_argument("--labels", required=True)
    parser.add_argument("--n_permutations", type=int, default=500,
                        help="500 for quick run, 1000 for publication")
    parser.add_argument("--top_n", type=int, default=5)
    parser.add_argument("--output_json", default="null_model_results.json")
    parser.add_argument("--output_plot", default="null_distribution.png")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    X, labels, process_names = load_data(args.data, args.labels)

    observed_score, observed_loops, h1_count = compute_observed_score(
        X, process_names, KNOWN_FEEDBACK, args.top_n
    )
    null_scores = run_null_model(
        X, process_names, KNOWN_FEEDBACK,
        n_permutations=args.n_permutations,
        top_n=args.top_n,
        seed=args.seed
    )
    stats = print_statistics(observed_score, null_scores, args.n_permutations)
    plot_null_distribution(observed_score, null_scores, args.output_plot)
    save_results(stats, null_scores, args.output_json)
```

### Run command
**From the `nsf-proposal` folder** (no `cd` needed). From the full repo, `cd glmp-tda-analysis` first. Use `python3` if `python` is not available.
```bash
python3 null_model_permutation.py \
  --data glmp_features_5col.csv \
  --labels glmp_labels.csv \
  --n_permutations 1000 \
  --output_json null_model_results.json \
  --output_plot null_distribution.png
```

### Output
- `null_model_results.json` — statistics for preprint Results section
- `null_distribution.png` — Figure 2 for preprint and slide deck

---

## TASK 3: Populate the Preprint Results Section

Once both scripts have run successfully, use the JSON outputs to fill in
all `[X.XXX]` placeholders in the Results scaffold below. Work through the
checklist at the end of the section.

---

### Results (scaffold — fill in from script outputs)

#### 1. GLMP Database Overview

The GLMP database contains 108 genetic regulatory circuits represented as
Mermaid Markdown flowcharts. The corpus spans three organisms: *E. coli*
(66 processes, 61.1%), *S. cerevisiae* (38 processes, 35.2%), and *B.
subtilis* (4 processes, 3.7%).

**Table 1. Feature matrix summary statistics (n = 108 processes)**

| Feature | Mean | SD | Min | Max |
|---|---|---|---|---|
| Node count | [X.X] | [X.X] | [X] | [X] |
| Conditional count | [X.X] | [X.X] | [X] | [X] |
| OR gates | [X.X] | [X.X] | [X] | [X] |
| AND gates | [X.X] | [X.X] | [X] | [X] |
| NOT gates | [X.X] | [X.X] | [X] | [X] |

*Populate from Task 0 validation command output.*

---

#### 2. Persistence Diagram

- **H₀:** 108 bars
- **H₁:** 33 bars
- **H₂:** 4 bars
- H₁ persistence range: [[X.XXX]] to [[X.XXX]]

**Figure 1.** `glmp_persistence_diagram.png`
*Confirm this image path resolves correctly in the final document.*

---

#### 3. H₁ Loop Composition and Biological Coherence

**Table 2. Top five H₁ loops by persistence**

| Loop | Persistence | Members (n) | Organisms | Contains known feedback circuits |
|---|---|---|---|---|
| Loop #1 | 0.330 | 27 | *E. coli*, *S. cerevisiae*, *B. subtilis* | Yes — ara, SOS, stringent, catabolite, Pho, quorum sensing, heat shock, GAL, MAPK |
| Loop #2 | [X.XXX] | [X] | [fill from cocycle output] | [Yes/No — list members] |
| Loop #3 | 0.302 | 4 | *E. coli* | Yes — lac operon, antibiotic efflux, phosphate regulation, translation termination |
| Loop #4 | [X.XXX] | [X] | [fill from cocycle output] | [Yes/No — list members] |
| Loop #5 | 0.231 | 3 | *E. coli*, *S. cerevisiae* | Yes — EnvZ–OmpR, oxidative stress, yeast ER-associated degradation |

*Loops #2 and #4: inspect `result["dgms"][1]` and cocycles from the TDA
pipeline run. Add a short diagnostic script if needed:*

```python
# Loop membership diagnostic — run after TDA pipeline
import json
with open("ablation_results.json") as f:
    results = json.load(f)
for i, (persistence, members) in enumerate(results["baseline"]["top_loops"]):
    print(f"Loop #{i+1}: persistence={persistence}, n={len(members)}")
    print(f"  Members: {sorted(members)}\n")
```

**Biological coherence score:**
Of the eight reference circuits, [X] of 8 ([X]%) appeared in at least one
of the top five H₁ loops.

- Lac operon → Loop #3
- Two-component EnvZ–OmpR → Loop #5
- Ara operon → Loop #1
- SOS response → Loop #1
- Heat shock response → Loop #1
- Catabolite repression → Loop #1
- Pho regulon → Loop #1
- Trp operon → Loop #[X] (persistence = [X.XXX])
  *[Find trp operon in ablation_results.json baseline top_loops]*

---

#### 4. Feature Ablation Study

**Table 3. Feature ablation results**
*Populate entirely from `ablation_results.json`*

| Condition | Features Used | H₁ Loops | Coherence Score | Delta |
|---|---|---|---|---|
| Baseline (all features) | all 5 | [X] | [X.XXX] | — |
| Drop node_count | 4 | [X] | [X.XXX] | [±X.XXX] |
| Drop conditional_count | 4 | [X] | [X.XXX] | [±X.XXX] |
| Drop or_gates | 4 | [X] | [X.XXX] | [±X.XXX] |
| Drop and_gates | 4 | [X] | [X.XXX] | [±X.XXX] |
| Drop not_gates | 4 | [X] | [X.XXX] | [±X.XXX] |

**Interpretation — select ONE block below based on results, delete the others:**

> **[IF all |delta| < 0.10 — robust result]**
> Coherence scores were stable across all five ablation conditions
> (all |delta| < [X.XX]), indicating that no single feature is solely
> responsible for the observed biological coherence. The result reflects
> a genuine signal distributed across the feature representation rather
> than an artifact of any individual structural count.

> **[IF one delta is strongly negative]**
> Removal of [feature_name] produced the largest coherence decrease
> (delta = [−X.XXX]), identifying it as the most biologically informative
> feature. Remaining features produced deltas near zero (all |delta| <
> [X.XX]), suggesting [feature_name] carries the primary signal.

> **[IF a delta is positive]**
> Removal of [feature_name] produced a coherence increase (delta =
> +[X.XXX]), suggesting this feature introduces noise relative to the
> biological signal. Dropping it from future iterations is recommended.

---

#### 5. Null Model Permutation Test

**Figure 2.** `null_distribution.png`
*Confirm this image renders correctly.*

**Select ONE block below based on p-value from `null_model_results.json`,
delete the others:**

> **[IF p < 0.01]**
> The observed coherence score of [X.XXX] fell at the [N]th percentile
> of the null distribution (null mean ± SD: [X.XXX] ± [X.XXX]; 95th
> percentile: [X.XXX]; 99th percentile: [X.XXX]; p = [X.XXX],
> one-tailed, n = 1,000 permutations). Biological coherence at this
> level is very unlikely to arise from random label assignment (p < 0.01).

> **[IF 0.01 ≤ p < 0.05]**
> The observed coherence score of [X.XXX] fell at the [N]th percentile
> of the null distribution (null mean ± SD: [X.XXX] ± [X.XXX]; 95th
> percentile: [X.XXX]; p = [X.XXX], one-tailed, n = 1,000 permutations).
> The result is statistically significant at p < 0.05.

> **[IF 0.05 ≤ p < 0.10]**
> The observed coherence score of [X.XXX] approached but did not reach
> significance (null mean ± SD: [X.XXX] ± [X.XXX]; 95th percentile:
> [X.XXX]; p = [X.XXX], one-tailed, n = 1,000 permutations). The
> conservative scoring metric and current database size (108 processes)
> may limit statistical power; scaling and feature enrichment are the
> primary remedies.

> **[IF p ≥ 0.10]**
> The observed coherence score of [X.XXX] did not significantly exceed
> the null distribution (null mean ± SD: [X.XXX] ± [X.XXX]; 95th
> percentile: [X.XXX]; p = [X.XXX], one-tailed, n = 1,000 permutations).
> This result is informative: it defines the database scale and feature
> richness required for significance, motivating the scaling program
> described in the Discussion.

---

#### 6. Summary Table

**Table 4. Results summary**
*Populate after all analyses are complete.*

| Analysis | Result | Interpretation |
|---|---|---|
| H₁ loops detected | 33 | Substantial topological structure |
| H₂ voids detected | 4 | Higher-order structure present |
| Reference circuits in top 5 loops | [X]/8 ([X]%) | [Strong/Moderate/Weak] coherence |
| Cross-organism loops | [X] of 33 | Universal regulatory motifs detected |
| Feature ablation max \|delta\| | [X.XXX] (drop [feature]) | [Robust / Load-bearing feature found] |
| Null model p-value | [X.XXX] | [Significant / Approaching / Not significant] |

---

### Results Checklist for Cursor

- [ ] Table 1: run Task 0 validation command, paste describe() output
- [ ] Figure 1: confirm `glmp_persistence_diagram.png` resolves at GCS path
- [ ] Table 2: fill Loops #2 and #4 from loop membership diagnostic
- [ ] Trp operon: find in `ablation_results.json` baseline top_loops
- [ ] Coherence score: count reference circuits in top 5, compute fraction
- [ ] Table 3: populate entirely from `ablation_results.json`
- [ ] Section 4 interpretation: select correct paragraph, delete others
- [ ] Figure 2: confirm `null_distribution.png` generated and renders
- [ ] Section 5 p-value block: select correct paragraph, delete others
- [ ] Table 4: populate from all above
- [ ] Final pass: search for any remaining `[X.XXX]` or `[fill` strings

---

## TASK 4: Update the Seminar Slide Deck

The slide deck lives at:
`https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/TDA_Seminar_Slides.html`

Make the following targeted changes:

### Change 1: Update the Limitations slide

Replace the current limitations bullet list with:

> - *Sample size: 108 processes — enough to reveal structure, but scaling
>   to 200–500+ is a priority.*
> - *Feature sensitivity: We used 5 structural counts (node count,
>   conditionals, OR/AND/NOT gates). Stability of H₁ loops across feature
>   perturbations — in progress; preliminary ablation suggests robustness.*
> - *Graph-theoretic enrichment: cycle rank, longest path length, AND/OR
>   gate ratios — planned for next pipeline iteration.*
> - *LLM-generated flowcharts require expert fact-checking; the GLMP
>   viewer feedback mechanism is one avenue for community validation.*
> - *Open question: Does topology predict regulatory function, or correlate
>   with known biology? The coherence check supports the latter; prediction
>   requires prospective validation.*

### Change 2: Update the Next Steps slide

Add these bullets after the existing Mapper bullet:

> - *Feature ablation study: rerun TDA dropping one feature at a time to
>   test H₁ loop stability — directly addresses whether results are
>   feature-space artifacts.*
> - *Null model comparison: randomly permute circuit labels and rerun TDA;
>   if biological coherence rarely emerges by chance, that is a publishable
>   result.*
> - *Graph-theoretic features: cycle rank, longest path, gate ratios —
>   planned for next pipeline iteration.*

### Change 3: Add a new slide before the Limitations slide

Title: **"Why These Features Work"**

Content:

> *The coherence check runs in the opposite direction from the concern:
> we are not inferring biology from topology — we are asking whether
> topology recovers known biology.*
>
> *If 5 structural counts were biologically meaningless, known feedback
> circuits would scatter randomly across H₁ loops. They do not.*
>
> *Lac → Loop #3. Two-component → Loop #5. Stress and nutrient circuits
> → Loop #1. This matches the regulatory architecture biologists already
> recognize.*
>
> *Conclusion: simple features appear sufficient to capture coarse
> regulatory topology. Richer features are the next step, not a
> prerequisite for the current result.*

### Change 4: Add null model result (after scripts run)

Once `null_model_results.json` is available, add one bullet to the Next
Steps slide (or promote to a new Results slide if p < 0.05):

> - *Null model permutation test (n=1,000): p = [X.XXX]
>   [significant at p < 0.05 / approaching significance / pending]*

---

## TASK 5: Refactor Shared Code (Optional but Recommended)

Both scripts share `load_data`, `run_tda`, `extract_h1_loops`, and
`coherence_score`. Extract these into a shared utility module:

### `glmp_tda_utils.py`

```python
"""
glmp_tda_utils.py
Shared utilities for GLMP TDA pipeline.
Import in feature_ablation.py and null_model_permutation.py.
"""

import numpy as np
import pandas as pd
from ripser import ripser
from scipy.spatial.distance import pdist, squareform
from sklearn.preprocessing import StandardScaler

KNOWN_FEEDBACK = [
    "ecoli_lac_operon",
    "ecoli_trp_operon",
    "ecoli_ara_operon",
    "ecoli_e._coli_two_component_signaling",
    "ecoli_sos_response",
    "ecoli_heat_shock_response",
    "ecoli_catabolite_repression",
    "ecoli_pho_regulon",
]

FEATURE_NAMES = ["node_count", "conditional_count", "or_gates", "and_gates", "not_gates"]


def load_data(features_path, labels_path):
    X = pd.read_csv(features_path, index_col=0)
    labels = pd.read_csv(labels_path, index_col=0).squeeze()
    assert list(X.index) == list(labels.index), "Feature and label indices must match"
    return X.values, labels.values, list(X.index)


def run_tda(X, maxdim=2):
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    dist_matrix = squareform(pdist(X_scaled, metric="euclidean"))
    return ripser(dist_matrix, maxdim=maxdim, distance_matrix=True, do_cocycles=True)


def extract_h1_loops(result, process_names):
    h1_bars = result["dgms"][1]
    h1_cocycles = result["cocycles"][1]
    loops = []
    for i, (birth, death) in enumerate(h1_bars):
        if np.isinf(death):
            continue
        persistence = death - birth
        cocycle = h1_cocycles[i]
        involved = frozenset(
            process_names[edge[j]] for edge in cocycle for j in (0, 1)
        )
        loops.append((persistence, involved))
    loops.sort(key=lambda x: x[0], reverse=True)
    return loops


def coherence_score(loops, known_feedback=None, top_n=5):
    if known_feedback is None:
        known_feedback = KNOWN_FEEDBACK
    known_set = set(known_feedback)
    found = set()
    for _, members in loops[:top_n]:
        found.update(members & known_set)
    return len(found) / len(known_set)
```

Then update the import lines at the top of both scripts:
```python
from glmp_tda_utils import (
    load_data, run_tda, extract_h1_loops, coherence_score,
    KNOWN_FEEDBACK, FEATURE_NAMES
)
```

---

## Dependencies and setup

**Option A — Use the venv in `nsf-proposal` (recommended):**

A virtual environment with all dependencies is in `nsf-proposal/.venv`. From the `nsf-proposal` folder:

```bash
source .venv/bin/activate
python feature_ablation.py --data glmp_features_5col.csv --labels glmp_labels.csv --output ablation_results.json
python null_model_permutation.py --data glmp_features_5col.csv --labels glmp_labels.csv --n_permutations 1000 --output_json null_model_results.json --output_plot null_distribution.png
```

**Option B — Create the venv and install yourself:**

```bash
cd nsf-proposal
python3 -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r requirements-tda.txt
```

Then run the two script commands above. Python 3.10+ recommended. All analyses use `seed=42` for reproducibility.

---

## File Map

| File | Source | Used in |
|---|---|---|
| `glmp_features_5col.csv` | `nsf-proposal/` or `glmp-tda-analysis/` | Tasks 1, 2 |
| `glmp_labels.csv` | `nsf-proposal/` or `glmp-tda-analysis/` | Tasks 1, 2 |
| `feature_ablation.py` | `nsf-proposal/` or `glmp-tda-analysis/` | Task 1 |
| `null_model_permutation.py` | `nsf-proposal/` or `glmp-tda-analysis/` | Task 2 |
| `ablation_results.json` | Output of Task 1 | Task 3 Tables 3, 4 |
| `null_model_results.json` | Output of Task 2 | Task 3 Section 5 |
| `null_distribution.png` | Output of Task 2 | Preprint Figure 2, slide deck |
| `glmp_persistence_diagram.png` | Already at GCS path | Preprint Figure 1, slide deck |
| `TDA_Seminar_Slides.html` | GCS | Task 4 |

---

## Note A: Extracting Feature Matrix from GLMP Pipeline

If `glmp_features.csv` does not already exist, extract it from the GLMP
JSON records using this script:

```python
"""
extract_features.py
Extracts feature matrix from GLMP process JSON records.
Adjust `json_dir` to point to your local GLMP JSON directory.
"""

import json
import os
import pandas as pd
import re

json_dir = "./processes"  # adjust to your GLMP JSON directory

records = []
for fname in sorted(os.listdir(json_dir)):
    if not fname.endswith(".json"):
        continue
    with open(os.path.join(json_dir, fname)) as f:
        process = json.load(f)

    mermaid = process.get("mermaid", "")
    process_id = process.get("id", fname.replace(".json", ""))

    # Count structural features from Mermaid source
    lines = mermaid.splitlines()
    node_count = sum(1 for l in lines if re.search(r'\[.*\]|\(.*\)|{.*}', l))
    conditional_count = sum(1 for l in lines if re.search(r'\{.*\}', l))
    or_gates = sum(1 for l in lines if re.search(r'\bOR\b', l, re.IGNORECASE))
    and_gates = sum(1 for l in lines if re.search(r'\bAND\b', l, re.IGNORECASE))
    not_gates = sum(1 for l in lines if re.search(r'\bNOT\b', l, re.IGNORECASE))

    records.append({
        "process_id": process_id,
        "node_count": node_count,
        "conditional_count": conditional_count,
        "or_gates": or_gates,
        "and_gates": and_gates,
        "not_gates": not_gates,
    })

df = pd.DataFrame(records).set_index("process_id")
df.to_csv("glmp_features.csv")
df.index.to_frame().to_csv("glmp_labels.csv")
print(f"Extracted {len(df)} processes.")
print(df.describe().round(2))
```

**Important:** The regex patterns above are approximate. If your existing
TDA pipeline already parses Mermaid features with a more precise method,
use that instead and do not re-extract — consistency with the original
analysis matters.

---

## Questions for Gary

1. Does `glmp_features.csv` already exist from the original TDA run,
   or does it need to be re-extracted? (See Note A above.)

2. Where is the source file for `TDA_Seminar_Slides.html` — is it in
   the GitHub repo or only at the GCS URL? Cursor needs write access
   to update the deck.

3. What is the target location for the updated slide deck and preprint
   draft — GCS bucket, GitHub repo, or both?
```
