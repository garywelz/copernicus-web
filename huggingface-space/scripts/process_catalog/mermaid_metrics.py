"""Derive table metrics from Mermaid source."""

from __future__ import annotations

import re
from typing import Any


def analyze_mermaid(mermaid: str) -> dict[str, Any]:
    if not mermaid:
        return {
            "nodes": 0,
            "edges": 0,
            "conditionals": 0,
            "andGates": 0,
            "orGates": 0,
            "notGates": 0,
            "loops": 0,
            "level": "low",
        }

    node_ids = set(re.findall(r"\b([A-Za-z][A-Za-z0-9_]*)\s*[\[\(\{]", mermaid))
    edge_pattern = r"([A-Za-z][A-Za-z0-9_]*)\s*-->"
    edges = re.findall(edge_pattern, mermaid)
    edge_count = len(edges)

    incoming: dict[str, int] = {}
    outgoing: dict[str, int] = {}
    for source, target in re.findall(
        r"([A-Za-z][A-Za-z0-9_]*)\s*-->\s*(?:\|[^|]+\|\s*)?([A-Za-z][A-Za-z0-9_]*)",
        mermaid,
    ):
        outgoing[source] = outgoing.get(source, 0) + 1
        incoming[target] = incoming.get(target, 0) + 1

    conditionals = len(re.findall(r"\{[^}]+\}", mermaid))
    and_gates = sum(1 for count in incoming.values() if count >= 2)
    or_gates = sum(
        1
        for node in outgoing
        if incoming.get(node, 0) == 1 and outgoing[node] >= 2
    )
    loops = len(re.findall(r"-->\s*\|[^|]*(?:loop|repeat|again|back)[^|]*\|", mermaid, re.I))

    nodes = len(node_ids) or max(edge_count, 1)
    level = "low"
    if nodes >= 12 or edge_count >= 14:
        level = "high"
    elif nodes >= 7 or edge_count >= 8:
        level = "medium"

    return {
        "nodes": nodes,
        "edges": edge_count,
        "conditionals": conditionals,
        "andGates": and_gates,
        "orGates": or_gates,
        "notGates": 0,
        "loops": loops,
        "level": level,
    }


def index_row_from_process(doc: dict[str, Any]) -> dict[str, Any]:
    metrics = analyze_mermaid(doc.get("mermaid", ""))
    complexity = doc.get("complexity") or {}
    if isinstance(complexity, dict):
        for key in ("nodes", "edges", "conditionals", "loops", "andGates", "orGates", "notGates"):
            value = complexity.get(key)
            # A zero in curated complexity must not stomp a nonzero count
            # measured from the Mermaid source.
            if value is not None and not (value == 0 and metrics.get(key, 0) > 0):
                metrics[key] = value
        if complexity.get("level"):
            metrics["level"] = complexity["level"]

    process_type = doc.get("processType", "algorithm")
    row = {
        "id": doc["id"],
        "name": doc["name"],
        "processType": process_type,
        "subcategory": doc["subcategory"],
        "subcategory_name": doc.get("subcategory_name") or doc["subcategory"],
        "complexity": metrics["level"],
        "nodes": metrics["nodes"],
        "edges": metrics["edges"],
        "orGates": metrics["orGates"],
        "loops": metrics["loops"],
        "andGates": metrics["andGates"],
        "axioms": complexity.get("axioms", 0) if isinstance(complexity, dict) else 0,
        "definitions": complexity.get("definitions", 0) if isinstance(complexity, dict) else 0,
        "lemmas": complexity.get("lemmas", 0) if isinstance(complexity, dict) else 0,
        "theorems": complexity.get("theorems", 0) if isinstance(complexity, dict) else 0,
        "corollaries": complexity.get("corollaries", 0) if isinstance(complexity, dict) else 0,
        "graphMetrics": {
            "nodes": metrics["nodes"],
            "edges": metrics["edges"],
            "conditionals": metrics["conditionals"],
            "andGates": metrics["andGates"],
            "orGates": metrics["orGates"],
            "notGates": metrics["notGates"],
            "loops": metrics["loops"],
        },
        "metricSource": "mermaid",
        "graphType": doc.get("graphType", "flowchart"),
        "domainContext": doc.get("subcategory_name") or doc["subcategory"],
        "category": doc.get("subcategory_name") or doc["subcategory"],
        "conditionals": metrics["conditionals"],
        "notGates": metrics["notGates"],
        "totalGates": metrics["andGates"] + metrics["orGates"] + metrics["notGates"],
    }
    # Table-viewer columns: proof-graph link/counts and named collections.
    # Only carried when present on the canonical document.
    for key in (
        "proofGraphHtml",
        "algorithm_capsules",
        "temporary_assumptions",
        "frontier",
        "namedCollections",
    ):
        if doc.get(key) is not None:
            row[key] = doc[key]
    return row
