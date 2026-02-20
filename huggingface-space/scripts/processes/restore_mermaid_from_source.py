#!/usr/bin/env python3
"""
Restore previously-generated Mermaid flowcharts after an accidental overwrite.

Goal:
- Keep current JSONs (including citations/sources) intact
- Replace ONLY the `mermaid` field from a rollback source (either local *.backup files
  or a parallel "source root" tree like `programming-framework/.../processes`)
- Recompute `complexity.nodes`, `complexity.edges`, and `complexity.logicGates` from Mermaid

Examples:
  # Computer science: restore from programming-framework copy
  python3 scripts/processes/restore_mermaid_from_source.py \
    --db-dir computer-science-processes-database \
    --source-root programming-framework/computer-science-processes-database/processes

  # Chemistry: restore from adjacent *.json.backup files
  python3 scripts/processes/restore_mermaid_from_source.py --db-dir chemistry-processes-database --use-backup
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def parse_mermaid(mermaid_text: str) -> Tuple[Dict[str, str], List[Tuple[str, str]]]:
    """
    Parse Mermaid to extract nodes and edges.
    - nodes: node_id -> node_label
    - edges: list of (source_id, target_id)
    """
    nodes: Dict[str, str] = {}
    edges: List[Tuple[str, str]] = []

    if not mermaid_text:
        return nodes, edges

    # Node definitions: ID[Label] or ID("Label")-style is handled in our generators via ["..."] or [...]
    node_pattern = r'(\w+)\s*[\[(]([^\])]+)[\])]'
    for match in re.finditer(node_pattern, mermaid_text):
        node_id = match.group(1)
        node_label = match.group(2).strip().strip('"')
        nodes[node_id] = node_label

    # Edges: ID1 --> ID2 or ID1 -->|label| ID2
    edge_pattern = r"(\w+)\s*(?:-->|--)\s*(?:\|.*?\|\s*)?(\w+)"
    for match in re.finditer(edge_pattern, mermaid_text):
        edges.append((match.group(1), match.group(2)))

    return nodes, edges


def count_logic_gates(nodes: Dict[str, str], edges: List[Tuple[str, str]]) -> Tuple[int, int]:
    """
    AND node: 2+ incoming, 1 outgoing
    OR node: 1 incoming, 2+ outgoing
    """
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


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db-dir", required=True, help="e.g. chemistry-processes-database")
    ap.add_argument(
        "--source-root",
        help=(
            "Optional root directory that mirrors db_dir/processes structure, e.g. "
            "programming-framework/computer-science-processes-database/processes"
        ),
    )
    ap.add_argument(
        "--use-backup",
        action="store_true",
        help="Prefer adjacent *.json.backup as the Mermaid source when present.",
    )
    ap.add_argument("--dry-run", action="store_true", help="Report changes without writing files.")
    args = ap.parse_args()

    db_dir = Path(args.db_dir)
    processes_dir = db_dir / "processes"
    if not processes_dir.exists():
        raise SystemExit(f"Not found: {processes_dir}")

    source_root = Path(args.source_root) if args.source_root else None
    if source_root is not None and not source_root.exists():
        raise SystemExit(f"Not found: {source_root}")

    updated = 0
    missing_source = 0
    unchanged = 0
    errors = 0

    for target_path in sorted(processes_dir.rglob("*.json")):
        if target_path.name.endswith(".backup"):
            continue

        backup_path = Path(str(target_path) + ".backup")
        source_path: Optional[Path] = None

        if args.use_backup and backup_path.exists():
            source_path = backup_path
        elif source_root is not None:
            rel = target_path.relative_to(processes_dir)
            candidate = source_root / rel
            if candidate.exists():
                source_path = candidate
        elif backup_path.exists():
            # If user didn't specify but backups exist, use them.
            source_path = backup_path

        if source_path is None:
            missing_source += 1
            continue

        try:
            target = load_json(target_path)
            source = load_json(source_path)
            # Support multiple historical schemas:
            # - current HF JSONs: "mermaid"
            # - Firestore sync docs: "mermaid_code"
            # - some legacy GLMP docs: "mermaid_syntax"
            src_mermaid = (
                (source.get("mermaid") or "")
                or (source.get("mermaid_code") or "")
                or (source.get("mermaid_syntax") or "")
            ).strip()
            if not src_mermaid:
                missing_source += 1
                continue

            cur_mermaid = (target.get("mermaid") or "").strip()
            if cur_mermaid == src_mermaid:
                unchanged += 1
                continue

            target["mermaid"] = src_mermaid

            nodes, edges = parse_mermaid(src_mermaid)
            and_count, or_count = count_logic_gates(nodes, edges)

            complexity = target.get("complexity") or {}
            complexity["nodes"] = len(nodes)
            complexity["edges"] = len(edges)
            complexity.setdefault("conditionals", 0)
            lg = complexity.get("logicGates") or {}
            lg["andGates"] = and_count
            lg["orGates"] = or_count
            lg["total"] = and_count + or_count
            complexity["logicGates"] = lg
            target["complexity"] = complexity

            if not args.dry_run:
                write_json(target_path, target)

            updated += 1
        except Exception:
            errors += 1

    print(
        json.dumps(
            {
                "db_dir": str(db_dir),
                "updated": updated,
                "unchanged": unchanged,
                "missing_source": missing_source,
                "errors": errors,
                "dry_run": bool(args.dry_run),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

