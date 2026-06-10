#!/usr/bin/env python3
"""Publish process-index.json and metadata.json from canonical JSON under processes/."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from mermaid_metrics import analyze_mermaid, index_row_from_process
from schema import normalize_process, subcategory_label, validate_process

SCRIPT_DIR = Path(__file__).resolve().parent
HF_ROOT = SCRIPT_DIR.parent.parent


def database_root(name: str) -> Path:
    return HF_ROOT / name


def load_config(db_root: Path) -> dict[str, Any]:
    config_path = db_root / "catalog_config.json"
    if config_path.exists():
        with config_path.open(encoding="utf-8") as fh:
            return json.load(fh)
    return {
        "name": db_root.name,
        "version": "1.0.0",
        "category": db_root.name.split("-")[0],
        "colorScheme": "5-color",
        "description": f"Process charts for {db_root.name}",
        "excludeSubcategories": ["graph_type_pilots"],
        "excludeIds": [],
    }


def iter_process_json(db_root: Path, config: dict[str, Any]) -> list[tuple[Path, dict[str, Any]]]:
    processes_dir = db_root / "processes"
    if not processes_dir.exists():
        return []

    exclude_subcats = set(config.get("excludeSubcategories") or [])
    exclude_ids = set(config.get("excludeIds") or [])
    results: list[tuple[Path, dict[str, Any]]] = []

    for path in sorted(processes_dir.rglob("*.json")):
        if "_archive" in path.parts:
            continue
        subcategory = path.parent.name
        if subcategory in exclude_subcats:
            continue
        with path.open(encoding="utf-8") as fh:
            doc = json.load(fh)
        doc_id = doc.get("id") or path.stem
        if doc_id in exclude_ids:
            continue
        doc["id"] = doc_id
        doc.setdefault("subcategory", subcategory)
        results.append((path, doc))
    return results


def enrich_from_html(db_root: Path, doc: dict[str, Any]) -> dict[str, Any]:
    if doc.get("mermaid"):
        return doc
    subcategory = doc["subcategory"]
    stem = doc["id"]
    html_path = db_root / "processes" / subcategory / f"{stem}.html"
    if not html_path.exists():
        return doc
    html = html_path.read_text(encoding="utf-8", errors="replace")
    mermaid = extract_mermaid(html)
    if mermaid:
        doc = dict(doc)
        doc["mermaid"] = mermaid
    return doc


def extract_mermaid(content: str) -> str | None:
    import html as html_lib
    import re

    patterns = [
        r'<div[^>]*class="mermaid"[^>]*>\s*(.*?)\s*</div>',
        r'<pre[^>]*class="mermaid"[^>]*>\s*(.*?)\s*</pre>',
        r"```mermaid\s*\n(.*?)```",
    ]
    blocks: list[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, content, re.DOTALL | re.IGNORECASE):
            text = html_lib.unescape(match.group(1).strip())
            if len(text) >= 20:
                blocks.append(text)
    if not blocks:
        return None
    if len(blocks) == 1:
        return blocks[0]
    return "\n\n%% additional_graph\n\n".join(blocks)


def metadata_process_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "subcategory": row["subcategory"],
        "subcategory_name": row["subcategory_name"],
        "complexity": row["complexity"],
        "nodes": row["nodes"],
        "edges": row["edges"],
        "orGates": row["orGates"],
        "andGates": row["andGates"],
        "conditionals": row["conditionals"],
        "notGates": row["notGates"],
        "loops": row["loops"],
        "totalGates": row["totalGates"],
        "domainContext": row["domainContext"],
        "verified": True,
        "curationStatus": "json_canonical",
    }


def publish_database(db_name: str, *, write_json_files: bool = True, enrich_html: bool = True) -> dict[str, Any]:
    db_root = database_root(db_name)
    config = load_config(db_root)
    today = date.today().isoformat()

    loaded = iter_process_json(db_root, config)
    normalized: list[dict[str, Any]] = []
    errors: list[str] = []

    for path, doc in loaded:
        if enrich_html:
            doc = enrich_from_html(db_root, doc)
        doc = normalize_process(
            doc,
            subcategory=doc["subcategory"],
            category=config.get("category", "mathematics"),
        )
        doc["subcategory_name"] = subcategory_label(doc["subcategory"])
        issues = validate_process(doc)
        if issues:
            errors.append(f"{path.relative_to(db_root)}: {', '.join(issues)}")
            continue
        normalized.append(doc)

    index_rows = [index_row_from_process(doc) for doc in normalized]
    index_rows.sort(key=lambda r: (r["subcategory"], r["name"].lower()))

    subcategory_counts = Counter(row["subcategory"] for row in index_rows)
    stats = {
        "totalNodes": sum(r["nodes"] for r in index_rows),
        "totalEdges": sum(r["edges"] for r in index_rows),
        "totalConditionals": sum(r["conditionals"] for r in index_rows),
        "totalOrGates": sum(r["orGates"] for r in index_rows),
        "totalLoops": sum(r["loops"] for r in index_rows),
        "totalAndGates": sum(r["andGates"] for r in index_rows),
        "totalNotGates": sum(r["notGates"] for r in index_rows),
        "totalGates": sum(r["totalGates"] for r in index_rows),
    }

    catalog = {
        "name": config.get("name", db_name),
        "version": config.get("version", "1.0.0"),
        "created": config.get("created", today),
        "lastUpdated": today,
        "category": config.get("category", "unknown"),
        "colorScheme": config.get("colorScheme", "5-color"),
        "description": config.get("description", ""),
        "totalProcesses": len(index_rows),
        "subcategories": len(subcategory_counts),
        "statistics": stats,
        "subcategoryCounts": dict(sorted(subcategory_counts.items())),
        "processes": index_rows,
    }
    for key in ("collectionStats", "domainHierarchy", "subcategoryToArxiv"):
        if key in config:
            catalog[key] = config[key]

    metadata = dict(catalog)
    metadata["processes"] = [metadata_process_row(r) for r in index_rows]

    if write_json_files:
        for path, doc in loaded:
            if doc["id"] not in {n["id"] for n in normalized}:
                continue
            full = next(d for d in normalized if d["id"] == doc["id"])
            out_path = db_root / "processes" / full["subcategory"] / f"{full['id']}.json"
            if enrich_html and not doc.get("mermaid") and full.get("mermaid"):
                out_path.write_text(json.dumps(full, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        (db_root / "process-index.json").write_text(
            json.dumps(catalog, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        (db_root / "metadata.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    return {
        "database": db_name,
        "published": len(index_rows),
        "skipped": len(errors),
        "errors": errors,
        "subcategoryCounts": dict(subcategory_counts),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        default="mathematics-processes-database",
        help="Database folder under huggingface-space/",
    )
    parser.add_argument("--dry-run", action="store_true", help="Report counts without writing files")
    parser.add_argument("--no-enrich", action="store_true", help="Do not pull mermaid from sibling HTML")
    args = parser.parse_args()

    result = publish_database(
        args.database,
        write_json_files=not args.dry_run,
        enrich_html=not args.no_enrich,
    )
    print(json.dumps(result, indent=2))
    if result["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
