#!/usr/bin/env python3
"""
Apply curated, process-specific Mermaid flowcharts to Computer Science process JSONs
WITHOUT touching citations/sources.

Why:
- Some CS processes still show the generic template Mermaid (Inputs/Method Selection/Option A...).
- We want a larger set of good, non-generic graphs while keeping the current citations.

What it does:
- For each JSON in computer-science-processes-database/processes/**.json:
  - If the current Mermaid looks like the generic template (unless --force),
    replace ONLY `mermaid` using curated templates from `curated_flowcharts.py`.
  - Recompute `complexity.nodes`, `complexity.edges`, and `complexity.logicGates` from Mermaid.
  - Keep `sources` untouched.

Usage:
  cd huggingface-space
  python3 scripts/processes/apply_curated_cs_mermaid.py --db-dir computer-science-processes-database
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Local import from scripts/processes/
from curated_flowcharts import CS_TEMPLATES, Step  # type: ignore


COLOR_SCHEME: Dict[str, Dict[str, str]] = {
    "red": {"hex": "#ff6b6b", "category": "Triggers & Inputs"},
    "yellow": {"hex": "#ffd43b", "category": "Structures & Objects"},
    "green": {"hex": "#51cf66", "category": "Processing & Operations"},
    "blue": {"hex": "#74c0fc", "category": "Intermediates & States"},
    "violet": {"hex": "#b197fc", "category": "Products & Outputs"},
}


def looks_like_generic_template(mermaid_text: str) -> bool:
    if not mermaid_text:
        return False
    needles = ["Inputs", "Method Selection", "Option A", "Option B", "Option C", "Step 1", "Step 2", "Step 3"]
    return sum(1 for n in needles if n in mermaid_text) >= 6


def parse_mermaid(mermaid_text: str) -> Tuple[Dict[str, str], List[Tuple[str, str]]]:
    nodes: Dict[str, str] = {}
    edges: List[Tuple[str, str]] = []
    if not mermaid_text:
        return nodes, edges

    node_pattern = r'(\w+)\s*[\[(]([^\])]+)[\])]'
    for match in re.finditer(node_pattern, mermaid_text):
        node_id = match.group(1)
        node_label = match.group(2).strip().strip('"')
        nodes[node_id] = node_label

    edge_pattern = r"(\w+)\s*(?:-->|--)\s*(?:\|.*?\|\s*)?(\w+)"
    for match in re.finditer(edge_pattern, mermaid_text):
        edges.append((match.group(1), match.group(2)))

    return nodes, edges


def count_logic_gates(nodes: Dict[str, str], edges: List[Tuple[str, str]]) -> Tuple[int, int]:
    incoming: Dict[str, int] = {}
    outgoing: Dict[str, int] = {}
    for s, t in edges:
        outgoing[s] = outgoing.get(s, 0) + 1
        incoming[t] = incoming.get(t, 0) + 1

    and_count = 0
    or_count = 0
    all_ids = set(nodes.keys()) | set(incoming.keys()) | set(outgoing.keys())
    for node_id in all_ids:
        inc = incoming.get(node_id, 0)
        out = outgoing.get(node_id, 0)
        if inc >= 2 and out == 1:
            and_count += 1
        elif inc == 1 and out >= 2:
            or_count += 1
    return and_count, or_count


def _style_line(node_id: str, role: str) -> str:
    hex_color = COLOR_SCHEME[role]["hex"]
    text_color = "#000" if role == "yellow" else "#fff"
    return f"    style {node_id} fill:{hex_color},color:{text_color}"


def make_mermaid_curated_with_branch(process_name: str, steps: List[Step]) -> str:
    """
    Build a small, process-specific Mermaid diagram with a deliberate OR split + AND merge.
    This keeps shapes from being identical to the generic template while still being stable.
    """
    if not steps:
        steps = [{"label": process_name, "role": "green"}, {"label": "Output", "role": "violet"}]  # type: ignore[list-item]

    # Ensure there is an output
    if steps[-1]["role"] != "violet":
        steps = [*steps, {"label": "Output", "role": "violet"}]  # type: ignore[assignment]

    # Pick a split point if we have enough material; otherwise just linearize.
    if len(steps) < 7:
        node_ids = [f"N{i+1}" for i in range(len(steps))]
        lines: List[str] = ["graph TD"]
        for nid, step in zip(node_ids, steps):
            label = step["label"].replace("[", "(").replace("]", ")")
            lines.append(f'{nid}["{label}"]')
        lines.append("")
        for i in range(len(node_ids) - 1):
            lines.append(f"{node_ids[i]} --> {node_ids[i+1]}")
        lines.append("")
        for nid, step in zip(node_ids, steps):
            lines.append(_style_line(nid, step["role"]))
        return "\n".join(lines)

    # Structure:
    # pre (first 3) -> OR split -> branch A (next 2) / branch B (next 2) -> AND merge -> tail (rest)
    pre = steps[:3]
    a = steps[3:5]
    b = steps[5:7]
    tail = steps[7:]

    # Nodes
    lines: List[str] = ["graph TD"]

    nid = 1
    def add(step: Step) -> str:
        nonlocal nid
        node_id = f"N{nid}"
        nid += 1
        label = step["label"].replace("[", "(").replace("]", ")")
        lines.append(f'{node_id}["{label}"]')
        return node_id

    pre_ids = [add(s) for s in pre]
    or_id = add({"label": "Choose Approach", "role": "yellow"})  # type: ignore[arg-type]
    a_ids = [add(s) for s in a]
    b_ids = [add(s) for s in b]
    and_id = add({"label": "Integrate Results", "role": "blue"})  # type: ignore[arg-type]
    tail_ids = [add(s) for s in tail]

    # Edges
    lines.append("")
    for i in range(len(pre_ids) - 1):
        lines.append(f"{pre_ids[i]} --> {pre_ids[i+1]}")
    lines.append(f"{pre_ids[-1]} --> {or_id}")

    # OR split
    lines.append(f"{or_id} --> {a_ids[0]}")
    lines.append(f"{or_id} --> {b_ids[0]}")

    # Branch A/B internal
    lines.append(f"{a_ids[0]} --> {a_ids[1]}")
    lines.append(f"{b_ids[0]} --> {b_ids[1]}")

    # AND merge
    lines.append(f"{a_ids[1]} --> {and_id}")
    lines.append(f"{b_ids[1]} --> {and_id}")

    # Tail
    if tail_ids:
        lines.append(f"{and_id} --> {tail_ids[0]}")
        for i in range(len(tail_ids) - 1):
            lines.append(f"{tail_ids[i]} --> {tail_ids[i+1]}")
    else:
        lines.append(f"{and_id} --> {a_ids[1]}")  # fallback (shouldn't happen)

    # Styles
    lines.append("")
    role_map: Dict[str, str] = {}
    # We can infer roles from steps in insertion order using the same generated IDs
    # Reconstruct by iterating the same creation order:
    nid_check = 1
    for s in pre:
        role_map[f"N{nid_check}"] = s["role"]
        nid_check += 1
    role_map[f"N{nid_check}"] = "yellow"  # Choose Approach
    nid_check += 1
    for s in a:
        role_map[f"N{nid_check}"] = s["role"]
        nid_check += 1
    for s in b:
        role_map[f"N{nid_check}"] = s["role"]
        nid_check += 1
    role_map[f"N{nid_check}"] = "blue"  # Integrate Results
    nid_check += 1
    for s in tail:
        role_map[f"N{nid_check}"] = s["role"]
        nid_check += 1

    for node_id, role in role_map.items():
        lines.append(_style_line(node_id, role))

    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db-dir", required=True, help="e.g. computer-science-processes-database")
    ap.add_argument("--force", action="store_true", help="Rewrite Mermaid even if it doesn't look like the generic template.")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    db_dir = Path(args.db_dir)
    processes_dir = db_dir / "processes"
    if not processes_dir.exists():
        raise SystemExit(f"Not found: {processes_dir}")

    updated = 0
    skipped_not_generic = 0
    missing_template = 0
    errors = 0

    for path in sorted(processes_dir.rglob("*.json")):
        if path.name.endswith(".backup"):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            pid = data.get("id") or path.stem
            current_mermaid = (data.get("mermaid") or "").strip()

            if (not args.force) and (not looks_like_generic_template(current_mermaid)):
                skipped_not_generic += 1
                continue

            steps = CS_TEMPLATES.get(pid)
            if not steps:
                missing_template += 1
                continue

            name = data.get("name") or pid
            new_mermaid = make_mermaid_curated_with_branch(str(name), steps)
            if new_mermaid.strip() == current_mermaid.strip():
                continue

            data["mermaid"] = new_mermaid

            nodes, edges = parse_mermaid(new_mermaid)
            and_count, or_count = count_logic_gates(nodes, edges)
            complexity = data.get("complexity") or {}
            complexity["nodes"] = len(nodes)
            complexity["edges"] = len(edges)
            complexity.setdefault("conditionals", 0)
            lg = complexity.get("logicGates") or {}
            lg["andGates"] = and_count
            lg["orGates"] = or_count
            lg["total"] = and_count + or_count
            complexity["logicGates"] = lg
            data["complexity"] = complexity

            data["notes"] = (data.get("notes") or "").strip() + "\nCurated Mermaid applied (citations preserved)."

            if not args.dry_run:
                path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

            updated += 1
        except Exception:
            errors += 1

    print(
        json.dumps(
            {
                "db_dir": str(db_dir),
                "updated": updated,
                "skipped_not_generic": skipped_not_generic,
                "missing_template": missing_template,
                "errors": errors,
                "dry_run": bool(args.dry_run),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

