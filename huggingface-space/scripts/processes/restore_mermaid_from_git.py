#!/usr/bin/env python3
"""
Restore Mermaid flowcharts from a previous git revision while keeping current citations.

Why:
- If process JSONs were overwritten in the workspace (e.g., generic template Mermaid),
  but the "good" graphs existed earlier today, they often still exist in git history
  (commit history or reflog).

What it does:
- For each JSON in <db-dir>/processes/**.json (excluding *.backup):
  - Reads CURRENT JSON (keeps its `sources` etc.)
  - Reads OLD JSON from git at --ref for the same path
  - Copies ONLY the old `mermaid` into the current JSON
  - Recomputes complexity: nodes/edges/logicGates from the restored Mermaid

Safety:
- Default: only restore files whose current Mermaid "looks like" the generic template.

Usage:
  # 1) Find a candidate ref (examples):
  #    git log --oneline -n 20
  #    git reflog -n 20
  #
  # 2) Restore CS Mermaid from a ref:
  python3 scripts/processes/restore_mermaid_from_git.py \
    --db-dir computer-science-processes-database \
    --ref HEAD@{1}
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _find_repo_root(start: Path) -> Path:
    p = start.resolve()
    for _ in range(12):
        if (p / ".git").exists():
            return p
        if p.parent == p:
            break
        p = p.parent
    raise SystemExit("Could not find git repo root (no .git found above).")


def _git_show_json(repo_root: Path, ref: str, rel_path: str) -> Optional[Dict[str, Any]]:
    try:
        res = subprocess.run(
            ["git", "show", f"{ref}:{rel_path}"],
            cwd=str(repo_root),
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(res.stdout)
    except Exception:
        return None


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


def looks_like_generic_template(mermaid_text: str) -> bool:
    """
    Heuristic: the template generator uses these labels almost verbatim.
    """
    if not mermaid_text:
        return False
    needles = ["Inputs", "Method Selection", "Option A", "Option B", "Option C", "Step 1", "Step 2", "Step 3"]
    return sum(1 for n in needles if n in mermaid_text) >= 6


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db-dir", required=True, help="e.g. computer-science-processes-database")
    ap.add_argument("--ref", required=True, help="git ref, e.g. HEAD@{1} or <commit-sha>")
    ap.add_argument(
        "--force",
        action="store_true",
        help="Restore even if current Mermaid does not look generic.",
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    db_dir = Path(args.db_dir)
    processes_dir = db_dir / "processes"
    if not processes_dir.exists():
        raise SystemExit(f"Not found: {processes_dir}")

    repo_root = _find_repo_root(db_dir)

    updated = 0
    skipped_not_generic = 0
    missing_in_git = 0
    missing_mermaid_in_git = 0
    errors = 0

    for target_path in sorted(processes_dir.rglob("*.json")):
        if target_path.name.endswith(".backup"):
            continue

        try:
            cur = json.loads(target_path.read_text(encoding="utf-8"))
            cur_mermaid = (cur.get("mermaid") or "").strip()
            if (not args.force) and (not looks_like_generic_template(cur_mermaid)):
                skipped_not_generic += 1
                continue

            rel_path = str(target_path.resolve().relative_to(repo_root))
            old = _git_show_json(repo_root, args.ref, rel_path)
            if not old:
                missing_in_git += 1
                continue

            old_mermaid = (old.get("mermaid") or "").strip()
            if not old_mermaid:
                missing_mermaid_in_git += 1
                continue

            if cur_mermaid == old_mermaid:
                continue

            cur["mermaid"] = old_mermaid

            nodes, edges = parse_mermaid(old_mermaid)
            and_count, or_count = count_logic_gates(nodes, edges)
            complexity = cur.get("complexity") or {}
            complexity["nodes"] = len(nodes)
            complexity["edges"] = len(edges)
            complexity.setdefault("conditionals", 0)
            lg = complexity.get("logicGates") or {}
            lg["andGates"] = and_count
            lg["orGates"] = or_count
            lg["total"] = and_count + or_count
            complexity["logicGates"] = lg
            cur["complexity"] = complexity

            if not args.dry_run:
                target_path.write_text(json.dumps(cur, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

            updated += 1
        except Exception:
            errors += 1

    print(
        json.dumps(
            {
                "db_dir": str(db_dir),
                "ref": args.ref,
                "updated": updated,
                "skipped_not_generic": skipped_not_generic,
                "missing_in_git": missing_in_git,
                "missing_mermaid_in_git": missing_mermaid_in_git,
                "errors": errors,
                "dry_run": bool(args.dry_run),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

