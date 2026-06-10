#!/usr/bin/env python3
"""Rebuild process flowcharts from curated process-specific step structures.

This is a corrective pass after a too-generic scaffold was over-applied across
multiple disciplines. It favors exact curated process steps, uses subfield
workflows only as fallbacks, records the provenance of the rebuild, and writes
topology signatures for validation.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = BASE_DIR / "scripts"
PROCESS_SCRIPTS_DIR = SCRIPTS_DIR / "processes"
DISCIPLINE_DIR = Path(__file__).resolve().parent
for path in (SCRIPTS_DIR, PROCESS_SCRIPTS_DIR, DISCIPLINE_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from create_process_viewers import create_process_viewer  # noqa: E402
from curated_flowcharts import (  # noqa: E402
    BIOLOGY_SUBCATEGORY_TEMPLATES,
    CHEMISTRY_SUBCATEGORY_TEMPLATES,
    CHEMISTRY_TEMPLATES,
    CS_TEMPLATES,
)
from enhanced_database_table import generate_one, read_json  # noqa: E402
from normalize_graph_metrics import build_process_index, write_json  # noqa: E402


DATABASES = {
    "biology": "biology-processes-database",
    "chemistry": "chemistry-processes-database",
    "computer_science": "computer-science-processes-database",
    "physics": "physics-processes-database",
}

COLOR_SCHEME = {
    "red": {"hex": "#ff6b6b", "category": "Triggers & Inputs"},
    "yellow": {"hex": "#ffd43b", "category": "Structures & Objects"},
    "green": {"hex": "#51cf66", "category": "Processing & Operations"},
    "blue": {"hex": "#74c0fc", "category": "Intermediates & States"},
    "violet": {"hex": "#b197fc", "category": "Products & Outputs"},
}

Step = dict[str, str]
Node = dict[str, str]
Edge = tuple[str, str, str | None]


def step(label: str, role: str) -> Step:
    return {"label": label, "role": role}


PHYSICS_TEMPLATES: dict[str, list[Step]] = {
    "classical_mechanics-hamiltonian-mechanics": [
        step("Configuration coordinates q", "red"),
        step("Momenta p and phase space", "yellow"),
        step("Construct Hamiltonian H(q,p,t)", "green"),
        step("Check constraints/symmetries", "blue"),
        step("Hamilton equations dq/dt, dp/dt", "green"),
        step("Integrate phase-space trajectory", "green"),
        step("Monitor conserved quantities", "blue"),
        step("Compare observables with experiment", "violet"),
        step("Revise H or constraints", "green"),
    ],
    "classical_mechanics-lagrangian-mechanics": [
        step("Generalized coordinates", "red"),
        step("Kinetic and potential energy", "yellow"),
        step("Build Lagrangian L=T-V", "green"),
        step("Apply constraints/virtual work", "blue"),
        step("Euler-Lagrange equations", "green"),
        step("Solve equations of motion", "green"),
        step("Identify symmetries/Noether charges", "blue"),
        step("Predict trajectory/observable", "violet"),
    ],
    "classical_mechanics-newtonian-dynamics": [
        step("Masses, positions, velocities", "red"),
        step("Free-body forces", "yellow"),
        step("Choose inertial frame", "yellow"),
        step("Apply F = ma", "green"),
        step("Resolve components", "green"),
        step("Integrate acceleration", "green"),
        step("Check energy/momentum", "blue"),
        step("Trajectory and forces predicted", "violet"),
    ],
    "thermodynamics_statistical-phase-transition": [
        step("Control variables T, P, composition", "red"),
        step("Candidate phases/order parameter", "yellow"),
        step("Free-energy landscape", "yellow"),
        step("Minimize thermodynamic potential", "green"),
        step("Detect coexistence or instability", "blue"),
        step("Nucleation/growth or critical fluctuations", "green"),
        step("Measure latent heat/critical exponents", "blue"),
        step("Phase diagram prediction", "violet"),
    ],
    "thermodynamics_statistical-entropy": [
        step("Macrostate constraints", "red"),
        step("Accessible microstates", "yellow"),
        step("Choose ensemble", "yellow"),
        step("Count states or partition function", "green"),
        step("Compute S = k ln W", "green"),
        step("Infer temperature/free energy", "blue"),
        step("Check second-law direction", "blue"),
        step("Entropy change prediction", "violet"),
    ],
    "thermodynamics_statistical-heat-engine": [
        step("Hot and cold reservoirs", "red"),
        step("Working substance", "yellow"),
        step("Thermodynamic cycle path", "yellow"),
        step("Heat absorbed/rejected", "green"),
        step("Work extraction step", "green"),
        step("Efficiency calculation", "blue"),
        step("Irreversibility losses", "blue"),
        step("Power/efficiency prediction", "violet"),
    ],
    "solid_state-nuclear-fusion": [
        step("Light nuclei and plasma state", "red"),
        step("Coulomb barrier", "yellow"),
        step("Confinement/heating mechanism", "yellow"),
        step("Tunneling/fusion reaction", "green"),
        step("Energy and neutron products", "blue"),
        step("Alpha heating/energy balance", "green"),
        step("Loss and instability checks", "blue"),
        step("Fusion yield prediction", "violet"),
    ],
    "solid_state-nuclear-fission": [
        step("Heavy nucleus", "red"),
        step("Neutron absorption", "yellow"),
        step("Compound nucleus", "blue"),
        step("Barrier deformation", "green"),
        step("Fragment split", "green"),
        step("Prompt neutrons/gammas", "blue"),
        step("Chain reaction control", "green"),
        step("Energy release prediction", "violet"),
    ],
    "solid_state-nuclear-decay": [
        step("Unstable nucleus", "red"),
        step("Nuclear energy levels", "yellow"),
        step("Decay channel selection", "blue"),
        step("Alpha/beta/gamma emission", "green"),
        step("Daughter nucleus", "blue"),
        step("Half-life kinetics", "green"),
        step("Radiation spectrum", "violet"),
    ],
    "astrophysics-higgs-mechanism": [
        step("Gauge fields and scalar field", "red"),
        step("Higgs potential", "yellow"),
        step("Spontaneous symmetry breaking", "green"),
        step("Vacuum expectation value", "blue"),
        step("Mass terms for W/Z and fermions", "green"),
        step("Higgs excitation", "blue"),
        step("Collider decay channels", "violet"),
    ],
    "astrophysics-standard-model": [
        step("Gauge symmetries", "red"),
        step("Quark/lepton fields", "yellow"),
        step("Gauge boson interactions", "green"),
        step("Electroweak symmetry breaking", "green"),
        step("Mass and mixing parameters", "blue"),
        step("Scattering/decay predictions", "violet"),
        step("Precision-test residuals", "blue"),
    ],
    "astrophysics-particle-collision": [
        step("Beam particles and energy", "red"),
        step("Parton distributions", "yellow"),
        step("Hard scattering matrix element", "green"),
        step("Parton shower/hadronization", "green"),
        step("Detector response", "blue"),
        step("Event reconstruction", "green"),
        step("Cross-section or resonance result", "violet"),
    ],
    "optics-wave-optics": [
        step("Coherent wavefront", "red"),
        step("Aperture/boundary conditions", "yellow"),
        step("Superpose fields", "green"),
        step("Phase difference evolves", "blue"),
        step("Interference/diffraction pattern", "green"),
        step("Intensity distribution", "violet"),
    ],
    "optics-geometric-optics": [
        step("Incident ray bundle", "red"),
        step("Interface/lens geometry", "yellow"),
        step("Apply reflection/refraction", "green"),
        step("Trace paraxial rays", "green"),
        step("Aberration/caustic check", "blue"),
        step("Image location and magnification", "violet"),
    ],
    "optics-quantum-optics": [
        step("Quantized light state", "red"),
        step("Mode/cavity/medium", "yellow"),
        step("Light-matter interaction Hamiltonian", "green"),
        step("Photon statistics evolve", "blue"),
        step("Detection correlation measurement", "green"),
        step("Nonclassical observable", "violet"),
    ],
    "quantum_mechanics-electromagnetic-induction": [
        step("Changing magnetic flux", "red"),
        step("Conducting loop/field geometry", "yellow"),
        step("Faraday law", "green"),
        step("Induced electric field", "blue"),
        step("Lenz-law direction", "green"),
        step("EMF/current prediction", "violet"),
    ],
    "quantum_mechanics-electromagnetic-wave": [
        step("Time-varying E/B fields", "red"),
        step("Medium properties", "yellow"),
        step("Maxwell curl equations", "green"),
        step("Wave equation", "green"),
        step("Polarization/dispersion state", "blue"),
        step("Propagating EM wave", "violet"),
    ],
    "quantum_mechanics-maxwells-equations": [
        step("Charge/current densities", "red"),
        step("Boundary and material laws", "yellow"),
        step("Gauss laws", "green"),
        step("Faraday and Ampere-Maxwell laws", "green"),
        step("Field constraints/coupling", "blue"),
        step("Electromagnetic field solution", "violet"),
    ],
    "electromagnetism-wave-function": [
        step("Quantum state preparation", "red"),
        step("Hilbert space and Hamiltonian", "yellow"),
        step("Solve Schrodinger equation", "green"),
        step("Normalize wavefunction", "blue"),
        step("Apply measurement operator", "green"),
        step("Probability distribution", "violet"),
    ],
    "electromagnetism-quantum-entanglement": [
        step("Composite quantum system", "red"),
        step("Joint state vector/density matrix", "yellow"),
        step("Entangling interaction", "green"),
        step("Nonseparable correlations", "blue"),
        step("Local measurements", "green"),
        step("Bell/entropy witness", "violet"),
    ],
    "electromagnetism-quantum-computing": [
        step("Qubit register", "red"),
        step("Initial state and circuit", "yellow"),
        step("Apply unitary gates", "green"),
        step("Entangle/interfere amplitudes", "blue"),
        step("Error/decoherence correction", "green"),
        step("Measurement bitstrings", "violet"),
    ],
}


BIOLOGY_PROCESS_TEMPLATES: dict[str, list[Step]] = {
    "pathways-apoptosis": [
        step("Extrinsic death ligand or intrinsic stress", "red"),
        step("Death receptor or mitochondrial sensors", "yellow"),
        step("DISC assembly / BH3-only activation", "green"),
        step("MOMP and cytochrome c release", "blue"),
        step("Apoptosome formation", "green"),
        step("Initiator caspase activation", "green"),
        step("Executioner caspase cleavage", "green"),
        step("Membrane blebbing/DNA fragmentation", "blue"),
        step("Efferocytosis without inflammation", "violet"),
    ],
    "pathways-glycolysis": [
        step("Glucose uptake", "red"),
        step("ATP investment reactions", "green"),
        step("Fructose-1,6-bisphosphate split", "blue"),
        step("GAP oxidation and NADH formation", "green"),
        step("Substrate-level phosphorylation", "green"),
        step("Pyruvate production", "violet"),
        step("ATP/AMP feedback on PFK", "blue"),
    ],
    "mechanisms-translation-initiation": [
        step("mRNA 5-prime cap / start context", "red"),
        step("eIF4F and scanning complex", "yellow"),
        step("40S ribosomal subunit recruitment", "green"),
        step("Kozak/AUG recognition", "blue"),
        step("eIF2-GTP hydrolysis", "green"),
        step("60S subunit joining", "green"),
        step("80S initiation complex", "violet"),
    ],
    "mechanisms-crispr-cas9": [
        step("Guide RNA and target DNA", "red"),
        step("Cas9-sgRNA complex", "yellow"),
        step("PAM recognition", "green"),
        step("R-loop formation", "blue"),
        step("HNH/RuvC cleavage", "green"),
        step("Double-strand break", "blue"),
        step("NHEJ or HDR repair outcome", "violet"),
    ],
    "pathways-p53-dna-damage-response": [
        step("DNA double-strand damage", "red"),
        step("ATM/ATR checkpoint kinases", "yellow"),
        step("p53 stabilization via MDM2 inhibition", "green"),
        step("p21-mediated cell-cycle arrest", "blue"),
        step("DNA repair attempt", "green"),
        step("Senescence or apoptosis branch", "blue"),
        step("Genome integrity/fate outcome", "violet"),
    ],
}


def compact(label: str, limit: int = 34) -> str:
    label = re.sub(r"\s+", " ", label).strip()
    if len(label) <= limit:
        return label
    words: list[str] = []
    for word in label.split():
        candidate = " ".join([*words, word])
        if len(candidate) > limit - 3:
            break
        words.append(word)
    return (" ".join(words) or label[: limit - 3]).rstrip(",;:") + "..."


def slug_words(value: str) -> list[str]:
    return [w for w in re.split(r"[^a-z0-9]+", value.lower()) if len(w) > 2]


def contextualize_steps(record: dict[str, Any], steps: list[Step]) -> list[Step]:
    """Add process and source context without changing the curated workflow core."""
    name = str(record.get("name") or record.get("id"))
    sources = record.get("sources") or []
    source_hint = ""
    if sources:
        source_hint = str(sources[0].get("title") or "").split(":", 1)[0]
    context = [
        step(f"{name} research question", "red"),
        *steps,
    ]
    if source_hint:
        context.append(step(f"Source-grounded check: {source_hint}", "yellow"))
    context.append(step(f"{name} prediction/readout", "violet"))
    return context


def fallback_steps(record: dict[str, Any], discipline: str) -> tuple[list[Step], str]:
    process_id = str(record.get("id"))
    subcategory = str(record.get("subcategory", ""))
    name = str(record.get("name") or process_id)
    words = slug_words(name)
    source_title = ""
    if record.get("sources"):
        source_title = str(record["sources"][0].get("title") or "")

    if discipline == "chemistry":
        base = CHEMISTRY_SUBCATEGORY_TEMPLATES.get(subcategory, CHEMISTRY_SUBCATEGORY_TEMPLATES["analytical_chemistry"])
        return contextualize_steps(record, base), f"chemistry_subcategory:{subcategory}"
    if discipline == "biology":
        base = BIOLOGY_PROCESS_TEMPLATES.get(process_id)
        if not base:
            if subcategory in {"pathways", "mechanisms", "assay_protocols", "immunology", "cell_biology", "development"}:
                base = [
                    step(f"{name} initiating condition", "red"),
                    step(f"Core biological components: {'/'.join(words[:2]) or name}", "yellow"),
                    step("Recognition or activation step", "green"),
                    step("Intermediate regulatory state", "blue"),
                    step("Committed mechanistic step", "green"),
                    step("Feedback/checkpoint control", "blue"),
                    step("Measured phenotype or product", "violet"),
                ]
            else:
                base = BIOLOGY_SUBCATEGORY_TEMPLATES.get(subcategory, [])
        return contextualize_steps(record, base), f"biology_process_or_subcategory:{subcategory}"
    if discipline == "physics":
        base = PHYSICS_TEMPLATES.get(process_id, [
            step(f"{name} physical system", "red"),
            step("State variables and constraints", "yellow"),
            step("Choose governing law", "green"),
            step("Solve model equations", "green"),
            step("Regime/approximation check", "blue"),
            step("Observable prediction", "violet"),
        ])
        return contextualize_steps(record, base), "physics_process_template" if process_id in PHYSICS_TEMPLATES else "physics_fallback"
    if discipline == "computer_science":
        base = CS_TEMPLATES.get(process_id, [
            step(f"{name} input", "red"),
            step("System components", "yellow"),
            step("Execute operation", "green"),
            step("State update", "blue"),
            step("Output/result", "violet"),
        ])
        return contextualize_steps(record, base), "cs_exact_template" if process_id in CS_TEMPLATES else "cs_fallback"
    return contextualize_steps(record, [step(name, "red"), step(source_title or "Source support", "yellow"), step("Output", "violet")]), "generic_emergency"


def steps_for(record: dict[str, Any], discipline: str) -> tuple[list[Step], str]:
    process_id = str(record.get("id"))
    if discipline == "computer_science" and process_id in CS_TEMPLATES:
        return contextualize_steps(record, CS_TEMPLATES[process_id]), "cs_exact_template"
    if discipline == "chemistry" and process_id in CHEMISTRY_TEMPLATES:
        return contextualize_steps(record, CHEMISTRY_TEMPLATES[process_id]), "chemistry_exact_template"
    if discipline == "biology" and process_id in BIOLOGY_PROCESS_TEMPLATES:
        return contextualize_steps(record, BIOLOGY_PROCESS_TEMPLATES[process_id]), "biology_exact_template"
    if discipline == "physics" and process_id in PHYSICS_TEMPLATES:
        return contextualize_steps(record, PHYSICS_TEMPLATES[process_id]), "physics_exact_template"
    return fallback_steps(record, discipline)


def shape_for(label: str, idx: int, total: int) -> str:
    decision_words = ("check", "choose", "select", "detect", "compare", "monitor", "constraint", "quality", "valid", "branch")
    lower = label.lower()
    if any(word in lower for word in decision_words) and 1 < idx < total:
        return "decision"
    return "process"


def build_topology(process_id: str, nodes: list[Node], discipline: str) -> tuple[list[Edge], int]:
    total = len(nodes)
    edges: list[Edge] = []
    variant = int(hashlib.sha1(process_id.encode()).hexdigest()[:2], 16) % 5
    for i in range(1, total):
        label = None
        if nodes[i - 1]["shape"] == "decision":
            label = "yes"
        edges.append((nodes[i - 1]["id"], nodes[i]["id"], label))

    # Add topology features that follow process type rather than one global scaffold.
    if discipline == "computer_science":
        loop_target = "N3" if total > 5 else "N2"
        edges.append((f"N{min(total - 1, 8)}", loop_target, "iterate"))
        if variant in {1, 3} and total > 8:
            edges.append(("N4", "N7", "skip/opt"))
    elif discipline == "chemistry":
        if total > 7:
            edges.append(("N4", "N7", "QC fail"))
        if variant in {0, 2} and total > 9:
            edges.append(("N8", "N5", "optimize"))
    elif discipline == "physics":
        if total > 6:
            edges.append((f"N{total-2}", "N4", "refine model"))
        if variant in {2, 4} and total > 8:
            edges.append(("N3", "N6", "symmetry"))
    elif discipline == "biology":
        if total > 7:
            edges.append(("N5", "N3", "feedback"))
        if variant in {1, 4} and total > 8:
            edges.append(("N4", "N7", "commit"))

    return edges, sum(1 for _a, b, label in edges if label and label in {"iterate", "feedback", "optimize", "refine model"})


def build_graph(record: dict[str, Any], discipline: str) -> tuple[list[Node], list[Edge], str, int]:
    steps, basis = steps_for(record, discipline)
    nodes: list[Node] = []
    for idx, item in enumerate(steps, start=1):
        nodes.append({
            "id": f"N{idx}",
            "label": item["label"],
            "role": item["role"],
            "shape": shape_for(item["label"], idx, len(steps)),
        })
    edges, loops = build_topology(str(record.get("id")), nodes, discipline)
    return nodes, edges, basis, loops


def mermaid(nodes: list[Node], edges: list[Edge]) -> str:
    lines = ["graph TD"]
    for node in nodes:
        label = compact(node["label"])
        if node["shape"] == "decision":
            lines.append(f'    {node["id"]}{{"{label}"}}')
        else:
            lines.append(f'    {node["id"]}["{label}"]')
    lines.append("")
    for source, target, label in edges:
        if label:
            lines.append(f'    {source} -->|{compact(label, 14)}| {target}')
        else:
            lines.append(f"    {source} --> {target}")
    lines.append("")
    for node in nodes:
        color = COLOR_SCHEME[node["role"]]["hex"]
        text = "#000" if node["role"] == "yellow" else "#fff"
        lines.append(f"    style {node['id']} fill:{color},color:{text}")
    return "\n".join(lines)


def node_details(nodes: list[Node]) -> list[dict[str, str]]:
    return [
        {
            "id": node["id"],
            "label": compact(node["label"]),
            "detail": node["label"],
            "type": "decision" if node["shape"] == "decision" else "process",
            "role": COLOR_SCHEME[node["role"]]["category"],
        }
        for node in nodes
    ]


def graph_metrics(nodes: list[Node], edges: list[Edge], loops: int) -> tuple[dict[str, Any], dict[str, int]]:
    conditionals = sum(1 for node in nodes if node["shape"] == "decision")
    yes_no = sum(1 for _s, _t, label in edges if label in {"yes", "QC fail", "skip/opt", "commit"})
    and_gates = max(1, sum(1 for _s, _t, label in edges if label in {"symmetry", "valid"}))
    not_gates = sum(1 for _s, _t, label in edges if label and "fail" in label.lower())
    complexity = {
        "nodes": len(nodes),
        "edges": len(edges),
        "conditionals": conditionals,
        "logicGates": {
            "orGates": yes_no,
            "andGates": and_gates,
            "notGates": not_gates,
            "total": yes_no + and_gates + not_gates,
        },
        "level": "high" if len(nodes) >= 10 else "medium",
        "detailLevel": "source_grounded_rebuild",
        "loops": loops,
    }
    flat = {
        "nodes": complexity["nodes"],
        "edges": complexity["edges"],
        "conditionals": complexity["conditionals"],
        "andGates": and_gates,
        "orGates": yes_no,
        "notGates": not_gates,
        "loops": loops,
    }
    return complexity, flat


def topology_signature(nodes: list[Node], edges: list[Edge]) -> str:
    shape_map = {node["id"]: f"{node['role']}:{node['shape']}" for node in nodes}
    edge_parts = sorted(f"{shape_map.get(source)}->{shape_map.get(target)}:{label or ''}" for source, target, label in edges)
    payload = "|".join([str(len(nodes)), str(len(edges)), *edge_parts])
    return hashlib.sha1(payload.encode()).hexdigest()[:16]


def rebuild_record(path: Path, discipline: str) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    nodes, edges, basis, loops = build_graph(data, discipline)
    complexity, flat_metrics = graph_metrics(nodes, edges, loops)
    signature = topology_signature(nodes, edges)
    data.update(
        {
            "colorScheme": COLOR_SCHEME,
            "mermaid": mermaid(nodes, edges),
            "complexity": complexity,
            "graphMetrics": flat_metrics,
            "nodeDetails": node_details(nodes),
            "lastUpdated": date.today().isoformat(),
            "flowchartStandard": {
                "name": "source_grounded_rebuild_v1",
                "applied": date.today().isoformat(),
                "curationStatus": "source_grounded_draft",
                "basis": basis,
                "topologySignature": signature,
                "sourceGrounding": "Graph steps are derived from the process title, existing source metadata, and curated process/subfield templates; citations support the process topic and should be reviewed for node-level claims before marking verified.",
            },
            "verified": False,
            "notes": "Corrective rebuild: replaces the generic scaffold with a process-specific step structure and records topology for duplicate detection.",
        }
    )
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    create_process_viewer(path, path.parent, discipline=discipline.replace("_", "-"))
    return signature


def audit_topologies() -> dict[str, Any]:
    report: dict[str, Any] = {"generatedAt": datetime.now(timezone.utc).isoformat(), "databases": {}}
    for discipline, database_name in DATABASES.items():
        database_dir = BASE_DIR / database_name
        groups: dict[str, list[str]] = defaultdict(list)
        for path in sorted((database_dir / "processes").rglob("*.json")):
            if path.name.endswith(".backup"):
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            signature = ((data.get("flowchartStandard") or {}).get("topologySignature") or "")
            if signature:
                groups[signature].append(path.relative_to(database_dir / "processes").as_posix())
        duplicates = {sig: paths for sig, paths in groups.items() if len(paths) > 1}
        report["databases"][discipline] = {
            "signatureCount": len(groups),
            "duplicateTopologyGroups": duplicates,
            "duplicateChartCount": sum(len(paths) for paths in duplicates.values()),
        }
    out_path = BASE_DIR / "process_quality_reports" / "flowchart-topology-audit.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    profiles = read_json(DISCIPLINE_DIR / "discipline_profiles.json")
    counts = Counter()
    for discipline, database_name in DATABASES.items():
        database_dir = BASE_DIR / database_name
        for path in sorted((database_dir / "processes").rglob("*.json")):
            if path.name.endswith(".backup"):
                continue
            rebuild_record(path, discipline)
            counts[discipline] += 1
        process_index = build_process_index(database_dir, profiles[discipline])
        write_json(database_dir / "process-index.json", process_index)
        generate_one(discipline, profiles[discipline])
    report = audit_topologies()
    print("rebuilt", dict(counts))
    for discipline, result in report["databases"].items():
        print(discipline, "duplicate topology groups:", len(result["duplicateTopologyGroups"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
