"""
Merge flowchart loop counts into GLMP metadata and optionally update process JSONs.

Reads glmp_features.csv (which has loops from add_loops_to_features.py),
fetches metadata.json from GCS, adds loops to each process, and outputs
metadata_with_loops.json. Use this to regenerate the GLMP database table
with a Loops column.

Also optionally writes loops back to each process JSON for persistence.
"""

import json
import os
import sys
import requests
import pandas as pd

GLMP_METADATA_URL = "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/glmp-v2/data/metadata.json"
DEFAULT_PROCESSES_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..",
    "huggingface-space", "glmp-processes-database", "processes"
)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    if not os.path.exists("glmp_features.csv"):
        print("Run fetch_glmp_data.py and add_loops_to_features.py first.")
        sys.exit(1)

    df = pd.read_csv("glmp_features.csv")
    if "loops" not in df.columns:
        print("glmp_features.csv has no 'loops' column. Run add_loops_to_features.py first.")
        sys.exit(1)

    loops_map = dict(zip(df["process_id"], df["loops"].fillna(0).astype(int)))

    print("Fetching metadata...")
    r = requests.get(GLMP_METADATA_URL)
    r.raise_for_status()
    meta = r.json()

    for p in meta.get("processes", []):
        pid = p.get("id", "")
        p["loops"] = int(loops_map.get(pid, 0))

    out_path = os.path.join(script_dir, "metadata_with_loops.json")
    with open(out_path, "w") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"Saved {out_path}")

    # Optionally write loops back to process JSONs
    processes_dir = os.path.abspath(DEFAULT_PROCESSES_DIR)
    if os.path.isdir(processes_dir):
        updated = 0
        for pid, loops in loops_map.items():
            path = os.path.join(processes_dir, f"{pid}.json")
            if os.path.exists(path):
                try:
                    with open(path) as f:
                        data = json.load(f)
                    data["loops"] = int(loops)
                    with open(path, "w") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    updated += 1
                except Exception as e:
                    print(f"Warning: could not update {path}: {e}")
        print(f"Updated loops in {updated} process JSONs.")
    else:
        print(f"Processes dir not found: {processes_dir} (skipping JSON updates)")

    print("\nNext steps:")
    print("1. Upload metadata_with_loops.json to GCS as metadata.json (or use as-is).")
    print("2. Deploy glmp-database-table.html (with Loops column) to GCS.")


if __name__ == "__main__":
    main()
