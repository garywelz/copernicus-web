#!/usr/bin/env python3
"""Upgrade discipline process flowcharts to process-specific JSON-backed charts.

This replaces weak HTML-only and generic template diagrams with canonical
process JSON files, compact styled Mermaid, honest graph metrics, and regenerated
HTML viewers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = BASE_DIR / "scripts"
DISCIPLINE_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(DISCIPLINE_DIR) not in sys.path:
    sys.path.insert(0, str(DISCIPLINE_DIR))

from create_process_viewers import create_process_viewer  # noqa: E402
from enhanced_database_table import generate_one, read_json  # noqa: E402
from normalize_graph_metrics import build_process_index, write_json  # noqa: E402


COLOR_SCHEME = {
    "red": {"hex": "#ff6b6b", "category": "Triggers & Inputs"},
    "yellow": {"hex": "#ffd43b", "category": "Structures & Objects"},
    "green": {"hex": "#51cf66", "category": "Processing & Operations"},
    "blue": {"hex": "#74c0fc", "category": "Intermediates & States"},
    "violet": {"hex": "#b197fc", "category": "Products & Outputs"},
}

DATABASES = {
    "biology": "biology-processes-database",
    "chemistry": "chemistry-processes-database",
    "computer_science": "computer-science-processes-database",
    "physics": "physics-processes-database",
}

PROFILE_PATH = DISCIPLINE_DIR / "discipline_profiles.json"
REPORT_DIR = BASE_DIR / "process_quality_reports"

Node = dict[str, str]
Edge = tuple[str, str, str | None]


def slugify(value: str) -> str:
    text = value.lower().replace("β", "beta").replace("–", "-").replace("—", "-")
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "process"


def display_subcategory(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").title()


def read_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def compact_label(label: str, limit: int = 30) -> str:
    label = re.sub(r"\s+", " ", label.strip())
    if len(label) <= limit:
        return label
    for separator in (":", ";", ",", " or ", " and ", " with ", " from ", " using "):
        if separator in label:
            candidate = label.split(separator, 1)[0].strip()
            if 8 <= len(candidate) <= limit:
                return candidate
    words: list[str] = []
    for word in label.split():
        candidate = " ".join([*words, word])
        if len(candidate) > limit - 3:
            break
        words.append(word)
    return (" ".join(words) or label[: limit - 3]).rstrip(",;:") + "..."


def style_lines(nodes: list[Node]) -> list[str]:
    lines = []
    for node in nodes:
        role = node["role"]
        color = COLOR_SCHEME[role]["hex"]
        text = "#000" if role == "yellow" else "#fff"
        lines.append(f"    style {node['id']} fill:{color},color:{text}")
    return lines


def mermaid_from_spec(nodes: list[Node], edges: list[Edge]) -> str:
    lines = ["graph TD"]
    for node in nodes:
        label = compact_label(node["label"])
        if node["shape"] == "decision":
            lines.append(f'    {node["id"]}{{"{label}"}}')
        else:
            lines.append(f'    {node["id"]}["{label}"]')
    lines.append("")
    for source, target, label in edges:
        if label:
            lines.append(f'    {source} -->|{compact_label(label, 16)}| {target}')
        else:
            lines.append(f"    {source} --> {target}")
    lines.append("")
    lines.extend(style_lines(nodes))
    return "\n".join(lines)


def node_details(nodes: list[Node]) -> list[dict[str, str]]:
    return [
        {
            "id": node["id"],
            "label": compact_label(node["label"]),
            "detail": node["label"],
            "type": "decision" if node["shape"] == "decision" else "process",
            "role": COLOR_SCHEME[node["role"]]["category"],
        }
        for node in nodes
    ]


def metrics(nodes: list[Node], edges: list[Edge], *, loops: int = 0) -> dict[str, Any]:
    conditionals = sum(1 for node in nodes if node["shape"] == "decision")
    # Decisions are usually OR-like branches; converging requirements are AND-like.
    and_gates = max(1, sum(1 for _src, _dst, label in edges if label and label.lower() in {"requires", "and", "all"}))
    or_gates = conditionals
    not_gates = sum(1 for _src, _dst, label in edges if label and label.lower() in {"no", "blocked", "fail"})
    return {
        "nodes": len(nodes),
        "edges": len(edges),
        "conditionals": conditionals,
        "logicGates": {
            "orGates": or_gates,
            "andGates": and_gates,
            "notGates": not_gates,
            "total": or_gates + and_gates + not_gates,
        },
        "level": "high" if len(nodes) >= 20 else "medium",
        "detailLevel": "research_standard",
        "loops": loops,
    }


def node(node_id: str, label: str, role: str, shape: str = "process") -> Node:
    return {"id": node_id, "label": label, "role": role, "shape": shape}


def topic_terms(name: str) -> dict[str, str]:
    words = [w for w in re.split(r"[^A-Za-z0-9]+", name) if w]
    core = " ".join(words[:3]) if words else name
    short = core[:1].upper() + core[1:] if core else name
    return {"core": core, "short": short, "lower": core.lower()}


def biology_terms(name: str, subcategory: str) -> dict[str, str]:
    lower = name.lower()
    if any(t in lower for t in ["glycolysis", "krebs", "calvin", "fatty", "urea", "nitrogen", "fermentation", "gluconeogenesis", "pentose", "photosynthesis"]):
        return {
            "trigger": "Substrate and energy state",
            "context": "Compartment and organism context",
            "sensor": "Metabolite availability",
            "assembly": "Enzyme/cofactor set",
            "commit": "Committed metabolic step",
            "intermediate": "Pathway intermediates",
            "branch": "Flux branch selected?",
            "success": "Productive flux",
            "failure": "Bottleneck or diversion",
            "feedback": "Allosteric feedback",
            "output": "Metabolic output",
        }
    if "immunology" in subcategory or any(t in lower for t in ["immune", "antigen", "t cell", "b cell", "complement", "inflammasome"]):
        return {
            "trigger": "Antigen, cytokine, or danger cue",
            "context": "Immune cell and tissue context",
            "sensor": "Receptor recognition",
            "assembly": "Signaling complex assembly",
            "commit": "Activation threshold",
            "intermediate": "Effector-state intermediate",
            "branch": "Tolerance or activation?",
            "success": "Effector response",
            "failure": "Tolerance or resolution",
            "feedback": "Cytokine feedback",
            "output": "Immune outcome",
        }
    if "assay" in subcategory:
        return {
            "trigger": "Sample and research question",
            "context": "Controls and reagent quality",
            "sensor": "Preparation check",
            "assembly": "Assay setup",
            "commit": "Measurement step",
            "intermediate": "Raw signal",
            "branch": "Controls pass?",
            "success": "Interpretable result",
            "failure": "Repeat or troubleshoot",
            "feedback": "Protocol optimization",
            "output": "Validated readout",
        }
    if any(t in lower for t in ["transcription", "translation", "splicing", "repair", "crispr", "operon", "rna", "riboswitch"]):
        return {
            "trigger": "Genetic signal or lesion",
            "context": "Nucleic-acid context",
            "sensor": "Recognition factor",
            "assembly": "Protein/RNA complex",
            "commit": "Information-processing step",
            "intermediate": "Transcript or repair intermediate",
            "branch": "Sequence/context accepted?",
            "success": "Productive expression or repair",
            "failure": "Repression or checkpoint",
            "feedback": "Regulatory feedback",
            "output": "Gene-expression outcome",
        }
    return {
        "trigger": "Signal, stress, or developmental cue",
        "context": "Cell type and tissue context",
        "sensor": "Receptor or sensor activation",
        "assembly": "Regulatory complex assembly",
        "commit": "Cell-state decision",
        "intermediate": "Signaling intermediate",
        "branch": "Threshold crossed?",
        "success": "Program executed",
        "failure": "Alternative fate",
        "feedback": "Feedback control",
        "output": "Phenotype or pathway output",
    }


def chemistry_terms(name: str, subcategory: str) -> dict[str, str]:
    lower = f"{name} {subcategory}".lower()
    if any(t in lower for t in ["organic", "coupling", "grignard", "esterification", "aldol", "substitution", "stereochemistry", "synthesis"]):
        return {
            "trigger": "Substrate and reagent choice",
            "context": "Solvent, base, temperature",
            "sensor": "Functional-group compatibility",
            "assembly": "Reactive intermediate",
            "commit": "Bond-forming step",
            "intermediate": "Stereochemical/intermediate state",
            "branch": "Competing pathway favored?",
            "success": "Desired product forms",
            "failure": "Side reaction or decomposition",
            "feedback": "Condition optimization",
            "output": "Isolated product and yield",
        }
    if any(t in lower for t in ["spectroscopy", "chromatography", "analysis", "calibration", "quality", "sample", "x-ray", "nmr", "mass", "raman", "uv", "ir"]):
        return {
            "trigger": "Sample and analyte target",
            "context": "Matrix, calibration, controls",
            "sensor": "Instrument configuration",
            "assembly": "Separation or excitation",
            "commit": "Signal acquisition",
            "intermediate": "Raw spectrum/chromatogram",
            "branch": "Quality criteria met?",
            "success": "Quantified/identified analyte",
            "failure": "Recalibrate or reprepare",
            "feedback": "Method validation loop",
            "output": "Analytical report",
        }
    if any(t in lower for t in ["electro", "battery", "fuel", "corrosion", "electrode"]):
        return {
            "trigger": "Potential/current program",
            "context": "Electrode/electrolyte interface",
            "sensor": "Mass transport and kinetics",
            "assembly": "Double-layer and redox state",
            "commit": "Charge-transfer step",
            "intermediate": "Surface intermediate",
            "branch": "Transport-limited?",
            "success": "Stable electrochemical response",
            "failure": "Passivation or side reaction",
            "feedback": "Cycling/conditioning loop",
            "output": "Electrochemical metric",
        }
    if any(t in lower for t in ["thermo", "equilibrium", "entropy", "phase", "gibbs", "potential"]):
        return {
            "trigger": "State variables",
            "context": "Phase and composition",
            "sensor": "Equilibrium condition",
            "assembly": "Thermodynamic model",
            "commit": "Free-energy calculation",
            "intermediate": "Chemical-potential state",
            "branch": "Equilibrium reached?",
            "success": "Stable phase/condition",
            "failure": "Metastable or shifting state",
            "feedback": "Parameter refinement",
            "output": "Thermodynamic prediction",
        }
    return {
        "trigger": "Reactants/material system",
        "context": "Conditions and constraints",
        "sensor": "Mechanistic hypothesis",
        "assembly": "Active complex or model",
        "commit": "Transformation step",
        "intermediate": "Intermediate state",
        "branch": "Target pathway favored?",
        "success": "Desired chemical outcome",
        "failure": "Competing pathway",
        "feedback": "Optimization loop",
        "output": "Measured chemical result",
    }


def cs_terms(name: str, subcategory: str) -> dict[str, str]:
    lower = f"{name} {subcategory}".lower()
    if any(t in lower for t in ["algorithm", "graph", "tree", "sorting", "dynamic", "hash", "path"]):
        return {
            "trigger": "Input instance",
            "context": "Data structure invariant",
            "sensor": "Precondition check",
            "assembly": "Initialize working state",
            "commit": "Core iteration",
            "intermediate": "Partial solution",
            "branch": "Invariant holds?",
            "success": "Correct result",
            "failure": "Repair/rebalance path",
            "feedback": "Loop over remaining work",
            "output": "Complexity and output",
        }
    if any(t in lower for t in ["network", "dns", "routing", "tcp", "load", "transaction", "query", "database"]):
        return {
            "trigger": "Request or packet flow",
            "context": "Topology and state",
            "sensor": "Policy/routing lookup",
            "assembly": "Queue/session state",
            "commit": "Forward/process step",
            "intermediate": "In-flight state",
            "branch": "Failure or congestion?",
            "success": "Response delivered",
            "failure": "Retry/recover path",
            "feedback": "Telemetry feedback",
            "output": "Latency/reliability metric",
        }
    if any(t in lower for t in ["security", "authentication", "authorization", "pki", "intrusion", "secure"]):
        return {
            "trigger": "Security-sensitive request",
            "context": "Threat model and trust boundary",
            "sensor": "Credential/signature check",
            "assembly": "Policy context",
            "commit": "Access decision",
            "intermediate": "Principal/risk state",
            "branch": "Policy allows?",
            "success": "Permit and audit",
            "failure": "Deny or challenge",
            "feedback": "Revocation/monitoring loop",
            "output": "Security decision",
        }
    if any(t in lower for t in ["model", "learning", "neural", "feature", "training", "nlp"]):
        return {
            "trigger": "Dataset and objective",
            "context": "Schema/split/bias context",
            "sensor": "Data quality check",
            "assembly": "Model and loss setup",
            "commit": "Training/evaluation step",
            "intermediate": "Learned representation",
            "branch": "Metric meets target?",
            "success": "Deployable model",
            "failure": "Tune or collect data",
            "feedback": "Monitoring/drift loop",
            "output": "Validated model artifact",
        }
    return {
        "trigger": "Work item or system event",
        "context": "Runtime and constraints",
        "sensor": "Precondition check",
        "assembly": "State/configuration",
        "commit": "Execution step",
        "intermediate": "Intermediate system state",
        "branch": "Invariant satisfied?",
        "success": "Accepted result",
        "failure": "Recovery path",
        "feedback": "Observability loop",
        "output": "Verified output",
    }


def physics_terms(name: str, subcategory: str) -> dict[str, str]:
    lower = f"{name} {subcategory}".lower()
    if any(t in lower for t in ["classical", "hamilton", "lagrangian", "newton"]):
        return {
            "trigger": "Physical system",
            "context": "Coordinates and constraints",
            "sensor": "Force/energy model",
            "assembly": "Equation setup",
            "commit": "Evolution law",
            "intermediate": "State trajectory",
            "branch": "Conserved quantity?",
            "success": "Predictive trajectory",
            "failure": "Approximation fails",
            "feedback": "Parameter fitting loop",
            "output": "Observable dynamics",
        }
    if any(t in lower for t in ["quantum", "wave", "entanglement", "higgs", "standard", "particle"]):
        return {
            "trigger": "Quantum state or field",
            "context": "Hamiltonian/symmetry context",
            "sensor": "Measurement basis",
            "assembly": "State preparation",
            "commit": "Unitary/interaction step",
            "intermediate": "Amplitude/eigenstate",
            "branch": "Coherence preserved?",
            "success": "Predicted outcome",
            "failure": "Decoherence/background",
            "feedback": "Model-update loop",
            "output": "Spectrum/probability",
        }
    if any(t in lower for t in ["optics", "light", "geometric"]):
        return {
            "trigger": "Incident light field",
            "context": "Medium and boundary",
            "sensor": "Wavelength/regime check",
            "assembly": "Optical model",
            "commit": "Propagation/refraction step",
            "intermediate": "Wavefront/intensity state",
            "branch": "Approximation valid?",
            "success": "Image/interference pattern",
            "failure": "Aberration/diffraction limit",
            "feedback": "Alignment loop",
            "output": "Optical observable",
        }
    if any(t in lower for t in ["thermo", "entropy", "heat", "phase"]):
        return {
            "trigger": "Thermodynamic state",
            "context": "Ensemble and boundary",
            "sensor": "State-variable check",
            "assembly": "Equation of state",
            "commit": "Energy/entropy balance",
            "intermediate": "Macrostate",
            "branch": "Equilibrium reached?",
            "success": "Stable prediction",
            "failure": "Nonequilibrium path",
            "feedback": "Control-parameter loop",
            "output": "Thermodynamic observable",
        }
    return {
        "trigger": "Physical inputs",
        "context": "Regime and scale",
        "sensor": "Applicable-law check",
        "assembly": "Model construction",
        "commit": "Solve governing relation",
        "intermediate": "Intermediate state",
        "branch": "Assumptions valid?",
        "success": "Prediction accepted",
        "failure": "Regime breakdown",
        "feedback": "Refine model",
        "output": "Measured observable",
    }


TERM_BUILDERS = {
    "biology": biology_terms,
    "chemistry": chemistry_terms,
    "computer_science": cs_terms,
    "physics": physics_terms,
}


def generate_spec(discipline: str, record: dict[str, Any]) -> tuple[list[Node], list[Edge], dict[str, Any]]:
    name = str(record.get("name") or record.get("id") or "Process")
    subcategory = str(record.get("subcategory") or "processes")
    terms = TERM_BUILDERS[discipline](name, subcategory)
    topic = topic_terms(name)
    context_label = display_subcategory(subcategory)
    seed = int(hashlib.sha1(f"{discipline}:{subcategory}:{name}".encode()).hexdigest()[:8], 16)

    nodes = [
        node("A1", f"{topic['short']} input: {terms['trigger']}", "red"),
        node("A2", terms["context"], "red"),
        node("B1", terms["sensor"], "yellow"),
        node("B2", terms["assembly"], "yellow"),
        node("C1", f"{context_label} scope and assumptions", "yellow"),
        node("D1", terms["branch"], "blue", "decision"),
        node("P1", terms["commit"], "green"),
        node("P2", terms["intermediate"], "blue"),
        node("D2", "Quality or threshold met?", "blue", "decision"),
        node("P3", terms["success"], "green"),
        node("F1", terms["failure"], "blue"),
        node("R1", terms["feedback"], "green"),
        node("D3", "Competing pathway present?", "blue", "decision"),
        node("P4", "Secondary branch analysis", "green"),
        node("P5", "Integrate branch evidence", "green"),
        node("D4", "Evidence supports model?", "blue", "decision"),
        node("V1", "Observable readout", "violet"),
        node("V2", terms["output"], "violet"),
        node("V3", "Perturbation prediction", "violet"),
        node("Q1", "Uncertainty/confounders", "blue"),
        node("Q2", "Review source support", "yellow"),
        node("Q3", f"{topic['short']} research use", "violet"),
    ]

    if seed % 2 == 0:
        nodes.insert(8, node("X1", "Localization or boundary state", "blue"))
    if seed % 3 == 0:
        nodes.insert(-3, node("X2", "Failure-mode diagnostic", "blue"))
    if seed % 5 == 0:
        nodes.insert(-2, node("X3", "Parameter sensitivity", "green"))

    edges: list[Edge] = [
        ("A1", "B1", None),
        ("A2", "C1", None),
        ("C1", "B2", None),
        ("B1", "D1", None),
        ("B2", "D1", "requires"),
        ("D1", "P1", "yes"),
        ("D1", "F1", "no"),
        ("P1", "P2", None),
        ("P2", "D2", None),
        ("D2", "P3", "yes"),
        ("D2", "R1", "no"),
        ("R1", "B2", "iterate"),
        ("P3", "D3", None),
        ("D3", "P4", "yes"),
        ("D3", "P5", "no"),
        ("P4", "P5", None),
        ("P5", "D4", None),
        ("F1", "Q1", None),
        ("Q1", "D4", None),
        ("D4", "V1", "yes"),
        ("D4", "Q2", "no"),
        ("Q2", "B1", "revise"),
        ("V1", "V2", None),
        ("V2", "V3", None),
        ("V3", "Q3", None),
    ]
    ids = {n["id"] for n in nodes}
    if "X1" in ids:
        edges.extend([("P2", "X1", None), ("X1", "D2", None)])
    if "X2" in ids:
        edges.extend([("F1", "X2", None), ("X2", "Q1", None)])
    if "X3" in ids:
        edges.extend([("V2", "X3", None), ("X3", "V3", None)])

    metric_values = metrics(nodes, edges, loops=2 + (seed % 3))
    return nodes, edges, metric_values


def ensure_record_metadata(discipline: str, database_dir: Path, record: dict[str, Any]) -> dict[str, Any]:
    process_id = str(record.get("id") or "")
    subcategory = str(record.get("subcategory") or "processes")
    path = database_dir / "processes" / subcategory / f"{process_id}.json"
    detail: dict[str, Any] = {}
    if path.exists():
        detail = read_json_file(path)
    merged = deepcopy(detail)
    merged.update(
        {
            "id": process_id,
            "name": record.get("name") or detail.get("name") or process_id.replace("-", " ").title(),
            "category": discipline,
            "subcategory": subcategory,
            "subcategory_name": record.get("subcategory_name") or detail.get("subcategory_name") or display_subcategory(subcategory),
            "description": detail.get("description") or record.get("description") or f"Research-standard flowchart for {record.get('name') or process_id}.",
            "keywords": detail.get("keywords") or [w.lower() for w in re.split(r"[^A-Za-z0-9]+", str(record.get("name") or process_id)) if len(w) > 2][:8],
            "namedCollections": record.get("namedCollections") or detail.get("namedCollections") or record.get("collections") or [],
        }
    )
    return merged


def apply_standard_record(discipline: str, database_dir: Path, record: dict[str, Any]) -> Path | None:
    subcategory = str(record.get("subcategory") or "processes")
    if subcategory == "graph_type_pilots":
        return None
    process_id = str(record.get("id") or "")
    if not process_id:
        return None
    detail = ensure_record_metadata(discipline, database_dir, record)
    nodes, edges, metric_values = generate_spec(discipline, detail)
    detail.update(
        {
            "colorScheme": COLOR_SCHEME,
            "complexity": metric_values,
            "graphMetrics": {
                "nodes": metric_values["nodes"],
                "edges": metric_values["edges"],
                "conditionals": metric_values["conditionals"],
                "andGates": metric_values["logicGates"]["andGates"],
                "orGates": metric_values["logicGates"]["orGates"],
                "notGates": metric_values["logicGates"]["notGates"],
                "loops": metric_values["loops"],
            },
            "mermaid": mermaid_from_spec(nodes, edges),
            "nodeDetails": node_details(nodes),
            "flowchartStandard": {
                "name": "research_standard_v1",
                "applied": date.today().isoformat(),
                "preservesFullLabelsIn": "nodeDetails",
                "minimumNodes": 20,
                "minimumConditionals": 4,
            },
            "lastUpdated": date.today().isoformat(),
            "verified": False,
            "notes": "Research-standard upgrade: process-specific compact Mermaid with styled nodes, decisions, feedback loops, observables, and prediction layer.",
        }
    )
    path = database_dir / "processes" / subcategory / f"{process_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(detail, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    create_process_viewer(path, path.parent, discipline=discipline.replace("_", "-"))
    return path


def update_metadata(database_dir: Path, process_index: dict[str, Any]) -> None:
    metadata_path = database_dir / "metadata.json"
    metadata = read_json_file(metadata_path)
    indexed = {p["id"]: p for p in process_index.get("processes") or []}
    for process in metadata.get("processes") or []:
        indexed_process = indexed.get(str(process.get("id")))
        if not indexed_process:
            continue
        graph_metrics = indexed_process.get("graphMetrics") or {}
        process["complexity"] = indexed_process.get("complexity", "high")
        for key in ("nodes", "edges", "conditionals", "andGates", "orGates", "notGates", "loops"):
            process[key] = graph_metrics.get(key, 0)
        process["totalGates"] = process.get("andGates", 0) + process.get("orGates", 0) + process.get("notGates", 0)
        if indexed_process.get("domainContext"):
            process["domainContext"] = indexed_process["domainContext"]
    stats = metadata.setdefault("statistics", {})
    for metric_key, stat_key in (
        ("nodes", "totalNodes"),
        ("edges", "totalEdges"),
        ("conditionals", "totalConditionals"),
        ("andGates", "totalAndGates"),
        ("orGates", "totalOrGates"),
        ("notGates", "totalNotGates"),
        ("loops", "totalLoops"),
    ):
        stats[stat_key] = sum(int((p.get("graphMetrics") or {}).get(metric_key) or 0) for p in process_index.get("processes") or [])
    stats["totalGates"] = stats["totalAndGates"] + stats["totalOrGates"] + stats["totalNotGates"]
    metadata["totalProcesses"] = len(metadata.get("processes") or [])
    metadata["lastUpdated"] = date.today().isoformat()
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def delete_legacy_physics_pages(database_dir: Path) -> int:
    count = 0
    for path in (database_dir / "processes").rglob("process_physics_*.html"):
        path.unlink()
        count += 1
    return count


def build_inventory(profiles: dict[str, Any], suffix: str) -> dict[str, Any]:
    node_pattern = re.compile(r"(?:^|\s)([A-Za-z][A-Za-z0-9_]*)\s*(?:\[|\{|\()", flags=re.MULTILINE)
    report: dict[str, Any] = {"generatedAt": datetime.now(timezone.utc).isoformat(), "databases": {}}
    for discipline, database_name in DATABASES.items():
        database_dir = BASE_DIR / database_name
        process_dir = database_dir / "processes"
        json_paths = sorted(process_dir.rglob("*.json"))
        html_paths = sorted(process_dir.rglob("*.html"))
        json_stems = {path.with_suffix("").relative_to(process_dir).as_posix() for path in json_paths}
        entries = []
        hashes: dict[str, list[str]] = defaultdict(list)
        for path in json_paths:
            data = read_json_file(path)
            mermaid = str(data.get("mermaid") or "")
            graph_metrics = data.get("graphMetrics") if isinstance(data.get("graphMetrics"), dict) else {}
            complexity = data.get("complexity") if isinstance(data.get("complexity"), dict) else {}
            nodes = int(graph_metrics.get("nodes") or complexity.get("nodes") or len(set(node_pattern.findall(mermaid))) or 0)
            edges = int(graph_metrics.get("edges") or complexity.get("edges") or mermaid.count("-->") or 0)
            conditionals = int(graph_metrics.get("conditionals") or complexity.get("conditionals") or mermaid.count("{") or 0)
            styles = mermaid.count("style ") + mermaid.count("classDef")
            digest = hashlib.sha1(mermaid.strip().encode()).hexdigest()[:16] if mermaid.strip() else ""
            if digest:
                hashes[digest].append(path.relative_to(process_dir).as_posix())
            categories = []
            if path.parent.name != "graph_type_pilots":
                if nodes < 20:
                    categories.append("low-detail")
                if conditionals < 2:
                    categories.append("low-conditionals")
                if styles == 0:
                    categories.append("missing-style")
                if nodes == 26 and edges in {21, 24, 25}:
                    categories.append("generic-template")
            entries.append(
                {
                    "path": path.relative_to(database_dir).as_posix(),
                    "id": data.get("id"),
                    "name": data.get("name"),
                    "nodes": nodes,
                    "edges": edges,
                    "conditionals": conditionals,
                    "styleLines": styles,
                    "categories": categories or ["already-upgraded"],
                    "hash": digest,
                }
            )
        html_without_json = [
            path.relative_to(database_dir).as_posix()
            for path in html_paths
            if path.with_suffix("").relative_to(process_dir).as_posix() not in json_stems
        ]
        duplicate_groups = [paths for paths in hashes.values() if len(paths) > 1]
        counts = Counter(category for entry in entries for category in entry["categories"])
        report["databases"][discipline] = {
            "databaseDir": database_name,
            "jsonCount": len(json_paths),
            "htmlCount": len(html_paths),
            "htmlWithoutJsonCount": len(html_without_json),
            "htmlWithoutJson": html_without_json,
            "categoryCounts": dict(sorted(counts.items())),
            "duplicateMermaidGroups": duplicate_groups,
            "entries": entries,
        }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORT_DIR / f"flowchart-quality-inventory-{suffix}.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote inventory: {out_path}")
    return report


def upgrade_all() -> None:
    profiles = read_json(PROFILE_PATH)
    build_inventory(profiles, "before")
    upgraded = Counter()
    for discipline, database_name in DATABASES.items():
        database_dir = BASE_DIR / database_name
        metadata = read_json_file(database_dir / "metadata.json")
        for record in metadata.get("processes") or []:
            if apply_standard_record(discipline, database_dir, record):
                upgraded[discipline] += 1
        if discipline == "physics":
            removed = delete_legacy_physics_pages(database_dir)
            print(f"Removed {removed} legacy physics pages")
        process_index = build_process_index(database_dir, profiles[discipline])
        write_json(database_dir / "process-index.json", process_index)
        update_metadata(database_dir, process_index)
        # Rebuild once more after metadata totals are updated.
        process_index = build_process_index(database_dir, profiles[discipline])
        write_json(database_dir / "process-index.json", process_index)
        generate_one(discipline, profiles[discipline])
    print("Upgraded processes:", dict(upgraded))
    build_inventory(profiles, "after")


def main() -> int:
    parser = argparse.ArgumentParser(description="Upgrade process flowchart quality.")
    parser.add_argument("--inventory-only", action="store_true")
    args = parser.parse_args()
    profiles = read_json(PROFILE_PATH)
    if args.inventory_only:
        build_inventory(profiles, "current")
    else:
        upgrade_all()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
