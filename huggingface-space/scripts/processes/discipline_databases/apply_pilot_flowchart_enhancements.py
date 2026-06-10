#!/usr/bin/env python3
"""Apply the first research-grade pilot flowchart enhancements.

The pilot upgrades one process per discipline with richer Mermaid graphs and
metadata that can be reused as the pattern for the broader collection uplift.
"""

from __future__ import annotations

import json
import re
import sys
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = BASE_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from create_process_viewers import create_process_viewer  # noqa: E402


COLOR_SCHEME = {
    "red": {"hex": "#ff6b6b", "category": "Triggers & Inputs"},
    "yellow": {"hex": "#ffd43b", "category": "Structures & Objects"},
    "green": {"hex": "#51cf66", "category": "Processing & Operations"},
    "blue": {"hex": "#74c0fc", "category": "Intermediates & States"},
    "violet": {"hex": "#b197fc", "category": "Products & Outputs"},
}


Node = tuple[str, str, str, str]
Edge = tuple[str, str, str | None]

COMPACT_LABELS = {
    "Extrinsic death ligand, intrinsic stress, or therapeutic perturbation": "Death/stress trigger",
    "Cell state context: cell type, cell-cycle phase, survival signaling, inhibitor levels": "Cell-state context",
    "Map stimulus class and compartment of origin": "Classify stimulus",
    "Quantify damage/stress intensity and duration": "Assess intensity",
    "Death receptor pathway engaged?": "Death receptor?",
    "Fas/TNF/TRAIL receptor trimerization": "Receptor trimer",
    "FADD/TRADD adaptor recruitment": "Adaptor recruitment",
    "DISC assembly with procaspase-8/10": "DISC assembly",
    "c-FLIP or decoy receptor blocks DISC?": "DISC blocked?",
    "Type I cell: effector caspases activated directly?": "Direct execution?",
    "DNA damage, ER stress, ROS, growth-factor withdrawal, or oncogene stress": "Intrinsic stress",
    "p53, BH3-only proteins, JNK, or UPR sensors integrate stress": "Stress integration",
    "Anti-apoptotic BCL-2 family buffering exceeded?": "BCL-2 buffer exceeded?",
    "BAX/BAK activation and oligomerization": "BAX/BAK activation",
    "Mitochondrial outer membrane permeabilization": "MOMP",
    "Cytochrome c and SMAC/DIABLO released": "Cyt c / SMAC release",
    "Apaf-1 apoptosome assembles with procaspase-9": "Apoptosome",
    "Initiator caspases converge on caspase-3/7": "Caspase-3/7",
    "IAPs suppress executioner caspases?": "IAP brake?",
    "SMAC relieves XIAP inhibition or survival branch persists": "SMAC vs XIAP",
    "Executioner caspases cleave PARP, ICAD, lamins, and cytoskeletal proteins": "Executioner cleavage",
    "CAD nuclease fragments DNA and chromatin condenses": "DNA fragmentation",
    "Membrane blebbing and apoptotic body formation": "Apoptotic bodies",
    "Phagocytes recognize eat-me signals?": "Engulfed?",
    "Phosphatidylserine exposure recruits engulfment receptors": "Eat-me signal",
    "Efferocytosis clears apoptotic bodies without inflammatory spillover": "Efferocytosis",
    "Failed clearance causes secondary necrosis and DAMP release": "Secondary necrosis",
    "Feedback: caspase-3 amplifies mitochondrial and receptor branches": "Caspase feedback",
    "Regulatory brakes: NF-kB survival genes, PI3K-AKT, heat-shock proteins": "Survival brakes",
    "Observable readouts: Annexin V, caspase activity, TUNEL, mitochondrial potential": "Readouts",
    "Prediction layer: perturb BCL-2, caspase-8, XIAP, or phagocytosis to shift outcome": "Perturbation predictions",
    "Research question: redox potential, kinetics, transport, adsorption, or mechanism": "Research question",
    "Analyte, solvent, supporting electrolyte, concentration, and atmosphere": "Sample system",
    "Define potential window from thermodynamics and solvent stability": "Potential window",
    "Select working, reference, and counter electrodes": "Electrode setup",
    "Clean or polish working electrode": "Clean electrode",
    "Prepare blank electrolyte and analyte solution": "Prepare solutions",
    "Solution oxygen or impurity significant?": "Impurities?",
    "Degas, dry, filter, or remake solution": "Clean solution",
    "Run blank scan to establish background current": "Blank scan",
    "Background stable and reference electrode valid?": "Stable baseline?",
    "Correct reference, cell wiring, iR compensation, or electrode surface": "Correct setup",
    "Choose initial, vertex, final potentials and scan direction": "Set waveform",
    "Set scan rate series and number of cycles": "Scan-rate series",
    "Apply triangular potential waveform": "Apply waveform",
    "Measure current versus potential": "Measure current",
    "Forward scan oxidizes or reduces species": "Forward scan",
    "Reverse scan probes product back reaction": "Reverse scan",
    "Peak pair visible above noise?": "Peaks visible?",
    "Adjust concentration, scan rate, window, electrode area, or instrument gain": "Adjust method",
    "Extract anodic/cathodic peak potentials and peak currents": "Extract peaks",
    "Delta Ep and ipa/ipc indicate reversible electron transfer?": "Reversible?",
    "Reversible: estimate E0 prime and diffusion-controlled behavior": "Reversible result",
    "Quasi-reversible/irreversible: estimate heterogeneous rate and transfer coefficient": "Kinetic result",
    "Peak current scales with square root of scan rate?": "Diffusion scaling?",
    "Diffusion control; use Randles-Sevcik relationship": "Diffusion control",
    "Adsorption, coupled chemistry, or uncompensated resistance likely": "Nonideal behavior",
    "New peaks appear on repeated cycles?": "New peaks?",
    "Electrode fouling, passivation, product adsorption, or follow-up reaction": "Surface/product effects",
    "Condition electrode or limit cycling": "Recover surface",
    "Report voltammogram, conditions, corrections, controls, and uncertainty": "Report CV",
    "Prediction layer: vary scan rate, concentration, pH, ligand, or electrode material": "Perturbation predictions",
    "Client requests protected resource or operation": "Protected request",
    "Threat model: spoofing, replay, privilege escalation, token theft": "Threat model",
    "Identify required assurance level and trust boundary": "Assurance level",
    "Choose identity protocol: password, MFA, SSO, OAuth/OIDC, mTLS, API key": "Identity protocol",
    "Credential or token presented?": "Credential present?",
    "Redirect to identity provider or challenge client": "Challenge client",
    "Validate credential, factor, proof-of-possession, or signature": "Validate proof",
    "Authentication valid and fresh?": "Authenticated?",
    "Deny, rate-limit, log, and optionally step-up challenge": "Auth failure",
    "Create authenticated principal with subject, issuer, audience, expiry": "Principal",
    "Session or token integrity checks pass?": "Token valid?",
    "Reject replay, expired token, wrong audience, revoked session, or bad nonce": "Reject token",
    "Load identity attributes, groups, device posture, tenant, and risk signals": "Load context",
    "Normalize requested action, resource, data scope, and environment": "Normalize request",
    "Policy model selected?": "Policy model?",
    "Least-privilege policy allows action?": "Policy allows?",
    "Risk score or context requires step-up?": "Step-up needed?",
    "MFA, re-authentication, device attestation, or admin approval": "Step-up control",
    "Step-up satisfied?": "Step-up passed?",
    "Authorize operation and issue short-lived decision": "Authorize",
    "Enforce data filtering and field-level constraints": "Constrain data",
    "Audit decision with subject, resource, action, policy version, and reason": "Audit decision",
    "Policy, key, or account state changed?": "State changed?",
    "Invalidate cache/session/token and recompute decision": "Invalidate cache",
    "Observable signals: auth failures, denied actions, anomalous grants, latency": "Observability",
    "Prediction layer: simulate new role, policy, threat, or tenant boundary": "Policy simulation",
    "Physical system, material, lattice/model, or field theory": "Physical system",
    "Control variables: temperature, pressure, field, density, composition": "Control variables",
    "Define phases by symmetry, order parameter, and conserved quantities": "Define phases",
    "Select ensemble, boundary conditions, and finite-size scale": "Choose ensemble",
    "Construct free energy, partition function, or effective Hamiltonian": "Build model",
    "Multiple free-energy minima coexist?": "Minima coexist?",
    "First-order transition: metastability, nucleation barrier, latent heat": "First-order path",
    "Track hysteresis, spinodal limits, and phase coexistence line": "Coexistence line",
    "Order parameter changes discontinuously?": "Discontinuous?",
    "Continuous transition candidate": "Continuous path",
    "Correlation length grows and fluctuations dominate": "Correlation growth",
    "Susceptibility, heat capacity, and response functions diverge or peak": "Response peaks",
    "Mean-field assumptions valid?": "Mean-field valid?",
    "Use Landau expansion and mean-field critical exponents": "Landau model",
    "Use renormalization group or scaling ansatz": "RG/scaling model",
    "Finite-size or finite-time effects significant?": "Finite-size effects?",
    "Apply finite-size scaling or dynamic scaling collapse": "Scaling collapse",
    "Estimate thermodynamic-limit behavior": "Thermodynamic limit",
    "Disorder, frustration, or long-range forces relevant?": "Disorder relevant?",
    "Modify universality class or use percolation/glass/nonlocal model": "Modify class",
    "Identify dimension, symmetry, interaction range, and conservation laws": "Classify symmetry",
    "Assign universality class and critical exponents": "Universality class",
    "Observable evidence matches predicted scaling?": "Evidence matches?",
    "Compare experiment/simulation: diffraction, calorimetry, transport, magnetization": "Compare evidence",
    "Revise order parameter, model, or hidden variable hypothesis": "Revise model",
    "Feedback: update phase diagram and parameter boundaries": "Update diagram",
    "Output: phase diagram, transition order, critical point, exponents, uncertainties": "Phase diagram",
    "Prediction layer: perturb field, size, rate, impurity, pressure, or dimensionality": "Perturbation predictions",
}

