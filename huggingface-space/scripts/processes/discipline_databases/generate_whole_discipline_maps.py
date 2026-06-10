#!/usr/bin/env python3
"""
Generate candidate "Whole of ..." maps for discipline process databases.

The goal is to evaluate multiple visualization models before treating the
node-and-spoke force map as the default for every subject. Each generated
graph-data file contains several variants over the same process corpus:

- taxonomy: root -> subcategory -> process
- lens: root -> curated collection/lens -> process
- discipline-specific recommended model

The matching HTML viewer lets users switch variants and layout modes.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[3]
GENERATOR_DIR = Path(__file__).resolve().parent
PROFILE_FILE = GENERATOR_DIR / "discipline_profiles.json"

TARGET_DISCIPLINES = ("chemistry", "physics", "computer_science")

DISCIPLINE_OUTPUT = {
    "chemistry": {
        "title": "Whole of Chemistry",
        "file": "whole-of-chemistry.html",
        "data": "whole-of-chemistry-graph-data.json",
        "primary": "reaction_mechanism_hybrid",
        "summary": "Chemistry benefits from a hybrid of branch taxonomy, reaction families, analytical methods, materials systems, and process links.",
    },
    "physics": {
        "title": "Whole of Physics",
        "file": "whole-of-physics.html",
        "data": "whole-of-physics-graph-data.json",
        "primary": "regime_theory_map",
        "summary": "Physics is best treated as a regime/theory map over scales, governing laws, observables, and processes.",
    },
    "computer_science": {
        "title": "Whole of Computer Science",
        "file": "whole-of-computer-science.html",
        "data": "whole-of-computer-science-graph-data.json",
        "primary": "abstraction_stack",
        "summary": "Computer Science is strongest as a layered abstraction stack with dependency and process links.",
    },
}

MODEL_RUBRIC = {
    "force": "Best for exploratory browsing and cross-links.",
    "radial": "Best for hierarchy comprehension and compact coverage.",
    "layered": "Best for prerequisites, regimes, stacks, and conceptual direction.",
}

CHEMISTRY_FAMILIES = [
    {
        "id": "molecular_transformations",
        "name": "Molecular Transformations",
        "description": "Bond formation, bond breaking, organic and inorganic reaction mechanisms.",
        "terms": ["reaction", "mechanism", "organic", "inorganic", "coupling", "grignard", "substitution", "esterification", "condensation", "catalysis"],
    },
    {
        "id": "measurement_instrumentation",
        "name": "Measurement and Instrumentation",
        "description": "Analytical workflows, spectroscopy, chromatography, calibration, and validation.",
        "terms": ["analytical", "calibration", "spectroscopy", "chromatography", "nmr", "raman", "mass", "x-ray", "analysis"],
    },
    {
        "id": "materials_surfaces",
        "name": "Materials and Surfaces",
        "description": "Materials chemistry, surface chemistry, polymers, crystals, adsorption, and defects.",
        "terms": ["materials", "surface", "polymer", "crystal", "nanomaterial", "adsorption", "thin film", "defect"],
    },
    {
        "id": "energy_equilibrium",
        "name": "Energy, Equilibrium, and Rates",
        "description": "Thermodynamics, kinetics, electrochemistry, equilibrium, and reaction rates.",
        "terms": ["thermo", "kinetic", "rate", "equilibrium", "entropy", "gibbs", "electro", "arrhenius"],
    },
    {
        "id": "models_and_computation",
        "name": "Models and Computation",
        "description": "Quantum chemistry, theoretical chemistry, DFT, molecular dynamics, and computational models.",
        "terms": ["quantum", "theoretical", "computational", "dft", "molecular dynamics", "orbital", "electronic"],
    },
]

PHYSICS_REGIMES = [
    {
        "id": "classical_macro",
        "name": "Classical and Macroscopic",
        "description": "Newtonian, Lagrangian, Hamiltonian, fluids, waves, and macroscopic mechanics.",
        "terms": ["classical", "newton", "lagrangian", "hamiltonian", "mechanics", "force", "momentum", "fluid"],
    },
    {
        "id": "electromagnetic_optical",
        "name": "Electromagnetic and Optical",
        "description": "Maxwell systems, induction, light, optics, and electromagnetic waves.",
        "terms": ["electromagnetic", "maxwell", "induction", "optics", "wave", "light"],
    },
    {
        "id": "thermal_statistical",
        "name": "Thermal and Statistical",
        "description": "Heat, entropy, phase transitions, ensembles, and thermodynamic regimes.",
        "terms": ["thermal", "thermodynamic", "statistical", "heat", "entropy", "phase"],
    },
    {
        "id": "quantum_fields",
        "name": "Quantum, Particles, and Fields",
        "description": "Quantum states, fields, particles, symmetry, and high-energy processes.",
        "terms": ["quantum", "field", "particle", "higgs", "standard model", "wave function", "entanglement"],
    },
    {
        "id": "cosmic_nuclear",
        "name": "Nuclear and Cosmic",
        "description": "Nuclear transformations, stellar processes, astrophysical systems, and cosmology.",
        "terms": ["nuclear", "fusion", "fission", "decay", "astro", "cosmic", "stellar"],
    },
]

CS_LAYERS = [
    {
        "id": "foundations_theory",
        "name": "Foundations and Theory",
        "description": "Automata, computability, complexity, formal methods, and mathematical foundations.",
        "terms": ["theory", "complexity", "automata", "verification", "formal", "computability"],
    },
    {
        "id": "algorithms_data",
        "name": "Algorithms and Data Structures",
        "description": "Algorithms, data structures, graph methods, dynamic programming, sorting, and search.",
        "terms": ["algorithm", "graph", "sorting", "tree", "dynamic programming", "search", "data structure"],
    },
    {
        "id": "software_runtime",
        "name": "Software and Runtime",
        "description": "Programming workflows, software engineering, runtimes, memory, and operating systems.",
        "terms": ["software", "runtime", "memory", "operating", "scheduling", "requirements", "code review", "ci"],
    },
    {
        "id": "networks_distributed",
        "name": "Networks, Databases, and Distributed Systems",
        "description": "Networking, distributed systems, transactions, routing, databases, and consistency.",
        "terms": ["network", "distributed", "database", "transaction", "routing", "dns", "tcp", "query"],
    },
    {
        "id": "security_reliability",
        "name": "Security and Reliability",
        "description": "Authentication, authorization, PKI, incident response, reliability, and threat models.",
        "terms": ["security", "authentication", "authorization", "pki", "intrusion", "incident", "reliability"],
    },
    {
        "id": "ai_data_systems",
        "name": "AI, ML, and Data Systems",
        "description": "Machine learning, neural networks, feature engineering, NLP, training, and validation.",
        "terms": ["machine learning", "model", "feature", "neural", "nlp", "training", "validation"],
    },
]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "uncategorized"


def normalize_text(process: dict[str, Any]) -> str:
    parts = [
        process.get("id", ""),
        process.get("name", ""),
        process.get("subcategory", ""),
        process.get("subcategory_name", ""),
        process.get("category", ""),
        process.get("domainContext", ""),
        process.get("description", ""),
        " ".join(process.get("keywords") or []),
        " ".join(process.get("collections") or []),
    ]
    return " ".join(str(part).lower().replace("_", " ") for part in parts if part)


def process_url(process: dict[str, Any]) -> str:
    if process.get("url"):
        return str(process["url"])
    source = str(process.get("_sourceJsonPath") or "")
    if source.startswith("processes/") and source.endswith(".json"):
        return source[:-5] + ".html"
    return ""


def process_node(process: dict[str, Any]) -> dict[str, Any]:
    metrics = process.get("graphMetrics") or {}
    return {
        "id": f"process:{process['id']}",
        "name": process.get("name") or process["id"],
        "type": "process",
        "level": 3,
        "processId": process["id"],
        "url": process_url(process),
        "subcategory": process.get("subcategory"),
        "category": process.get("category"),
        "graphType": process.get("graphType", "flowchart"),
        "nodes": process.get("nodes") or metrics.get("nodes") or 0,
        "edges": process.get("edges") or metrics.get("edges") or 0,
        "description": process.get("description", ""),
    }


def add_link(links: list[dict[str, Any]], source: str, target: str, link_type: str = "contains") -> None:
    links.append({"source": source, "target": target, "type": link_type})


def root_node(profile: dict[str, Any], output: dict[str, str]) -> dict[str, Any]:
    return {
        "id": "root",
        "name": output["title"],
        "type": "root",
        "level": 0,
        "description": profile.get("subtitle", ""),
    }


def build_taxonomy_variant(profile: dict[str, Any], output: dict[str, str], processes: list[dict[str, Any]]) -> dict[str, Any]:
    nodes = [root_node(profile, output)]
    links: list[dict[str, Any]] = []
    subcategory_counts = Counter(str(p.get("subcategory") or "uncategorized") for p in processes)
    subcategory_names: dict[str, str] = {}
    for process in processes:
        sid = str(process.get("subcategory") or "uncategorized")
        subcategory_names.setdefault(sid, str(process.get("subcategory_name") or sid.replace("_", " ").title()))

    for subcategory, count in sorted(subcategory_counts.items(), key=lambda item: (-item[1], item[0])):
        node_id = f"subcategory:{subcategory}"
        nodes.append(
            {
                "id": node_id,
                "name": subcategory_names[subcategory],
                "type": "subcategory",
                "level": 1,
                "processCount": count,
                "description": "Generated from the existing process database subcategory.",
            }
        )
        add_link(links, "root", node_id)

    for process in processes:
        node = process_node(process)
        nodes.append(node)
        add_link(links, f"subcategory:{process.get('subcategory') or 'uncategorized'}", node["id"])

    return {
        "id": "taxonomy",
        "label": "Branch Taxonomy",
        "layout": "radial",
        "description": "Root-to-branch-to-process hierarchy. Useful as a coverage map and familiar table-of-contents view.",
        "recommendation": "secondary",
        "rubric": score_variant("taxonomy", profile["slug"]),
        "nodes": nodes,
        "links": links,
    }


def build_lens_variant(profile: dict[str, Any], output: dict[str, str], processes: list[dict[str, Any]], collections: list[dict[str, Any]]) -> dict[str, Any]:
    nodes = [root_node(profile, output)]
    links: list[dict[str, Any]] = []
    by_id = {str(p["id"]): p for p in processes if p.get("id")}
    used_processes: set[str] = set()

    for collection in collections:
        process_ids = [pid for pid in collection.get("processIds", []) if pid in by_id]
        if not process_ids:
            continue
        node_id = f"collection:{collection['id']}"
        nodes.append(
            {
                "id": node_id,
                "name": collection.get("label") or collection["id"],
                "type": "collection",
                "level": 1,
                "processCount": len(process_ids),
                "description": collection.get("description", ""),
            }
        )
        add_link(links, "root", node_id)
        for pid in process_ids:
            used_processes.add(pid)
            process = by_id[pid]
            pnode_id = f"process:{pid}"
            if not any(n["id"] == pnode_id for n in nodes):
                nodes.append(process_node(process))
            add_link(links, node_id, pnode_id, "lens")

    for process in processes:
        if process["id"] in used_processes:
            continue
        node_id = process_node(process)["id"]
        nodes.append(process_node(process))
        add_link(links, "root", node_id, "uncategorized")

    return {
        "id": "lens",
        "label": "Curated Lens Map",
        "layout": "force",
        "description": "Uses collection presets as conceptual lenses, letting processes appear under task-oriented groupings.",
        "recommendation": "candidate",
        "rubric": score_variant("lens", profile["slug"]),
        "nodes": dedupe_nodes(nodes),
        "links": links,
    }


def classify(process: dict[str, Any], families: list[dict[str, Any]]) -> str:
    text = normalize_text(process)
    for family in families:
        if any(term.lower() in text for term in family["terms"]):
            return family["id"]
    return "other"


def build_family_variant(
    profile: dict[str, Any],
    output: dict[str, str],
    processes: list[dict[str, Any]],
    families: list[dict[str, Any]],
    variant_id: str,
    label: str,
    layout: str,
    description: str,
) -> dict[str, Any]:
    nodes = [root_node(profile, output)]
    links: list[dict[str, Any]] = []
    family_map = {family["id"]: family for family in families}
    counts = Counter(classify(process, families) for process in processes)

    for family in families:
        node_id = f"family:{family['id']}"
        nodes.append(
            {
                "id": node_id,
                "name": family["name"],
                "type": "family",
                "level": 1,
                "processCount": counts[family["id"]],
                "description": family["description"],
            }
        )
        add_link(links, "root", node_id)

    if counts.get("other"):
        nodes.append(
            {
                "id": "family:other",
                "name": "Other / Mixed",
                "type": "family",
                "level": 1,
                "processCount": counts["other"],
                "description": "Processes not strongly matched by the first-pass family classifier.",
            }
        )
        add_link(links, "root", "family:other")

    for process in processes:
        family_id = classify(process, families)
        pnode = process_node(process)
        pnode["level"] = 3 if layout == "layered" else 2
        pnode["familyId"] = family_id
        nodes.append(pnode)
        add_link(links, f"family:{family_id}", pnode["id"], "classified_as")

        if layout == "layered":
            continue

        subcat = str(process.get("subcategory") or "")
        if subcat:
            branch_id = f"branch:{subcat}"
            if not any(n["id"] == branch_id for n in nodes):
                nodes.append(
                    {
                        "id": branch_id,
                        "name": str(process.get("subcategory_name") or subcat.replace("_", " ").title()),
                        "type": "branch",
                        "level": 2,
                        "description": "Original database branch/folder.",
                    }
                )
            add_link(links, branch_id, pnode["id"], "branch_contains")

    return {
        "id": variant_id,
        "label": label,
        "layout": layout,
        "description": description,
        "recommendation": "primary",
        "rubric": score_variant(variant_id, profile["slug"]),
        "nodes": dedupe_nodes(nodes),
        "links": dedupe_links(links),
    }


def dedupe_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for node in nodes:
        seen.setdefault(node["id"], node)
    return list(seen.values())


def dedupe_links(links: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    output = []
    for link in links:
        key = (link["source"], link["target"], link.get("type", ""))
        if key in seen:
            continue
        seen.add(key)
        output.append(link)
    return output


def score_variant(variant_id: str, discipline: str) -> dict[str, Any]:
    scores = {
        "taxonomy": {
            "subjectFidelity": 3,
            "navigability": 5,
            "crossLinks": 2,
            "pedagogy": 4,
            "extensibility": 4,
        },
        "lens": {
            "subjectFidelity": 4,
            "navigability": 4,
            "crossLinks": 4,
            "pedagogy": 4,
            "extensibility": 5,
        },
        "reaction_mechanism_hybrid": {
            "subjectFidelity": 5,
            "navigability": 4,
            "crossLinks": 5,
            "pedagogy": 4,
            "extensibility": 5,
        },
        "regime_theory_map": {
            "subjectFidelity": 5,
            "navigability": 4,
            "crossLinks": 5,
            "pedagogy": 5,
            "extensibility": 5,
        },
        "abstraction_stack": {
            "subjectFidelity": 5,
            "navigability": 4,
            "crossLinks": 4,
            "pedagogy": 5,
            "extensibility": 5,
        },
    }
    selected = scores.get(variant_id, scores["lens"])
    return {
        **selected,
        "total": sum(selected.values()),
        "notes": f"First-pass heuristic score for {discipline}; revise after visual inspection.",
    }


def build_variants(
    discipline: str,
    profile: dict[str, Any],
    process_index: dict[str, Any],
    collections: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    output = DISCIPLINE_OUTPUT[discipline]
    processes = [p for p in process_index.get("processes", []) if p.get("id")]
    variants = [
        build_taxonomy_variant(profile, output, processes),
        build_lens_variant(profile, output, processes, collections),
    ]
    if discipline == "chemistry":
        variants.append(
            build_family_variant(
                profile,
                output,
                processes,
                CHEMISTRY_FAMILIES,
                "reaction_mechanism_hybrid",
                "Reaction / Mechanism Hybrid",
                "force",
                "Groups processes by chemical function while preserving branch links; likely the best default for chemistry.",
            )
        )
    elif discipline == "physics":
        variants.append(
            build_family_variant(
                profile,
                output,
                processes,
                PHYSICS_REGIMES,
                "regime_theory_map",
                "Regime / Theory Map",
                "layered",
                "Organizes processes by physical regime and governing theory instead of a simple folder taxonomy.",
            )
        )
    elif discipline == "computer_science":
        variants.append(
            build_family_variant(
                profile,
                output,
                processes,
                CS_LAYERS,
                "abstraction_stack",
                "Abstraction Stack",
                "layered",
                "Places processes into conceptual layers from foundations through algorithms, systems, networks, security, and AI.",
            )
        )
    return variants


def variant_summary(variant: dict[str, Any]) -> dict[str, Any]:
    node_types = Counter(node["type"] for node in variant["nodes"])
    return {
        "id": variant["id"],
        "label": variant["label"],
        "layout": variant["layout"],
        "recommendation": variant["recommendation"],
        "nodes": len(variant["nodes"]),
        "links": len(variant["links"]),
        "nodeTypes": dict(sorted(node_types.items())),
        "rubricTotal": variant["rubric"]["total"],
    }


def build_graph_data(discipline: str, profile: dict[str, Any]) -> dict[str, Any]:
    database_dir = BASE_DIR / profile["databaseDir"]
    process_index = read_json(database_dir / "process-index.json")
    collections_path = database_dir / "collections.json"
    collections = read_json(collections_path) if collections_path.exists() else []
    output = DISCIPLINE_OUTPUT[discipline]
    variants = build_variants(discipline, profile, process_index, collections)
    return {
        "meta": {
            "title": output["title"],
            "discipline": discipline,
            "displayName": profile["displayName"],
            "summary": output["summary"],
            "primaryVariant": output["primary"],
            "tableFile": profile["tableFile"],
            "generatedFrom": "scripts/processes/discipline_databases/generate_whole_discipline_maps.py",
            "modelsCompared": MODEL_RUBRIC,
            "topicScaleExtensions": topic_extensions(discipline),
        },
        "variants": variants,
        "variantSummaries": [variant_summary(variant) for variant in variants],
    }


def topic_extensions(discipline: str) -> list[dict[str, str]]:
    common = [
        {
            "id": "glmp_style_process_corpus",
            "label": "GLMP-style process corpus",
            "model": "process family map plus influence network",
            "description": "Use the same map machinery for dense curated process corpora where each node opens a Mermaid process diagram.",
        }
    ]
    if discipline == "chemistry":
        return common + [
            {
                "id": "molecular_atomic_structures",
                "label": "Molecular, atomic, and subatomic structures",
                "model": "scale hierarchy plus structure-interaction network",
                "description": "Map atoms, bonds, orbitals, molecules, materials, and reactions as scale-linked structures.",
            }
        ]
    if discipline == "physics":
        return common + [
            {
                "id": "physical_universe",
                "label": "Physical universe",
                "model": "scale/regime map",
                "description": "Organize subatomic, atomic, molecular, planetary, stellar, galactic, and cosmological scales with theory links.",
            },
            {
                "id": "subatomic_standard_model",
                "label": "Subatomic structures",
                "model": "particle/interaction bipartite graph",
                "description": "Connect particles, fields, interactions, symmetries, conservation laws, and experimental processes.",
            },
        ]
    if discipline == "computer_science":
        return common + [
            {
                "id": "computing_stack",
                "label": "Computing stack",
                "model": "layered abstraction map",
                "description": "Show hardware, runtime, operating systems, networks, databases, applications, AI systems, and security concerns.",
            }
        ]
    return common


def render_html(discipline: str, profile: dict[str, Any]) -> str:
    output = DISCIPLINE_OUTPUT[discipline]
    title = output["title"]
    data_file = output["data"]
    table_file = profile["tableFile"]
    accent = profile.get("accent", "#2563eb")
    profile_json = json.dumps({"accent": accent, "displayName": profile["displayName"]})
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — Candidate Maps</title>
  <script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f8fafc; color: #0f172a; overflow: hidden; }}
    .header {{ position: fixed; inset: 0 0 auto 0; height: 58px; z-index: 10; background: rgba(255,255,255,0.96); box-shadow: 0 2px 12px rgba(15,23,42,0.12); display: flex; align-items: center; gap: 16px; padding: 10px 18px; }}
    .header h1 {{ margin: 0; font-size: 1.1rem; color: {accent}; white-space: nowrap; }}
    .header a {{ color: {accent}; font-weight: 700; text-decoration: none; white-space: nowrap; }}
    .controls {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; font-size: 0.9rem; }}
    select, button, input {{ font: inherit; border: 1px solid #cbd5e1; border-radius: 8px; background: white; padding: 6px 9px; }}
    button {{ cursor: pointer; color: #0f172a; }}
    #chart {{ position: fixed; top: 58px; left: 0; right: 360px; bottom: 0; background: radial-gradient(circle at top left, #fff, #eef2ff); }}
    .sidebar {{ position: fixed; top: 58px; right: 0; bottom: 0; width: 360px; overflow-y: auto; background: white; border-left: 1px solid #e2e8f0; padding: 16px; }}
    .sidebar h2 {{ margin: 0 0 8px; font-size: 1rem; color: {accent}; }}
    .sidebar p {{ line-height: 1.45; color: #475569; font-size: 0.9rem; }}
    .stat-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; margin: 12px 0; }}
    .stat {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 10px; }}
    .stat strong {{ display: block; font-size: 1.2rem; color: #0f172a; }}
    .legend {{ display: grid; gap: 6px; margin-top: 10px; }}
    .legend-item {{ display: flex; align-items: center; gap: 8px; font-size: 0.85rem; color: #334155; }}
    .dot {{ width: 11px; height: 11px; border-radius: 999px; display: inline-block; }}
    .rubric {{ display: grid; gap: 6px; margin-top: 10px; }}
    .rubric-row {{ display: grid; grid-template-columns: 1fr 36px; gap: 8px; font-size: 0.82rem; }}
    .node {{ cursor: pointer; stroke: #0f172a; stroke-width: 1.1; }}
    .node:hover {{ stroke-width: 2.5; }}
    .link {{ stroke: #94a3b8; stroke-opacity: 0.5; }}
    .label {{ pointer-events: none; fill: #0f172a; paint-order: stroke; stroke: rgba(255,255,255,0.85); stroke-width: 3px; stroke-linejoin: round; }}
    .tooltip {{ position: fixed; display: none; max-width: 320px; padding: 10px 12px; background: rgba(15,23,42,0.94); color: white; border-radius: 8px; line-height: 1.35; font-size: 0.86rem; z-index: 20; pointer-events: none; }}
    .tooltip small {{ opacity: 0.86; }}
  </style>
</head>
<body>
  <div class="header">
    <h1>{title}</h1>
    <div class="controls">
      <label>Variant <select id="variant"></select></label>
      <label>Layout <select id="layout"><option value="auto">Auto</option><option value="force">Force</option><option value="radial">Radial</option><option value="layered">Layered</option></select></label>
      <input id="search" type="search" placeholder="Search nodes">
      <button id="reset" type="button">Reset</button>
    </div>
    <a id="back-link" href="{table_file}">Database Table</a>
  </div>
  <div id="chart"></div>
  <aside class="sidebar">
    <h2 id="variant-title">Loading...</h2>
    <p id="variant-description"></p>
    <div class="stat-grid" id="stats"></div>
    <h2>Rubric</h2>
    <div class="rubric" id="rubric"></div>
    <h2>Legend</h2>
    <div class="legend" id="legend"></div>
    <h2>Topic-scale extensions</h2>
    <div id="extensions"></div>
  </aside>
  <div class="tooltip" id="tooltip"></div>
  <script>
    const PROFILE = {profile_json};
    const DATA_FILE = "{data_file}";
    const TABLE_FILE = "{table_file}";
    const baseUrl = window.location.hostname.includes('storage.googleapis.com')
      ? 'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/{profile["databaseDir"]}'
      : '.';
    document.getElementById('back-link').href = baseUrl + '/' + TABLE_FILE;
    let graphData;
    let simulation;
    const chart = d3.select('#chart');
    const tooltip = d3.select('#tooltip');
    const width = () => document.getElementById('chart').clientWidth;
    const height = () => document.getElementById('chart').clientHeight;
    const colors = {{ root: '#dc2626', subcategory: '#2563eb', collection: '#7c3aed', family: '#0f766e', branch: '#ea580c', process: '#16a34a' }};

    function escapeHtml(s) {{ return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }}
    function nodeColor(d) {{ return colors[d.type] || '#64748b'; }}
    function nodeRadius(d) {{
      if (d.type === 'root') return 22;
      if (d.type === 'family' || d.type === 'collection') return 15;
      if (d.type === 'subcategory' || d.type === 'branch') return 12;
      return Math.max(5, Math.min(9, 4 + Math.sqrt(Number(d.nodes || 4))));
    }}
    function linkDistance(d) {{ return d.target.type === 'process' ? 56 : 78; }}
    function showTooltip(event, d) {{
      tooltip.style('display', 'block').style('left', (event.pageX + 12) + 'px').style('top', (event.pageY + 12) + 'px')
        .html('<strong>' + escapeHtml(d.name) + '</strong><small>' +
          '<br>' + escapeHtml(d.type || '') +
          (d.processCount ? '<br>' + d.processCount + ' processes' : '') +
          (d.nodes ? '<br>' + d.nodes + ' diagram nodes' : '') +
          (d.description ? '<br>' + escapeHtml(d.description) : '') +
          (d.url ? '<br>Click to open process page' : '') + '</small>');
    }}
    function renderSidebar(variant) {{
      document.getElementById('variant-title').textContent = variant.label;
      document.getElementById('variant-description').textContent = variant.description;
      document.getElementById('stats').innerHTML = [
        ['Nodes', variant.nodes.length],
        ['Links', variant.links.length],
        ['Rubric', variant.rubric.total],
        ['Default', variant.layout]
      ].map(([label, value]) => `<div class="stat"><strong>${{value}}</strong><span>${{label}}</span></div>`).join('');
      const rubricRows = Object.entries(variant.rubric).filter(([k]) => k !== 'notes' && k !== 'total');
      document.getElementById('rubric').innerHTML = rubricRows.map(([k, v]) => `<div class="rubric-row"><span>${{k}}</span><strong>${{v}}</strong></div>`).join('') + `<p>${{escapeHtml(variant.rubric.notes || '')}}</p>`;
      const types = Array.from(new Set(variant.nodes.map(n => n.type))).sort();
      document.getElementById('legend').innerHTML = types.map(type => `<div class="legend-item"><span class="dot" style="background:${{nodeColor({{ type }})}}"></span>${{type.replace(/_/g, ' ')}}</div>`).join('');
      document.getElementById('extensions').innerHTML = (graphData.meta.topicScaleExtensions || []).map(ext => `<p><strong>${{escapeHtml(ext.label)}}</strong><br><small>${{escapeHtml(ext.model)}}: ${{escapeHtml(ext.description)}}</small></p>`).join('');
    }}
    function layoutPositions(nodes, links, mode) {{
      const w = width();
      const h = height();
      if (mode === 'radial') {{
        const byLevel = d3.group(nodes, d => d.level || 0);
        const maxLevel = Math.max(...Array.from(byLevel.keys()));
        byLevel.forEach((levelNodes, level) => {{
          const radius = level === 0 ? 0 : Math.min(w, h) * (0.12 + 0.34 * (level / Math.max(1, maxLevel)));
          levelNodes.forEach((node, i) => {{
            const angle = (2 * Math.PI * i) / Math.max(1, levelNodes.length);
            node.fx = w / 2 + radius * Math.cos(angle);
            node.fy = h / 2 + radius * Math.sin(angle);
          }});
        }});
      }} else if (mode === 'layered') {{
        const root = nodes.find(n => n.type === 'root');
        if (root) {{ root.fx = w * 0.11; root.fy = h * 0.5; }}
        const families = nodes.filter(n => n.type === 'family' || n.type === 'collection' || n.type === 'subcategory');
        families.forEach((node, i) => {{
          node.fx = w * 0.36;
          node.fy = ((i + 1) / (families.length + 1)) * h;
        }});
        const familyY = new Map(families.map(n => [n.id.replace(/^family:/, ''), n.fy]));
        const directY = new Map(families.map(n => [n.id, n.fy]));
        const grouped = d3.group(nodes.filter(n => n.type === 'process'), n => n.familyId || parentId(n.id));
        grouped.forEach((groupNodes, key) => {{
          const centerY = familyY.get(key) || directY.get(key) || h * 0.5;
          const band = Math.min(h / Math.max(2, families.length), 150);
          groupNodes.forEach((node, i) => {{
            const offset = ((i + 1) / (groupNodes.length + 1) - 0.5) * band;
            const lane = i % 3;
            node.fx = w * (0.64 + lane * 0.08);
            node.fy = centerY + offset;
          }});
        }});
      }} else {{
        nodes.forEach(n => {{ n.fx = null; n.fy = null; }});
      }}
    }}
    function parentId(nodeId) {{
      const link = currentLinks.find(l => l.target && l.target.id === nodeId);
      return link && link.source ? link.source.id : '';
    }}
    let currentLinks = [];
    function renderVariant() {{
      if (simulation) simulation.stop();
      chart.selectAll('*').remove();
      const selectedId = document.getElementById('variant').value;
      const variant = graphData.variants.find(v => v.id === selectedId) || graphData.variants[0];
      const selectedLayout = document.getElementById('layout').value === 'auto' ? variant.layout : document.getElementById('layout').value;
      const query = document.getElementById('search').value.trim().toLowerCase();
      const nodes = variant.nodes.map(d => ({{ ...d }}));
      const nodeById = new Map(nodes.map(n => [n.id, n]));
      const links = variant.links.map(l => ({{ ...l, source: nodeById.get(l.source), target: nodeById.get(l.target) }})).filter(l => l.source && l.target);
      currentLinks = links;
      layoutPositions(nodes, links, selectedLayout);
      renderSidebar(variant);
      const svg = chart.append('svg').attr('width', width()).attr('height', height());
      const g = svg.append('g');
      svg.call(d3.zoom().scaleExtent([0.08, 5]).on('zoom', e => g.attr('transform', e.transform)));
      const link = g.append('g').selectAll('line').data(links).join('line').attr('class', 'link').attr('stroke-width', d => d.type === 'branch_contains' ? 0.8 : 1.3);
      const node = g.append('g').selectAll('circle').data(nodes).join('circle')
        .attr('class', 'node')
        .attr('r', nodeRadius)
        .attr('fill', d => query && !(`${{d.name}} ${{d.type}} ${{d.description || ''}}`.toLowerCase().includes(query)) ? '#cbd5e1' : nodeColor(d))
        .on('mouseover', showTooltip)
        .on('mousemove', event => tooltip.style('left', (event.pageX + 12) + 'px').style('top', (event.pageY + 12) + 'px'))
        .on('mouseout', () => tooltip.style('display', 'none'))
        .on('click', (event, d) => {{ if (d.url) window.open(baseUrl + '/' + d.url, '_blank'); }})
        .call(d3.drag().on('start', dragstarted).on('drag', dragged).on('end', dragended));
      const label = g.append('g').selectAll('text')
        .data(nodes.filter(n => n.type !== 'process' || (query && n.name.toLowerCase().includes(query))))
        .join('text').attr('class', 'label').attr('font-size', d => d.type === 'root' ? 14 : d.type === 'process' ? 9 : 11).attr('dx', d => nodeRadius(d) + 4).attr('dy', '0.35em').text(d => d.name);
      simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links).id(d => d.id).distance(linkDistance))
        .force('charge', d3.forceManyBody().strength(d => d.type === 'root' ? -700 : d.type === 'process' ? -90 : -260))
        .force('center', d3.forceCenter(width() / 2, height() / 2))
        .force('collision', d3.forceCollide().radius(d => nodeRadius(d) + 5));
      simulation.on('tick', () => {{
        link.attr('x1', d => d.source.x).attr('y1', d => d.source.y).attr('x2', d => d.target.x).attr('y2', d => d.target.y);
        node.attr('cx', d => d.x).attr('cy', d => d.y);
        label.attr('x', d => d.x).attr('y', d => d.y);
      }});
      function dragstarted(event, d) {{ if (!event.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; }}
      function dragged(event, d) {{ d.fx = event.x; d.fy = event.y; }}
      function dragended(event, d) {{ if (!event.active) simulation.alphaTarget(0); if (selectedLayout === 'force') {{ d.fx = null; d.fy = null; }} }}
    }}
    d3.json(baseUrl + '/' + DATA_FILE).then(data => {{
      graphData = data;
      document.getElementById('variant').innerHTML = data.variants.map(v => `<option value="${{v.id}}" ${{v.id === data.meta.primaryVariant ? 'selected' : ''}}>${{v.label}}</option>`).join('');
      document.getElementById('variant').addEventListener('change', renderVariant);
      document.getElementById('layout').addEventListener('change', renderVariant);
      document.getElementById('search').addEventListener('input', renderVariant);
      document.getElementById('reset').addEventListener('click', () => {{ document.getElementById('search').value = ''; document.getElementById('layout').value = 'auto'; renderVariant(); }});
      renderVariant();
    }});
  </script>
</body>
</html>
"""


