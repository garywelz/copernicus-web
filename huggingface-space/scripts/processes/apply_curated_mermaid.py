#!/usr/bin/env python3
"""
Apply curated, non-generic Mermaid flowcharts while preserving citations.

Supports:
- chemistry: uses CHEMISTRY_TEMPLATES or CHEMISTRY_SUBCATEGORY_TEMPLATES
- biology: uses BIOLOGY_SUBCATEGORY_TEMPLATES

It only rewrites files whose Mermaid still looks like the generic template
(Inputs/Method Selection/Option A...), unless --force is provided.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from curated_flowcharts import (
    BIOLOGY_SUBCATEGORY_TEMPLATES,
    CHEMISTRY_SUBCATEGORY_TEMPLATES,
    CHEMISTRY_TEMPLATES,
    Step,
)


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
    Non-generic but stable Mermaid:
    pre -> OR split -> branch A / branch B -> AND merge -> tail
    """
    if not steps:
        steps = [{"label": process_name, "role": "green"}, {"label": "Output", "role": "violet"}]  # type: ignore[list-item]

    if steps[-1]["role"] != "violet":
        steps = [*steps, {"label": "Output", "role": "violet"}]  # type: ignore[assignment]

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

    pre = steps[:3]
    a = steps[3:5]
    b = steps[5:7]
    tail = steps[7:]

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
    or_id = add({"label": "Choose Path", "role": "yellow"})  # type: ignore[arg-type]
    a_ids = [add(s) for s in a]
    b_ids = [add(s) for s in b]
    and_id = add({"label": "Integrate", "role": "blue"})  # type: ignore[arg-type]
    tail_ids = [add(s) for s in tail]

    lines.append("")
    for i in range(len(pre_ids) - 1):
        lines.append(f"{pre_ids[i]} --> {pre_ids[i+1]}")
    lines.append(f"{pre_ids[-1]} --> {or_id}")

    lines.append(f"{or_id} --> {a_ids[0]}")
    lines.append(f"{or_id} --> {b_ids[0]}")
    lines.append(f"{a_ids[0]} --> {a_ids[1]}")
    lines.append(f"{b_ids[0]} --> {b_ids[1]}")
    lines.append(f"{a_ids[1]} --> {and_id}")
    lines.append(f"{b_ids[1]} --> {and_id}")

    if tail_ids:
        lines.append(f"{and_id} --> {tail_ids[0]}")
        for i in range(len(tail_ids) - 1):
            lines.append(f"{tail_ids[i]} --> {tail_ids[i+1]}")
    else:
        lines.append(f"{and_id} --> {a_ids[1]}")

    lines.append("")
    role_map: Dict[str, str] = {}
    nid_check = 1
    for s in pre:
        role_map[f"N{nid_check}"] = s["role"]
        nid_check += 1
    role_map[f"N{nid_check}"] = "yellow"
    nid_check += 1
    for s in a:
        role_map[f"N{nid_check}"] = s["role"]
        nid_check += 1
    for s in b:
        role_map[f"N{nid_check}"] = s["role"]
        nid_check += 1
    role_map[f"N{nid_check}"] = "blue"
    nid_check += 1
    for s in tail:
        role_map[f"N{nid_check}"] = s["role"]
        nid_check += 1

    for node_id, role in role_map.items():
        lines.append(_style_line(node_id, role))

    return "\n".join(lines)


def _get_steps(category: str, pid: str, subcategory: str) -> Optional[List[Step]]:
    cat = category.strip().lower().replace("-", "_")
    if cat == "chemistry":
        return CHEMISTRY_TEMPLATES.get(pid) or CHEMISTRY_SUBCATEGORY_TEMPLATES.get(subcategory)
    if cat == "biology":
        return BIOLOGY_SUBCATEGORY_TEMPLATES.get(subcategory)
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db-dir", required=True, help="e.g. chemistry-processes-database")
    ap.add_argument("--category", required=True, choices=["chemistry", "biology"])
    ap.add_argument("--force", action="store_true")
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
            data: Dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
            pid = str(data.get("id") or path.stem)
            subcat = str(data.get("subcategory") or path.parent.name)
            current_mermaid = (data.get("mermaid") or "").strip()

            if (not args.force) and (not looks_like_generic_template(current_mermaid)):
                skipped_not_generic += 1
                continue

            steps = _get_steps(args.category, pid, subcat)
            if not steps:
                missing_template += 1
                continue

            name = str(data.get("name") or pid)
            new_mermaid = make_mermaid_curated_with_branch(name, steps)
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

            data["notes"] = (str(data.get("notes") or "")).strip() + "\nCurated Mermaid applied (citations preserved)."

            if not args.dry_run:
                path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

            updated += 1
        except Exception:
            errors += 1

    print(
        json.dumps(
            {
                "db_dir": str(db_dir),
                "category": args.category,
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