COMPACT_EDGE_LABELS = {
    "no or intrinsic stress": "no / intrinsic",
    "no, BID/tBID amplifies mitochondria": "BID/tBID",
    "SMAC feedback if released": "SMAC",
    "repeat blank": "repeat",
    "recover surface": "recover",
    "credential returned": "returned",
    "attribute/relationship": "ABAC/ReBAC",
    "scope/capability": "scope",
    "role-based": "RBAC",
    "iterate model": "iterate",
}


def sanitize_label(label: str) -> str:
    return label.replace('"', "'").replace("\n", " ")


def compact_label(label: str) -> str:
    if label in COMPACT_LABELS:
        return COMPACT_LABELS[label]
    compact = re.sub(r"^(Observable readouts|Prediction layer|Feedback|Output):\s*", "", label)
    if len(compact) <= 28:
        return compact
    words = compact.split()
    return " ".join(words[:4]).rstrip(",;:") + "..."


def compact_edge_label(label: str) -> str:
    if label in COMPACT_EDGE_LABELS:
        return COMPACT_EDGE_LABELS[label]
    return label


def build_mermaid(nodes: list[Node], edges: list[Edge]) -> str:
    lines = ["graph TD"]
    for node_id, shape, label, _role in nodes:
        safe = sanitize_label(compact_label(label))
        if shape == "decision":
            lines.append(f'    {node_id}{{"{safe}"}}')
        else:
            lines.append(f'    {node_id}["{safe}"]')
    lines.append("")
    for source, target, label in edges:
        if label:
            lines.append(f'    {source} -->|{sanitize_label(compact_edge_label(label))}| {target}')
        else:
            lines.append(f"    {source} --> {target}")
    lines.append("")
    for node_id, _shape, _label, role in nodes:
        fill = COLOR_SCHEME[role]["hex"]
        text = "#000" if role == "yellow" else "#fff"
        lines.append(f"    style {node_id} fill:{fill},color:{text}")
    return "\n".join(lines)


def graph_metrics(nodes: list[Node], edges: list[Edge], *, and_gates: int, or_gates: int, not_gates: int, loops: int) -> dict[str, Any]:
    conditionals = sum(1 for _node_id, shape, _label, _role in nodes if shape == "decision")
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
        "level": "high",
        "detailLevel": "research_pilot",
        "loops": loops,
    }


def node_details(nodes: list[Node]) -> list[dict[str, str]]:
    return [
        {
            "id": node_id,
            "label": compact_label(label),
            "detail": label,
            "type": "decision" if shape == "decision" else "process",
            "role": COLOR_SCHEME[role]["category"],
        }
        for node_id, shape, label, role in nodes
    ]


def source(title: str, authors: str, journal: str, year: str, url: str, doi: str | None = None) -> dict[str, Any]:
    return {
        "title": title,
        "authors": authors,
        "journal": journal,
        "year": year,
        "pubmed": None,
        "doi": doi,
        "url": url,
    }


def update_json(path: Path, update: dict[str, Any]) -> None:
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = {}
    merged = deepcopy(data)
    merged.update(update)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def render_viewer(path: Path, discipline: str) -> None:
    create_process_viewer(path, path.parent, discipline=discipline)


