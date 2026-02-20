"""
null_model_permutation.py

Null model comparison for GLMP TDA pipeline.
Randomly permutes circuit labels and reruns TDA to ask:
  "How often does biological coherence this high arise by chance?"

If observed coherence falls above the 95th percentile of the null
distribution, that is a publishable result with p < 0.05.

Usage:
  python null_model_permutation.py --data glmp_features_5col.csv --labels glmp_labels.csv
  python null_model_permutation.py --data glmp_features_5col.csv --labels glmp_labels.csv \
    --n_permutations 1000
"""

import argparse
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
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
    if not all(c in X.columns for c in FEATURE_NAMES):
        raise ValueError(f"Feature file must contain columns: {FEATURE_NAMES}")
    X = X[FEATURE_NAMES].astype(float)
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
    process_names = np.array(process_names)
    loops = []
    for i, (birth, death) in enumerate(h1_bars):
        if np.isinf(death):
            continue
        persistence = death - birth
        cocycle = h1_cocycles[i]
        involved = set()
        for edge in cocycle:
            for j in (0, 1):
                idx = int(edge[j])
                involved.add(process_names[idx])
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
        "observed_score": float(observed_score),
        "null_mean": float(null_mean),
        "null_std": float(null_std),
        "null_95th_percentile": float(null_95),
        "null_99th_percentile": float(null_99),
        "p_value": float(p_value),
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
    parser.add_argument("--data", default="glmp_features_5col.csv")
    parser.add_argument("--labels", default="glmp_labels.csv")
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
