#!/usr/bin/env python3
"""Add the planned biology process expansion records and pages."""

from __future__ import annotations

import json
import re
from collections import Counter
from html import escape
from pathlib import Path


BASE = Path(__file__).resolve().parents[3]
BIO_DIR = BASE / "biology-processes-database"
METADATA_PATH = BIO_DIR / "metadata.json"
PRESET_PATH = Path(__file__).resolve().parent / "collection_presets" / "biology.json"

SUBCATEGORY_NAMES = {
    "pathways": "Pathways",
    "mechanisms": "Mechanisms",
    "assay_protocols": "Assay / Lab Protocols",
    "immunology": "Immunology",
    "development": "Development and Organismal Biology",
    "cell_biology": "Cell Biology",
}

COLLECTION_LABELS = {
    "metabolism": "Metabolism",
    "signaling-cell-fate": "Signaling and Cell Fate",
    "gene-expression": "Gene Expression",
    "immunology": "Immunology and Host Defense",
    "organismal-biology": "Organismal Biology",
    "cell-biology": "Cell Biology and Proteostasis",
}

PROCESS_ROWS = [
    ("Photosynthesis Light Reactions", "pathways", "metabolism", "high", "Chloroplast thylakoid", "Light reactions convert photon energy into ATP and NADPH through photosystem II, electron transport, photosystem I, and ATP synthase.", "Cyclic electron flow needed?", "Return electrons to cytochrome b6f", "Linear flow reduces NADP"),
    ("Gluconeogenesis", "pathways", "metabolism", "high", "Liver cytosol/mitochondria", "Gluconeogenesis synthesizes glucose from lactate, glycerol, and amino acid carbon skeletons during fasting.", "Energy and glucagon high?", "Activate glucose production", "Suppress futile cycling"),
    ("Pentose Phosphate Pathway", "pathways", "metabolism", "medium", "Cytosol", "The pentose phosphate pathway produces NADPH for reductive biosynthesis and ribose-5-phosphate for nucleotide synthesis.", "Need ribose or NADPH?", "Favor nucleotide precursor output", "Recycle carbon for reducing power"),
    ("Fatty Acid Beta-Oxidation", "pathways", "metabolism", "high", "Mitochondrial matrix", "Beta-oxidation breaks fatty acyl-CoA molecules into acetyl-CoA while producing FADH2 and NADH.", "Fatty acid chain remains?", "Repeat beta-oxidation cycle", "Route acetyl-CoA to TCA or ketogenesis"),
    ("Transcription Initiation in Eukaryotes", "mechanisms", "gene-expression", "high", "Nucleus", "Eukaryotic transcription initiation assembles regulatory factors and RNA polymerase II at promoters before productive RNA synthesis.", "Enhancer and promoter compatible?", "Stabilize preinitiation complex", "Maintain repressed or poised state"),
    ("mRNA Splicing", "mechanisms", "gene-expression", "high", "Nucleus", "Pre-mRNA splicing removes introns and joins exons through spliceosome assembly, lariat formation, and exon ligation.", "Alternative exon selected?", "Generate transcript isoform", "Use constitutive splice pattern"),
    ("Translation Initiation", "mechanisms", "gene-expression", "medium", "Ribosome/cytosol", "Translation initiation assembles the ribosomal subunits, initiator tRNA, and mRNA at a start codon.", "Start codon context strong?", "Initiate translation", "Continue scanning or reduce initiation"),
    ("Protein Folding and Chaperone Response", "cell_biology", "cell-biology", "high", "Cytosol/ER", "Protein folding pathways guide nascent chains toward native conformations while molecular chaperones prevent aggregation.", "Protein reaches native state?", "Proceed to function or trafficking", "Send to quality control and degradation"),
    ("Ubiquitin-Proteasome Degradation", "cell_biology", "cell-biology", "high", "Cytosol/nucleus", "The ubiquitin-proteasome system marks short-lived or damaged proteins with ubiquitin chains for proteasomal degradation.", "Ubiquitin chain sufficient?", "Commit to proteasomal degradation", "Edit or remove ubiquitin signal"),
    ("GPCR Signaling", "pathways", "signaling-cell-fate", "high", "Plasma membrane", "G protein-coupled receptor signaling converts extracellular ligand binding into intracellular second messenger responses.", "Receptor persistently stimulated?", "Recruit arrestin and desensitize", "Reset G protein cycle"),
    ("JAK-STAT Signaling", "pathways", "signaling-cell-fate", "medium", "Cytokine receptor", "JAK-STAT signaling transmits cytokine and growth factor signals from membrane receptors to transcriptional responses.", "SOCS feedback induced?", "Dampen pathway activity", "Continue transcriptional response"),
    ("NF-kB Inflammatory Signaling", "pathways", "signaling-cell-fate", "high", "Immune and stress response", "NF-kB signaling converts inflammatory, pathogen, and stress signals into transcription of immune and survival genes.", "Negative feedback genes expressed?", "Restore pathway restraint", "Sustain inflammatory signaling"),
    ("Wnt / Beta-Catenin Signaling", "pathways", "signaling-cell-fate", "high", "Development and tissue homeostasis", "Canonical Wnt signaling stabilizes beta-catenin and regulates developmental and stem cell gene programs.", "Wnt ligand absent?", "Destroy beta-catenin", "Activate Wnt target genes"),
    ("p53 DNA Damage Response", "pathways", "signaling-cell-fate", "high", "Genome surveillance", "The p53 pathway senses DNA damage and coordinates cell cycle arrest, DNA repair, senescence, or apoptosis.", "Damage repairable?", "Arrest and repair DNA", "Trigger apoptosis or senescence"),
    ("Autophagy", "cell_biology", "cell-biology", "high", "Lysosome/vacuole", "Macroautophagy captures cytoplasmic material in autophagosomes and delivers it to lysosomes for recycling.", "Selective cargo tagged?", "Recruit cargo receptors", "Bulk cytoplasm turnover"),
    ("Innate Immune Pattern Recognition", "immunology", "immunology", "high", "Innate immune cells", "Pattern recognition receptors detect pathogen-associated or damage-associated molecular patterns and initiate antimicrobial responses.", "Signal location and ligand type?", "Use TLR pathway", "Use cytosolic PRR pathway"),
    ("Antigen Processing and MHC Presentation", "immunology", "immunology", "high", "Antigen-presenting cells", "Antigen processing generates peptides for display on MHC molecules to CD4 or CD8 T cells.", "Antigen source cytosolic?", "Load MHC I pathway", "Load MHC II pathway"),
    ("T Cell Receptor Activation", "immunology", "immunology", "high", "Adaptive immunity", "T cell receptor activation integrates antigen recognition, costimulation, kinase signaling, and transcription factor activation.", "Costimulation present?", "Activate and proliferate", "Anergy or tolerance"),
    ("Cell Differentiation", "development", "organismal-biology", "high", "Development and stem cells", "Cell differentiation converts progenitor cells into specialized cell types through signaling and transcription factor networks.", "Commitment signal sustained?", "Lock in lineage identity", "Remain plastic or choose alternate fate"),
    ("Plant Hormone Auxin Signaling", "development", "organismal-biology", "medium", "Plant development", "Auxin signaling regulates plant growth, tropisms, organ formation, and patterning through Aux/IAA and ARF proteins.", "Polar transport reinforces gradient?", "Strengthen developmental pattern", "Diffuse or weaken auxin response"),
    ("Fatty Acid Synthesis", "pathways", "metabolism", "high", "Cytosol", "Fatty acid synthesis builds long-chain fatty acids from acetyl-CoA and malonyl-CoA using fatty acid synthase and NADPH.", "Energy and citrate abundant?", "Promote lipogenesis", "Limit fatty acid synthesis"),
    ("Urea Cycle", "pathways", "metabolism", "medium", "Liver mitochondria/cytosol", "The urea cycle detoxifies ammonia by converting nitrogen waste into urea for excretion.", "Ammonia load high?", "Increase urea cycle flux", "Maintain basal nitrogen disposal"),
    ("Nitrogen Fixation", "pathways", "metabolism", "high", "Diazotrophic bacteria", "Nitrogen fixation reduces atmospheric nitrogen to ammonia using nitrogenase, ATP, and electron donors.", "Oxygen exposure high?", "Protect nitrogenase or reduce activity", "Continue fixation"),
    ("Fermentation: Lactate and Ethanol Branches", "pathways", "metabolism", "medium", "Anaerobic metabolism", "Fermentation regenerates NAD+ when respiratory electron acceptors are limited.", "Organism branch type?", "Reduce pyruvate to lactate", "Produce ethanol from acetaldehyde"),
    ("Nucleotide Excision Repair", "mechanisms", "gene-expression", "high", "DNA repair", "Nucleotide excision repair removes bulky DNA lesions by recognizing distortion, excising the damaged segment, and filling the gap.", "Lesion blocks transcription?", "Use transcription-coupled repair", "Use global genome repair"),
    ("Homologous Recombination Repair", "mechanisms", "gene-expression", "high", "Double-strand break repair", "Homologous recombination repairs DNA double-strand breaks using a homologous template.", "Sister chromatid available?", "Favor accurate homologous repair", "Use alternative repair or checkpoint arrest"),
    ("RNA Interference / siRNA Pathway", "mechanisms", "gene-expression", "medium", "Post-transcriptional regulation", "RNA interference uses small RNAs to guide Argonaute complexes to complementary RNA targets.", "Complementarity high?", "Slice target RNA", "Repress translation or destabilize mRNA"),
    ("Notch Signaling", "pathways", "signaling-cell-fate", "medium", "Cell-cell communication", "Notch signaling transmits direct cell-contact information through ligand binding and receptor cleavage.", "Neighbor contact maintained?", "Sustain Notch transcription", "Signal decays"),
    ("Necroptosis", "pathways", "signaling-cell-fate", "high", "Regulated cell death", "Necroptosis is an inflammatory regulated cell death pathway driven by RIPK1, RIPK3, and MLKL.", "Caspase-8 active?", "Favor apoptosis or survival branch", "Commit to necroptosis"),
    ("Complement Cascade", "immunology", "immunology", "high", "Innate humoral immunity", "The complement cascade amplifies pathogen recognition through classical, lectin, or alternative initiation pathways.", "Host regulatory proteins present?", "Limit complement damage", "Amplify complement attack"),
    ("B Cell Activation and Antibody Production", "immunology", "immunology", "high", "Adaptive humoral immunity", "B cell activation integrates antigen binding, helper T cell signals, class switching, and affinity maturation.", "T cell help available?", "Generate strong antibody response", "Weak or T-independent response"),
    ("Inflammasome Activation", "immunology", "immunology", "high", "Innate immune cytosol", "Inflammasomes sense cytosolic danger signals, activate caspase-1, mature cytokines, and can trigger pyroptosis.", "Danger signal sustained?", "Trigger cytokine release and pyroptosis", "Resolve primed state"),
    ("Epithelial-Mesenchymal Transition", "development", "organismal-biology", "high", "Development and cancer biology", "Epithelial-mesenchymal transition changes epithelial cells into motile mesenchymal-like cells.", "Signal reversible?", "Partial EMT or plasticity", "Stable mesenchymal state"),
    ("Morphogen Gradient Patterning", "development", "organismal-biology", "medium", "Embryonic patterning", "Morphogen gradients provide positional information during development through threshold-dependent gene expression.", "Concentration above threshold?", "Activate high-threshold fate", "Activate low-threshold or default fate"),
    ("Circadian Clock Regulation", "development", "organismal-biology", "high", "Daily biological timing", "Circadian clocks generate approximately 24-hour rhythms through transcription-translation feedback loops and entrainment cues.", "Light cue shifts clock?", "Reset phase through entrainment pathway", "Maintain endogenous rhythm"),
]