def apoptosis_spec() -> tuple[list[Node], list[Edge], dict[str, Any]]:
    nodes: list[Node] = [
        ("A1", "process", "Extrinsic death ligand, intrinsic stress, or therapeutic perturbation", "red"),
        ("A2", "process", "Cell state context: cell type, cell-cycle phase, survival signaling, inhibitor levels", "red"),
        ("B1", "process", "Map stimulus class and compartment of origin", "yellow"),
        ("B2", "process", "Quantify damage/stress intensity and duration", "green"),
        ("D1", "decision", "Death receptor pathway engaged?", "blue"),
        ("E1", "process", "Fas/TNF/TRAIL receptor trimerization", "yellow"),
        ("E2", "process", "FADD/TRADD adaptor recruitment", "yellow"),
        ("E3", "process", "DISC assembly with procaspase-8/10", "green"),
        ("D2", "decision", "c-FLIP or decoy receptor blocks DISC?", "blue"),
        ("E4", "process", "Caspase-8 activation", "green"),
        ("D3", "decision", "Type I cell: effector caspases activated directly?", "blue"),
        ("I1", "process", "DNA damage, ER stress, ROS, growth-factor withdrawal, or oncogene stress", "red"),
        ("I2", "process", "p53, BH3-only proteins, JNK, or UPR sensors integrate stress", "green"),
        ("D4", "decision", "Anti-apoptotic BCL-2 family buffering exceeded?", "blue"),
        ("I3", "process", "BAX/BAK activation and oligomerization", "green"),
        ("I4", "process", "Mitochondrial outer membrane permeabilization", "green"),
        ("I5", "process", "Cytochrome c and SMAC/DIABLO released", "blue"),
        ("I6", "process", "Apaf-1 apoptosome assembles with procaspase-9", "yellow"),
        ("I7", "process", "Caspase-9 activation", "green"),
        ("C1", "process", "Initiator caspases converge on caspase-3/7", "green"),
        ("D5", "decision", "IAPs suppress executioner caspases?", "blue"),
        ("C2", "process", "SMAC relieves XIAP inhibition or survival branch persists", "green"),
        ("C3", "process", "Executioner caspases cleave PARP, ICAD, lamins, and cytoskeletal proteins", "green"),
        ("C4", "process", "CAD nuclease fragments DNA and chromatin condenses", "green"),
        ("C5", "process", "Membrane blebbing and apoptotic body formation", "green"),
        ("D6", "decision", "Phagocytes recognize eat-me signals?", "blue"),
        ("C6", "process", "Phosphatidylserine exposure recruits engulfment receptors", "yellow"),
        ("C7", "process", "Efferocytosis clears apoptotic bodies without inflammatory spillover", "green"),
        ("F1", "process", "Failed clearance causes secondary necrosis and DAMP release", "blue"),
        ("R1", "process", "Feedback: caspase-3 amplifies mitochondrial and receptor branches", "green"),
        ("R2", "process", "Regulatory brakes: NF-kB survival genes, PI3K-AKT, heat-shock proteins", "yellow"),
        ("O1", "process", "Observable readouts: Annexin V, caspase activity, TUNEL, mitochondrial potential", "violet"),
        ("O2", "process", "Prediction layer: perturb BCL-2, caspase-8, XIAP, or phagocytosis to shift outcome", "violet"),
    ]
    edges: list[Edge] = [
        ("A1", "B1", None),
        ("A2", "B2", None),
        ("B1", "D1", None),
        ("B2", "I2", None),
        ("D1", "E1", "yes"),
        ("D1", "I1", "no or intrinsic stress"),
        ("E1", "E2", None),
        ("E2", "E3", None),
        ("E3", "D2", None),
        ("D2", "R2", "yes"),
        ("D2", "E4", "no"),
        ("E4", "D3", None),
        ("D3", "C1", "yes"),
        ("D3", "I3", "no, BID/tBID amplifies mitochondria"),
        ("I1", "I2", None),
        ("I2", "D4", None),
        ("D4", "R2", "no"),
        ("D4", "I3", "yes"),
        ("I3", "I4", None),
        ("I4", "I5", None),
        ("I5", "I6", None),
        ("I6", "I7", None),
        ("I7", "C1", None),
        ("C1", "D5", None),
        ("D5", "C2", "yes"),
        ("C2", "C1", "SMAC feedback if released"),
        ("D5", "C3", "no"),
        ("C3", "C4", None),
        ("C4", "C5", None),
        ("C5", "D6", None),
        ("D6", "C6", "yes"),
        ("C6", "C7", None),
        ("D6", "F1", "no"),
        ("C3", "R1", None),
        ("R1", "I4", "amplify"),
        ("R2", "O2", None),
        ("C7", "O1", None),
        ("F1", "O1", None),
        ("O1", "O2", None),
    ]
    metrics = graph_metrics(nodes, edges, and_gates=5, or_gates=6, not_gates=3, loops=3)
    return nodes, edges, metrics


def cyclic_voltammetry_spec() -> tuple[list[Node], list[Edge], dict[str, Any]]:
    nodes: list[Node] = [
        ("A1", "process", "Research question: redox potential, kinetics, transport, adsorption, or mechanism", "red"),
        ("A2", "process", "Analyte, solvent, supporting electrolyte, concentration, and atmosphere", "red"),
        ("B1", "process", "Define potential window from thermodynamics and solvent stability", "yellow"),
        ("B2", "process", "Select working, reference, and counter electrodes", "yellow"),
        ("B3", "process", "Clean or polish working electrode", "green"),
        ("B4", "process", "Prepare blank electrolyte and analyte solution", "green"),
        ("D1", "decision", "Solution oxygen or impurity significant?", "blue"),
        ("B5", "process", "Degas, dry, filter, or remake solution", "green"),
        ("C1", "process", "Run blank scan to establish background current", "green"),
        ("D2", "decision", "Background stable and reference electrode valid?", "blue"),
        ("C2", "process", "Correct reference, cell wiring, iR compensation, or electrode surface", "green"),
        ("C3", "process", "Choose initial, vertex, final potentials and scan direction", "yellow"),
        ("C4", "process", "Set scan rate series and number of cycles", "yellow"),
        ("C5", "process", "Apply triangular potential waveform", "green"),
        ("C6", "process", "Measure current versus potential", "green"),
        ("C7", "process", "Forward scan oxidizes or reduces species", "green"),
        ("C8", "process", "Reverse scan probes product back reaction", "green"),
        ("D3", "decision", "Peak pair visible above noise?", "blue"),
        ("N1", "process", "Adjust concentration, scan rate, window, electrode area, or instrument gain", "green"),
        ("P1", "process", "Extract anodic/cathodic peak potentials and peak currents", "green"),
        ("D4", "decision", "Delta Ep and ipa/ipc indicate reversible electron transfer?", "blue"),
        ("R1", "process", "Reversible: estimate E0 prime and diffusion-controlled behavior", "violet"),
        ("Q1", "process", "Quasi-reversible/irreversible: estimate heterogeneous rate and transfer coefficient", "violet"),
        ("D5", "decision", "Peak current scales with square root of scan rate?", "blue"),
        ("M1", "process", "Diffusion control; use Randles-Sevcik relationship", "green"),
        ("M2", "process", "Adsorption, coupled chemistry, or uncompensated resistance likely", "blue"),
        ("D6", "decision", "New peaks appear on repeated cycles?", "blue"),
        ("M3", "process", "Electrode fouling, passivation, product adsorption, or follow-up reaction", "blue"),
        ("M4", "process", "Condition electrode or limit cycling", "green"),
        ("O1", "process", "Report voltammogram, conditions, corrections, controls, and uncertainty", "violet"),
        ("O2", "process", "Prediction layer: vary scan rate, concentration, pH, ligand, or electrode material", "violet"),
    ]
    edges: list[Edge] = [
        ("A1", "B1", None), ("A2", "B2", None), ("B1", "C3", None), ("B2", "B3", None),
        ("B3", "B4", None), ("B4", "D1", None), ("D1", "B5", "yes"), ("B5", "C1", None),
        ("D1", "C1", "no"), ("C1", "D2", None), ("D2", "C2", "no"), ("C2", "C1", "repeat blank"),
        ("D2", "C3", "yes"), ("C3", "C4", None), ("C4", "C5", None), ("C5", "C6", None),
        ("C6", "C7", None), ("C7", "C8", None), ("C8", "D3", None), ("D3", "N1", "no"),
        ("N1", "C4", "iterate"), ("D3", "P1", "yes"), ("P1", "D4", None), ("D4", "R1", "yes"),
        ("D4", "Q1", "no"), ("P1", "D5", None), ("D5", "M1", "yes"), ("D5", "M2", "no"),
        ("P1", "D6", None), ("D6", "M3", "yes"), ("M3", "M4", None), ("M4", "B3", "recover surface"),
        ("D6", "O1", "no"), ("R1", "O1", None), ("Q1", "O1", None), ("M1", "O1", None),
        ("M2", "O2", None), ("O1", "O2", None),
    ]
    metrics = graph_metrics(nodes, edges, and_gates=4, or_gates=6, not_gates=2, loops=4)
    return nodes, edges, metrics


