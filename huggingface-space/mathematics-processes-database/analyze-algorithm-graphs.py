#!/usr/bin/env python3
"""
Analyze algorithm flowcharts (Mermaid) to compute:
- OR gates: nodes with 2+ outgoing edges (decision/branch points)
- Loops: back-edges (edges that close a cycle)
- AND gates: merge nodes (2+ incoming) that are NOT loop heads AND NOT OR-merges.
  OR-merge = join after exclusive branch (all predecessors are direct successors of same decision).
  AND gate = fork-join where multiple paths must all complete (parallel sync).

For axiomatic theories: parse Process Statistics from HTML (Axioms, Definitions, Lemmas,
Theorems, Corollaries) and write to metadata.

Run from mathematics-processes-database directory:
  python3 analyze-algorithm-graphs.py
"""

import json
import re
from pathlib import Path
from collections import defaultdict

DB_DIR = Path(__file__).parent
PROCESSES_DIR = DB_DIR / "processes"
METADATA_PATH = DB_DIR / "metadata.json"


def extract_mermaid_from_html(html_path: Path) -> str | None:
    """Extract Mermaid graph definition from HTML file."""
    content = html_path.read_text(encoding="utf-8")
    # Match content inside <div class="mermaid"> ... </div>
    match = re.search(r'<div\s+class="mermaid">\s*(.*?)\s*</div>', content, re.DOTALL)
    if not match:
        return None
    return match.group(1).strip()


def parse_mermaid_edges(mermaid: str) -> tuple[list[tuple[str, str]], dict[str, str], int]:
    """Parse Mermaid graph. Returns (edges, node_shapes, sequential_and_count)."""
    edges = []
    node_shapes = {}
    sequential_and_count = 0
    node_def_pattern = re.compile(r'(\w+)(\[[^\]]*\])|(\w+)(\{[^\}]*\})')
    # Capture edge label: -->|label| or -->
    edge_pattern = re.compile(
        r'(\w+)(?:\[[^\]]*\]|\{[^\}]*\})?\s*-->\s*(?:\|([^|]*)\|)?\s*(\w+)(?:\[[^\]]*\]|\{[^\}]*\})?'
    )
    for line in mermaid.split("\n"):
        line = line.strip()
        if not line or line.startswith("graph") or line.startswith("classDef") or line.startswith("class "):
            continue
        for m in node_def_pattern.finditer(line):
            if m.group(2):
                node_shapes[m.group(1)] = "rect"
            elif m.group(4):
                node_shapes[m.group(3)] = "diamond"
        for m in edge_pattern.finditer(line):
            edges.append((m.group(1), m.group(3)))
            if m.group(2) and "sequential AND" in m.group(2):
                sequential_and_count += 1
    return edges, node_shapes, sequential_and_count


def analyze_graph(edges: list[tuple[str, str]], node_shapes: dict[str, str] | None = None, sequential_and_count: int = 0) -> dict:
    """
    Analyze graph for OR gates, loops (back-edges), and true AND gates.
    Returns {orGates, loops, andGates}.
    """
    if not edges:
        return {"nodes": 0, "edges": 0, "orGates": 0, "loops": 0, "andGates": 0}

    # Build adjacency: node -> list of successors
    out_edges = defaultdict(list)
    in_edges = defaultdict(list)
    for u, v in edges:
        out_edges[u].append(v)
        in_edges[v].append(u)

    all_nodes = set(out_edges.keys()) | set(in_edges.keys())

    # DFS to find back-edges
    # Back-edge: (u, v) where v is ancestor of u
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in all_nodes}
    back_edges = []

    def dfs(u, stack):
        color[u] = GRAY
        stack.append(u)
        for v in out_edges[u]:
            if color[v] == WHITE:
                dfs(v, stack)
            elif color[v] == GRAY:
                back_edges.append((u, v))
        stack.pop()
        color[u] = BLACK

    for node in all_nodes:
        if color[node] == WHITE:
            dfs(node, [])

    loop_heads = {v for _, v in back_edges}

    # OR gates: 2+ outgoing
    or_gates = sum(1 for n in all_nodes if len(out_edges[n]) >= 2)

    # AND gates: merge (2+ incoming), not loop head, and NOT OR-merge.
    # OR-merge = join after exclusive branch (decision); common predecessor is a diamond.
    # Parallel AND = join after fork; common predecessor is a rectangle (both paths taken).
    node_shapes = node_shapes or {}

    def is_or_merge(node: str) -> bool:
        preds = in_edges[node]
        if len(preds) < 2:
            return False
        # Merge with 3+ incoming: typically OR-merge (switch/case join), not parallel AND
        if len(preds) >= 3:
            return True
        # Merge with 2 incoming, both from diamonds: OR-merge (join of exclusive branches)
        if len(preds) == 2 and all(node_shapes.get(p) == "diamond" for p in preds):
            return True
        for x in all_nodes:
            if all(p in out_edges[x] for p in preds):
                # X feeds all predecessors. If X is a decision (diamond), it's OR-merge.
                # If X is a rectangle (fork), it's parallel AND — don't exclude.
                if node_shapes.get(x) == "diamond":
                    return True
        return False

    structural_and = sum(
        1 for n in all_nodes
        if len(in_edges[n]) >= 2 and n not in loop_heads and not is_or_merge(n)
    )
    and_gates = structural_and + sequential_and_count

    return {
        "nodes": len(all_nodes),
        "edges": len(edges),
        "orGates": or_gates,
        "loops": len(back_edges),
        "andGates": and_gates,
    }


