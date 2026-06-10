"""Canonical process JSON schema (aligned with chemistry-processes-database)."""

from __future__ import annotations

from datetime import date
from typing import Any

REQUIRED_FIELDS = ("id", "name", "category", "subcategory", "description", "mermaid")

DEFAULT_COLOR_SCHEME = {
    "red": {"hex": "#ff6b6b", "category": "Triggers & Inputs"},
    "yellow": {"hex": "#ffd43b", "category": "Structures & Objects"},
    "green": {"hex": "#51cf66", "category": "Processing & Operations"},
    "blue": {"hex": "#74c0fc", "category": "Intermediates & States"},
    "violet": {"hex": "#b197fc", "category": "Products & Outputs"},
}

SUBCATEGORY_NAMES: dict[str, str] = {
    "abstract_algebra": "Abstract Algebra",
    "algebraic_geometry": "Algebraic Geometry",
    "bioinformatics": "Bioinformatics",
    "calculus_analysis": "Calculus & Analysis",
    "category_theory": "Category Theory",
    "commutative_algebra": "Commutative Algebra",
    "complex_analysis": "Complex Analysis",
    "differential_geometry": "Differential Geometry",
    "discrete_mathematics": "Discrete Mathematics",
    "foundations": "Foundations",
    "functional_analysis": "Functional Analysis",
    "geometry_topology": "Geometry & Topology",
    "graph_type_pilots": "Graph Type Pilots",
    "information_theory": "Information Theory",
    "k_theory": "K-Theory",
    "linear_algebra": "Linear Algebra",
    "mathematical_physics": "Mathematical Physics",
    "metric_geometry": "Metric Geometry",
    "number_theory": "Number Theory",
    "numerical_analysis": "Numerical Analysis",
    "operator_algebras": "Operator Algebras",
    "optimization": "Optimization",
    "partial_differential_equations": "Partial Differential Equations",
    "proof_graphs": "Proof Graphs",
    "quantum_algebra": "Quantum Algebra",
    "representation_theory": "Representation Theory",
    "spectral_theory": "Spectral Theory",
    "statistics_probability": "Statistics & Probability",
    "symplectic_geometry": "Symplectic Geometry",
}


def subcategory_label(subcategory: str) -> str:
    return SUBCATEGORY_NAMES.get(
        subcategory,
        subcategory.replace("_", " ").title(),
    )


def normalize_process(
    doc: dict[str, Any],
    *,
    subcategory: str,
    category: str = "mathematics",
) -> dict[str, Any]:
    """Fill chemistry-aligned defaults on a process document."""
    today = date.today().isoformat()
    pid = doc["id"]
    out = dict(doc)
    out.setdefault("category", category)
    out.setdefault("subcategory", subcategory)
    out.setdefault("subcategory_name", subcategory_label(subcategory))
    out.setdefault("colorScheme", DEFAULT_COLOR_SCHEME)
    out.setdefault("keywords", [])
    out.setdefault("sources", [])
    out.setdefault("relatedProcesses", [])
    out.setdefault("created", today)
    out.setdefault("lastUpdated", today)
    out.setdefault("verified", True)
    out.setdefault("flowchartStandard", "GLMP_6color")
    if "complexity" not in out or not isinstance(out["complexity"], dict):
        out["complexity"] = {"level": "medium", "nodes": 0, "edges": 0, "conditionals": 0}
    if not out.get("processType"):
        out["processType"] = infer_process_type(out)
    return out


def infer_process_type(doc: dict[str, Any]) -> str:
    explicit = doc.get("processType")
    if explicit:
        return explicit
    if doc.get("subcategory") == "proof_graphs" or doc.get("graphType") == "proof_graph":
        return "proof_graph"
    c = doc.get("complexity") or {}
    if any(c.get(k) for k in ("axioms", "definitions", "theorems", "lemmas", "corollaries")):
        return "axiomatic_theory"
    mermaid = (doc.get("mermaid") or "").lower()
    if "axiom" in mermaid or "theorem" in mermaid or "definition" in mermaid:
        return "axiomatic_theory"
    return "algorithm"


def validate_process(doc: dict[str, Any]) -> list[str]:
    errors = []
    for field in REQUIRED_FIELDS:
        if not doc.get(field):
            errors.append(f"missing {field}")
    if doc.get("mermaid") and len(doc["mermaid"]) < 20:
        errors.append("mermaid too short")
    return errors