def slugify(name: str) -> str:
    text = name.lower()
    text = text.replace("mrna", "mrna").replace("sirna", "sirna")
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text


def make_mermaid(row: tuple[str, str, str, str, str, str, str, str, str]) -> str:
    name, _subcat, collection, _complexity, context, _description, question, yes, no = row
    topic = name.replace(" / ", " and ")
    steps = [
        f"{topic} input or trigger",
        f"{context} receives signal or substrate",
        "Recognition and assembly phase",
        "Core enzymatic or regulatory step",
        "Amplification and checkpoint step",
        "Downstream response is produced",
        "System resets or feeds forward",
    ]
    if collection == "metabolism":
        steps[2] = "Substrate is activated or committed"
        steps[3] = "Carbon, electrons, or nitrogen are transferred"
        steps[5] = "Metabolic product enters next pathway"
    elif collection == "gene-expression":
        steps[2] = "Nucleic acid or protein complex is recruited"
        steps[3] = "Information processing step executes"
        steps[5] = "Expression or repair outcome is produced"
    elif collection == "immunology":
        steps[2] = "Immune receptor or effector complex assembles"
        steps[3] = "Signal cascade activates immune function"
        steps[5] = "Effector response is deployed"
    elif collection == "cell-biology":
        steps[2] = "Cellular quality-control machinery engages"
        steps[3] = "Cargo or protein state is remodeled"
        steps[5] = "Homeostasis is restored or stress response continues"
    elif collection == "organismal-biology":
        steps[2] = "Developmental regulators interpret context"
        steps[3] = "Gene and cell-state programs change"
        steps[5] = "Pattern or phenotype is stabilized"
    lines = ["graph TD"]
    for i, step in enumerate(steps, start=1):
        lines.append(f"    N{i}[{step}]")
        if i > 1:
            lines.append(f"    N{i-1} --> N{i}")
    lines.append(f"    N7 --> D1{{{question}}}")
    lines.append(f"    D1 -->|Yes| Y1[{yes}]")
    lines.append(f"    D1 -->|No| Z1[{no}]")
    return "\n".join(lines)