def update_featured_maps(profile: dict[str, Any], discipline: str) -> dict[str, Any]:
    output = DISCIPLINE_OUTPUT[discipline]
    updated = deepcopy(profile)
    maps = [m for m in updated.get("featuredMaps", []) if m.get("url") != output["file"]]
    maps.append(
        {
            "label": output["title"],
            "url": output["file"],
            "description": output["summary"],
        }
    )
    updated["featuredMaps"] = maps
    return updated


def generate_one(discipline: str, profiles: dict[str, Any], update_profiles: bool) -> None:
    profile = profiles[discipline]
    database_dir = BASE_DIR / profile["databaseDir"]
    output = DISCIPLINE_OUTPUT[discipline]
    graph_data = build_graph_data(discipline, profile)
    write_json(database_dir / output["data"], graph_data)
    (database_dir / output["file"]).write_text(render_html(discipline, profile), encoding="utf-8")
    if update_profiles:
        updated = update_featured_maps(profile, discipline)
        profiles[discipline] = updated
        write_json(database_dir / "discipline-profile.json", {**updated, "generatedFrom": "scripts/processes/discipline_databases/generate_whole_discipline_maps.py"})
    print(f"Generated {output['title']}: {database_dir / output['file']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate whole-discipline candidate maps.")
    parser.add_argument("disciplines", nargs="*", choices=TARGET_DISCIPLINES)
    parser.add_argument("--update-profiles", action="store_true", help="Add generated maps to discipline-profile.json and discipline_profiles.json.")
    args = parser.parse_args()

    profiles = read_json(PROFILE_FILE)
    disciplines = args.disciplines or list(TARGET_DISCIPLINES)
    for discipline in disciplines:
        generate_one(discipline, profiles, args.update_profiles)
    if args.update_profiles:
        write_json(PROFILE_FILE, profiles)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