def authz_spec() -> tuple[list[Node], list[Edge], dict[str, Any]]:
    nodes: list[Node] = [
        ("A1", "process", "Client requests protected resource or operation", "red"),
        ("A2", "process", "Threat model: spoofing, replay, privilege escalation, token theft", "red"),
        ("B1", "process", "Identify required assurance level and trust boundary", "yellow"),
        ("B2", "process", "Choose identity protocol: password, MFA, SSO, OAuth/OIDC, mTLS, API key", "yellow"),
        ("D1", "decision", "Credential or token presented?", "blue"),
        ("C1", "process", "Redirect to identity provider or challenge client", "green"),
        ("C2", "process", "Validate credential, factor, proof-of-possession, or signature", "green"),
        ("D2", "decision", "Authentication valid and fresh?", "blue"),
        ("F1", "process", "Deny, rate-limit, log, and optionally step-up challenge", "blue"),
        ("C3", "process", "Create authenticated principal with subject, issuer, audience, expiry", "green"),
        ("D3", "decision", "Session or token integrity checks pass?", "blue"),
        ("F2", "process", "Reject replay, expired token, wrong audience, revoked session, or bad nonce", "blue"),
        ("C4", "process", "Load identity attributes, groups, device posture, tenant, and risk signals", "yellow"),
        ("C5", "process", "Normalize requested action, resource, data scope, and environment", "yellow"),
        ("D4", "decision", "Policy model selected?", "blue"),
        ("P1", "process", "RBAC role expansion", "green"),
        ("P2", "process", "ABAC/ReBAC policy evaluation", "green"),
        ("P3", "process", "Capability, scope, or entitlement check", "green"),
        ("D5", "decision", "Least-privilege policy allows action?", "blue"),
        ("F3", "process", "Deny by default and return safe error", "blue"),
        ("D6", "decision", "Risk score or context requires step-up?", "blue"),
        ("C6", "process", "MFA, re-authentication, device attestation, or admin approval", "green"),
        ("D7", "decision", "Step-up satisfied?", "blue"),
        ("C7", "process", "Authorize operation and issue short-lived decision", "violet"),
        ("C8", "process", "Enforce data filtering and field-level constraints", "green"),
        ("C9", "process", "Audit decision with subject, resource, action, policy version, and reason", "green"),
        ("D8", "decision", "Policy, key, or account state changed?", "blue"),
        ("R1", "process", "Invalidate cache/session/token and recompute decision", "green"),
        ("O1", "process", "Observable signals: auth failures, denied actions, anomalous grants, latency", "violet"),
        ("O2", "process", "Prediction layer: simulate new role, policy, threat, or tenant boundary", "violet"),
    ]
    edges: list[Edge] = [
        ("A1", "B1", None), ("A2", "B1", None), ("B1", "B2", None), ("B2", "D1", None),
        ("D1", "C1", "no"), ("C1", "C2", "credential returned"), ("D1", "C2", "yes"),
        ("C2", "D2", None), ("D2", "F1", "no"), ("D2", "C3", "yes"), ("C3", "D3", None),
        ("D3", "F2", "no"), ("D3", "C4", "yes"), ("C4", "C5", None), ("C5", "D4", None),
        ("D4", "P1", "role-based"), ("D4", "P2", "attribute/relationship"), ("D4", "P3", "scope/capability"),
        ("P1", "D5", None), ("P2", "D5", None), ("P3", "D5", None), ("D5", "F3", "no"),
        ("D5", "D6", "yes"), ("D6", "C6", "yes"), ("C6", "D7", None), ("D7", "F3", "no"),
        ("D7", "C7", "yes"), ("D6", "C7", "no"), ("C7", "C8", None), ("C8", "C9", None),
        ("C9", "D8", None), ("D8", "R1", "yes"), ("R1", "C4", "refresh"), ("D8", "O1", "no"),
        ("F1", "O1", None), ("F2", "O1", None), ("F3", "O1", None), ("O1", "O2", None),
    ]
    metrics = graph_metrics(nodes, edges, and_gates=5, or_gates=8, not_gates=4, loops=2)
    return nodes, edges, metrics


