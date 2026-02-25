"""
Add flowchart loop counts to glmp_features.csv.

Reads process JSON files (from local or GCS), computes back-edge count per process,
and adds a 'loops' column to the feature table.
"""

import json
import os
import sys
import requests
import pandas as pd

from count_flowchart_loops import count_flowchart_loops

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
DEFAULT_PROCESSES_DIR = os.path.join(
    REPO_ROOT, "huggingface-space", "glmp-processes-database", "processes"
)
GLMP_PROCESS_URL = "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/glmp-v2/processes/{}.json"


def get_mermaid_for_process(process_id: str, processes_dir: str | None = None) -> str | None:
    """Load mermaid from local JSON or fetch from GCS."""
    processes_dir = processes_dir or DEFAULT_PROCESSES_DIR
    local_path = os.path.join(processes_dir, f"{process_id}.json")

    if os.path.exists(local_path):
        try:
            with open(local_path) as f:
                data = json.load(f)
            return data.get("mermaid") or None
        except Exception:
            return None

    try:
        url = GLMP_PROCESS_URL.format(process_id)
        r = requests.get(url, timeout=10)
        if r.ok:
            data = r.json()
            return data.get("mermaid") or None
    except Exception:
        pass
    return None


def add_loops_column(
    csv_path: str = "glmp_features.csv",
    processes_dir: str | None = None,
    out_path: str | None = None,
) -> pd.DataFrame:
    """
    Add 'loops' column to glmp_features.csv.
    """
    os.chdir(SCRIPT_DIR)
    out_path = out_path or csv_path

    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found. Run fetch_glmp_data.py first.")
        sys.exit(1)

    df = pd.read_csv(csv_path)
    if "loops" in df.columns:
        print("'loops' column already exists. Overwriting.")
    df["loops"] = 0

    processes_dir = processes_dir or DEFAULT_PROCESSES_DIR
    missing = []
    for i, row in df.iterrows():
        pid = row["process_id"]
        mermaid = get_mermaid_for_process(pid, processes_dir)
        if mermaid:
            df.at[i, "loops"] = count_flowchart_loops(mermaid)
        else:
            missing.append(pid)

    df.to_csv(out_path, index=False)
    print(f"Saved {out_path} with {len(df)} processes, loops column added.")
    if missing:
        print(f"Warning: no mermaid for {len(missing)} process(es): {missing[:5]}...")
    print(f"Loop count range: {df['loops'].min()} - {df['loops'].max()}")
    return df


def main():
    add_loops_column()


if __name__ == "__main__":
    main()