def extract_axiomatic_stats_from_html(html_path: Path) -> dict | None:
    """
    Extract Axioms, Definitions, Lemmas, Theorems, Corollaries from Process Statistics
    in axiomatic theory HTML. Returns dict or None if not found.
    """
    content = html_path.read_text(encoding="utf-8")
    result = {}
    for key in ("Axioms", "Definitions", "Lemmas", "Theorems", "Corollaries"):
        # Match <li><strong>Axioms:</strong> 3</li> (or Axioms: 0)
        m = re.search(
            rf'<li><strong>{key}:</strong>\s*(\d+)</li>',
            content,
            re.IGNORECASE
        )
        if m:
            result[key.lower()] = int(m.group(1))
    return result if result else None


# Map Mermaid class names to our stat keys (Euclid uses postulate, commonnotion, proposition)
# Use lowercase for case-insensitive matching (e.g. commonNotion -> commonnotion)
# Common notions and postulates both count as axioms.
CLASS_TO_STAT = {
    "axiom": "axioms",
    "postulate": "axioms",      # Euclid postulates
    "commonnotion": "axioms",   # Euclid common notions
    "definition": "definitions",
    "lemma": "lemmas",
    "theorem": "theorems",
    "proposition": "theorems",  # Euclid propositions = theorems
    "corollary": "corollaries",
}


def _class_to_stat(class_name: str) -> str | None:
    """Resolve class name to stat key (case-insensitive)."""
    return CLASS_TO_STAT.get(class_name.lower()) if class_name else None


def extract_axiomatic_node_ids_from_mermaid(mermaid: str) -> dict[str, set[str]] | None:
    """
    Extract node IDs per stat type from Mermaid class lines.
    Returns dict of stat_key -> set of node_ids for deduplication when aggregating.
    E.g. "class P1,P2,P3,P4,P5 postulate" -> axioms: {P1,P2,P3,P4,P5}
    """
    result: dict[str, set[str]] = defaultdict(set)
    for line in mermaid.split("\n"):
        line = line.strip()
        if line.startswith("class ") and not line.startswith("classDef"):
            rest = line[6:].strip()  # after "class "
            parts = rest.split(None, 1)
            if len(parts) == 2:
                node_part, class_name = parts
                key = _class_to_stat(class_name)
                if key:
                    for nid in (x.strip() for x in node_part.split(",") if x.strip()):
                        result[key].add(nid)
    return dict(result) if result else None


def extract_axiomatic_stats_from_mermaid(mermaid: str) -> dict | None:
    """
    Fallback: count nodes per class from Mermaid class lines.
    E.g. "class G1,G2,G3,G4 axiom" -> axioms=4.
    Supports: axiom, postulate, commonnotion, definition, lemma, theorem, proposition, corollary.
    """
    ids_map = extract_axiomatic_node_ids_from_mermaid(mermaid)
    if not ids_map:
        return None
    return {k: len(v) for k, v in ids_map.items()}


def update_html_process_stats(html_path: Path, result: dict) -> None:
    """Update Process Statistics section in algorithm HTML to match analysis."""
    content = html_path.read_text(encoding="utf-8")
    # Match entire stats block (Nodes, Edges, and any of OR/AND gates, Loops)
    # to avoid duplicates when re-running on already-updated files
    stats_pattern = re.compile(
        r'(<li><strong>(?:Nodes|Edges|OR gates|AND gates|Loops|True AND):</strong> \d+</li>\s*)+',
        re.DOTALL
    )  # matches both "True AND" and "AND gates" for backwards compatibility
    new_block = (
        f'<li><strong>Nodes:</strong> {result["nodes"]}</li>\n                        '
        f'<li><strong>Edges:</strong> {result["edges"]}</li>\n                        '
        f'<li><strong>OR gates:</strong> {result["orGates"]}</li>\n                        '
        f'<li><strong>Loops:</strong> {result["loops"]}</li>\n                        '
        f'<li><strong>AND gates:</strong> {result["andGates"]}</li>\n                        '
    )
    new_content, n = stats_pattern.subn(new_block, content, count=1)
    if n > 0:
        html_path.write_text(new_content, encoding="utf-8")
    elif "True AND" in content:
        # Fallback: replace any remaining "True AND" with "AND gates" (e.g. non-matching formats)
        html_path.write_text(content.replace("True AND:", "AND gates:"), encoding="utf-8")


