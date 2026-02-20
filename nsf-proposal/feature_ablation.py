"""
feature_ablation.py

Feature ablation study for GLMP TDA pipeline.
Reruns Vietoris-Rips TDA dropping one feature at a time, then compares
biological coherence of H1 loops against the full-feature baseline.

Known feedback circuits used as coherence reference:
  lac operon, trp operon, ara operon, two-component signaling,
  SOS response, heat shock, catabolite repression, Pho regulon

Usage:
  python feature_ablation.py --data glmp_features_5col.csv --labels glmp_labels.csv
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
    # Use only the 5 feature columns if extra columns present
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


def run_ablation(X, process_names, feature_names, known_feedback, top_n=5):
    results = {}

    print("Running baseline (all features)...")
    result_full = run_tda(X)
    loops_full = extract_h1_loops(result_full, process_names)
    baseline_score = coherence_score(loops_full, known_feedback, top_n)
    h1_count_full = sum(1 for b, d in result_full["dgms"][1] if not np.isinf(d))

    results["baseline"] = {
        "features_used": feature_names,
        "h1_count": int(h1_count_full),
        "coherence_score": float(baseline_score),
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
            "h1_count": int(h1_count_abl),
            "coherence_score": float(score_abl),
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
    def default_list(obj):
        if isinstance(obj, set):
            return list(obj)
        raise TypeError

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=default_list)
    print(f"\nFull results saved to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GLMP TDA Feature Ablation Study")
    parser.add_argument("--data", default="glmp_features_5col.csv")
    parser.add_argument("--labels", default="glmp_labels.csv")
    parser.add_argument("--top_n", type=int, default=5)
    parser.add_argument("--output", default="ablation_results.json")
    args = parser.parse_args()

    X, labels, process_names = load_data(args.data, args.labels)
    results = run_ablation(X, process_names, FEATURE_NAMES, KNOWN_FEEDBACK, top_n=args.top_n)
    print_summary(results)
    save_results(results, args.output)
