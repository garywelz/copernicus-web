#!/usr/bin/env python3
"""
Normalize process graph metadata into a GLMP-style shape.

This module is intentionally non-destructive: it reads source metadata and
per-process JSON files, then returns enriched process records for generated
artifacts such as process-index.json.
"""

from __future__ import annotations

import argparse
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


BASE_DIR = Path(__file__).resolve().parents[3]
GENERATOR_DIR = Path(__file__).resolve().parent
PROFILE_FILE = GENERATOR_DIR / "discipline_profiles.json"

GRAPH_METRIC_KEYS = (
    "nodes",
    "edges",
    "conditionals",
    "andGates",
    "orGates",
    "notGates",
    "loops",
)

GRAPH_TYPE_DEFAULT = "flowchart"
GRAPH_TYPE_PREFIXES = (
    "taxonomy",
    "lineage_tree",
    "influence_network",
    "state_transition",
    "timeline",
    "dependency_graph",
)


def read_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def number(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value.strip()))
        except ValueError:
            return 0
    return 0


def first_number(*values: Any) -> Tuple[int, bool]:
    for value in values:
        if value is None:
            continue
        return number(value), True
    return 0, False


def get_path(data: Dict[str, Any], path: Iterable[str]) -> Any:
    current: Any = data
    for part in path:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def count_mermaid_edges(mermaid: str) -> int:
    if not mermaid:
        return 0
    return sum(1 for line in mermaid.splitlines() if "-->" in line or "---" in line)


def count_mermaid_nodes(mermaid: str) -> int:
    if not mermaid:
        return 0
    identifiers = set()
    for match in re.finditer(r"(?:^|\s)([A-Za-z][A-Za-z0-9_]*)\s*(?:\[|\{|\()", mermaid):
        identifiers.add(match.group(1))
    return len(identifiers)


def infer_from_mermaid(data: Dict[str, Any]) -> Tuple[Dict[str, int], bool]:
    mermaid = str(data.get("mermaid") or data.get("diagram") or "")
    metrics = {key: 0 for key in GRAPH_METRIC_KEYS}
    if not mermaid:
        return metrics, False

    metrics["nodes"] = count_mermaid_nodes(mermaid)
    metrics["edges"] = count_mermaid_edges(mermaid)
    metrics["conditionals"] = len(re.findall(r"\{[^}]+\}", mermaid))
    metrics["notGates"] = len(re.findall(r"\b(?:NOT|No|Inhibit|Repress|Block)\b", mermaid, flags=re.I))
    metrics["loops"] = len(re.findall(r"\b(?:loop|feedback|return|cycle)\b", mermaid, flags=re.I))
    return metrics, any(metrics.values())


def normalize_graph_metrics(process: Dict[str, Any], detail: Dict[str, Any] | None = None) -> Tuple[Dict[str, int], str]:
    merged = {}
    if detail:
        merged.update(detail)
    merged.update(process)
    complexity = merged.get("complexity") if isinstance(merged.get("complexity"), dict) else {}
    logic_gates = merged.get("logicGates") if isinstance(merged.get("logicGates"), dict) else {}
    complexity_logic = complexity.get("logicGates") if isinstance(complexity.get("logicGates"), dict) else {}
    graph_metrics = merged.get("graphMetrics") if isinstance(merged.get("graphMetrics"), dict) else {}

    direct_values = {
        "nodes": first_number(graph_metrics.get("nodes"), merged.get("nodes"), merged.get("totalNodes"), complexity.get("nodes")),
        "edges": first_number(graph_metrics.get("edges"), merged.get("edges"), merged.get("totalEdges"), complexity.get("edges")),
        "conditionals": first_number(graph_metrics.get("conditionals"), merged.get("conditionals"), merged.get("totalConditionals"), complexity.get("conditionals")),
        "andGates": first_number(graph_metrics.get("andGates"), merged.get("andGates"), merged.get("totalAndGates"), logic_gates.get("andGates"), logic_gates.get("and"), complexity_logic.get("andGates"), complexity_logic.get("and")),
        "orGates": first_number(graph_metrics.get("orGates"), merged.get("orGates"), merged.get("totalOrGates"), logic_gates.get("orGates"), logic_gates.get("or"), complexity_logic.get("orGates"), complexity_logic.get("or")),
        "notGates": first_number(graph_metrics.get("notGates"), merged.get("notGates"), merged.get("totalNotGates"), logic_gates.get("notGates"), logic_gates.get("not"), complexity_logic.get("notGates"), complexity_logic.get("not")),
        "loops": first_number(graph_metrics.get("loops"), merged.get("loops"), merged.get("totalLoops"), complexity.get("loops")),
    }
    metrics = {key: value for key, (value, _present) in direct_values.items()}
    has_direct = any(present for _value, present in direct_values.values())

    inferred, has_inferred = infer_from_mermaid(merged)
    for key in GRAPH_METRIC_KEYS:
        if not direct_values[key][1] and inferred[key]:
            metrics[key] = inferred[key]

    return metrics, "metadata" if has_direct else ("inferred" if has_inferred else "missing")


def normalize_graph_type(data: Dict[str, Any]) -> str:
    graph_type = str(data.get("graphType") or data.get("graph_type") or "").strip()
    if graph_type:
        return graph_type
    process_id = str(data.get("id") or "")
    subcategory = str(data.get("subcategory") or "")
    for prefix in GRAPH_TYPE_PREFIXES:
        if process_id.startswith(prefix + "-") or subcategory == prefix:
            return prefix
    return GRAPH_TYPE_DEFAULT