def main():
    with open(METADATA_PATH, encoding="utf-8") as f:
        metadata = json.load(f)

    processes = metadata["processes"]
    algorithm_ids = {p["id"] for p in processes if p.get("processType") == "algorithm"}

    total_or = 0
    total_loops = 0
    total_and = 0

    for proc in processes:
        pid = proc["id"]
        if proc.get("processType") != "algorithm":
            proc["orGates"] = 0
            proc["loops"] = 0
            proc["andGates"] = 0
            proc.pop("trueAndGates", None)
            proc.pop("totalGates", None)
            # Parse axiomatic theory stats from HTML, fallback to Mermaid, then aggregate from children
            subcat = proc["subcategory"]
            html_path = PROCESSES_DIR / subcat / f"{pid}.html"
            stats = None
            if html_path.exists():
                stats = extract_axiomatic_stats_from_html(html_path)
                if not stats:
                    mermaid = extract_mermaid_from_html(html_path)
                    if mermaid:
                        stats = extract_axiomatic_stats_from_mermaid(mermaid)
            # Index pages: aggregate from child HTML files (e.g. group-theory from *-axioms-foundations.html)
            # Use node-ID deduplication when children have Mermaid (same axiom/theorem can appear on multiple pages)
            if not stats:
                subcat_dir = PROCESSES_DIR / subcat
                merged_ids: dict[str, set[str]] = defaultdict(set)
                child_counts: list[dict] = []
                if subcat_dir.exists():
                    child_files = sorted(subcat_dir.glob(f"{pid}-*.html"))
                    for child_file in child_files:
                        m = extract_mermaid_from_html(child_file)
                        if m:
                            ids_map = extract_axiomatic_node_ids_from_mermaid(m)
                            if ids_map:
                                for k, v in ids_map.items():
                                    merged_ids[k].update(v)
                                continue
                        cs = extract_axiomatic_stats_from_html(child_file)
                        if cs:
                            child_counts.append(cs)
                if merged_ids:
                    stats = {}
                    for k in ("axioms", "definitions", "lemmas", "theorems", "corollaries"):
                        if k in merged_ids:
                            stats[k] = len(merged_ids[k])
                elif child_counts:
                    stats = {}
                    for key in ("axioms", "definitions", "lemmas", "theorems", "corollaries"):
                        stats[key] = sum(c.get(key, 0) or 0 for c in child_counts)
            if stats:
                for key in ("axioms", "definitions", "lemmas", "theorems", "corollaries"):
                    proc[key] = stats.get(key, 0) or 0
                print(f"  {proc['name']}: axioms={proc['axioms']}, defs={proc['definitions']}, lemmas={proc['lemmas']}, thms={proc['theorems']}, cors={proc['corollaries']}")
            continue

        subcat = proc["subcategory"]
        html_path = PROCESSES_DIR / subcat / f"{pid}.html"

        if not html_path.exists():
            print(f"  Warning: {html_path} not found")
            proc["orGates"] = proc.get("orGates", 0)
            proc["loops"] = 0
            proc["andGates"] = 0
            proc.pop("trueAndGates", None)
            proc.pop("totalGates", None)
            continue

        mermaid = extract_mermaid_from_html(html_path)
        if not mermaid:
            print(f"  Warning: No Mermaid in {html_path}")
            proc["orGates"] = proc.get("orGates", 0)
            proc["loops"] = 0
            proc["andGates"] = 0
            proc.pop("trueAndGates", None)
            proc.pop("totalGates", None)
            continue

        edges, node_shapes, sequential_and_count = parse_mermaid_edges(mermaid)
        result = analyze_graph(edges, node_shapes, sequential_and_count)

        proc["nodes"] = result["nodes"]
        proc["edges"] = result["edges"]
        proc["orGates"] = result["orGates"]
        proc["loops"] = result["loops"]
        proc["andGates"] = result["andGates"]
        update_html_process_stats(html_path, result)
        proc.pop("trueAndGates", None)
        proc.pop("totalGates", None)

        total_or += result["orGates"]
        total_loops += result["loops"]
        total_and += result["andGates"]

        print(f"  {proc['name']}: OR={result['orGates']}, Loops={result['loops']}, AND={result['andGates']}")

    # Update global statistics for algorithms
    stats = metadata.get("statistics", {})
    stats["totalOrGates"] = total_or
    stats["totalLoops"] = total_loops
    stats["totalAndGates"] = total_and
    stats.pop("totalTrueAndGates", None)
    stats.pop("totalGates", None)
    metadata["statistics"] = stats

    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nUpdated {METADATA_PATH}")
    print(f"Totals: OR gates={total_or}, Loops={total_loops}, AND gates={total_and}")


if __name__ == "__main__":
    main()