def metrics(mermaid: str) -> dict[str, int]:
    node_ids = set(re.findall(r"\b([A-Z][A-Za-z0-9_]*)\s*(?:\[|\{)", mermaid))
    edges = sum(1 for line in mermaid.splitlines() if "-->" in line)
    conditionals = mermaid.count("{")
    loops = 1 if "cycle" in mermaid.lower() or "feedback" in mermaid.lower() or "reset" in mermaid.lower() else 0
    return {
        "nodes": len(node_ids),
        "edges": edges,
        "conditionals": conditionals,
        "andGates": 0,
        "orGates": conditionals,
        "notGates": 0,
        "loops": loops,
    }


def render_page(row: tuple[str, str, str, str, str, str, str, str, str], process_id: str, mermaid: str, metric_values: dict[str, int]) -> str:
    name, subcategory, collection, complexity, context, description, *_ = row
    metric_html = "".join(
        f'<div class="metric"><strong>{value}</strong>{label}</div>'
        for label, value in [
            ("Nodes", metric_values["nodes"]),
            ("Edges", metric_values["edges"]),
            ("Conditionals", metric_values["conditionals"]),
            ("OR gates", metric_values["orGates"]),
            ("AND gates", metric_values["andGates"]),
            ("Loops", metric_values["loops"]),
        ]
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape(name)} - Biology Process</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #16a34a 0%, #0f172a 100%); min-height: 100vh; padding: 20px; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: white; border-radius: 15px; box-shadow: 0 20px 40px rgba(0,0,0,0.1); overflow: hidden; }}
        .header {{ background: linear-gradient(135deg, #16a34a 0%, #15803d 100%); color: white; padding: 30px; }}
        .header h1 {{ margin: 0 0 10px 0; font-size: 2em; }}
        .header-meta {{ display: flex; flex-wrap: wrap; gap: 15px; margin-top: 15px; font-size: 0.9em; opacity: 0.95; }}
        .meta-item {{ background: rgba(255,255,255,0.2); padding: 5px 12px; border-radius: 20px; }}
        .nav-links {{ padding: 15px 30px; background: #f8f9fa; border-bottom: 1px solid #ecf0f1; }}
        .nav-links a {{ color: #15803d; text-decoration: none; margin-right: 20px; font-weight: 600; }}
        .content {{ padding: 30px; }}
        .description, .notes, .metrics {{ background: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 24px; line-height: 1.6; color: #1f2937; }}
        .flowchart-container {{ background: #f8f9fa; padding: 30px; border-radius: 10px; margin: 30px 0; overflow-x: auto; }}
        .flowchart-container h2, .description h2, .metrics h2, .notes h2 {{ color: #1f2937; margin-bottom: 14px; }}
        .mermaid {{ background: white; padding: 20px; border-radius: 8px; }}
        .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; }}
        .metric {{ background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px; }}
        .metric strong {{ display: block; color: #15803d; font-size: 1.2em; }}
        footer {{ padding: 20px 30px; color: #64748b; background: #f8fafc; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{escape(name)}</h1>
            <div class="header-meta">
                <span class="meta-item">{escape(SUBCATEGORY_NAMES[subcategory])}</span>
                <span class="meta-item">{escape(context)}</span>
                <span class="meta-item">Complexity: {escape(complexity)}</span>
                <span class="meta-item">Collection: {escape(COLLECTION_LABELS[collection])}</span>
            </div>
        </div>
        <div class="nav-links"><a id="back-link" href="#">Back to Biology Database</a></div>
        <script>
            document.getElementById('back-link').href = window.location.hostname.includes('storage.googleapis.com')
                ? 'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/biology-processes-database/biology-database-table.html'
                : '../../biology-database-table.html';
        </script>
        <div class="content">
            <div class="description"><h2>Description</h2><p>{escape(description)}</p></div>
            <div class="flowchart-container"><h2>Process Flowchart</h2><div class="mermaid">
{mermaid}
            </div></div>
            <div class="metrics"><h2>Graph Metrics</h2><div class="metric-grid">{metric_html}</div></div>
            <div class="notes"><h2>Curation Notes</h2><p>This curated process page is a compact Programming Framework representation based on standard textbook and review-level biological knowledge. It is intended for navigation, teaching, and future refinement with primary literature annotations.</p></div>
        </div>
        <footer>Static host: GCS. Mermaid rendering via CDN. Generated as part of the Biology Process Expansion. ID: {process_id}</footer>
    </div>
    <script>mermaid.initialize({{ startOnLoad: true, securityLevel: 'loose' }});</script>
</body>
</html>
"""


def main() -> int:
    metadata = json.loads(METADATA_PATH.read_text())
    records = []
    for row in PROCESS_ROWS:
        name, subcategory, collection, complexity, context, _description, *_ = row
        process_id = f"{subcategory}-{slugify(name)}"
        mermaid = make_mermaid(row)
        metric_values = metrics(mermaid)
        records.append(
            {
                "id": process_id,
                "name": name,
                "subcategory": subcategory,
                "subcategory_name": SUBCATEGORY_NAMES[subcategory],
                "complexity": complexity,
                "nodes": metric_values["nodes"],
                "edges": metric_values["edges"],
                "conditionals": metric_values["conditionals"],
                "orGates": metric_values["orGates"],
                "andGates": metric_values["andGates"],
                "notGates": metric_values["notGates"],
                "loops": metric_values["loops"],
                "namedCollections": [collection],
                "domainContext": context,
                "graphType": "flowchart",
                "category": SUBCATEGORY_NAMES[subcategory],
            }
        )
        folder = BIO_DIR / "processes" / subcategory
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{process_id}.html").write_text(render_page(row, process_id, mermaid, metric_values), encoding="utf-8")

    record_by_id = {record["id"]: record for record in records}
    metadata["processes"] = [process for process in metadata.get("processes", []) if process.get("id") not in record_by_id]
    metadata["processes"].extend(records)
    metadata["totalProcesses"] = len(metadata["processes"])
    subcategory_counts = Counter(process["subcategory"] for process in metadata["processes"])
    metadata["subcategoryCounts"] = dict(sorted(subcategory_counts.items()))
    metadata["subcategories"] = len(subcategory_counts)
    metadata["statistics"] = {
        "totalNodes": sum(int(process.get("nodes", 0)) for process in metadata["processes"]),
        "totalEdges": sum(int(process.get("edges", 0)) for process in metadata["processes"]),
        "totalOrGates": sum(int(process.get("orGates", 0)) for process in metadata["processes"]),
        "totalAndGates": sum(int(process.get("andGates", 0)) for process in metadata["processes"]),
        "totalConditionals": sum(int(process.get("conditionals", 0)) for process in metadata["processes"]),
        "totalNotGates": sum(int(process.get("notGates", 0)) for process in metadata["processes"]),
        "totalLoops": sum(int(process.get("loops", 0)) for process in metadata["processes"]),
    }
    metadata["lastUpdated"] = "2026-04-28"
    METADATA_PATH.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    presets = json.loads(PRESET_PATH.read_text())
    by_id = {preset["id"]: preset for preset in presets}
    by_id["immunology"] = {
        "id": "immunology",
        "label": "Immunology and Host Defense",
        "description": "Immune recognition, antigen presentation, lymphocyte activation, complement, and inflammatory responses.",
        "match": ["immune", "immunity", "antigen", "mhc", "t cell", "b cell", "complement", "inflammasome", "inflammatory", "pattern recognition"],
    }
    by_id["cell-biology"] = {
        "id": "cell-biology",
        "label": "Cell Biology and Proteostasis",
        "description": "Protein folding, degradation, autophagy, trafficking, and cell-state maintenance.",
        "match": ["protein folding", "chaperone", "ubiquitin", "proteasome", "autophagy", "proteostasis", "cell biology"],
    }
    PRESET_PATH.write_text(json.dumps(list(by_id.values()), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"added/updated {len(records)} process records")
    print(f"total metadata processes: {metadata['totalProcesses']}")
    print(f"subcategory counts: {metadata['subcategoryCounts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