def phase_transition_spec() -> tuple[list[Node], list[Edge], dict[str, Any]]:
    nodes: list[Node] = [
        ("A1", "process", "Physical system, material, lattice/model, or field theory", "red"),
        ("A2", "process", "Control variables: temperature, pressure, field, density, composition", "red"),
        ("B1", "process", "Define phases by symmetry, order parameter, and conserved quantities", "yellow"),
        ("B2", "process", "Select ensemble, boundary conditions, and finite-size scale", "yellow"),
        ("C1", "process", "Construct free energy, partition function, or effective Hamiltonian", "green"),
        ("D1", "decision", "Multiple free-energy minima coexist?", "blue"),
        ("F1", "process", "First-order transition: metastability, nucleation barrier, latent heat", "green"),
        ("F2", "process", "Track hysteresis, spinodal limits, and phase coexistence line", "green"),
        ("D2", "decision", "Order parameter changes discontinuously?", "blue"),
        ("S1", "process", "Continuous transition candidate", "green"),
        ("S2", "process", "Correlation length grows and fluctuations dominate", "green"),
        ("S3", "process", "Susceptibility, heat capacity, and response functions diverge or peak", "green"),
        ("D3", "decision", "Mean-field assumptions valid?", "blue"),
        ("M1", "process", "Use Landau expansion and mean-field critical exponents", "green"),
        ("M2", "process", "Use renormalization group or scaling ansatz", "green"),
        ("D4", "decision", "Finite-size or finite-time effects significant?", "blue"),
        ("N1", "process", "Apply finite-size scaling or dynamic scaling collapse", "green"),
        ("N2", "process", "Estimate thermodynamic-limit behavior", "green"),
        ("D5", "decision", "Disorder, frustration, or long-range forces relevant?", "blue"),
        ("X1", "process", "Modify universality class or use percolation/glass/nonlocal model", "green"),
        ("U1", "process", "Identify dimension, symmetry, interaction range, and conservation laws", "yellow"),
        ("U2", "process", "Assign universality class and critical exponents", "violet"),
        ("D6", "decision", "Observable evidence matches predicted scaling?", "blue"),
        ("E1", "process", "Compare experiment/simulation: diffraction, calorimetry, transport, magnetization", "green"),
        ("E2", "process", "Revise order parameter, model, or hidden variable hypothesis", "blue"),
        ("R1", "process", "Feedback: update phase diagram and parameter boundaries", "green"),
        ("O1", "process", "Output: phase diagram, transition order, critical point, exponents, uncertainties", "violet"),
        ("O2", "process", "Prediction layer: perturb field, size, rate, impurity, pressure, or dimensionality", "violet"),
    ]
    edges: list[Edge] = [
        ("A1", "B1", None), ("A2", "B2", None), ("B1", "C1", None), ("B2", "C1", None),
        ("C1", "D1", None), ("D1", "F1", "yes"), ("F1", "F2", None), ("F2", "D2", None),
        ("D1", "S1", "no"), ("S1", "S2", None), ("S2", "S3", None), ("S3", "D2", None),
        ("D2", "U1", "classify"), ("D2", "F1", "discontinuous"), ("U1", "D3", None),
        ("D3", "M1", "yes"), ("D3", "M2", "no"), ("M1", "D4", None), ("M2", "D4", None),
        ("D4", "N1", "yes"), ("D4", "N2", "no"), ("N1", "D5", None), ("N2", "D5", None),
        ("D5", "X1", "yes"), ("D5", "U2", "no"), ("X1", "U2", None), ("U2", "E1", None),
        ("E1", "D6", None), ("D6", "E2", "no"), ("E2", "R1", None), ("R1", "C1", "iterate model"),
        ("D6", "O1", "yes"), ("O1", "O2", None), ("F2", "O1", None), ("S3", "O1", None),
    ]
    metrics = graph_metrics(nodes, edges, and_gates=4, or_gates=6, not_gates=1, loops=2)
    return nodes, edges, metrics


def p53_damage_spec() -> tuple[list[Node], list[Edge], dict[str, Any]]:
    nodes: list[Node] = [
        ("A1", "process", "DNA damage trigger", "red"),
        ("A2", "process", "Cell context", "red"),
        ("B1", "process", "ATM/ATR sensing", "yellow"),
        ("B2", "process", "CHK1/CHK2 relay", "green"),
        ("C1", "process", "MDM2 inhibition", "green"),
        ("C2", "process", "p53 stabilization", "green"),
        ("D1", "decision", "Damage repairable?", "blue"),
        ("R1", "process", "p21 induction", "green"),
        ("R2", "process", "Cell-cycle arrest", "green"),
        ("R3", "process", "DNA repair genes", "green"),
        ("D2", "decision", "Repair succeeds?", "blue"),
        ("S1", "process", "Checkpoint release", "green"),
        ("S2", "process", "Survival outcome", "violet"),
        ("F1", "process", "Persistent damage", "blue"),
        ("D3", "decision", "Stress severe?", "blue"),
        ("P1", "process", "PUMA/NOXA/BAX", "green"),
        ("P2", "process", "Mitochondrial apoptosis", "green"),
        ("P3", "process", "Caspase execution", "green"),
        ("N1", "process", "Senescence program", "green"),
        ("N2", "process", "SASP monitoring", "blue"),
        ("D4", "decision", "p53 disabled?", "blue"),
        ("E1", "process", "Genome instability", "blue"),
        ("E2", "process", "Therapy resistance risk", "blue"),
        ("O1", "process", "Readouts", "violet"),
        ("O2", "process", "Perturbation predictions", "violet"),
    ]
    edges: list[Edge] = [
        ("A1", "B1", None), ("A2", "D4", None), ("B1", "B2", None), ("B2", "C1", None),
        ("C1", "C2", None), ("C2", "D1", None), ("D1", "R1", "yes"), ("R1", "R2", None),
        ("R2", "R3", None), ("R3", "D2", None), ("D2", "S1", "yes"), ("S1", "S2", None),
        ("D2", "F1", "no"), ("D1", "F1", "no"), ("F1", "D3", None), ("D3", "N1", "moderate"),
        ("N1", "N2", None), ("D3", "P1", "severe"), ("P1", "P2", None), ("P2", "P3", None),
        ("D4", "E1", "yes"), ("E1", "E2", None), ("D4", "C2", "no"), ("P3", "O1", None),
        ("N2", "O1", None), ("S2", "O1", None), ("E2", "O2", None), ("O1", "O2", None),
    ]
    metrics = graph_metrics(nodes, edges, and_gates=3, or_gates=4, not_gates=2, loops=1)
    return nodes, edges, metrics


def suzuki_coupling_spec() -> tuple[list[Node], list[Edge], dict[str, Any]]:
    nodes: list[Node] = [
        ("A1", "process", "Aryl halide partner", "red"),
        ("A2", "process", "Organoboron partner", "red"),
        ("A3", "process", "Catalyst/base/solvent", "red"),
        ("B1", "process", "Substrate screen", "yellow"),
        ("D1", "decision", "Oxidative addition feasible?", "blue"),
        ("C1", "process", "Pd(0) activation", "green"),
        ("C2", "process", "Oxidative addition", "green"),
        ("D2", "decision", "Base activates boronate?", "blue"),
        ("C3", "process", "Boronate formation", "green"),
        ("C4", "process", "Transmetalation", "green"),
        ("D3", "decision", "Ligand supports coupling?", "blue"),
        ("C5", "process", "Reductive elimination", "green"),
        ("O1", "process", "Biaryl product", "violet"),
        ("F1", "process", "Protodeboronation", "blue"),
        ("F2", "process", "Homocoupling", "blue"),
        ("F3", "process", "Catalyst deactivation", "blue"),
        ("R1", "process", "Optimize ligand/base", "green"),
        ("R2", "process", "Adjust water/temperature", "green"),
        ("D4", "decision", "Yield/selectivity acceptable?", "blue"),
        ("Q1", "process", "LC/NMR/GC-MS assay", "green"),
        ("O2", "process", "Optimization map", "violet"),
        ("O3", "process", "Prediction layer", "violet"),
    ]
    edges: list[Edge] = [
        ("A1", "B1", None), ("A2", "B1", None), ("A3", "C1", None), ("B1", "D1", None),
        ("D1", "R1", "no"), ("D1", "C2", "yes"), ("C1", "C2", None), ("C2", "D2", None),
        ("D2", "R2", "no"), ("D2", "C3", "yes"), ("C3", "C4", None), ("C4", "D3", None),
        ("D3", "R1", "no"), ("D3", "C5", "yes"), ("C5", "O1", None), ("C3", "F1", "side"),
        ("C4", "F2", "side"), ("C1", "F3", "side"), ("R1", "C1", "iterate"), ("R2", "C3", "iterate"),
        ("O1", "Q1", None), ("F1", "Q1", None), ("F2", "Q1", None), ("F3", "Q1", None),
        ("Q1", "D4", None), ("D4", "O2", "yes"), ("D4", "R1", "no"), ("O2", "O3", None),
    ]
    metrics = graph_metrics(nodes, edges, and_gates=4, or_gates=4, not_gates=1, loops=3)
    return nodes, edges, metrics


