"""
Count flowchart loops (back-edges) from Mermaid diagram.

Definition: A back-edge is an edge u→v where v is at an earlier layer than u.
Layers are computed via BFS from source nodes (in-degree 0).
Each back-edge corresponds to one feedback loop in the process flow.
Self-loops (u→u) count as 1 each.
"""

import re
from collections import defaultdict, deque


def parse_mermaid_to_graph(mermaid: str):
    """
    Parse Mermaid flowchart string into directed graph.
    Returns (nodes: set, edges: list of (src, tgt)).
    """
    nodes = set()
    edges = []

    # Remove comments and style lines
    lines = []
    for line in mermaid.split("\n"):
        line = line.strip()
        if not line or line.startswith("%%") or line.startswith("style "):
            continue
        lines.append(line)

    text = " ".join(lines)

    # Mermaid edge patterns (directed: -->, ->, ---, --)
    # Node IDs can be followed by [text], (text), {text} - we capture the id only
    # Edges: id1[foo] --> id2[bar], id1 -->|label| id2
    node_id = r'([A-Za-z0-9_]+)'  # capture id
    node_suffix = r'(?:\[[^\]]*\]|\{[^}]*\}|\([^)]*\)|"[^"]*")?'  # optional []({})""
    edge_pattern = re.compile(
        node_id + node_suffix + r'\s*'
        r'(?:-->|->|--)\s*'
        r'(?:\|[^|]*\|\s*)?'  # optional label
        r'([A-Za-z0-9_]+)' + node_suffix,
        re.IGNORECASE
    )

    # Also handle bracketed node refs: A[foo] --> B[bar] - we use the leading id (A, B)
    # Simpler: match ID --> ID where ID is alphanumeric + underscore, or in quotes
    for m in edge_pattern.finditer(text):
        src = m.group(1).strip('"').strip()
        tgt = m.group(2).strip('"').strip()
        nodes.add(src)
        nodes.add(tgt)
        edges.append((src, tgt))

    # Fallback: look for --> or -> patterns with node-like tokens
    if not edges:
        # Try splitting by arrows and extracting adjacent identifiers
        parts = re.split(r'\s*-->\s*|\s*->\s*|\s*--\s*', text)
        # Extract node ids from parts (before [ or { or ( or end)
        def extract_id(s):
            s = s.strip()
            m = re.match(r'^([A-Za-z0-9_]+)', s)
            return m.group(1) if m else None
        ids = [extract_id(p) for p in parts if extract_id(p)]
        for i in range(len(ids) - 1):
            if ids[i] and ids[i + 1]:
                nodes.add(ids[i])
                nodes.add(ids[i + 1])
                edges.append((ids[i], ids[i + 1]))

    return nodes, edges


def compute_layers(nodes, edges):
    """
    BFS from source nodes (in-degree 0). layer[v] = distance from nearest source.
    For nodes unreachable from any source (cycles with no entry), assign layers
    via BFS from the node with smallest id in that component.
    """
    in_deg = defaultdict(int)
    out_adj = defaultdict(list)
    for u, v in edges:
        out_adj[u].append(v)
        in_deg[v] += 1
    for n in nodes:
        in_deg.setdefault(n, 0)

    layer = {}
    sources = [n for n in nodes if in_deg[n] == 0]

    if sources:
        q = deque((s, 0) for s in sources)
        while q:
            u, d = q.popleft()
            if u in layer:
                continue
            layer[u] = d
            for v in out_adj[u]:
                if v not in layer:
                    q.append((v, d + 1))

    # Handle unreachable nodes (in cycles with no source)
    unreachable = [n for n in nodes if n not in layer]
    while unreachable:
        # Pick smallest id as pseudo-source for this component
        start = min(unreachable)
        q = deque([(start, 0)])
        comp = set()
        while q:
            u, d = q.popleft()
            if u in layer:
                continue
            layer[u] = d
            comp.add(u)
            for v in out_adj[u]:
                if v not in layer:
                    q.append((v, d + 1))
            for u2, v2 in edges:
                if v2 == u and u2 not in layer:
                    q.append((u2, d + 1))
        unreachable = [n for n in nodes if n not in layer]

    return layer


def count_back_edges(nodes, edges, layer):
    """Count edges (u,v) where layer[u] > layer[v]. Self-loops count as 1 each."""
    count = 0
    for u, v in edges:
        if u == v:
            count += 1
        elif u in layer and v in layer and layer[u] > layer[v]:
            count += 1
    return count


def count_flowchart_loops(mermaid: str) -> int:
    """
    Count flowchart loops (back-edges) in a Mermaid diagram.
    Returns 0 for empty/invalid input.
    """
    if not mermaid or not mermaid.strip():
        return 0
    try:
        nodes, edges = parse_mermaid_to_graph(mermaid)
        if not nodes or not edges:
            return 0
        layer = compute_layers(nodes, edges)
        return count_back_edges(nodes, edges, layer)
    except Exception:
        return 0


if __name__ == "__main__":
    # Quick test
    test = """
    graph TD
    A[Start] --> B[Step1]
    B --> C[Step2]
    C --> D[Step3]
    D --> B
    """
    print("Test (D->B is back-edge):", count_flowchart_loops(test))  # expect 1

    test2 = """
    graph TD
    A --> B
    B --> C
    C --> A
    """
    print("Test (C->A back-edge):", count_flowchart_loops(test2))  # expect 1
