#!/usr/bin/env python3
"""
Generate new process JSON files (and later HTML viewers) while preserving stable URLs.

- Writes process JSONs into: <db_dir>/processes/<subcategory>/<subcategory>-<slug>.json
- Ensures the JSON filename stem matches what database tables link to:
    processes/${process.subcategory}/${process.id}.html
  (i.e., we set metadata/process.id == filename stem)
- Fetches 3 real literature references from Crossref for each process name.

This script is intentionally conservative:
- Never overwrites existing JSON files (skips if present)
- Produces consistent schema with existing discipline process JSONs
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote_plus
from urllib.request import urlopen

from curated_flowcharts import (
    CHEMISTRY_SUBCATEGORY_TEMPLATES,
    CHEMISTRY_TEMPLATES,
    CS_TEMPLATES,
    Step,
)


COLOR_SCHEME: Dict[str, Dict[str, str]] = {
    "red": {"hex": "#ff6b6b", "category": "Triggers & Inputs"},
    "yellow": {"hex": "#ffd43b", "category": "Structures & Objects"},
    "green": {"hex": "#51cf66", "category": "Processing & Operations"},
    "blue": {"hex": "#74c0fc", "category": "Intermediates & States"},
    "violet": {"hex": "#b197fc", "category": "Products & Outputs"},
}


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[’'`]", "", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text


def _crossref_get_json(url: str, timeout: int = 30) -> Dict[str, Any]:
    with urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _format_crossref_authors(authors: Any) -> str:
    if not isinstance(authors, list):
        return ""
    parts: List[str] = []
    for a in authors[:10]:
        if not isinstance(a, dict):
            continue
        given = (a.get("given") or "").strip()
        family = (a.get("family") or "").strip()
        name = ", ".join([p for p in [family, given] if p])
        if name:
            parts.append(name)
    return "; ".join(parts)


def crossref_top_dois(query: str, *, rows: int = 10) -> List[Dict[str, Any]]:
    """
    Returns a list of source dicts with: title, authors, journal, year, doi, url.
    """
    q = quote_plus(query)
    url = f"https://api.crossref.org/works?query={q}&rows={rows}"
    data = _crossref_get_json(url)
    items = (data.get("message") or {}).get("items") or []
    sources: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        doi = (item.get("DOI") or "").strip()
        if not doi or not doi.startswith("10."):
            continue

        titles = item.get("title") or []
        title = titles[0].strip() if isinstance(titles, list) and titles else ""
        journal = ""
        container = item.get("container-title") or []
        if isinstance(container, list) and container:
            journal = str(container[0]).strip()
        year = ""
        issued = (item.get("issued") or {}).get("date-parts") or []
        if issued and isinstance(issued, list) and issued[0] and isinstance(issued[0], list):
            year = str(issued[0][0])

        sources.append(
            {
                "title": title or f"Crossref work ({doi})",
                "authors": _format_crossref_authors(item.get("author")),
                "journal": journal,
                "year": year,
                "pubmed": None,
                "doi": doi,
                "url": f"https://doi.org/{doi}",
            }
        )
        if len(sources) >= 3:
            break
    return sources


def make_mermaid_26_node_template(process_name: str) -> str:
    """
    Creates a consistent, generic 26-node flowchart like the existing CS/Math/Physics ones.
    This is intentionally template-based (not domain-accurate), matching current style.
    """
    # Use stable labels (A..Z) and a simple linear-ish structure with a couple merges.
    nodes = [chr(ord("A") + i) + "1" for i in range(26)]
    labels = [
        "Inputs",
        "Method Selection",
        "Resources",
        "Setup",
        "Execution",
        "Analysis",
        "Option A",
        "Option B",
        "Option C",
        "Step 1",
        "Step 2",
        "Step 3",
        "Intermediate 1",
        "Intermediate 2",
        "Intermediate 3",
        "Validation",
        f"{process_name} Process",
        "Verification",
        "Result",
        "Review",
        "Parameters",
        "Output",
        "Post-Processing",
        "Finalization",
        "Summary",
        "Complete",
    ]

    # Edges: 24 total (like the existing sets)
    edges: List[Tuple[str, str]] = [
        (nodes[0], nodes[1]),
        (nodes[2], nodes[3]),
        (nodes[4], nodes[5]),
        (nodes[1], nodes[6]),
        (nodes[3], nodes[7]),
        (nodes[5], nodes[8]),
        (nodes[6], nodes[9]),
        (nodes[7], nodes[10]),
        (nodes[8], nodes[11]),
        (nodes[9], nodes[12]),
        (nodes[10], nodes[13]),
        (nodes[11], nodes[14]),
        (nodes[12], nodes[15]),
        (nodes[13], nodes[16]),
        (nodes[14], nodes[16]),  # merge
        (nodes[15], nodes[17]),
        (nodes[16], nodes[18]),
        (nodes[17], nodes[19]),
        (nodes[18], nodes[20]),
        (nodes[19], nodes[21]),
        (nodes[20], nodes[22]),
        (nodes[21], nodes[23]),
        (nodes[22], nodes[24]),
        (nodes[23], nodes[25]),
    ]

    lines: List[str] = ["graph TD"]
    for src, dst in edges:
        s_idx = int(src[0], 36) - int("A", 36)  # A->0, B->1...
        d_idx = int(dst[0], 36) - int("A", 36)
        lines.append(f"{src}[{labels[s_idx]}] --> {dst}[{labels[d_idx]}]")

    # Style: 5-color scheme (match existing pattern: 3 red, 9 yellow, most green, final violet)
    red = [nodes[0], nodes[2], nodes[4]]
    yellow = [nodes[1], nodes[3], nodes[5], nodes[6], nodes[7], nodes[8], nodes[9], nodes[10], nodes[11]]
    green = [n for n in nodes if n not in red + yellow + [nodes[-1]]]
    violet = [nodes[-1]]

    lines.append("")
    for n in red:
        lines.append(f"    style {n} fill:{COLOR_SCHEME['red']['hex']},color:#fff")
    for n in yellow:
        lines.append(f"    style {n} fill:{COLOR_SCHEME['yellow']['hex']},color:#000")
    for n in green:
        lines.append(f"    style {n} fill:{COLOR_SCHEME['green']['hex']},color:#fff")
    for n in violet:
        lines.append(f"    style {n} fill:{COLOR_SCHEME['violet']['hex']},color:#fff")

    return "\n".join(lines)


def make_mermaid_from_steps(process_name: str, steps: List[Step]) -> str:
    """
    Build a process-specific Mermaid diagram from ordered steps.
    This prevents the "everything looks identical" failure mode.
    """
    if not steps:
        return make_mermaid_26_node_template(process_name)

    # Ensure final output node exists
    if steps[-1]["role"] != "violet":
        steps = [*steps, {"label": "Output", "role": "violet"}]  # type: ignore[assignment]

    node_ids = [f"S{i+1}" for i in range(len(steps))]
    lines: List[str] = ["graph TD"]

    for nid, step in zip(node_ids, steps):
        label = step["label"].replace("[", "(").replace("]", ")")
        lines.append(f'{nid}["{label}"]')

    lines.append("")
    for i in range(len(node_ids) - 1):
        lines.append(f"{node_ids[i]} --> {node_ids[i+1]}")

    lines.append("")
    for nid, step in zip(node_ids, steps):
        role = step["role"]
        hex_color = COLOR_SCHEME[role]["hex"]
        text_color = "#000" if role == "yellow" else "#fff"
        lines.append(f"    style {nid} fill:{hex_color},color:{text_color}")

    return "\n".join(lines)


def _normalize_category(category: str) -> str:
    return category.strip().lower().replace("-", "_")


def _curated_steps_for(
    category: str, process_id: str, subcategory: str, process_name: str
) -> Optional[List[Step]]:
    cat = _normalize_category(category)
    if cat == "computer_science":
        return CS_TEMPLATES.get(process_id)
    if cat == "chemistry":
        # Prefer a process-specific template; otherwise use a subcategory template.
        return CHEMISTRY_TEMPLATES.get(process_id) or CHEMISTRY_SUBCATEGORY_TEMPLATES.get(subcategory)
    return None


def _count_linear_steps(steps: List[Step]) -> Tuple[int, int]:
    n = len(steps)
    return n, max(0, n - 1)


def build_sources(process_name: str) -> List[Dict[str, Any]]:
    # Always include your methodology reference first
    sources: List[Dict[str, Any]] = [
        {
            "title": "Programming Framework: A Universal Process Visualization Methodology",
            "authors": "Welz, G.",
            "journal": "CopernicusAI Knowledge Engine",
            "year": "2025",
            "url": "https://huggingface.co/spaces/garywelz/programming_framework",
            "doi": None,
            "pubmed": None,
            "notes": f"Process visualization: {process_name}. Created using the Programming Framework methodology.",
        }
    ]

    # Add 3 real references from Crossref (DOI-based)
    refs = crossref_top_dois(process_name)
    sources.extend(refs)
    return sources


def write_process_json(
    *,
    db_dir: Path,
    category: str,
    subcategory: str,
    subcategory_name: str,
    process_name: str,
    process_id: Optional[str],
    created_date: str,
    overwrite: bool,
    use_curated: bool,
    require_curated: bool,
) -> Optional[Path]:
    processes_dir = db_dir / "processes" / subcategory
    processes_dir.mkdir(parents=True, exist_ok=True)

    final_id = (process_id or "").strip() or f"{subcategory}-{slugify(process_name)}"
    out_path = processes_dir / f"{final_id}.json"
    if out_path.exists() and not overwrite:
        return None

    existing_created: Optional[str] = None
    if out_path.exists() and overwrite:
        try:
            existing = json.loads(out_path.read_text(encoding="utf-8"))
            existing_created = existing.get("created")
        except Exception:
            existing_created = None

    curated_steps: Optional[List[Step]] = None
    if use_curated:
        curated_steps = _curated_steps_for(category, final_id, subcategory, process_name)
        if curated_steps is None and require_curated:
            raise ValueError(
                f"No curated flowchart template for category={category} id={final_id} subcategory={subcategory} "
                f"name={process_name!r}. Add it to scripts/processes/curated_flowcharts.py or run without --require-curated."
            )

    if curated_steps is not None:
        mermaid = make_mermaid_from_steps(process_name, curated_steps)
        nodes, edges = _count_linear_steps(curated_steps if curated_steps[-1]["role"] == "violet" else [*curated_steps, {"label": "Output", "role": "violet"}])  # type: ignore[list-item]
        notes = "Auto-generated process with curated (non-generic) flowchart steps and Crossref citations."
    else:
        mermaid = make_mermaid_26_node_template(process_name)
        nodes, edges = 26, 24
        notes = "Auto-generated process (template flowchart) with Crossref citations."

    sources = build_sources(process_name)

    payload: Dict[str, Any] = {
        "id": final_id,
        "name": process_name,
        "category": category,
        "subcategory": subcategory,
        "subcategory_name": subcategory_name,
        "description": f"{process_name} process visualization. This process flowchart outlines key steps, checks, and outputs.",
        "complexity": {
            "nodes": nodes,
            "edges": edges,
            "conditionals": 0,
            "logicGates": {"orGates": 0, "andGates": 0, "total": 0},
            "level": "medium",
            "detailLevel": "medium",
        },
        "colorScheme": COLOR_SCHEME,
        "mermaid": mermaid,
        "sources": sources,
        "keywords": [w for w in slugify(process_name).split("-") if w][:10],
        "relatedProcesses": [],
        "created": existing_created or created_date,
        "lastUpdated": created_date,
        "verified": False,
        "notes": notes,
    }

    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-dir", required=True, help="e.g. computer-science-processes-database")
    parser.add_argument("--category", required=True, help="e.g. computer_science")
    parser.add_argument("--plan", required=True, help="JSON file containing processes to add")
    parser.add_argument("--created-date", default="2026-01-15", help="YYYY-MM-DD")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing process JSONs (keeps same IDs/URLs, replaces content).",
    )
    parser.add_argument(
        "--curated",
        action="store_true",
        help="Use curated per-process Mermaid steps when available (prevents identical charts).",
    )
    parser.add_argument(
        "--require-curated",
        action="store_true",
        help="Fail if a process has no curated steps (prevents silently falling back to generic charts).",
    )
    args = parser.parse_args()

    db_dir = Path(args.db_dir)
    plan_path = Path(args.plan)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    items = plan.get("processes") or []

    created: List[Path] = []
    skipped = 0

    for item in items:
        # Accept either a human plan (subcategory+name) or a full overwrite plan
        # exported from metadata.json (explicit id included).
        subcat = item.get("subcategory") or ""
        name = item.get("name") or ""
        pid = item.get("id")

        if not subcat and isinstance(pid, str) and "-" in pid:
            subcat = pid.split("-", 1)[0]
        if not subcat:
            raise ValueError(f"Missing subcategory for plan item: {item}")
        if not name:
            # Worst-case fallback: use id to synthesize a display name
            name = (pid or subcat).replace("-", " ").replace("_", " ").title()

        subcat_name = item.get("subcategory_name") or subcat.replace("_", " ").title()
        p = write_process_json(
            db_dir=db_dir,
            category=args.category,
            subcategory=subcat,
            subcategory_name=subcat_name,
            process_name=name,
            process_id=pid,
            created_date=args.created_date,
            overwrite=args.overwrite,
            use_curated=args.curated or args.require_curated,
            require_curated=args.require_curated,
        )
        if p is None:
            skipped += 1
        else:
            created.append(p)
            # Be polite to Crossref
            time.sleep(0.2)

    print(f"Created {len(created)} new process JSON files; skipped {skipped} existing.")


if __name__ == "__main__":
    main()