def tcp_congestion_spec() -> tuple[list[Node], list[Edge], dict[str, Any]]:
    nodes: list[Node] = [
        ("A1", "process", "Application sends data", "red"),
        ("A2", "process", "Network path conditions", "red"),
        ("B1", "process", "Initialize cwnd/ssthresh", "yellow"),
        ("C1", "process", "Slow start", "green"),
        ("D1", "decision", "ACKs arrive?", "blue"),
        ("C2", "process", "Increase cwnd quickly", "green"),
        ("D2", "decision", "cwnd >= ssthresh?", "blue"),
        ("C3", "process", "Congestion avoidance", "green"),
        ("C4", "process", "Additive increase", "green"),
        ("D3", "decision", "Loss detected?", "blue"),
        ("L1", "process", "Triple duplicate ACK", "blue"),
        ("L2", "process", "Timeout", "blue"),
        ("R1", "process", "Fast retransmit", "green"),
        ("R2", "process", "Fast recovery", "green"),
        ("R3", "process", "Reset cwnd", "green"),
        ("D4", "decision", "ECN mark?", "blue"),
        ("E1", "process", "Reduce sending rate", "green"),
        ("D5", "decision", "RTT/jitter rising?", "blue"),
        ("Q1", "process", "Queue buildup signal", "blue"),
        ("O1", "process", "Throughput/latency", "violet"),
        ("O2", "process", "Fairness/stability", "violet"),
        ("O3", "process", "Prediction layer", "violet"),
    ]
    edges: list[Edge] = [
        ("A1", "B1", None), ("A2", "D5", None), ("B1", "C1", None), ("C1", "D1", None),
        ("D1", "C2", "yes"), ("D1", "L2", "no"), ("C2", "D2", None), ("D2", "C1", "no"),
        ("D2", "C3", "yes"), ("C3", "C4", None), ("C4", "D3", None), ("D3", "L1", "dup ACK"),
        ("D3", "L2", "timeout"), ("D3", "D4", "no"), ("L1", "R1", None), ("R1", "R2", None),
        ("R2", "C3", "recover"), ("L2", "R3", None), ("R3", "C1", "restart"), ("D4", "E1", "yes"),
        ("E1", "C3", "continue"), ("D4", "O1", "no"), ("D5", "Q1", "yes"), ("Q1", "E1", None),
        ("D5", "O1", "no"), ("O1", "O2", None), ("O2", "O3", None),
    ]
    metrics = graph_metrics(nodes, edges, and_gates=3, or_gates=5, not_gates=1, loops=4)
    return nodes, edges, metrics


def hamiltonian_spec() -> tuple[list[Node], list[Edge], dict[str, Any]]:
    nodes: list[Node] = [
        ("A1", "process", "Physical system", "red"),
        ("A2", "process", "Coordinates and momenta", "red"),
        ("B1", "process", "Choose generalized variables", "yellow"),
        ("B2", "process", "Define constraints", "yellow"),
        ("C1", "process", "Build Lagrangian", "green"),
        ("D1", "decision", "Legendre transform valid?", "blue"),
        ("C2", "process", "Canonical momenta", "green"),
        ("C3", "process", "Hamiltonian H(q,p,t)", "green"),
        ("D2", "decision", "Explicit time dependence?", "blue"),
        ("E1", "process", "Energy not conserved", "blue"),
        ("E2", "process", "Energy conserved candidate", "green"),
        ("C4", "process", "Hamilton equations", "green"),
        ("D3", "decision", "Symmetry present?", "blue"),
        ("S1", "process", "Conserved quantity", "green"),
        ("C5", "process", "Phase-space trajectory", "green"),
        ("D4", "decision", "Integrable system?", "blue"),
        ("I1", "process", "Action-angle variables", "green"),
        ("K1", "process", "Numerical symplectic integration", "green"),
        ("D5", "decision", "Constraints/gauge?", "blue"),
        ("G1", "process", "Dirac constraint analysis", "green"),
        ("O1", "process", "Observables", "violet"),
        ("O2", "process", "Prediction layer", "violet"),
    ]
    edges: list[Edge] = [
        ("A1", "B1", None), ("A2", "B1", None), ("B1", "B2", None), ("B2", "C1", None),
        ("C1", "D1", None), ("D1", "C2", "yes"), ("D1", "G1", "no"), ("C2", "C3", None),
        ("C3", "D2", None), ("D2", "E1", "yes"), ("D2", "E2", "no"), ("E1", "C4", None),
        ("E2", "C4", None), ("C4", "D3", None), ("D3", "S1", "yes"), ("D3", "C5", "no"),
        ("S1", "C5", None), ("C5", "D4", None), ("D4", "I1", "yes"), ("D4", "K1", "no"),
        ("I1", "O1", None), ("K1", "O1", None), ("C3", "D5", None), ("D5", "G1", "yes"),
        ("G1", "C4", None), ("O1", "O2", None),
    ]
    metrics = graph_metrics(nodes, edges, and_gates=3, or_gates=5, not_gates=1, loops=1)
    return nodes, edges, metrics