def normalize_complexity(data: Dict[str, Any]) -> str:
    complexity = data.get("complexity")
    if isinstance(complexity, str):
        return complexity
    if isinstance(complexity, dict):
        if complexity.get("level"):
            return str(complexity["level"])
        nodes = number(complexity.get("nodes") or data.get("nodes") or data.get("totalNodes"))
    else:
        nodes = number(data.get("nodes") or data.get("totalNodes"))
    if nodes >= 30:
        return "high"
    if nodes >= 12:
        return "medium"
    if nodes > 0:
        return "low"
    return ""


def derive_domain_context(process: Dict[str, Any], detail: Dict[str, Any] | None, profile: Dict[str, Any]) -> str:
    merged = {}
    if detail:
        merged.update(detail)
    merged.update(process)
    for key in ("domainContext", "organism", "materialSystem", "system", "regime", "dataType", "domain", "structure"):
        value = merged.get(key)
        if value:
            return str(value)
    for key in ("subcategory_name", "subcategory", "category"):
        value = merged.get(key)
        if value:
            return str(value).replace("_", " ").title()
    return str(profile.get("defaultContext") or "")


def load_process_details(database_dir: Path) -> Dict[str, Dict[str, Any]]:
    details: Dict[str, Dict[str, Any]] = {}
    processes_dir = database_dir / "processes"
    if not processes_dir.exists():
        return details
    for path in processes_dir.rglob("*.json"):
        try:
            data = read_json(path)
        except Exception:
            continue
        data["_sourceJsonPath"] = str(path.relative_to(database_dir))
        key = str(data.get("id") or path.stem)
        details[key] = data
        details[path.stem] = data
    return details


def merge_process(process: Dict[str, Any], detail: Dict[str, Any] | None, profile: Dict[str, Any]) -> Dict[str, Any]:
    output = deepcopy(process)
    if detail:
        for key in ("description", "keywords", "mermaid", "graphType", "domainContext", "organism", "_sourceJsonPath"):
            if key in detail and key not in output:
                output[key] = detail[key]
    metrics, source = normalize_graph_metrics(output, detail)
    output["graphMetrics"] = metrics
    output["metricSource"] = source
    output["graphType"] = normalize_graph_type(output if "graphType" in output else (detail or output))
    output["domainContext"] = derive_domain_context(output, detail, profile)
    output["complexity"] = normalize_complexity(output)
    output["category"] = output.get("category") or output.get("subcategory_name") or output.get("subcategory") or profile.get("displayName")
    for key, value in metrics.items():
        output[key] = value
    output["totalGates"] = metrics["andGates"] + metrics["orGates"] + metrics["notGates"]
    return output


def supplemental_process_from_detail(detail: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
    process_id = str(detail.get("id") or Path(detail.get("_sourceJsonPath", "process")).stem)
    source_path = str(detail.get("_sourceJsonPath") or "")
    subcategory = detail.get("subcategory")
    if not subcategory and "/" in source_path:
        subcategory = source_path.split("/", 1)[0]
    return {
        "id": process_id,
        "name": detail.get("name") or process_id.replace("-", " ").replace("_", " ").title(),
        "subcategory": subcategory or "graph_type_pilots",
        "subcategory_name": str(subcategory or "Graph Type Pilots").replace("_", " ").title(),
        "complexity": detail.get("complexity", ""),
        "category": detail.get("category") or detail.get("subcategory_name") or "Graph Type Pilot",
        "namedCollections": detail.get("namedCollections") or detail.get("collections") or ["graph-type-pilots"],
    }


def build_process_index(database_dir: Path, profile: Dict[str, Any]) -> Dict[str, Any]:
    metadata = read_json(database_dir / "metadata.json")
    details = load_process_details(database_dir)
    processes: List[Dict[str, Any]] = []
    seen = set()
    for process in metadata.get("processes") or []:
        process_id = str(process.get("id") or "")
        detail = details.get(process_id) or details.get(process_id.split("/")[-1])
        processes.append(merge_process(process, detail, profile))
        seen.add(process_id)

    for key, detail in details.items():
        process_id = str(detail.get("id") or key)
        if process_id in seen:
            continue
        processes.append(merge_process(supplemental_process_from_detail(detail, profile), detail, profile))
        seen.add(process_id)

    stats = deepcopy(metadata.get("statistics") or {})
    for metric_key, stat_key in (
        ("nodes", "totalNodes"),
        ("edges", "totalEdges"),
        ("conditionals", "totalConditionals"),
        ("andGates", "totalAndGates"),
        ("orGates", "totalOrGates"),
        ("notGates", "totalNotGates"),
        ("loops", "totalLoops"),
    ):
        stats[stat_key] = sum(number(p.get("graphMetrics", {}).get(metric_key)) for p in processes)
    stats["totalGates"] = stats["totalAndGates"] + stats["totalOrGates"] + stats["totalNotGates"]

    process_index = deepcopy(metadata)
    process_index["processes"] = processes
    process_index["statistics"] = stats
    process_index["totalProcesses"] = len(processes)
    process_index["normalizedGraphMetrics"] = True
    process_index["generatedFrom"] = "scripts/processes/discipline_databases/normalize_graph_metrics.py"
    return process_index


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate normalized process-index.json files.")
    parser.add_argument("disciplines", nargs="*", default=["biology", "chemistry", "physics", "computer_science"])
    parser.add_argument("--write", action="store_true", help="Write process-index.json files")
    args = parser.parse_args()

    profiles = read_json(PROFILE_FILE)
    for discipline in args.disciplines:
        profile = profiles[discipline]
        database_dir = BASE_DIR / profile["databaseDir"]
        process_index = build_process_index(database_dir, profile)
        if args.write:
            write_json(database_dir / "process-index.json", process_index)
        print(f"{discipline}: {len(process_index.get('processes') or [])} normalized processes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
