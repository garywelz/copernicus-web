"""
Fetch GLMP biological process data from the metadata JSON.
The JSON contains: process_id, process_name, organism, category, complexity,
nodes, conditionals, or_gates, and_gates, not_gates.
After fetching, adds flowchart loop counts (back-edges) per process.
"""

import os
import requests
import pandas as pd

GLMP_METADATA_URL = "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/glmp-v2/data/metadata.json"


def fetch_and_parse_glmp():
    """Fetch GLMP metadata JSON and parse into structured DataFrame."""
    print("Fetching GLMP metadata...")
    response = requests.get(GLMP_METADATA_URL)
    response.raise_for_status()
    data = response.json()

    processes = data.get("processes", [])
    if not processes:
        raise ValueError("No processes found in metadata")

    rows = []
    for p in processes:
        lg = p.get("logicGates", {})
        rows.append({
            "process_id": p.get("id", ""),
            "process_name": p.get("name", ""),
            "organism": p.get("organism", ""),
            "category": p.get("category", ""),
            "complexity": p.get("complexity", "unknown"),
            "node_count": int(p.get("nodes", 0)),
            "conditional_count": int(p.get("conditionals", 0)),
            "or_gates": int(lg.get("or", 0)),
            "and_gates": int(lg.get("and", 0)),
            "not_gates": int(p.get("notGates", 0)),  # kept in CSV but not used as TDA feature
        })

    return pd.DataFrame(rows)


def main():
    df = fetch_and_parse_glmp()
    print(f"Parsed {len(df)} processes")

    # Save to CSV (this is our feature dataset)
    df.to_csv("glmp_features.csv", index=False)
    print("Saved to glmp_features.csv")

    # Add flowchart loop counts
    try:
        from add_loops_to_features import add_loops_column
        add_loops_column()
    except Exception as e:
        print(f"Warning: could not add loops column: {e}")
        print("Run add_loops_to_features.py manually to add loops.")

    print(f"Columns: {list(pd.read_csv('glmp_features.csv').columns)}")
    print("\nSample:")
    print(pd.read_csv("glmp_features.csv").head())

    return df


if __name__ == "__main__":
    main()