PILOTS = [
    {
        "path": BASE_DIR / "biology-processes-database/processes/pathways/pathways-apoptosis.json",
        "discipline": "biology",
        "id": "pathways-apoptosis",
        "name": "Apoptosis Pathway",
        "category": "biology",
        "subcategory": "pathways",
        "subcategory_name": "Pathways",
        "description": "Research-grade pilot map of apoptosis as an integrated extrinsic/intrinsic cell-death decision network, including receptor signaling, mitochondrial commitment, caspase execution, regulatory brakes, clearance, observables, and perturbation points.",
        "keywords": ["apoptosis", "caspases", "BCL-2 family", "mitochondria", "death receptor", "efferocytosis"],
        "namedCollections": ["signaling-cell-fate"],
        "spec": apoptosis_spec,
        "sources": [
            source("Molecular mechanisms of apoptosis", "Elmore, S.", "Toxicologic Pathology", "2007", "https://doi.org/10.1080/01926230701320337", "10.1080/01926230701320337"),
            source("The BCL-2 protein family: opposing activities that mediate cell death", "Cory, S.; Adams, J. M.", "Nature Reviews Cancer", "2002", "https://doi.org/10.1038/nrc883", "10.1038/nrc883"),
            source("Caspases: enemies within", "Thornberry, N. A.; Lazebnik, Y.", "Science", "1998", "https://doi.org/10.1126/science.281.5381.1312", "10.1126/science.281.5381.1312"),
        ],
    },
    {
        "path": BASE_DIR / "chemistry-processes-database/processes/electrochemistry/electrochemistry-cyclic-voltammetry.json",
        "discipline": "chemistry",
        "id": "electrochemistry-cyclic-voltammetry",
        "name": "Cyclic Voltammetry",
        "category": "chemistry",
        "subcategory": "electrochemistry",
        "subcategory_name": "Electrochemistry",
        "description": "Research-grade pilot map of cyclic voltammetry as an experimental decision workflow connecting cell preparation, potential programming, voltammogram interpretation, transport/kinetic diagnostics, artifacts, and perturbation-driven predictions.",
        "keywords": ["cyclic voltammetry", "electrochemistry", "redox", "scan rate", "Randles-Sevcik", "electrode kinetics"],
        "spec": cyclic_voltammetry_spec,
        "sources": [
            source("Understanding Voltammetry", "Compton, R. G.; Banks, C. E.", "World Scientific", "2018", "https://doi.org/10.1142/q0155", "10.1142/q0155"),
            source("Cyclic Voltammetry and Its Applications", "Chooto, P.", "Voltammetry", "2019", "https://doi.org/10.5772/intechopen.83451", "10.5772/intechopen.83451"),
            source("Electrochemical Methods: Fundamentals and Applications", "Bard, A. J.; Faulkner, L. R.", "Wiley", "2001", "https://www.wiley.com/en-us/Electrochemical+Methods%3A+Fundamentals+and+Applications%2C+2nd+Edition-p-9780471043720"),
        ],
    },
    {
        "path": BASE_DIR / "computer-science-processes-database/processes/security/security-authentication-and-authorization.json",
        "discipline": "computer-science",
        "id": "security-authentication-and-authorization",
        "name": "Authentication and Authorization",
        "category": "computer_science",
        "subcategory": "security",
        "subcategory_name": "Security & Cryptography",
        "description": "Research-grade pilot map of authentication and authorization as a zero-trust access decision workflow, including identity proofing, token validation, policy evaluation, step-up controls, auditability, cache invalidation, and threat-informed observability.",
        "keywords": ["authentication", "authorization", "OAuth", "OIDC", "RBAC", "ABAC", "zero trust", "policy enforcement"],
        "spec": authz_spec,
        "sources": [
            source("OAuth 2.0 Authorization Framework", "Hardt, D.", "RFC 6749", "2012", "https://doi.org/10.17487/RFC6749", "10.17487/RFC6749"),
            source("OpenID Connect Core 1.0", "Sakimura, N.; Bradley, J.; Jones, M.; de Medeiros, B.; Mortimore, C.", "OpenID Foundation", "2014", "https://openid.net/specs/openid-connect-core-1_0.html"),
            source("Zero Trust Architecture", "Rose, S.; Borchert, O.; Mitchell, S.; Connelly, S.", "NIST SP 800-207", "2020", "https://doi.org/10.6028/NIST.SP.800-207", "10.6028/NIST.SP.800-207"),
        ],
    },
    {
        "path": BASE_DIR / "physics-processes-database/processes/thermodynamics_statistical/thermodynamics_statistical-phase-transition.json",
        "discipline": "physics",
        "id": "thermodynamics_statistical-phase-transition",
        "name": "Phase Transition",
        "category": "physics",
        "subcategory": "thermodynamics_statistical",
        "subcategory_name": "Thermodynamics & Statistical Physics",
        "description": "Research-grade pilot map of phase transitions as a regime-aware modeling workflow linking order parameters, free-energy landscapes, transition order, critical scaling, universality, finite-size effects, evidence, and predictive perturbations.",
        "keywords": ["phase transition", "critical phenomena", "order parameter", "renormalization group", "universality", "finite-size scaling"],
        "spec": phase_transition_spec,
        "sources": [
            source("The Renormalization Group: Critical Phenomena and the Kondo Problem", "Wilson, K. G.", "Reviews of Modern Physics", "1975", "https://doi.org/10.1103/RevModPhys.47.773", "10.1103/RevModPhys.47.773"),
            source("Renormalization Group Theory of Critical Phenomena", "Fisher, M. E.", "Reviews of Modern Physics", "1983", "https://doi.org/10.1103/RevModPhys.55.805", "10.1103/RevModPhys.55.805"),
            source("Computational studies of phase transitions and critical phenomena", "Binder, K.", "Reviews of Modern Physics", "2015", "https://doi.org/10.1103/RevModPhys.87.867", "10.1103/RevModPhys.87.867"),
        ],
    },
    {
        "path": BASE_DIR / "biology-processes-database/processes/pathways/pathways-p53-dna-damage-response.json",
        "discipline": "biology",
        "id": "pathways-p53-dna-damage-response",
        "name": "p53 DNA Damage Response",
        "category": "biology",
        "subcategory": "pathways",
        "subcategory_name": "Pathways",
        "description": "Research-grade compact map of p53 DNA damage response as a cell-fate decision system linking damage sensing, p53 stabilization, arrest and repair, senescence, apoptosis, loss-of-function risk, observables, and perturbation points.",
        "keywords": ["p53", "DNA damage", "checkpoint", "apoptosis", "senescence", "MDM2"],
        "namedCollections": ["signaling-cell-fate"],
        "spec": p53_damage_spec,
        "sources": [
            source("p53, guardian of the genome", "Lane, D. P.", "Nature", "1992", "https://doi.org/10.1038/358015a0", "10.1038/358015a0"),
            source("The regulation of p53 by Mdm2", "Michael, D.; Oren, M.", "Seminars in Cancer Biology", "2003", "https://doi.org/10.1016/S1044-579X(03)00066-7", "10.1016/S1044-579X(03)00066-7"),
            source("p53 in health and disease", "Vousden, K. H.; Lane, D. P.", "Nature Reviews Molecular Cell Biology", "2007", "https://doi.org/10.1038/nrm2147", "10.1038/nrm2147"),
        ],
    },
    {
        "path": BASE_DIR / "chemistry-processes-database/processes/organic_chemistry/organic_chemistry-suzuki-coupling.json",
        "discipline": "chemistry",
        "id": "organic_chemistry-suzuki-coupling",
        "name": "Suzuki Coupling",
        "category": "chemistry",
        "subcategory": "organic_chemistry",
        "subcategory_name": "Organic Chemistry",
        "description": "Research-grade compact map of Suzuki coupling as a catalytic-cycle and optimization workflow covering oxidative addition, boronate activation, transmetalation, reductive elimination, side reactions, analytical readouts, and predictive condition changes.",
        "keywords": ["Suzuki coupling", "cross-coupling", "palladium catalysis", "transmetalation", "biaryl synthesis"],
        "spec": suzuki_coupling_spec,
        "sources": [
            source("Palladium-catalyzed cross-coupling reactions of organoboron compounds", "Miyaura, N.; Suzuki, A.", "Chemical Reviews", "1995", "https://doi.org/10.1021/cr00039a007", "10.1021/cr00039a007"),
            source("Recent advances in the Suzuki-Miyaura cross-coupling reaction", "Kotha, S.; Lahiri, K.; Kashinath, D.", "Tetrahedron", "2002", "https://doi.org/10.1016/S0040-4020(02)00486-9", "10.1016/S0040-4020(02)00486-9"),
            source("Palladium-Catalyzed Cross-Coupling Reactions in the Synthesis of Pharmaceuticals", "Magano, J.; Dunetz, J. R.", "Chemical Reviews", "2011", "https://doi.org/10.1021/cr100346g", "10.1021/cr100346g"),
        ],
    },
    {
        "path": BASE_DIR / "computer-science-processes-database/processes/networks/networks-tcp-congestion-control.json",
        "discipline": "computer-science",
        "id": "networks-tcp-congestion-control",
        "name": "TCP Congestion Control",
        "category": "computer_science",
        "subcategory": "networks",
        "subcategory_name": "Computer Networks",
        "description": "Research-grade compact map of TCP congestion control as a feedback system linking ACKs, congestion window dynamics, slow start, congestion avoidance, loss signals, ECN, queue buildup, recovery, fairness, and prediction points.",
        "keywords": ["TCP", "congestion control", "slow start", "AIMD", "packet loss", "ECN"],
        "spec": tcp_congestion_spec,
        "sources": [
            source("Congestion Avoidance and Control", "Jacobson, V.", "ACM SIGCOMM", "1988", "https://doi.org/10.1145/52324.52356", "10.1145/52324.52356"),
            source("TCP Congestion Control", "Allman, M.; Paxson, V.; Blanton, E.", "RFC 5681", "2009", "https://doi.org/10.17487/RFC5681", "10.17487/RFC5681"),
            source("The Addition of Explicit Congestion Notification (ECN) to IP", "Ramakrishnan, K.; Floyd, S.; Black, D.", "RFC 3168", "2001", "https://doi.org/10.17487/RFC3168", "10.17487/RFC3168"),
        ],
    },
    {
        "path": BASE_DIR / "physics-processes-database/processes/classical_mechanics/classical_mechanics-hamiltonian-mechanics.json",
        "discipline": "physics",
        "id": "classical_mechanics-hamiltonian-mechanics",
        "name": "Hamiltonian Mechanics",
        "category": "physics",
        "subcategory": "classical_mechanics",
        "subcategory_name": "Classical Mechanics",
        "description": "Research-grade compact map of Hamiltonian mechanics as a modeling workflow connecting generalized variables, Legendre transforms, canonical equations, symmetries, conservation laws, constraints, integrability, numerical integration, observables, and predictions.",
        "keywords": ["Hamiltonian mechanics", "phase space", "canonical equations", "symplectic integration", "conservation laws"],
        "spec": hamiltonian_spec,
        "sources": [
            source("Classical Mechanics", "Goldstein, H.; Poole, C.; Safko, J.", "Addison-Wesley", "2002", "https://www.pearson.com/en-us/subject-catalog/p/classical-mechanics/P200000006187"),
            source("Mathematical Methods of Classical Mechanics", "Arnold, V. I.", "Springer", "1989", "https://doi.org/10.1007/978-1-4757-2063-1", "10.1007/978-1-4757-2063-1"),
            source("Geometric Numerical Integration", "Hairer, E.; Lubich, C.; Wanner, G.", "Springer", "2006", "https://doi.org/10.1007/3-540-30666-8", "10.1007/3-540-30666-8"),
        ],
    },
]


