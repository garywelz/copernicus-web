#!/usr/bin/env python3
"""
Export a "full replacement plan" from a discipline `metadata.json`.

Goal: enable URL-stable overwrites of *all existing* processes by emitting
plan items that include explicit `id`, `name`, `subcategory`, `subcategory_name`.

Usage:
  python3 scripts/processes/export_plan_from_metadata.py \
    --metadata biology-processes-database/metadata.json \
    --out scripts/processes/biology_full_plan.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", required=True, help="Path to metadata.json")
    parser.add_argument("--out", required=True, help="Output plan JSON path")
    args = parser.parse_args()

    metadata_path = Path(args.metadata)
    out_path = Path(args.out)

    meta = json.loads(metadata_path.read_text(encoding="utf-8"))
    processes = meta.get("processes") or []

    plan_items: List[Dict[str, Any]] = []
    for p in processes:
        if not isinstance(p, dict):
            continue
        pid = p.get("id")
        if not pid:
            continue
        plan_items.append(
            {
                "id": pid,
                "name": p.get("name") or pid,
                "subcategory": p.get("subcategory") or pid.split("-", 1)[0],
                "subcategory_name": p.get("subcategory_name") or (p.get("subcategory") or "").replace("_", " ").title(),
            }
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"processes": plan_items}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(plan_items)} processes to {out_path}")


if __name__ == "__main__":
    main()