def update_metadata_summary(process_id: str, path: Path, metrics: dict[str, Any]) -> None:
    database_dir = path.parents[2]
    metadata_path = database_dir / "metadata.json"
    if not metadata_path.exists():
        return
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    for process in metadata.get("processes", []):
        if process.get("id") != process_id:
            continue
        process["complexity"] = "high"
        process["nodes"] = metrics["nodes"]
        process["edges"] = metrics["edges"]
        process["conditionals"] = metrics["conditionals"]
        process["orGates"] = metrics["logicGates"]["orGates"]
        process["andGates"] = metrics["logicGates"]["andGates"]
        process["notGates"] = metrics["logicGates"]["notGates"]
        process["loops"] = metrics["loops"]
        break
    metadata["lastUpdated"] = date.today().isoformat()
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    today = date.today().isoformat()
    for pilot in PILOTS:
        nodes, edges, metrics = pilot["spec"]()
        mermaid = build_mermaid(nodes, edges)
        path = pilot["path"]
        process_id = pilot.get("id") or json.loads(path.read_text(encoding="utf-8"))["id"]
        name = pilot.get("name") or json.loads(path.read_text(encoding="utf-8"))["name"]
        update = {
            "id": process_id,
            "name": name,
            "category": pilot.get("category") or pilot["discipline"].replace("-", "_"),
            "subcategory": pilot.get("subcategory"),
            "subcategory_name": pilot.get("subcategory_name"),
            "description": pilot["description"],
            "complexity": metrics,
            "graphMetrics": {
                "nodes": metrics["nodes"],
                "edges": metrics["edges"],
                "conditionals": metrics["conditionals"],
                "andGates": metrics["logicGates"]["andGates"],
                "orGates": metrics["logicGates"]["orGates"],
                "notGates": metrics["logicGates"]["notGates"],
                "loops": metrics["loops"],
            },
            "colorScheme": COLOR_SCHEME,
            "mermaid": mermaid,
            "nodeDetails": node_details(nodes),
            "sources": pilot["sources"],
            "keywords": pilot["keywords"],
            "researchEnhancements": {
                "pilot": True,
                "model": "research_grade_flowchart",
                "nodeSemantics": ["trigger", "context", "decision", "operation", "state", "feedback", "observable", "prediction"],
                "reviewFocus": ["mechanistic correctness", "decision density", "evidence support", "intervention value"],
            },
            "lastUpdated": today,
            "verified": False,
            "notes": "Research-grade pilot enhancement: expanded from summary flowchart to condition-rich map with observables, feedback, failure/edge cases, and prediction points.",
        }
        if pilot.get("namedCollections"):
            update["namedCollections"] = pilot["namedCollections"]
        update_json(path, update)
        update_metadata_summary(str(process_id), path, metrics)
        render_viewer(path, pilot["discipline"])
        print(f"updated {path.relative_to(BASE_DIR)}: {metrics['nodes']} nodes, {metrics['conditionals']} conditionals")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
